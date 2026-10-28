# Igala Music — proposed product and implementation plan

Status: the first local implementation is built. Production deployment and private storage configuration remain pending. See `MUSIC_SETUP.md` for setup, validation, and current limits.

## Direction

Build a dedicated music section within IgalaHeritage at `/music/`: a curated listening experience for Igala music, artists, and releases. Reuse the existing Django accounts, Supabase PostgreSQL database, and established visual identity. Treat Spotify as a reference for listening behaviour, while giving the product its own cultural identity.

Confirmed launch requirements:

- Free listening without signing in.
- Sign in to like tracks and create private playlists.
- Staff uploads and signed-in artist submissions are included. Staff review artist submissions before publication.
- No songs have been supplied. The catalogue starts empty; generated audio is used only in isolated testing.
- Playback continues within Music and stops when navigating outside it.
- Stream only music for which publication and streaming permission have been recorded.
- No subscriptions, advertising, offline playback, or download feature in the first release.

## Listening experience

| Screen | Purpose |
| --- | --- |
| Discover | One editorial feature, new releases, selected artists, and curated collections. All populated from real catalogue data. |
| Search | Search tracks, artists, and releases; filter by artist and genre. Paginate larger results. |
| Artist | Artwork, concise biography, credits, tracks, and releases. |
| Release | Cover, artist credits, release date, ordered track list, and play action. |
| Track | Shareable detail page with credits and a play action. |
| Your library | Liked tracks and private playlists for signed-in listeners. |
| Playlist | Ordered tracks, playback, and owner-only editing. |

Use the site's green and cream palette, Space Grotesk headings, IBM Plex Sans body text, and restrained monospace metadata. Let artwork and artist names carry the page. Avoid explanatory hero paragraphs, placeholder charts, fake play counts, and autoplay.

Desktop: compact music navigation, artwork-led discovery, readable track rows, and a bottom player. Mobile: condensed navigation, a bottom mini-player, and an expandable now-playing panel. Reserve page space so the player never covers controls or the footer.

Player requirements:

- Play/pause, seek, elapsed time, duration, next/previous, queue, shuffle, repeat, mute, and volume where supported.
- Exactly one active music audio element. Coordinate with existing pronunciation audio to avoid simultaneous playback.
- Playback continues between music screens through navigation inside a persistent music shell.
- Normal navigation outside the music section stops playback in the initial release. Continuous playback across the entire heritage site is a separate scope decision.
- Refresh restores the queue and playback position in a paused state. Never promise autoplay after refresh or guaranteed mobile background playback.
- Handle buffering, unavailable tracks, failed requests, expired playback URLs, and queue entries that have been unpublished.
- Keyboard-accessible controls, labelled sliders, visible focus, reduced motion, and adequate touch targets.

## Catalogue and data

Create a dedicated Django `music` app rather than adding music models to `main` or `library`. The table below is the original target model breakdown. In the first implementation, audio metadata and permission records live on `Track` and `MusicSubmission`, and featured artists use a many-to-many relationship. Separate asset and credit-role models can follow if needed.

| Model | Essential information |
| --- | --- |
| Artist | Name, unique slug, biography, artwork, publication status. |
| Release | Album/EP/single, title, artwork, credited artists, release date, status. |
| Track | Title, unique slug, optional release, track number, duration, genre, publication status. |
| TrackArtist | Track, artist, credit role, display order; supports collaborations. |
| AudioAsset | Private storage key, file size, detected format, duration, bitrate, validation state. |
| Genre | Name and slug, maintained by staff. |
| Playlist | Owner, title, visibility; private initially. |
| PlaylistItem | Playlist, track, stable position; enforce owner-only changes. |
| SavedTrack | User and track, unique together. |
| MusicPermission | Rights contact, permission evidence, permitted use, applicable dates, and review status. Evidence is private. |

Keep publication status separate from file validity. A valid file is not automatically approved for streaming. Staff can draft, publish, unpublish, and replace assets without changing shared track URLs. Search, playlist playback, and stream authorization must exclude unpublished material.

Add aggregated listening statistics later. Do not treat browser play-button clicks as verified streams or royalty accounting.

## Hosting and streaming

