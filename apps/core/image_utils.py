"""Image optimization helpers.

Shared by content/academics/core models so every image upload is resized and
re-compressed on save. This keeps originals from being served in full; the
biggest win is downscaling large phone/camera photos that would otherwise be
sent to every visitor.

Only the uploaded file is modified in place (same path/format), so existing
template references (``obj.image.url``) keep working with no extra setup.
"""
from io import BytesIO

from django.core.files.base import ContentFile

from PIL import Image, ImageOps


def optimize_image(image_field, max_width=1600, max_height=1600, quality=82):
    """Resize and re-compress a Django ``ImageFieldFile`` in place.

    Args:
        image_field: An ``ImageFieldFile`` (e.g. ``obj.image``) or None.
        max_width/max_height: Maximum dimensions; larger images are downscaled
            while preserving aspect ratio.
        quality: JPEG/WebP quality (0-95).

    Safely no-ops when the field is empty, unreadable, or not a raster image
    (e.g. SVG), so a bad/unsupported upload never breaks model ``save()``.
    """
    if not image_field:
        return
    try:
        image_field.seek(0)
    except Exception:
        return

    try:
        img = Image.open(image_field)
    except Exception:
        return

    # Keep the original format/extension unless it's not Web-friendly.
    fmt = (getattr(img, "format") or "JPEG").upper()
    if fmt == "SVG":
        return

    # Apply EXIF orientation so photos aren't rotated by the browser.
    try:
        img = ImageOps.exif_transpose(img)
    except Exception:
        pass

    if fmt not in ("JPEG", "JPG", "PNG", "WEBP"):
        # Fall back to JPEG for unsupported formats.
        fmt = "JPEG"

    # Downscale if larger than the target, preserving aspect ratio.
    if img.width > max_width or img.height > max_height:
        img.thumbnail((max_width, max_height), Image.LANCZOS)

    # JPEG/WebP don't support alpha; flatten transparency onto white.
    if fmt in ("JPEG", "JPG", "WEBP") and img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[-1])
        img = background
    elif img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")

    buffer = BytesIO()
    if fmt in ("JPEG", "JPG"):
        img.save(buffer, "JPEG", quality=quality, optimize=True, progressive=True)
    elif fmt == "WEBP":
        img.save(buffer, "WEBP", quality=quality, method=4)
    else:
        img.save(buffer, "PNG", optimize=True)

    buffer.seek(0)
    try:
        image_field.save(image_field.name, ContentFile(buffer.read()), save=False)
    except Exception:
        return
