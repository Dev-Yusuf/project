import math
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from mutagen import File, MutagenError
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4
from mutagen.wave import WAVE


def audio_metadata(upload):
    if upload.size > settings.MUSIC_MAX_UPLOAD_BYTES:
        raise ValidationError('Music files must be 25 MB or smaller.')
    extension = Path(upload.name).suffix.lower()
    formats = {'.mp3': MP3, '.m4a': MP4, '.wav': WAVE}
    if extension not in formats:
        raise ValidationError('Upload an MP3, M4A, or WAV file.')
    position = upload.tell()
    try:
        upload.seek(0)
        audio = File(upload)
        if not isinstance(audio, formats[extension]):
            raise ValidationError('The audio content does not match its file extension.')
        duration = audio.info.length
        if not math.isfinite(duration) or not 0 < duration <= 7200:
            raise ValidationError('Upload playable audio with a duration below two hours.')
        return max(1, round(duration))
    except (MutagenError, OSError, ValueError, EOFError) as exc:
        raise ValidationError('The audio could not be read. Upload a valid music file.') from exc
    finally:
        upload.seek(position)


def validate_music_audio(upload):
    # Existing storage objects were checked on upload; avoid downloading on every edit.
    if getattr(upload, '_committed', False):
        return
    audio_metadata(upload)
