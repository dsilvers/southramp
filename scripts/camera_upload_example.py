#!/usr/bin/env python
"""
Minimal example: grab a snapshot from a camera and upload it to South Ramp.

Fill in CAMERA_SECRET (from the Camera's admin page) and CAMERA_SNAPSHOT_URL
(your camera's own snapshot/CGI endpoint), then run this on a schedule
(cron, systemd timer, whatever the camera's host machine already uses).
"""
import time

import requests

CAMERA_SECRET = "00000000-0000-0000-0000-000000000000"
CAMERA_SNAPSHOT_URL = "http://192.0.2.10/cgi-bin/api.cgi?cmd=Snap&channel=1&user=CHANGE_ME&password=CHANGE_ME"
UPLOAD_URL = f"https://southramp.com/camera/{CAMERA_SECRET}/"
IMAGE_FILE = "/tmp/southramp_snapshot.jpg"


def main():
    print("Downloading from camera...")
    resp = requests.get(CAMERA_SNAPSHOT_URL, timeout=10)
    resp.raise_for_status()
    with open(IMAGE_FILE, "wb") as f:
        f.write(resp.content)

    print("Uploading...")
    filename = f"{int(time.time())}.jpg"
    start = time.time()
    with open(IMAGE_FILE, "rb") as f:
        try:
            upload_resp = requests.post(UPLOAD_URL, files={"image": (filename, f)}, timeout=30)
            upload_resp.raise_for_status()
        except requests.RequestException as exc:
            print(f"Error uploading file: {exc}")
            return

    print(f"Done uploading, took {time.time() - start:.1f} seconds")


if __name__ == "__main__":
    main()
