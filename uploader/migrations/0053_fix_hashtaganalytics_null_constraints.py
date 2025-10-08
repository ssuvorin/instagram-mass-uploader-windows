# Generated manually to fix null constraints on HashtagAnalytics fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('uploader', '0051_merge_all_migrations'),
    ]

    operations = [
        # Ensure all nullable fields have proper defaults
        migrations.AlterField(
            model_name='hashtaganalytics',
            name='total_followers',
            field=models.BigIntegerField(default=0, blank=True, help_text="Current follower count"),
        ),
        migrations.AlterField(
            model_name='hashtaganalytics',
            name='total_shares',
            field=models.BigIntegerField(default=0, blank=True, help_text="Total shares/reposts"),
        ),
        migrations.AlterField(
            model_name='hashtaganalytics',
            name='growth_rate',
            field=models.FloatField(default=0.0, blank=True, help_text="Follower growth rate (%)"),
        ),
        migrations.AlterField(
            model_name='hashtaganalytics',
            name='instagram_stories_views',
            field=models.BigIntegerField(default=0, blank=True, help_text="Instagram stories views"),
        ),
        migrations.AlterField(
            model_name='hashtaganalytics',
            name='instagram_reels_views',
            field=models.BigIntegerField(default=0, blank=True, help_text="Instagram reels views"),
        ),
        migrations.AlterField(
            model_name='hashtaganalytics',
            name='youtube_subscribers',
            field=models.BigIntegerField(default=0, blank=True, help_text="YouTube subscribers"),
        ),
        migrations.AlterField(
            model_name='hashtaganalytics',
            name='youtube_watch_time',
            field=models.BigIntegerField(default=0, blank=True, help_text="YouTube watch time (minutes)"),
        ),
        migrations.AlterField(
            model_name='hashtaganalytics',
            name='tiktok_video_views',
            field=models.BigIntegerField(default=0, blank=True, help_text="TikTok video views"),
        ),
        migrations.AlterField(
            model_name='hashtaganalytics',
            name='tiktok_profile_views',
            field=models.BigIntegerField(default=0, blank=True, help_text="TikTok profile views"),
        ),
        migrations.AlterField(
            model_name='hashtaganalytics',
            name='total_accounts',
            field=models.IntegerField(default=0, blank=True, help_text="Total number of accounts analyzed"),
        ),
        migrations.AlterField(
            model_name='hashtaganalytics',
            name='avg_videos_per_account',
            field=models.FloatField(default=0.0, blank=True, help_text="Average videos per account"),
        ),
        migrations.AlterField(
            model_name='hashtaganalytics',
            name='max_videos_per_account',
            field=models.IntegerField(default=0, blank=True, help_text="Maximum videos per account"),
        ),
        migrations.AlterField(
            model_name='hashtaganalytics',
            name='avg_views_per_video',
            field=models.FloatField(default=0.0, blank=True, help_text="Average views per video"),
        ),
        migrations.AlterField(
            model_name='hashtaganalytics',
            name='max_views_per_video',
            field=models.BigIntegerField(default=0, blank=True, help_text="Maximum views per video"),
        ),
        migrations.AlterField(
            model_name='hashtaganalytics',
            name='avg_views_per_account',
            field=models.FloatField(default=0.0, blank=True, help_text="Average views per account"),
        ),
        migrations.AlterField(
            model_name='hashtaganalytics',
            name='max_views_per_account',
            field=models.BigIntegerField(default=0, blank=True, help_text="Maximum views per account"),
        ),
        migrations.AlterField(
            model_name='hashtaganalytics',
            name='avg_likes_per_video',
            field=models.FloatField(default=0.0, blank=True, help_text="Average likes per video"),
        ),
        migrations.AlterField(
            model_name='hashtaganalytics',
            name='max_likes_per_video',
            field=models.BigIntegerField(default=0, blank=True, help_text="Maximum likes per video"),
        ),
        migrations.AlterField(
            model_name='hashtaganalytics',
            name='avg_likes_per_account',
            field=models.FloatField(default=0.0, blank=True, help_text="Average likes per account"),
        ),
        migrations.AlterField(
            model_name='hashtaganalytics',
            name='max_likes_per_account',
            field=models.BigIntegerField(default=0, blank=True, help_text="Maximum likes per account"),
        ),
    ]

