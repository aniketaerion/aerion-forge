"""Locale-independent typed configuration parsing."""

import re
from pathlib import PurePath
from typing import Any

from forge.configuration.errors import ConfigurationValueParseError
from forge.configuration.models import SettingDefinition, SettingValueType

BOOL = {
    "true": True,
    "1": True,
    "yes": True,
    "on": True,
    "false": False,
    "0": False,
    "no": False,
    "off": False,
}
SIZE = {"b": 1, "kib": 1024, "mib": 1024**2, "gib": 1024**3}
DURATION = {"s": 1, "m": 60, "h": 3600, "d": 86400}


def parse_value(definition: SettingDefinition, value: Any) -> Any:
    if value is None and definition.value_type in (
        SettingValueType.OPTIONAL_STRING,
        SettingValueType.OPTIONAL_INTEGER,
    ):
        return None
    text = str(value).strip()
    try:
        kind = definition.value_type
        if kind in (
            SettingValueType.STRING,
            SettingValueType.PATH,
            SettingValueType.ENUM,
            SettingValueType.OPTIONAL_STRING,
        ):
            parsed: Any = text
        elif kind in (SettingValueType.INTEGER, SettingValueType.OPTIONAL_INTEGER):
            parsed = int(text)
        elif kind is SettingValueType.FLOAT:
            parsed = float(text)
        elif kind is SettingValueType.BOOLEAN:
            if text.casefold() not in BOOL:
                raise ValueError("ambiguous boolean")
            parsed = BOOL[text.casefold()]
        elif kind is SettingValueType.STRING_LIST:
            parsed = (
                tuple(sorted({x.strip() for x in text.split(",") if x.strip()}))
                if not isinstance(value, (list, tuple))
                else tuple(sorted({str(x).strip() for x in value if str(x).strip()}))
            )
        elif kind is SettingValueType.INTEGER_LIST:
            parsed = tuple(int(x.strip()) for x in text.split(",") if x.strip())
        elif kind is SettingValueType.BYTE_SIZE:
            parsed = _unit(text, SIZE)
        elif kind is SettingValueType.DURATION:
            parsed = _unit(text, DURATION)
        else:
            parsed = value
        if definition.allowed_values and str(parsed) not in definition.allowed_values:
            raise ValueError("value is not allowed")
        if (
            isinstance(parsed, (int, float))
            and definition.minimum is not None
            and parsed < definition.minimum
        ):
            raise ValueError("value is below minimum")
        if (
            isinstance(parsed, (int, float))
            and definition.maximum is not None
            and parsed > definition.maximum
        ):
            raise ValueError("value is above maximum")
        if definition.pattern and not re.fullmatch(definition.pattern, str(parsed)):
            raise ValueError("value has invalid format")
        if kind is SettingValueType.PATH and ".." in PurePath(text).parts:
            raise ValueError("path traversal is not allowed")
        return parsed
    except (ValueError, TypeError) as exc:
        raise ConfigurationValueParseError(f"Invalid value for {definition.key}: {exc}") from exc


def _unit(text: str, units: dict[str, int]) -> int:
    match = re.fullmatch(r"(\d+)\s*([A-Za-z]+)?", text)
    if not match:
        raise ValueError("invalid unit value")
    unit = (match.group(2) or ("b" if units is SIZE else "s")).casefold()
    if unit not in units:
        raise ValueError("unsupported unit")
    return int(match.group(1)) * units[unit]
