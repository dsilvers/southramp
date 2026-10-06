import cameras.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cameras', '0008_alter_camera_ftp_password_alter_camera_ftp_username'),
    ]

    operations = [
        migrations.AddField(
            model_name='image',
            name='thumbnail',
            field=models.ImageField(blank=True, upload_to=cameras.models.camera_image_upload_to),
        ),
    ]
