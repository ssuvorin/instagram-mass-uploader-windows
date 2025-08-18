from django.contrib import admin
from .models import WorkerNode, TaskLock


@admin.register(WorkerNode)
class WorkerNodeAdmin(admin.ModelAdmin):
	list_display = ('name', 'base_url', 'capacity', 'is_active', 'last_heartbeat')
	list_filter = ('is_active',)
	search_fields = ('name', 'base_url')


@admin.register(TaskLock)
class TaskLockAdmin(admin.ModelAdmin):
	list_display = ('kind', 'task_id', 'created_at')
	list_filter = ('kind',)
	search_fields = ('task_id',)
	ordering = ('-created_at',)


