"""
Helpers of the image collection module: content-type sniffing, integrity
checksums, capture-time extraction and signed download links.
"""
import hashlib
import hmac
import io
import re
import time
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from urllib.parse import quote

from PIL import Image

# Formats accepted from cameras and phones. Detection relies on file signatures,
# not on the client-supplied Content-Type header.
_SIGNATURES = [
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"II*\x00", "image/tiff"),
    (b"MM\x00*", "image/tiff"),
    (b"BM", "image/bmp"),
]

# EXIF tag ids
_TAG_DATETIME = 306
_TAG_MAKE = 271
_TAG_MODEL = 272
_EXIF_IFD = 0x8769
_TAG_DATETIME_ORIGINAL = 36867
_TAG_DATETIME_DIGITIZED = 36868
_TAG_OFFSET_TIME_ORIGINAL = 36881

# A capture time later than "now + skew" is treated as a broken camera clock.
_MAX_CLOCK_SKEW = timedelta(days=1)
# Cameras with a reset clock report dates around 1970-2000.
_MIN_PLAUSIBLE = datetime(2000, 1, 1, tzinfo=timezone.utc)


def detect_image_type(data: bytes) -> Optional[str]:
    head = data[:16]
    for sig, mime in _SIGNATURES:
        if head.startswith(sig):
            return mime
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    return None


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_filename(name: Optional[str], default: str = "image") -> str:
    """Strip directories and control characters from a client file name."""
    name = (name or "").replace("\\", "/").split("/")[-1]
    name = "".join(ch for ch in name if unicodedata.category(ch)[0] != "C").strip()
    name = name.lstrip(".")
    return name[:200] or default


def content_disposition(disposition: str, filename: str) -> str:
    """RFC 6266 header value that is safe for any (incl. Cyrillic) file name."""
    ascii_name = re.sub(r"[^A-Za-z0-9._-]+", "_", unicodedata.normalize("NFKD", filename)).strip("_") or "file"
    return f"{disposition}; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(filename)}"


def to_utc_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_datetime(value) -> Optional[datetime]:
    """Parse ISO-8601 strings or Unix epoch (seconds or milliseconds) into an aware UTC datetime."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip()
        if re.fullmatch(r"\d{9,13}(\.\d+)?", text):
            num = float(text)
            if num > 1e11:  # milliseconds, as produced by File.lastModified in browsers
                num /= 1000.0
            return datetime.fromtimestamp(num, tz=timezone.utc)
        try:
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _parse_exif_datetime(value, offset=None) -> Optional[datetime]:
    if not value:
        return None
    text = str(value).strip().replace("\x00", "")
    try:
        dt = datetime.strptime(text, "%Y:%m:%d %H:%M:%S")
    except ValueError:
        return None
    tz = timezone.utc
    if offset:
        m = re.fullmatch(r"([+-])(\d{2}):(\d{2})", str(offset).strip())
        if m:
            sign = 1 if m.group(1) == "+" else -1
            tz = timezone(sign * timedelta(hours=int(m.group(2)), minutes=int(m.group(3))))
    return dt.replace(tzinfo=tz).astimezone(timezone.utc)


def read_exif(data: bytes) -> dict:
    """Return capture time and basic camera info found in the image, if any."""
    info: dict = {}
    try:
        with Image.open(io.BytesIO(data)) as img:
            info["width"], info["height"] = img.size
            exif = img.getexif()
    except Exception:
        return info
    if not exif:
        return info
    sub = {}
    try:
        sub = exif.get_ifd(_EXIF_IFD) or {}
    except Exception:
        sub = {}
    captured = (
        _parse_exif_datetime(sub.get(_TAG_DATETIME_ORIGINAL), sub.get(_TAG_OFFSET_TIME_ORIGINAL))
        or _parse_exif_datetime(sub.get(_TAG_DATETIME_DIGITIZED), sub.get(_TAG_OFFSET_TIME_ORIGINAL))
        or _parse_exif_datetime(exif.get(_TAG_DATETIME))
    )
    if captured:
        info["capturedAt"] = captured
    for tag, key in ((_TAG_MAKE, "cameraMake"), (_TAG_MODEL, "cameraModel")):
        val = exif.get(tag)
        if val:
            info[key] = str(val).strip().replace("\x00", "")[:100]
    return info


def resolve_capture_time(
    exif_time: Optional[datetime], client_time: Optional[datetime], server_time: datetime
) -> Tuple[datetime, str]:
    """
    Pick the most trustworthy capture time: EXIF from the camera, then the file
    modification time reported by the client, then the moment of upload.
    """
    latest = server_time + _MAX_CLOCK_SKEW
    for candidate, source in ((exif_time, "exif"), (client_time, "client")):
        if candidate and _MIN_PLAUSIBLE <= candidate <= latest:
            return candidate, source
    return server_time, "server"


# ─── Signed links ────────────────────────────────────────────────

def _signature(secret: str, kind: str, file_id: str, expires: int) -> str:
    msg = f"{kind}:{file_id}:{expires}".encode()
    return hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()


def sign_link(secret: str, kind: str, file_id: str, ttl_seconds: int, now: Optional[float] = None) -> Tuple[int, str]:
    expires = int((now if now is not None else time.time()) + ttl_seconds)
    return expires, _signature(secret, kind, file_id, expires)


def verify_link(secret: str, kind: str, file_id: str, expires, sig: str, now: Optional[float] = None) -> bool:
    try:
        expires = int(expires)
    except (TypeError, ValueError):
        return False
    if expires < (now if now is not None else time.time()):
        return False
    return hmac.compare_digest(_signature(secret, kind, file_id, expires), sig or "")
