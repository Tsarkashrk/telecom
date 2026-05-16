import ipaddress
import re
from pathlib import Path


USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_]+$")
PHONE_ALLOWED_PATTERN = re.compile(r"^[+\d\s\-()]+$")
CONTROL_CHARS_PATTERN = re.compile(r"[\r\n\t\x00-\x1f\x7f]+")
SAFE_FILENAME_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,127}$")

MAX_LOG_FIELD_LENGTH = 255
MAX_IP_FIELD_LENGTH = 50


def normalize_username(value: str) -> str:
    return value.strip()


def validate_username_allowlist(value: str) -> str:
    if not USERNAME_PATTERN.fullmatch(value):
        raise ValueError("Username содержит недопустимые символы")
    return value


def normalize_phone(value: str) -> str:
    candidate = value.strip()
    if not PHONE_ALLOWED_PATTERN.fullmatch(candidate):
        raise ValueError("Некорректный формат номера телефона")

    has_plus = candidate.startswith("+")
    digits = re.sub(r"\D", "", candidate)
    normalized = f"+{digits}" if has_plus else digits

    if len(digits) < 10 or len(digits) > 15:
        raise ValueError("Некорректная длина номера телефона")

    return normalized


def sanitize_log_value(value: str | None, max_length: int = MAX_LOG_FIELD_LENGTH) -> str | None:
    if value is None:
        return None

    sanitized = CONTROL_CHARS_PATTERN.sub(" ", value).strip()
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]

    return sanitized or None


def extract_client_ip(x_forwarded_for: str | None, fallback: str = "unknown") -> str:
    if not x_forwarded_for:
        return fallback

    first_hop = x_forwarded_for.split(",")[0].strip()

    try:
        parsed = ipaddress.ip_address(first_hop)
        return parsed.compressed[:MAX_IP_FIELD_LENGTH]
    except ValueError:
        return fallback


def validate_safe_filename(value: str) -> str:
    candidate = value.strip()
    if not SAFE_FILENAME_PATTERN.fullmatch(candidate):
        raise ValueError("Недопустимое имя файла")
    if candidate in {".", ".."}:
        raise ValueError("Недопустимое имя файла")
    return candidate


def safe_join(base_dir: str | Path, *parts: str) -> Path:
    base = Path(base_dir).expanduser().resolve()
    target = base.joinpath(*parts).resolve()
    if base != target and base not in target.parents:
        raise ValueError("Недопустимый путь файла")
    return target


def csv_sanitize_cell(value: object) -> str:
    if value is None:
        return ""
    text = str(value)
    text = CONTROL_CHARS_PATTERN.sub(" ", text).strip()
    if text[:1] in {"=", "+", "-", "@"}:
        return "'" + text
    return text
