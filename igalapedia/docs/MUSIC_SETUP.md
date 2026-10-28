# Igala Music: setup and operation

The `music` Django app provides guest listening, search, artist/release/track pages, private playlists, likes, staff uploads, and moderated artist submissions. No real songs or artist records are included. The interface is an original implementation using familiar music-player patterns; it does not use Spotify's catalogue, SDK, branding, or proprietary backend.

## Before production deployment

1. Install the updated requirements, including Mutagen for audio metadata validation.
2. Create a **private** Supabase Storage bucket dedicated to music, for example `music-private`. Do not make it public and do not add anonymous read or upload policies.
3. Set `MUSIC_STORAGE_BUCKET` to that bucket's name in Render. The existing Supabase S3 endpoint, region, and storage credentials must have access to it. No new credentials belong in source control.
4. Set the bucket's file-size limit to at least the application's 25 MB audio limit. Track and submission cover images use this private bucket too. Artist and release artwork use the existing media storage.
5. Deploy through the project's existing build process and apply migrations with `python manage.py migrate`. This includes the new `music` migrations.
6. Validate playback and seeking using a permission-approved test recording on staging before opening uploads to artists.

`render.yaml` declares the new environment variable. `.env.example` documents it. The app can render an empty music catalogue without that variable, but music uploads and playback require working storage. It deliberately refuses to use the existing public media bucket for music.

The Supabase bucket's actual privacy setting must be checked in the dashboard. Generating a signed URL does not make a public bucket private.

## Local development

Use `--settings=igalapedia.development_settings` for a persistent local SQLite database (`db.sqlite3`) and filesystem uploads under `media/`. Music audio and submitted covers live under `media/music/`, which is ignored by Git. These settings do not change the normal Supabase configuration and cannot run on Render.

```powershell
.\env\Scripts\python.exe manage.py migrate --settings=igalapedia.development_settings
.\env\Scripts\python.exe manage.py import_local_music "C:\path\song.mp3" --title "Song title" --artist "Artist name" --publish-for-local-testing --settings=igalapedia.development_settings
.\env\Scripts\python.exe manage.py runserver --settings=igalapedia.development_settings
```

The import copies the recording; the source remains untouched. MPEG files containing valid MP3 audio are stored with an `.mp3` extension. The publish flag permits local listening tests only; without it, imports remain drafts. Importing the same title and artist again is rejected. Files copied into the folder manually do not create catalogue records. Local media URLs are served only by Django's development server; never deploy these test records or settings as production streaming permission.

## Staff uploads

1. In Django admin, create an Artist and mark it published when ready.
2. Optionally create a Release, select its artist and type, and mark it published.
3. Add a Track: title, artist, audio, optional release/genre/artwork, and rights-holder contact or permission reference.
4. Review streaming permission and select **Rights confirmed**. Keep supporting context in the private rights notes.
5. Publish the Track. Audio duration is read from the file, not entered by the uploader. A published track must have validated audio, a published artist, and a published release if assigned.
6. Select **Is featured** to feature a real track on Discover.

No publication bulk action bypasses the normal validation. Artist names are not required to be unique; profiles are identified by unique slugs so staff can distinguish people with similar names.

## Artist submissions

- Existing Django accounts can submit at `/music/submit/`.
- A submission includes title, artist name, genre, audio, optional cover artwork, rights contact, permission details, and a required streaming-permission declaration.
- Audio and submitted artwork remain in private storage. The pending submission is visible only to its uploader and authorized staff; it is excluded from search and playback.
- `/music/submissions/` shows the uploader's statuses and review notes.
- Staff review at Django admin → Music submissions → **Review submission**. Preview audio, verify permission and credits, and select the correct published artist profile. An artist name supplied by an uploader does not grant control of an existing profile.
- Approval requires music-submission change permission and track-add permission. It publishes one track and retains the review record. Repeated approval is rejected.
- Rejection requires a review note visible to the uploader. Rejected submissions remain for audit; they are not automatically deleted.
- The initial limit is 10 pending submissions and 10 submissions per account per day. These are application quotas, not a complete anti-abuse or identity-verification system.

Supported audio: MP3, M4A, and WAV up to 25 MB and two hours. MP3 is the most straightforward playback choice. M4A compatibility depends on the encoded audio codec. There is no automatic transcoding. Invalid format headers, mismatched extensions, unreadable metadata, and invalid durations are rejected. Audio metadata validation does not replace a human listening review.

## Playback architecture

- `/music/api/tracks/<id>/play/` checks publication and streaming permission before returning a temporary audio URL. It is available to guests and sends no private permission notes or storage credentials.
- Audio downloads directly from storage; Django does not proxy song bytes.
- `PrivateMusicStorage` uses the existing S3-compatible client with signed URLs, no public ACL, and a separate bucket. The default expiry is one hour (`MUSIC_PLAYBACK_URL_SECONDS`).
- A single `<audio>` element sits outside `#music-content`. The browser replaces only music content when navigating between music screens. Track/artist links in the player use the same navigation.
- Queue, repeat/shuffle choice, and playback position are kept in session storage. Refresh restores them paused. Playback starts only through a listener action.
- Queue controls include next/previous, removal, clear, shuffle, repeat all/one, seeking, volume, and mute. Mobile has a mini-player and an expandable now-playing view with keyboard focus handling.
- Navigating outside Music performs normal navigation and stops playback. The main navigation's Music link stays inside the persistent shell when already listening.
- The player refreshes playback authorization once after an eligible playback error. Unpublished tracks cannot obtain a new URL. Already issued URLs remain valid until expiry; unpublishing is not instant revocation of existing storage URLs.

## Listening library

- Listening and browsing require no account.
- Liking tracks and managing playlists require login and CSRF-protected POST requests.
- Playlists are private. Only their owner can view, rename, delete, add/remove songs, or reorder tracks.
- Likes and playlist membership are unique per user/track or playlist/track. Add and like actions are idempotent.
- Unpublished tracks are omitted from personal libraries and playback queues when content is fetched or authorized again.

## Verification and current limits

Run `python -B manage.py test --settings=igalapedia.test_settings --noinput` for isolated regression tests. These settings use an in-memory database and in-memory files; they do not touch production uploads, Supabase, or SMTP.

Browser checks used generated WAV tones in a temporary local database to verify guest playback, navigation continuity, seeking, next-track control, the queue, likes, playlists, live search, and the mobile expanded player. Those tones are not included in application fixtures.

Actual Supabase signed-URL delivery, byte-range seeking, and expiry behaviour still require a configured private bucket and staging validation. Render free-tier sleep still affects opening the site and new backend requests. No production deployment or storage-bucket changes were made by this implementation.

This release intentionally excludes payments, advertising, offline downloads, adaptive bitrate streaming, automated transcoding, public playlists, verified artist ownership claims, and royalty accounting. Staff can moderate artist submissions now; a separate verified-artist management dashboard can follow.
