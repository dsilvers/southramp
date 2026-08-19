import os

from pyftpdlib.handlers import FTPHandler


class CameraUploadHandler(FTPHandler):
    def log_cmd(self, cmd, arg, respcode, respstr):
        # pyftpdlib only logs a small whitelist of commands (CWD, MKD, etc)
        # at INFO by default, so most of an FTP session — STOR, PASV, PORT,
        # TYPE, and whatever else these undocumented cheap cameras send — is
        # normally invisible outside DEBUG. Log everything, since there's no
        # vendor documentation to predict what a given camera will do.
        if cmd == "PASS":
            arg = "*" * 6
        self.log(f"{cmd} {arg} {respcode} {respstr!r}".strip())

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
