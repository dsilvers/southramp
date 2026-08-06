from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cameras', '0007_embedimage_camera_embed_enabled_camera_embed_sizes_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='camera',
            name='ftp_password',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AlterField(
            model_name='camera',
            name='ftp_username',
            field=models.CharField(blank=True, max_length=100, unique=True),
        ),
    ]
