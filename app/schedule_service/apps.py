from django.apps import AppConfig


class ScheduleServiceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'schedule_service'

    def ready(self) -> None:
        pass
