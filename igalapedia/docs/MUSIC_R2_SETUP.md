# Cloudflare R2 music storage

Django runs on Render and catalogue data stays in Supabase PostgreSQL. Music audio,
track covers, and submission covers use a private R2 bucket when
`MUSIC_STORAGE_PROVIDER=r2`. Artist/release images and other public uploads continue
to use the existing Supabase media backend. No new package or schema migration is
required for this storage switch.

## 1. Create the Cloudflare resources

1. Sign in to https://dash.cloudflare.com/ and select **Storage & databases > R2 >
   Overview**. Activate the R2 subscription if needed. It has a recurring free
   allowance, with paid usage beyond that allowance; review the billing screen.
2. Create a **Standard** bucket named `igala-music` (or another lowercase name).
3. Keep the bucket private. Leave the public `r2.dev` URL and public custom domains
   disabled. Django will issue temporary S3 signed URLs for approved playback.
4. On R2 Overview, under **Account Details**, select **Manage** beside API Tokens.
   Create an **Account API token**, if your account role permits it, named
   `igalapedia-music`. Select **Object Read & Write**, scoped only to this bucket.
5. Store the resulting **Access Key ID** and **Secret Access Key** securely. The
   secret is displayed only once. Use these S3 credentials, not the general
   Cloudflare API token string. Never commit them or paste them into chat.
6. Copy the account's **S3 API endpoint**. Usually it is
   `https://<ACCOUNT_ID>.r2.cloudflarestorage.com`. Jurisdiction-specific buckets
   have a different endpoint (for example `.eu.r2.cloudflarestorage.com`): copy the
   exact displayed endpoint. Do not append the bucket name or use a public URL.

## 2. Configure CORS

Select **igala-music > Settings > CORS Policy > Add CORS policy**. Use the JSON tab
and paste this policy, replacing the example website with your actual origin:

For the current production website, [r2-music-cors.json](r2-music-cors.json) is
ready to paste and allows `https://igalaheritage.onrender.com`.

```json
[
  {
    "AllowedOrigins": ["https://YOUR-SERVICE.onrender.com"],
    "AllowedMethods": ["GET", "HEAD"],
    "AllowedHeaders": ["Range", "If-Range"],
    "ExposeHeaders": ["Accept-Ranges", "Content-Range", "Content-Length"],
    "MaxAgeSeconds": 3600
  }
]
```

Add your custom website origin as another item in `AllowedOrigins` if applicable.
Origins include the scheme and optional port, with no path or trailing slash.
For local cloud-storage testing, add `http://127.0.0.1:8000` and/or
`http://localhost:8000` when those are the origins actually used. CORS does not
grant object access: a valid signed URL is still needed. Current uploads go
through authenticated Django forms; no browser PUT permission is required.

## 3. Configure Render

Open your web service's **Environment** page and add:

| Variable | Value |
| --- | --- |
| `MUSIC_STORAGE_PROVIDER` | `r2` |
| `R2_BUCKET_NAME` | `igala-music` |
| `R2_ENDPOINT_URL` | The account S3 endpoint copied above |
| `R2_ACCESS_KEY_ID` | R2 Access Key ID |
| `R2_SECRET_ACCESS_KEY` | R2 Secret Access Key |
| `R2_REGION_NAME` | `auto` |

Keep `DATABASE_URL`, `SUPABASE_*`, `AWS_*`, and `SECRET_KEY` as configured. R2
credentials belong only in `R2_*`: replacing the existing AWS credentials would
break Supabase image uploads. `MUSIC_STORAGE_BUCKET` is used only by the legacy
Supabase music backend, not R2.

Push the backend changes, then save the variables and redeploy. Existing Render
services need the variables entered manually; `sync: false` in `render.yaml`
does not fill secrets on an existing service.

Missing R2 variables leave storage unavailable rather than falling back to
Supabase, public URLs, or ambient AWS credentials. The empty catalogue and static
build do not require an R2 connection. Upload forms display the existing friendly
unavailable message until configuration is complete. New application processes
must start after changing storage settings.

## 4. Check configuration and playback

With the service environment available, run from `igalapedia/`:

```sh
python manage.py check_music_storage
python manage.py check_music_storage --remote
```

The first command validates settings offline. The second sends a read-only
`HeadBucket` request; it does not upload/delete files or access database records.
Neither prints credentials or signed URLs. On Render, use the service shell if
available. These commands use the normal cloud settings; local development
settings deliberately keep filesystem storage and are not a cloud readiness test.

Then use a recording you have permission to stream:

1. Upload a track through staff administration. Fill in artist and permission
   information, confirm rights, then publish it.
2. Confirm its audio object appears in R2, and that artist images still use
   Supabase. Uploading a file manually into R2 does not create a track record.
3. Open `/music/` as a guest. Play the track and seek forward/backward. The
   playback API should return a signed R2 URL; audio bytes go straight to R2.
4. Confirm an unsigned object request is denied. Signed URLs allow anyone holding
   the link to listen until expiry (one hour by default); they do not prevent
   copying a recording. Do not share these URLs in logs or screenshots.
5. Submit a track using a regular artist account. Verify it remains unavailable
   to guest playback until staff approve it. Staff and the submitting account can
   preview it through the existing protected preview route.

## Existing files and rollback

Changing providers does not copy files. Before switching a catalogue that already
has cloud uploads, copy all music audio and track/submission artwork from the old
private bucket into R2 **with the same object keys**. Database file fields store
these keys. Preserve the source until the switch is verified. Do not load local
SQLite fixture records into production as a migration strategy.

Setting `MUSIC_STORAGE_PROVIDER=supabase` restores the existing music backend,
which requires `MUSIC_STORAGE_BUCKET` and the Supabase storage credentials. Files
uploaded only to R2 must be copied back with the same keys before they can play
through that backend.

## Scope and verification

This implementation uses private S3 presigned GET URLs. It does not add a public
CDN hostname, Cloudflare Worker, automatic transcoding, direct browser uploads,
or a media migration. Cloudflare's presigned S3 URLs do not work on custom
domains; a future edge delivery layer requires separate implementation.

R2 transport tests use fake credentials and stubbed S3 responses, including signed
URL generation, bucket-scoped uploads without public ACLs, missing settings,
endpoint validation, and the read-only readiness command. Live R2 CORS, access,
playback, and seeking must be checked after the real bucket is configured.

Official references:

- https://developers.cloudflare.com/r2/get-started/
- https://developers.cloudflare.com/r2/api/tokens/
- https://developers.cloudflare.com/r2/examples/aws/boto3/
- https://developers.cloudflare.com/r2/buckets/cors/
- https://developers.cloudflare.com/r2/api/s3/presigned-urls/
- https://developers.cloudflare.com/r2/pricing/
