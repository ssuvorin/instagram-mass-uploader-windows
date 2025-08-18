from django.db import migrations, models


class Migration(migrations.Migration):

	initial = True

	dependencies = []

	operations = [
		migrations.CreateModel(
			name='WorkerNode',
			fields=[
				('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
				('name', models.CharField(blank=True, default='', max_length=120)),
				('base_url', models.URLField(unique=True)),
				('capacity', models.IntegerField(default=1)),
				('is_active', models.BooleanField(default=True)),
				('last_heartbeat', models.DateTimeField(blank=True, null=True)),
				('last_error', models.TextField(blank=True, default='')),
				('created_at', models.DateTimeField(auto_now_add=True)),
				('updated_at', models.DateTimeField(auto_now=True)),
			],
			options={'ordering': ['-is_active', '-capacity', 'name']},
		),
		migrations.CreateModel(
			name='TaskLock',
			fields=[
				('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
				('kind', models.CharField(choices=[('bulk', 'Bulk Upload'), ('bulk_login', 'Bulk Login'), ('warmup', 'Warmup'), ('avatar', 'Avatar'), ('bio', 'Bio'), ('follow', 'Follow'), ('proxy_diag', 'Proxy Diagnostics'), ('media_uniq', 'Media Uniq')], max_length=32)),
				('task_id', models.IntegerField()),
				('created_at', models.DateTimeField(auto_now_add=True)),
			],
		),
		migrations.AddIndex(
			model_name='tasklock',
			index=models.Index(fields=['kind', 'task_id'], name='dashboard_t_kind_ta_2ab805_idx'),
		),
		migrations.AlterUniqueTogether(
			name='tasklock',
			unique_together={('kind', 'task_id')},
		),
	]


