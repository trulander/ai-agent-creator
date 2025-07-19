from django.contrib import admin
from .models import ActivitySchedule
from github_integration.models import Repository, ProjectTheme


@admin.register(Repository)
class RepositoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'url', 'last_activity_date')
    search_fields = ('name', 'url')

@admin.register(ProjectTheme)
class ProjectThemeAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name', 'system_prompt')

@admin.register(ActivitySchedule)
class ActivityScheduleAdmin(admin.ModelAdmin):
    list_display = ('project_theme', 'days_of_week', 'start_time', 'end_time')
    list_filter = ('days_of_week', 'project_theme')
