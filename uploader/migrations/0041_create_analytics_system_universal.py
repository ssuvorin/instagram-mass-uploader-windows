# Generated manually for Windows compatibility
# This migration creates the entire analytics system and works independently

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cabinet', '0005_calculationhistory_client_name'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Create ClientAnalytics model
        migrations.CreateModel(
            name='ClientAnalytics',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('social_network', models.CharField(choices=[('INSTAGRAM', 'Instagram'), ('YOUTUBE', 'YouTube'), ('TIKTOK', 'TikTok')], help_text='Social network platform', max_length=20)),
                ('total_posts', models.IntegerField(default=0, help_text='Total number of posts/videos')),
                ('total_views', models.BigIntegerField(default=0, help_text='Total views across all posts')),
                ('total_likes', models.BigIntegerField(default=0, help_text='Total likes across all posts')),
                ('total_comments', models.BigIntegerField(default=0, help_text='Total comments across all posts')),
                ('total_shares', models.BigIntegerField(default=0, help_text='Total shares across all posts')),
                ('total_followers', models.BigIntegerField(default=0, help_text='Total followers count')),
                ('growth_rate', models.FloatField(default=0.0, help_text='Growth rate percentage')),
                ('instagram_stories_views', models.BigIntegerField(blank=True, default=0, help_text='Instagram stories views')),
                ('instagram_reels_views', models.BigIntegerField(blank=True, default=0, help_text='Instagram reels views')),
                ('youtube_subscribers', models.BigIntegerField(blank=True, default=0, help_text='YouTube subscribers count')),
                ('youtube_watch_time', models.BigIntegerField(blank=True, default=0, help_text='YouTube watch time in minutes')),
                ('tiktok_video_views', models.BigIntegerField(blank=True, default=0, help_text='TikTok video views')),
                ('tiktok_profile_views', models.BigIntegerField(blank=True, default=0, help_text='TikTok profile views')),
                ('hashtag', models.CharField(help_text='Hashtag without #', max_length=100)),
                ('notes', models.TextField(blank=True, help_text='Additional notes')),
                ('is_manual', models.BooleanField(default=False, help_text='Whether this is manually entered data')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('client', models.ForeignKey(help_text='Client this analytics belongs to', on_delete=django.db.models.deletion.CASCADE, related_name='client_analytics', to='cabinet.client')),
                ('created_by', models.ForeignKey(blank=True, help_text='User who created this analytics entry', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_analytics', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Client analytics',
                'verbose_name_plural': 'Client analytics',
            },
        ),
        
        # Create HashtagAnalytics model
        migrations.CreateModel(
            name='HashtagAnalytics',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('social_network', models.CharField(choices=[('INSTAGRAM', 'Instagram'), ('YOUTUBE', 'YouTube'), ('TIKTOK', 'TikTok')], help_text='Social network platform', max_length=20)),
                ('hashtag', models.CharField(help_text='Hashtag without #', max_length=100)),
                ('analyzed_medias', models.IntegerField(default=0, help_text='Number of analyzed media posts')),
                ('total_views', models.BigIntegerField(default=0, help_text='Total views across all posts')),
                ('total_likes', models.BigIntegerField(default=0, help_text='Total likes across all posts')),
                ('total_comments', models.BigIntegerField(default=0, help_text='Total comments across all posts')),
                ('total_shares', models.BigIntegerField(default=0, help_text='Total shares across all posts')),
                ('total_followers', models.BigIntegerField(default=0, help_text='Total followers count')),
                ('growth_rate', models.FloatField(default=0.0, help_text='Growth rate percentage')),
                ('average_views', models.FloatField(default=0.0, help_text='Average views per post')),
                ('engagement_rate', models.FloatField(default=0.0, help_text='Engagement rate (likes+comments+shares)/views')),
                ('instagram_stories_views', models.BigIntegerField(blank=True, default=0, help_text='Instagram stories views')),
                ('instagram_reels_views', models.BigIntegerField(blank=True, default=0, help_text='Instagram reels views')),
                ('youtube_subscribers', models.BigIntegerField(blank=True, default=0, help_text='YouTube subscribers count')),
                ('youtube_watch_time', models.BigIntegerField(blank=True, default=0, help_text='YouTube watch time in minutes')),
                ('tiktok_video_views', models.BigIntegerField(blank=True, default=0, help_text='TikTok video views')),
                ('tiktok_profile_views', models.BigIntegerField(blank=True, default=0, help_text='TikTok profile views')),
                ('notes', models.TextField(blank=True, help_text='Additional notes')),
                ('is_manual', models.BooleanField(default=False, help_text='Whether this is manually entered data')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('client', models.ForeignKey(blank=True, help_text='Client this analytics belongs to', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='hashtag_analytics', to='cabinet.client')),
                ('created_by', models.ForeignKey(blank=True, help_text='User who created this analytics entry', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_hashtag_analytics', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Hashtag analytics',
                'verbose_name_plural': 'Hashtag analytics',
            },
        ),
        
        # Add advanced account metrics to HashtagAnalytics
        migrations.AddField(
            model_name='hashtaganalytics',
            name='total_accounts',
            field=models.IntegerField(default=0, help_text='Total number of accounts'),
        ),
        migrations.AddField(
            model_name='hashtaganalytics',
            name='avg_videos_per_account',
            field=models.FloatField(default=0.0, help_text='Average videos per account'),
        ),
        migrations.AddField(
            model_name='hashtaganalytics',
            name='max_videos_per_account',
            field=models.IntegerField(default=0, help_text='Maximum videos per account'),
        ),
        migrations.AddField(
            model_name='hashtaganalytics',
            name='avg_views_per_video',
            field=models.FloatField(default=0.0, help_text='Average views per video'),
        ),
        migrations.AddField(
            model_name='hashtaganalytics',
            name='max_views_per_video',
            field=models.IntegerField(default=0, help_text='Maximum views per video'),
        ),
        migrations.AddField(
            model_name='hashtaganalytics',
            name='avg_views_per_account',
            field=models.FloatField(default=0.0, help_text='Average views per account'),
        ),
        migrations.AddField(
            model_name='hashtaganalytics',
            name='max_views_per_account',
            field=models.IntegerField(default=0, help_text='Maximum views per account'),
        ),
        migrations.AddField(
            model_name='hashtaganalytics',
            name='avg_likes_per_video',
            field=models.FloatField(default=0.0, help_text='Average likes per video'),
        ),
        migrations.AddField(
            model_name='hashtaganalytics',
            name='max_likes_per_video',
            field=models.IntegerField(default=0, help_text='Maximum likes per video'),
        ),
        migrations.AddField(
            model_name='hashtaganalytics',
            name='avg_likes_per_account',
            field=models.FloatField(default=0.0, help_text='Average likes per account'),
        ),
        migrations.AddField(
            model_name='hashtaganalytics',
            name='max_likes_per_account',
            field=models.IntegerField(default=0, help_text='Maximum likes per account'),
        ),
    ]
