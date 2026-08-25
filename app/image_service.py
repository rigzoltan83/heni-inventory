from io import BytesIO
from pathlib import Path
from uuid import uuid4

from flask import current_app
from PIL import Image, ImageOps, UnidentifiedImageError
from werkzeug.utils import secure_filename


ALLOWED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
}

MAX_IMAGE_SIZE = (
    1600,
    1600,
)

JPEG_QUALITY = 84
WEBP_QUALITY = 84


class ImageUploadError(Exception):
    pass


def _get_output_extension(image):
    if image.mode in (
        "RGBA",
        "LA",
    ):
        return ".png"

    return ".webp"


def _prepare_image(
    file_storage,
):
    try:
        image = Image.open(
            file_storage.stream
        )

        image = ImageOps.exif_transpose(
            image
        )

        image.thumbnail(
            MAX_IMAGE_SIZE,
            Image.Resampling.LANCZOS,
        )

        return image

    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
    ) as exc:
        raise ImageUploadError(
            "A kiválasztott fájl nem feldolgozható kép."
        ) from exc


def save_item_image(file_storage):
    if (
        file_storage is None
        or not file_storage.filename
    ):
        raise ImageUploadError(
            "Nincs kiválasztott képfájl."
        )

    original_filename = (
        file_storage.filename.strip()
    )

    safe_original = secure_filename(
        original_filename
    )

    suffix = (
        Path(safe_original)
        .suffix
        .lower()
    )

    if suffix not in ALLOWED_EXTENSIONS:
        raise ImageUploadError(
            "Csak JPG, JPEG, PNG vagy WebP kép tölthető fel."
        )

    image = _prepare_image(
        file_storage
    )

    output_extension = (
        _get_output_extension(
            image
        )
    )

    filename = (
        f"{uuid4().hex}"
        f"{output_extension}"
    )

    upload_folder = Path(
        current_app.config[
            "ITEM_UPLOAD_FOLDER"
        ]
    )

    upload_folder.mkdir(
        parents=True,
        exist_ok=True,
    )

    target = (
        upload_folder
        / filename
    )

    try:
        if output_extension == ".png":
            image.save(
                target,
                format="PNG",
                optimize=True,
            )

        else:
            if image.mode not in (
                "RGB",
                "L",
            ):
                image = image.convert(
                    "RGB"
                )

            image.save(
                target,
                format="WEBP",
                quality=WEBP_QUALITY,
                method=6,
            )

    except OSError as exc:
        raise ImageUploadError(
            "A kép mentése sikertelen."
        ) from exc

    finally:
        image.close()

    return (
        filename,
        original_filename,
    )


def delete_item_image_file(filename):
    if not filename:
        return

    upload_folder = Path(
        current_app.config[
            "ITEM_UPLOAD_FOLDER"
        ]
    )

    target = (
        upload_folder
        / filename
    )

    if target.exists():
        target.unlink()
