import os

from pyftpdlib.handlers import FTPHandler


class CameraUploadHandler(FTPHandler):

    def on_file_received(self, file_path):
        from cameras.models import Camera
        from cameras.utils import InvalidImageError, save_camera_image

        camera = Camera.objects.filter(id=self.camera_id).first()
        if camera is None:
            os.remove(file_path)
            return

        try:
            with open(file_path, "rb") as fh:
                save_camera_image(camera, fh, os.path.basename(file_path))
        except InvalidImageError:
            pass

        os.remove(file_path)

    def on_incomplete_file_received(self, file_path):
        if os.path.exists(file_path):
            os.remove(file_path)
