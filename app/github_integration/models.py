from django.db import models

# Create your models here.
class Repository(models.Model):
    name: str = models.CharField(max_length=255, unique=True)
    url: str = models.URLField(max_length=500)
    github_token: str = models.CharField(max_length=255)
    github_username: str = models.CharField(max_length=255)
    github_email: str = models.CharField(max_length=255)
    last_activity_date: models.DateField = models.DateField(null=True, blank=True)

    def __str__(self) -> str:
        return self.name


class ProjectTheme(models.Model):
    name: str = models.CharField(max_length=255, unique=True)
    system_prompt: str = models.TextField("Начальный промпт для AI")
    repository: Repository = models.ForeignKey(Repository, on_delete=models.DO_NOTHING, null=True, blank=True)

    def __str__(self) -> str:
        return self.name
