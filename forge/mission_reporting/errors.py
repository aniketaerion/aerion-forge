"""Mission Reporting exceptions."""


class MissionReportingError(Exception):
    """Base Mission Reporting error."""


class MissionReportingDisabledError(MissionReportingError):
    """Raised when Mission Reporting is disabled."""


class MissionReportingValidationError(MissionReportingError):
    """Raised when Mission Reporting inputs are invalid."""


class MissionReportingBuildError(MissionReportingError):
    """Raised when a report cannot be built."""


class MissionReportingRenderError(MissionReportingError):
    """Raised when report rendering fails."""


class MissionReportingReportError(MissionReportingError):
    """Raised when report persistence or rollback fails."""
