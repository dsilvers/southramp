# South Ramp

Django app that tracks airport ramp **locations**, the **cameras** at each
one, and the **images** those cameras upload. Two independent paths feed
images in: a small FTP server and a legacy-compatible HTTP endpoint.

Live at https://southramp.com/. Admin at https://southramp.com/southramp-admin/.

## Data model

- **Location** — `name`, `slug` (auto-generated from name), `hidden`,
  `order` (plain integer, lower sorts first; ties break on name).
- **Camera** — belongs to a Location. `name`, `slug`, `hidden`, `order`,
  plus identifiers used for ingestion:
  - `id` — UUID primary key, generated once, never changes.
  - `secret` — UUID, used in the HTTP upload URL. Editable, because
    onboarding an existing physical camera means typing in whatever
    secret is already baked into its firmware, not generating a new one.
  - `ftp_username` / `ftp_password` — 12-character alphanumeric, auto-generated
    on save if left blank, used for FTP login. Also editable, for the same
    reason.
- **Image** — belongs to a Camera. `file`, `taken_at` (when it was
  uploaded — set by the server at upload time, not by the client).
- **UnrecognizedUpload** — an HTTP upload whose secret didn't match any
  Camera. Kept around (with an image preview and a "Create camera" link)
  in admin so you can identify hardware that hasn't been onboarded yet.

`hidden` on a Location or Camera means "not listed on the front page" —
not "blocked". If you have the direct link (`/camera/<slug>/` or
`/<location-slug>/`), it works regardless of the hidden flag. A Location's
detail page (`/<location-slug>/`) also always shows *all* of its cameras,
hidden or not, once you're looking at that specific location.

## Ingesting images

Two ways an image gets into the system, both converting to JPEG via
Pillow if the upload isn't already one, and both rejecting anything that
doesn't decode as a real image (a corrupt/partial upload just gets a
`200 OK` back with nothing saved — no point cluttering the discovery
list with a client's failed upload).

**FTP** — `southramp.com:2121`, login with a camera's
`ftp_username`/`ftp_password`, upload any image file. Passive mode is
required (port range configured via `FTP_PASSIVE_PORTS`, currently
60000-60100, opened in UFW).

**HTTP** — `POST` a multipart file to `/camera/<camera-secret>/` (trailing
slash optional — both are accepted, since some devices don't send one and
a 301 redirect would silently turn their POST into a bodyless GET). The
file field must be named `image`. See `scripts/camera_upload_example.py`
for a minimal working example. If the secret doesn't match any camera,
the upload is kept as an `UnrecognizedUpload` instead of an `Image`, and
shows up in admin so you can create the matching Camera.

## Writing an upload script

