import os
import random

from celery import shared_task
from celery.utils.log import get_task_logger
from django.db.models import Q
from django.utils import timezone

from ai_integration.ai_service import AIService

from ai_integration.models import AIAgentTask, StatusesAIAgentTask
from ai_integration.helpers.ai_model_enum import AIModels

from schedule_service.models import ActivitySchedule
from github_integration.models import Repository, ProjectTheme

logger = get_task_logger(__name__)


@shared_task(name="run_ai_agent", bind=True)
def run_ai_agent(self, project_theme_id: int, ai_agent_task_id: str = None) -> None:
    try:
        project_theme = ProjectTheme.objects.get(id=project_theme_id)
        repository = project_theme.repository
        task = AIAgentTask.objects.filter(id=ai_agent_task_id).last()
        if not task:
            logger.error(f"AI Agent Task:{ai_agent_task_id} for project:{project_theme_id} not found")
            raise AIAgentTask.DoesNotExist
        if task.status == StatusesAIAgentTask.DONE.value:
            return f"Задача в статусе Done, пропускаем выполнение"


        try:
            model = AIModels(task.ai_model)
        except ValueError:
            logger.error(f"AI Model:{task.ai_model} for project:{project_theme_id} not found, using default {AIModels.GEMINI_2_0_FLASH.value}")
            model = AIModels.GEMINI_2_0_FLASH

        ai_service = AIService(
            system_prompt=project_theme.system_prompt,
            chat_id=f"{project_theme.name}-{repository.name}",
            github_token=repository.github_token,
            github_username=repository.github_username,
            github_email=repository.github_email,
            repo_url=repository.url,
            model=model
        )

        ai_service.invoke(human_message=task.prompt or "Продолжи")
        task.status = StatusesAIAgentTask.DONE.value
        task.save()

    except AIAgentTask.DoesNotExist:
        # Если задача не найдена, завершаем без повтора
        raise Exception(f"run_ai_agent Task:{ai_agent_task_id} for project:{project_theme_id} not found")
    except Exception as e:
        logger.error(f"Exception occurred genegate_ai_code: {e}")
        # При любой ошибке обновляем статус на ERROR
        task = AIAgentTask.objects.get(id=ai_agent_task_id)
        task.status = StatusesAIAgentTask.ERROR.value
        task.save()
        # # Инициируем повтор, если не исчерпаны попытки
        # raise self.retry(exc=e)
        raise e

