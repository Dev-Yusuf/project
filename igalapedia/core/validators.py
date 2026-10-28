"""Upload type and size checks used by public and admin model forms.

These checks do not constitute malware scanning. Serve uploads from a separate
media origin rather than the application's authenticated origin.
"""
from pathlib import Path

from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError


def _header(upload, extensions, max_bytes):
    if upload.size > max_bytes:
        raise ValidationError(f'File must be no larger than {max_bytes // (1024 * 1024)} MB.')
    extension = Path(upload.name).suffix.lower()
    if extension not in extensions:
        raise ValidationError('Unsupported file extension.')
    position = upload.tell()
    try:
        upload.seek(0)
        header = upload.read(16)
    finally:
        upload.seek(position)
    return extension, header


def validate_pdf_upload(upload):
    _, header = _header(upload, {'.pdf'}, 25 * 1024 * 1024)
    if not header.startswith(b'%PDF-'):
        raise ValidationError('Please upload a PDF file.')


def validate_audio_upload(upload):
    extension, header = _header(upload, {'.mp3', '.wav', '.ogg', '.m4a', '.flac'}, 20 * 1024 * 1024)
    valid = {
        '.mp3': header.startswith(b'ID3') or (len(header) >= 2 and header[0] == 255 and header[1] & 224 == 224),
        '.wav': header.startswith(b'RIFF') and header[8:12] == b'WAVE',
        '.ogg': header.startswith(b'OggS'),
        '.m4a': header[4:8] == b'ftyp',
        '.flac': header.startswith(b'fLaC'),
    }
    if not valid[extension]:
        raise ValidationError('The file contents do not match the selected audio format.')


def validate_image_upload(upload):
    extension, _ = _header(upload, {'.jpg', '.jpeg', '.png', '.gif', '.webp'}, 5 * 1024 * 1024)
    position = upload.tell()
    try:
        upload.seek(0)
        image = Image.open(upload)
        expected = {'.jpg': 'JPEG', '.jpeg': 'JPEG', '.png': 'PNG', '.gif': 'GIF', '.webp': 'WEBP'}
        if image.format != expected[extension] or image.width * image.height > 20_000_000:
            raise ValidationError('Unsupported image format or dimensions (maximum 20 million pixels).')
        image.verify()
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError,
            EOFError, Image.DecompressionBombError) as exc:
        raise ValidationError('Please upload a valid image.') from exc
    finally:
        upload.seek(position)
