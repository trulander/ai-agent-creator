import os
from celery import Celery
from django.conf import settings

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_agent_creator.settings')

app = Celery('ai_agent_creator')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a 'CELERY_' prefix.
# app.config_from_object('django.conf:settings', namespace='CELERY')
app.conf.update(**settings.CELERY_CONFIGURATION)
# Load task modules from all registered Django app configs.
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self) -> None:
    print(f'Request: {self.request!r}') 