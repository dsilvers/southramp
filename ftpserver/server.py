import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from pyftpdlib.servers import FTPServer  # noqa: E402

from . import config  # noqa: E402
from .authorizer import DjangoCameraAuthorizer  # noqa: E402
from .handler import CameraUploadHandler  # noqa: E402


def main():
    authorizer = DjangoCameraAuthorizer(media_root=config.FTP_MEDIA_ROOT)

    handler = CameraUploadHandler
    handler.authorizer = authorizer
    handler.passive_ports = config.PASSIVE_PORTS
    handler.permit_foreign_addresses = True

    server = FTPServer((config.FTP_HOST, config.FTP_PORT), handler)
    server.serve_forever()


if __name__ == "__main__":
    main()
