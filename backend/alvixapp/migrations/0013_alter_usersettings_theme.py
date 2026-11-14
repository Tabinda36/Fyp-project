from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('alvixapp', '0012_avatarsettings'),
    ]

    operations = [
        migrations.AlterField(
            model_name='usersettings',
            name='theme',
            field=models.CharField(
                choices=[('Dark', 'Dark'), ('Light', 'Light')],
                default='Dark',
                max_length=10,
            ),
        ),
    ]