Most cameras don't speak this system's protocol natively, so the usual
setup is a small script running on a machine that *can* reach the camera
(often the camera's own local network), which pulls a snapshot and
forwards it on. The shape is always the same three steps:

1. **Get an image from the camera.** Most IP cameras expose a snapshot
   URL over their own local HTTP API (check the camera's manual for a
   "snapshot" or "CGI" endpoint). Fetch it with `requests.get()` rather
   than shelling out to `wget`/`curl` via `os.system()` — string-formatting
   a URL into a shell command is a command-injection risk the moment any
   part of that URL comes from somewhere less trustworthy than a constant
   you typed yourself, and `requests` also saves you from parsing HTTP
   errors out of a subprocess's exit code.
2. **POST it to South Ramp.** `POST` to `https://southramp.com/camera/<secret>/`
   (get `<secret>` from that camera's page in
   `/southramp-admin/cameras/camera/`) as `multipart/form-data` with the
   file under the field name **`image`** — that field name is required,
   the server only looks for that one. A trailing slash is optional. A
   successful upload is a bare `200 OK` with no body worth parsing; treat
   anything else as failure.
3. **Run it on a schedule.** A cron job or systemd timer on whatever
   machine can see the camera, at whatever interval makes sense for that
   camera.

```python
import time
import requests

CAMERA_SECRET = "00000000-0000-0000-0000-000000000000"
CAMERA_SNAPSHOT_URL = "http://10.0.0.3/cgi-bin/api.cgi?cmd=Snap&channel=1"
UPLOAD_URL = f"https://southramp.com/camera/{CAMERA_SECRET}/"

resp = requests.get(CAMERA_SNAPSHOT_URL, timeout=10)
resp.raise_for_status()

filename = f"{int(time.time())}.jpg"
try:
    upload_resp = requests.post(UPLOAD_URL, files={"image": (filename, resp.content)}, timeout=30)
    upload_resp.raise_for_status()
except requests.RequestException as exc:
    print(f"Error uploading file: {exc}")
```

A few things that are easy to get wrong the first time:

- **The field name really must be `image`.** Anything else (`file`,
  `photo`, `upload`) is silently ignored server-side — the request still
  returns `200 OK` (there's no way for the server to know you meant to
  attach something), it just won't have created an `Image`.
- **Wrong or unrecognized secret ≠ error.** A `200 OK` doesn't confirm the
  secret matched a real camera — an unrecognized secret is filed as an
  `UnrecognizedUpload` instead (see Admin, below) rather than rejected, so
  a typo'd secret can go unnoticed for a while. Check the camera's page
  after the first upload to confirm an `Image` actually showed up.
- **Corrupt/partial downloads are dropped, not stored.** If step 1
  produced a truncated or non-image response (camera timeout, wrong URL,
  etc.), the server detects it isn't a real image and discards it — you
  won't see it in admin at all. If uploads seem to be going nowhere, check
  that `CAMERA_SNAPSHOT_URL` is actually returning a valid image first
  (`file` on the saved bytes, or just open it).
- Don't reuse `os.system()`/`subprocess` with strings built from external
  input for either step — build one is enough to want the habit for the
  next script too.

A ready-to-copy version of the above lives at
`scripts/camera_upload_example.py`.

## Admin

- Create/edit Locations and Cameras (name, order, hidden, and — for
  cameras — location, secret, FTP credentials) at
  `/southramp-admin/cameras/`.
- Reorder from the list view: `order` is an editable column, change
  several values and hit Save once at the bottom.
- **Unrecognized uploads**: `/southramp-admin/cameras/unrecognizedupload/`
  shows a thumbnail and a "Create camera" link that pre-fills the secret
  on a new Camera's add form.

## Housekeeping

A daily cron job (`southramp` user, 3:15am, see `crontab -l`) runs
`scripts/delete_old_images.sh`, which deletes `Image` rows (and their
files) older than 5 days via `manage.py delete_old_images`.

## Running locally

```
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in real values, then export them or use a tool like direnv
python manage.py migrate
python manage.py runserver
```

See `.env.example` for the full list of settings (and `config/settings.py`
for how each one is used).

The FTP server (`ftpserver/server.py`) needs the same environment plus
`DJANGO_SETTINGS_MODULE=config.settings`; run it with
`python -m ftpserver.server`.

## Deployment

Runs on `southramp.com` as the `southramp` user, under two systemd
services:

- `southramp-django.service` — gunicorn on `127.0.0.1:8001`, fronted by
  nginx (`/etc/nginx/sites-available/southramp.com`, see
  `deploy/southramp.conf` in this repo for the source of truth on that
  config).
- `southramp-ftp.service` — the FTP server.

Service unit files and the nginx vhost live in `deploy/`; they're copied
to `/etc/systemd/system/` and `/etc/nginx/sites-available/southramp.com`
respectively (with the certbot-managed SSL block preserved on top of the
latter — see the file for what certbot appended).

Both use the pyenv virtualenv `southramp-django` and read secrets from
`/home/southramp/django/.env` (not committed — see `EnvironmentFile=` in
the `.service` files for what's expected in it).
