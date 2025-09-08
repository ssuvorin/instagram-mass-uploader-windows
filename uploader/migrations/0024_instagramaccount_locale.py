from django.db import migrations, models


ALLOWED = {"ru_BY", "en_IN", "es_CL", "es_MX", "pt_BR"}


def backfill_locale(apps, schema_editor):
    InstagramAccount = apps.get_model('uploader', 'InstagramAccount')
    for acc in InstagramAccount.objects.all().only('id', 'locale'):
        try:
            val = (acc.locale or '').strip()
        except Exception:
            val = ''
        if val not in ALLOWED:
            InstagramAccount.objects.filter(id=acc.id).update(locale='ru_BY')


class Migration(migrations.Migration):
    dependencies = [
        ('uploader', '0023_instagramaccount_client_hashtaganalytics'),
    ]

    operations = [
        migrations.AddField(
            model_name='instagramaccount',
            name='locale',
            field=models.CharField(default='ru_BY', help_text='Dolphin-style locale, e.g. ru_BY en_IN es_CL es_MX pt_BR', max_length=5),
        ),
        migrations.RunPython(backfill_locale, migrations.RunPython.noop),
    ]


