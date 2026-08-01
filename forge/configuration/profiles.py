"""Built-in runtime profile presets."""

from forge.configuration.errors import ConfigurationProfileNotFoundError
from forge.configuration.models import RuntimeProfileName

PROFILES = {
    RuntimeProfileName.DEVELOPMENT: {
        "logging.level": "INFO",
        "logging.verbose": False,
        "persistence.history_limit": 5,
    },
    RuntimeProfileName.TEST: {
        "logging.level": "WARNING",
        "persistence.history_limit": 1,
        "persistence.memory_directory": "memory/test",
        "reporting.output_directory": "reports/test",
    },
    RuntimeProfileName.PRODUCTION: {
        "logging.level": "WARNING",
        "logging.verbose": False,
        "security.redact_sensitive_values": True,
    },
    RuntimeProfileName.CI: {
        "logging.level": "WARNING",
        "logging.verbose": False,
        "persistence.history_limit": 1,
        "persistence.memory_directory": "memory/ci",
        "reporting.output_directory": "reports/ci",
    },
}
PROFILE_DESCRIPTIONS = {
    RuntimeProfileName.DEVELOPMENT: "Local development with readable logging.",
    RuntimeProfileName.TEST: "Isolated deterministic test execution.",
    RuntimeProfileName.PRODUCTION: "Strict conservative production operation.",
    RuntimeProfileName.CI: "Non-interactive isolated continuous integration.",
}


def get_profile(value: str) -> RuntimeProfileName:
    try:
        return RuntimeProfileName(value.casefold())
    except ValueError as exc:
        raise ConfigurationProfileNotFoundError(f"Unknown runtime profile: {value}") from exc
