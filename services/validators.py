"""Input validation for uploads and user-supplied fields."""
from django.conf import settings
from rest_framework.exceptions import ValidationError

ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp"}


def validate_image(upload):
    if upload is None:
        return None
    max_bytes = settings.MAX_IMAGE_UPLOAD_MB * 1024 * 1024
    if upload.size > max_bytes:
        raise ValidationError({"image": f"Image exceeds {settings.MAX_IMAGE_UPLOAD_MB} MB limit."})
    name = (upload.name or "").lower()
    if not any(name.endswith(e) for e in ALLOWED_EXT):
        raise ValidationError({"image": "Only JPG, PNG or WEBP images are accepted."})
    if upload.content_type not in settings.ALLOWED_IMAGE_TYPES:
        raise ValidationError({"image": "Unsupported content type."})
    data = upload.read()
    upload.seek(0)
    try:  # verify the bytes really are an image
        from io import BytesIO

        from PIL import Image

        img = Image.open(BytesIO(data))
        img.verify()
        if img.width * img.height > 40_000_000:
            raise ValidationError({"image": "Image resolution too large."})
    except ImportError:
        # Pillow optional: fall back to magic-number check
        if not (data[:3] == b"\xff\xd8\xff" or data[:8] == b"\x89PNG\r\n\x1a\n" or data[8:12] == b"WEBP"):
            raise ValidationError({"image": "File is not a valid image."})
    except ValidationError:
        raise
    except Exception:
        raise ValidationError({"image": "File is not a valid image."})
    return data


def clean_float(value, name, lo, hi):
    try:
        v = float(value)
    except (TypeError, ValueError):
        raise ValidationError({name: "Must be a number."})
    if not lo <= v <= hi:
        raise ValidationError({name: f"Must be between {lo} and {hi}."})
    return v


def clean_text(value, name, max_len):
    v = (value or "").strip()
    if len(v) > max_len:
        raise ValidationError({name: f"Maximum {max_len} characters."})
    return v