- Render runs Django, catalogue queries, account actions, and playback authorization.
- Supabase PostgreSQL stores music metadata and relationships, not audio bytes.
- Use dedicated storage for music assets. Keep uploads, permission evidence, and unreleased audio private; do not reuse the existing public media URL behaviour for private music.
- Proposed default: private published audio with short-lived playback URLs issued only after checking track availability. Public cover artwork can be cached independently.
- The browser downloads audio directly from storage. Django must not proxy entire songs.
- Validate HTTP range requests, seeking, content types, cross-origin behaviour, and URL renewal against the actual storage setup before committing to the delivery path.
- Signed URLs remain usable until expiry; unpublishing blocks new authorizations but is not an instant revocation mechanism for existing URLs. Establish an asset-removal procedure when needed.
- Start with validated, prepared MP3 files and one playback quality. Use a separate music upload policy instead of silently changing the current 20 MB limit for dictionary audio.
- For larger or unstable-network uploads, introduce authorized direct-to-storage resumable uploads and server-side final validation. Never expose storage service credentials to the browser.
- If automated conversion is needed later, add a background processing worker. Do not transcode inside web requests. Adaptive streaming and multiple bitrates follow demonstrated demand.

Render free-service sleep still affects initial pages and new Django requests. Direct storage delivery avoids routing audio through a sleeping web service, but does not make the application always available. Revisit always-on compute for a public music launch.

Bandwidth matters more than catalogue size: five minutes at 128 kbps is approximately 4.8 MB, so 1,000 complete plays transfer approximately 4.8 GB before artwork, retries, and other traffic. Confirm the account's current storage and transfer allowances before setting a launch budget.

## Content workflow

Initial staff workflow:

1. Create the artist and release records.
2. Record permission and upload prepared audio/artwork.
3. Validate actual audio format, size, duration, and playback; review credits.
4. Preview the unpublished track as an authorized staff member.
5. Publish explicitly. The track becomes searchable and playable.
6. Unpublish when necessary; prevent new playback authorizations and handle existing storage access according to the removal procedure.

Artist submissions are included in the first implementation, with private uploads, ownership checks, quotas, and pending/approved/rejected states. Approval is a staff action. Staff assign approved recordings to the correct published artist. A verified artist-claim workflow and separate artist-management dashboard remain future work.

## Build order and acceptance

1. **Catalogue foundation:** music app, schema, staff administration, storage isolation, permissions, and sample content in an isolated local database. Verify unpublished assets cannot be accessed through the app.
2. **First listening slice:** catalogue, artist and track/release screens, playback authorization, and the persistent player. Verify play, pause, seek, next, music-page navigation, and failure recovery on desktop and mobile.
3. **Discovery:** search, genre/artist filters, curated collections, pagination, deep links, and browser Back behaviour.
4. **Personal library:** liked tracks, private playlists, ordering, and persisted queues. Test ownership, duplicate actions, and unpublished playlist entries.
5. **Launch preparation:** real permission-approved catalogue, storage transfer checks, accessibility review, upload abuse limits, backups, playback-error monitoring, and a staging deployment before production.
6. **Artist platform later:** verified artist ownership claims, resumable uploads, a dedicated artist-management dashboard, and useful aggregate statistics. The basic submission and staff-review flow is already part of the first release.

Do not begin with subscriptions, payments, machine-learning recommendations, public social playlists, lyrics publishing, offline downloads, or automatic royalty calculations. Each requires separate product and operational decisions.

## Decisions confirmed by the user

1. Both staff uploads and artist submissions.
2. No existing songs; empty catalogue for launch preparation.
3. Free guest listening; accounts for uploads, likes, and private playlists.
4. Continuous playback within Music only.
5. Spotify-inspired browsing and listening patterns with original IgalaHeritage design and implementation.

## Platform references checked during planning

- Render free-service sleep and filesystem limits: https://render.com/docs/free
- Supabase public/private asset delivery and signed URL limitations: https://supabase.com/docs/guides/storage/serving/downloads
- Supabase resumable uploads: https://supabase.com/docs/guides/storage/uploads/resumable-uploads
- Supabase storage bandwidth: https://supabase.com/docs/guides/storage/serving/bandwidth

These are platform constraints, not a quote for this project's actual operating costs.
