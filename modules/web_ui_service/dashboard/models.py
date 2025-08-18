from django.db import models
from django.utils import timezone


class WorkerNode(models.Model):
	name = models.CharField(max_length=120, blank=True, default="")
	base_url = models.URLField(unique=True)
	capacity = models.IntegerField(default=1)
	is_active = models.BooleanField(default=True)
	last_heartbeat = models.DateTimeField(null=True, blank=True)
	last_error = models.TextField(blank=True, default="")
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['-is_active', '-capacity', 'name']

	def __str__(self) -> str:
		return f"{self.name or self.base_url} (cap={self.capacity}, active={self.is_active})"

	def mark_heartbeat(self, ok: bool, error: str | None = None) -> None:
		self.last_heartbeat = timezone.now()
		self.is_active = ok
		if error:
			self.last_error = error
		self.save(update_fields=['last_heartbeat', 'is_active', 'last_error', 'updated_at'])


class TaskLock(models.Model):
	KIND_CHOICES = [
		('bulk', 'Bulk Upload'),
		('bulk_login', 'Bulk Login'),
		('warmup', 'Warmup'),
		('avatar', 'Avatar'),
		('bio', 'Bio'),
		('follow', 'Follow'),
		('proxy_diag', 'Proxy Diagnostics'),
		('media_uniq', 'Media Uniq'),
	]
	kind = models.CharField(max_length=32, choices=KIND_CHOICES)
	task_id = models.IntegerField()
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		unique_together = ('kind', 'task_id')
		indexes = [models.Index(fields=['kind', 'task_id'])]

	def __str__(self) -> str:
		return f"Lock({self.kind}#{self.task_id})"


