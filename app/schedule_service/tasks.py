import random
from datetime import timedelta, datetime

from celery import shared_task
from celery.utils.log import get_task_logger

from django.utils import timezone

from ai_integration.models import AIAgentTask, AIAgentPrompts, StatusesAIAgentTask
from ai_integration.tasks import run_ai_agent
from schedule_service.models import ActivitySchedule



logger = get_task_logger(__name__)

@shared_task(name="run_scheduled_ai_tasks")
def run_scheduled_ai_tasks():
    now = timezone.now()
    pending_tasks = AIAgentTask.objects.filter(
        scheduled_time__lte=now, status=StatusesAIAgentTask.PENDING.value
    )

    for task in pending_tasks:
        task.status = StatusesAIAgentTask.RUNNING.value
        task.save()
        run_ai_agent.apply_async(
            kwargs={
                "project_theme_id": task.project_theme_id,
                "ai_agent_task_id": task.id,
            },
            # retry_policy={
            #     "max_retries": 2,
            #     "interval_start": 60,
            #     "interval_step": 60
            # },
        )

@shared_task(name="schedule_ai_tasks")
def schedule_ai_tasks():
    tomorrow = timezone.now().date() + timedelta(days=1)
    day_name = tomorrow.strftime("%a")

    schedules = ActivitySchedule.objects.filter(days_of_week__contains=day_name)

    for schedule in schedules:
        existing_tasks = AIAgentTask.objects.filter(
            activity_schedule=schedule, scheduled_time__date=tomorrow
        ).count()

        if existing_tasks >= schedule.count_runs:
            continue

        # Создаём timezone-aware datetime
        start_time = timezone.make_aware(
            datetime.combine(tomorrow, schedule.start_time)
        )
        end_time = timezone.make_aware(
            datetime.combine(tomorrow, schedule.end_time)
        )
        time_diff = (end_time - start_time).seconds // 60
        interval = time_diff // max(schedule.count_runs, 1)

        tasks = []
        for i in range(schedule.count_runs):
            prompt_parts = []
            if i == 0:
                prompt_parts.append(AIAgentPrompts.PLAN_FOR_DAY.format(count_runs=schedule.count_runs))
                prompt_parts.append(AIAgentPrompts.DO_PLAN_FEATURES.format(count_runs=schedule.count_runs))
                prompt_parts.append(AIAgentPrompts.CREATE_NEW_BRANCH.value)
                # prompt_parts.append(AIAgentPrompts.ADD_FEATURE.value)
            else:
                prompt_parts.append(AIAgentPrompts.CONTINUE.value)
            if i == schedule.count_runs - 1 or schedule.count_runs == 1:
                prompt_parts.append(AIAgentPrompts.DO_MERGE_ALL.value)




            random_minutes = random.randint(i * interval, (i + 1) * interval)
            schedule_time = start_time + timedelta(minutes=random_minutes)

            tasks.append(
                AIAgentTask(
                    project_theme=schedule.project_theme,
                    activity_schedule=schedule,
                    prompt=", ".join(prompt_parts),
                    status=StatusesAIAgentTask.PENDING.value,
                    created_at=timezone.now(),  # Реальное время создания
                    scheduled_time=schedule_time,  # Время планируемого запуска
                    ai_model=schedule.ai_model,
                )
            )

        AIAgentTask.objects.bulk_create(tasks)

