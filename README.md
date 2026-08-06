# South Ramp

Django app that tracks airport ramp **locations**, the **cameras** at each
one, and the **images** those cameras upload. Two independent paths feed
images in: a small FTP server and a legacy-compatible HTTP endpoint.

Live at https://southramp.com/. Admin at https://southramp.com/southramp-admin/.
`/robots.txt` disallows all crawlers — this isn't meant to be indexed.

## Data model

- **Location** — `name`, `slug` (auto-generated from name), `hidden`,
  `order` (plain integer, lower sorts first; ties break on name), plus
  Dynamic DNS fields (see [Dynamic DNS](#dynamic-dns) below):
  `dynamic_dns_enabled`, `dynamic_dns_username` / `dynamic_dns_password`
  (12-character alphanumeric, auto-generated on save if left blank — same
  pattern as `Camera.ftp_username`/`ftp_password` below), `last_known_ip`,
  `ip_updated_at`.
- **Camera** — belongs to a Location. `name`, `slug` (unique per-Location,
  not globally — see the URL note below), `hidden`, `order`, plus
  identifiers used for ingestion:
  - `id` — UUID primary key, auto-generated and not directly editable
    (Django decides insert-vs-update by primary key value, so a plain
    "edit this field" doesn't rename a row — it either errors or creates
    a duplicate). To actually change one, select the camera in the admin
    list and use the **Change ID** action, which creates the new row,
    re-points its Images, and deletes the old row atomically.
  - `secret` — UUID, used in the HTTP upload URL. Editable, because
    onboarding an existing physical camera means typing in whatever
    secret is already baked into its firmware, not generating a new one.
  - `ftp_username` / `ftp_password` — 12-character alphanumeric, auto-generated
    on save if left blank, used for FTP login. Also editable, for the same
    reason.

  Plus Remote Pull fields (see [Remote Pull](#remote-pull) below):
  `remote_pull_enabled`, `remote_pull_use_location_ddns`, `remote_pull_url`,
  `remote_pull_timeout` (seconds, default 7); and Embed fields (see
  [Embedding](#embedding) below): `embed_enabled`, `embed_sizes`.
- **Image** — belongs to a Camera. `file`, `taken_at` (when it was
  uploaded — set by the server at upload time, not by the client).
- **EmbedImage** — a resized copy of an Image at one configured width, for
  embedding. See [Embedding](#embedding) below.
- **UnrecognizedUpload** — an HTTP upload whose secret didn't match any
  Camera. Kept around (with an image preview and a "Create camera" link)
  in admin so you can identify hardware that hasn't been onboarded yet.

`hidden` on a Location or Camera means "not listed on the front page" —
not "blocked". If you have the direct link (`/<location-slug>/<camera-slug>/`
or `/<location-slug>/`), it works regardless of the hidden flag. A
Location's detail page (`/<location-slug>/`) also always shows *all* of
its cameras, hidden or not, once you're looking at that specific
location.

A camera's public detail page lives at `/<location-slug>/<camera-slug>/`
rather than a bare `/camera/<slug>/` — camera slugs are only unique
*within* a Location (two Locations can each have a camera slugged `cam1`),
so the URL needs the Location to disambiguate. `/camera/<secret>/` is a
separate, unrelated path used only for uploads (see below) and never
shown to people.

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

## Dynamic DNS

Each Location's site router can report its current public IP so we always
know how to reach it, without us having to go poke someone to ask. This
piggybacks on the "Custom" Dynamic DNS service most routers (UniFi
included) already support — no VPN, no extra hardware.

The router speaks the old dyndns2 protocol: a plain HTTP GET with HTTP
Basic Auth, no request body. South Ramp exposes that at a fixed path:

```
GET https://southramp.com/nic/update?hostname=<anything>&myip=<ip>
Authorization: Basic <base64 username:password>
```

- `myip` is optional — if the router doesn't send it, the server falls
  back to the IP the request actually came from.
- `hostname` is accepted but ignored for lookup; the username alone
  identifies the Location (each Location's dyndns2 username/password is
  unique to it), so there's nothing else to disambiguate.
- Response body is `good <ip>` on success or `badauth` if the
  username/password don't match an enabled Location — same convention
  dyndns2 clients already expect.

**UniFi setup** (matches the Dynamic DNS dialog's fields): Service =
`Custom`, Hostname = anything (unused, e.g. the location's name), Username
/ Password = the values generated on that Location's admin page, Server =
`southramp.com`.

**Manual test:**

```
curl -u <username>:<password> "https://southramp.com/nic/update?myip=1.2.3.4"
```

A Location with `dynamic_dns_enabled` unchecked rejects updates with
`badauth`, same as a wrong password — flipping the checkbox is what
actually turns updates on, independent of whether credentials exist.

## Remote Pull

The flip side of "Writing an upload script" (below): instead of something
external pushing images to South Ramp, South Ramp can reach out and pull a
snapshot itself, directly from a camera's own snapshot URL — useful when a
camera is reachable straight from the server (e.g. over the location's
router) and there's no need for a separate script running on-site.

A cron job runs `manage.py pull_remote_images` every 2 minutes
(`scripts/pull_remote_images.sh`, installed in the `southramp` crontab).
For each Camera with `remote_pull_enabled` checked, it fetches
`remote_pull_url` (timing out after `remote_pull_timeout` seconds, default
7) and saves the result as a new `Image`, exactly like an FTP or HTTP
upload would.

If `remote_pull_use_location_ddns` is also checked, the URL's hostname is
replaced with the Location's `last_known_ip` (see
[Dynamic DNS](#dynamic-dns) above) before each fetch — for a camera behind
a router with a dynamic IP, point `remote_pull_url` at whatever
path/port/credentials the camera needs (e.g.
`http://placeholder/cgi-bin/api.cgi?cmd=Snap&channel=1`) and the actual
host gets swapped in at pull time. If the Location has no known IP yet,
that camera is skipped (logged, not treated as an error) until a DDNS
update arrives.

The cron wrapper uses `flock` so overlapping runs are a no-op instead of
piling up, and `timeout 5m` so a hung camera can't wedge the job forever —
plain, well-tested tools rather than hand-rolled locking/timeout logic.

## Embedding

A Camera with `embed_enabled` checked and `embed_sizes` set to a
comma-separated list of pixel widths (e.g. `400,800,1200`) gets a resized
JPEG generated at each of those widths every time it receives a new
image — whether that image arrived over FTP, HTTP upload, or Remote Pull,
since all three funnel through the same `save_camera_image()` call.
Resizing preserves aspect ratio (only the width is specified) and always
outputs JPEG regardless of the source format.

Each camera then has a stable embed URL per configured width:

```
GET https://southramp.com/embed/<camera-id>/<width>
```

e.g. `https://southramp.com/embed/6f0f27ea-6831-4958-a425-6e5d037678de/800`
— note the lack of a trailing slash, which is intentional (matches how
this was embedded on third-party pages previously). It's a plain
temporary (302) redirect to the actual resized JPEG's URL, so it's safe
to drop straight into an `<img src>` on another site — the browser
follows the redirect and caches against the real file, not this URL.

If the camera doesn't exist, doesn't have embedding enabled, has no
images yet, or just doesn't have one generated at that specific width
(e.g. it was requested before `embed_sizes` included it), the redirect
instead points at a static "Camera Unavailable" placeholder
(`static/cameras/img/camera-unavailable.jpg`) rather than 404ing — an
embedded `<img>` tag has no good way to react to an error response, so
this keeps it always resolving to *something* renderable.

`EmbedImage` rows are deleted (both the DB row and the file) whenever
their parent `Image` is cleaned up — see [Housekeeping](#housekeeping).

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
- **Dynamic DNS**: a Location's edit page has its own "Dynamic DNS"
  section — the enable checkbox, generated username/password, the
  endpoint URL to paste into the router, and the last IP/timestamp
  reported.
- **Remote Pull**: a Camera's edit page has its own "Remote Pull" section
  — the enable checkbox, the "use location DDNS" checkbox, the camera's
  snapshot URL, and the request timeout. See
  [Remote Pull](#remote-pull) above.
- **Embed**: a Camera's edit page has its own "Embed" section — the
  enable checkbox and the comma-separated list of widths. See
  [Embedding](#embedding) above.
- **Change ID**: select one Camera in the Camera list and use the
  "Change ID" action to safely change its primary key. See the `id`
  bullet under [Data model](#data-model) above for why this needs to be
  a dedicated action rather than an editable field.

## Housekeeping

A daily cron job (`southramp` user, 3:15am, see `crontab -l`) runs
`scripts/delete_old_images.sh`, which deletes `Image` rows (and their
files, and any `EmbedImage` rows/files generated from them) older than 5
days via `manage.py delete_old_images`.

A second cron job (`southramp` user, every 2 minutes) runs
`scripts/pull_remote_images.sh` — see [Remote Pull](#remote-pull) above.

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
