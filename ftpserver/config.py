import os

FTP_HOST = os.environ.get("FTP_HOST", "0.0.0.0")
FTP_PORT = int(os.environ.get("FTP_PORT", "2121"))

_passive_range = os.environ.get("FTP_PASSIVE_PORTS", "60000-60100")
_lo, _hi = (int(x) for x in _passive_range.split("-"))
PASSIVE_PORTS = range(_lo, _hi + 1)

FTP_MEDIA_ROOT = os.environ.get("FTP_MEDIA_ROOT", os.path.join(os.getcwd(), "mediafiles"))
