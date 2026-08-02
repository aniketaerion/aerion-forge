"""Actionable mission-planning exceptions."""


class MissionPlanningError(Exception):
    """Base planning failure."""


class MissionRequestError(MissionPlanningError):
    pass


class MissionTargetNotFoundError(MissionPlanningError):
    pass


class MissionPrerequisiteError(MissionPlanningError):
    pass


class MissionContextError(MissionPlanningError):
    pass


class MissionNormalizationError(MissionRequestError):
    pass


class MissionValidationError(MissionPlanningError):
    pass


class MissionPersistenceError(MissionPlanningError):
    pass


class MissionReportError(MissionPlanningError):
    pass


class MissionStoreCorruptionError(MissionPersistenceError):
    pass


class MissionSchemaMismatchError(MissionPersistenceError):
    pass


class MissionNotFoundError(MissionPlanningError):
    pass


class MissionPlanningDisabledError(MissionPlanningError):
    pass
