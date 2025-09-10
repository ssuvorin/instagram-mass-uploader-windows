# Generated manually for CalculationHistory model

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('cabinet', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CalculationHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('volume_millions', models.FloatField()),
                ('platforms', models.JSONField(default=list)),
                ('countries', models.JSONField(default=list)),
                ('currency', models.CharField(default='RUB', max_length=3)),
                ('own_badge', models.BooleanField(default=False)),
                ('own_content', models.BooleanField(default=False)),
                ('pilot', models.BooleanField(default=False)),
                ('vip_percent', models.FloatField(default=0.0)),
                ('urgent', models.BooleanField(default=False)),
                ('peak_season', models.BooleanField(default=False)),
                ('exclusive_content', models.BooleanField(default=False)),
                ('base_price_per_view', models.FloatField()),
                ('tier_multiplier', models.FloatField()),
                ('platform_multiplier', models.FloatField()),
                ('discounts_percent', models.FloatField()),
                ('surcharges_percent', models.FloatField()),
                ('market_discount_percent', models.FloatField()),
                ('final_cost_rub', models.FloatField()),
                ('final_cost_usd', models.FloatField()),
                ('calculation_data', models.JSONField()),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('agency', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='calculations', to='cabinet.agency')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='calculations', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='calculationhistory',
            index=models.Index(fields=['user', '-created_at'], name='cabinet_cal_user_id_fd8459_idx'),
        ),
        migrations.AddIndex(
            model_name='calculationhistory',
            index=models.Index(fields=['agency', '-created_at'], name='cabinet_cal_agency__b5d65a_idx'),
        ),
    ]
