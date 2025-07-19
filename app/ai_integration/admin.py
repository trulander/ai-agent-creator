import json
import pickle

from django.contrib import admin
from django.utils.safestring import mark_safe

from ai_integration.models import (
    AIStateBlobs,
    AIStateWrites,
    AIStateStorage,
    AIStateDefault,
    AIAgentTask,
)


# Register your models here.
@admin.register(AIStateBlobs)
class AIStateBlobsAdmin(admin.ModelAdmin):
    pass

@admin.register(AIStateWrites)
class AIStateWritesAdmin(admin.ModelAdmin):
    pass

@admin.register(AIStateStorage)
class AIStateStorageAdmin(admin.ModelAdmin):
    pass

@admin.register(AIStateDefault)
class AIStateDefaultAdmin(admin.ModelAdmin):
    readonly_fields = ["unpacked_data"]

    def unpacked_data(self, obj):
        try:
            raw_data = pickle.loads(obj.data)
            formatted = json.dumps(raw_data, indent=4, ensure_ascii=False)
            return mark_safe(f"<pre>{formatted}</pre>")
        except Exception as e:
            return f"Ошибка при десериализации: {e}"

    unpacked_data.short_description = "Данные (распакованные)"

@admin.register(AIAgentTask)
class AIAgentTaskAdmin(admin.ModelAdmin):
    list_display = ("id", "project_theme", "status", "scheduled_time", "ai_model")
    search_fields = ("project_theme", "status", "scheduled_time", "ai_model")
