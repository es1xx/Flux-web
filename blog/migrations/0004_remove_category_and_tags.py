# Generated manually for Category/Tag removal

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0003_profile_cooldowns'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='post',
            name='category',
        ),
        migrations.RemoveField(
            model_name='post',
            name='tags',
        ),
        migrations.DeleteModel(
            name='Category',
        ),
        migrations.DeleteModel(
            name='Tag',
        ),
    ]
