import logging
import os

from pyftpdlib.authorizers import AuthenticationFailed

logger = logging.getLogger("ftpserver.auth")


class DjangoCameraAuthorizer:
    """Authenticates FTP logins against Camera.ftp_username/ftp_password rows.

    pyftpdlib's FTPHandler duck-types its `authorizer` attribute (no common
    base class is exported by this pyftpdlib version), so this implements
    the same method surface as DummyAuthorizer without subclassing it.
    """

    def __init__(self, media_root):
        self.media_root = media_root

    def _get_camera(self, username):
        from cameras.models import Camera

        return Camera.objects.filter(ftp_username=username).first()

    def validate_authentication(self, username, password, handler):
        # Reject blank credentials outright rather than relying on no Camera
        # row ever having a blank ftp_username — filter(ftp_username="")
        # would otherwise match one if a future data path (bulk import,
        # fixture, raw SQL) ever bypassed Camera.save()'s auto-generation.
        if not username or not password:
            logger.warning(
                "FTP auth failed: missing credentials from %s", handler.remote_ip
            )
            raise AuthenticationFailed("Invalid username/password")

        camera = self._get_camera(username)
        if camera is None or camera.ftp_password != password:
            logger.warning(
                "FTP auth failed: invalid credentials for username=%r from %s",
                username,
                handler.remote_ip,
            )
            raise AuthenticationFailed("Invalid username/password")
        handler.camera_id = str(camera.id)

    def get_home_dir(self, username):
        camera = self._get_camera(username)
        home = os.path.join(self.media_root, "ftp_incoming", str(camera.id))
        os.makedirs(home, exist_ok=True)
        return home

    def has_user(self, username):
        return self._get_camera(username) is not None

    def has_perm(self, username, perm, path=None):
        return perm in "elradfmwMT"

    def get_perms(self, username):
        return "elradfmwMT"

    def get_msg_login(self, username):
        return "Southramp camera FTP ready."

    def get_msg_quit(self, username):
        return "Bye."

    def impersonate_user(self, username, password):
        pass

    def terminate_impersonation(self, username):
        pass
