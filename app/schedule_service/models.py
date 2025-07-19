from django.db import models

from ai_integration.helpers.ai_model_enum import AIModels
from github_integration.models import ProjectTheme


class ActivitySchedule(models.Model):
    project_theme = models.ForeignKey(
        ProjectTheme, on_delete=models.CASCADE, related_name="activity_schedules"
    )
    days_of_week = models.CharField(
        max_length=100,
        help_text="Comma-separated list of days (e.g., Mon,Tue,Wed)",
    )
    start_time = models.TimeField()
    end_time = models.TimeField()
    count_runs = models.IntegerField(default=0)
    ai_model = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Which model will be using by default for these tasks",
        choices=[(model.value, model.name) for model in AIModels],
    )

    def __str__(self) -> str:
        return f"{self.project_theme.name} Schedule"

