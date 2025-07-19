from enum import Enum

from django.db import models
from django.utils import timezone

from ai_integration.helpers.ai_model_enum import AIModels
from github_integration.models import ProjectTheme
from schedule_service.models import ActivitySchedule



class AIState(models.Model):
    id = None
    data = None
    class Meta:
        abstract = True


class AIStateBlobs(AIState):
    id = models.CharField(max_length=255, unique=True, primary_key=True)
    data = models.BinaryField()


class AIStateWrites(AIState):
    id = models.CharField(max_length=255, unique=True, primary_key=True)
    data = models.BinaryField()


class AIStateStorage(AIState):
    id = models.CharField(max_length=255, unique=True, primary_key=True)
    data = models.BinaryField()


class AIStateDefault(AIState):
    id = models.CharField(max_length=255, unique=True, primary_key=True)
    data = models.BinaryField()


class StatusesAIAgentTask(models.Choices):
    DONE = "DONE"
    RUNNING = "RUNNING"
    PENDING = "PENDING"
    ERROR = "ERROR"
    CANCELLED = "CANCELLED"


class AIAgentPrompts(Enum):
    # ADD_FEATURE = ("Добавь новую небольшую фичу. "
    #                "Фича должна быть завершена в рамках этого запроса. "
    #                "Измени не более 2-3 файлов и не пиши более 50 строк кода. "
    #                "Коммить каждый файл отдельно сразу после изменения. ")

    CREATE_NEW_BRANCH = ("Создай 1 новую ветку от main и переключись на неё. В этой ветке ты делаешь свои запланированные задачи из todo_list. Название веток за тобой. ")

    DO_PLAN_FEATURES = ("Еще раз, сейчас тебе нужно придумать {count_runs} задачи на {count_runs} дня вперед, обнови их в своем todo_list(update_todo_list). "
                        "За сегодня делаешь только 1 задачу, не выполняй все задачи из списка сразу. "
                        "Коммить каждый файл отдельно сразу после изменения. ")

    DO_MERGE_ALL = ("В конце создай pull request(create_pull_request) для текущей ветки и смержи его в main(merge_pull_request_and_checkout). "
                    "Перед этим проверь, что все изменения закоммичены. "
                    "Как все изменения cмержишь, удали ветку с выполненными задачами(delete_branch). ")

    CONTINUE = ("Продолжи работу над текущими задачами(tasks). "
                "Если ты не завершил предыдущую задачу, заверши ее и приступай к следующей 1 новой задаче. "
                "Заверши её в этой итерации. ")

    PLAN_FOR_DAY = ("Новый план: придумай и запиши в todolist {count_runs} задачи (tasks) на несколько дней вперед. Соблюдай правила (Работа со списком задач), прочитай документацию. "
                    "Каждая задача может включать как фичи, рефакторинг кода, обновление документации.., etc придумай сам что можно сделать в проекте. "
                    "Задачи должны быть небольшими. "
                    "Когда ты планируешь фичи, рефакторинг, ..etc, не распыляйся и не трогай больше 2-3 файлов за раз. "
                    "Запиши эти {count_runs} задачи(tasks) в свой todolist (update_todo_list). "
                    "За сегодня ты должен будешь сделать ТОЛЬКО 1 задачу из твоего списка. "
                    "Еще раз, 1 задача за 1 день, т.е сегодня ты делаешь только 1 задачу. Потом спроси 'делать ли дальше?' и все, жди ответ от "
                    "пользователя и не выполняй остальные задачи пока не получишь сообщение от пользователя что делать дальше. ")

    def format(self, **kwargs):
        return self.value.format(**kwargs)


class AIAgentTask(models.Model):
    id = models.AutoField(primary_key=True)
    project_theme = models.ForeignKey(to=ProjectTheme, on_delete=models.CASCADE, blank=True, null=True)
    activity_schedule = models.ForeignKey(to=ActivitySchedule, on_delete=models.DO_NOTHING, blank=True, null=True)
    prompt = models.TextField()
    status = models.CharField(max_length=255, blank=True, null=True, choices=StatusesAIAgentTask)
    created_at = models.DateTimeField(default=timezone.now)  # Истинное время создания
    scheduled_time = models.DateTimeField(null=True, blank=True)  # Время планируемого запуска
    ai_model = models.CharField(max_length=255, blank=True, null=True, choices=[(model.value, model.name) for model in AIModels])

