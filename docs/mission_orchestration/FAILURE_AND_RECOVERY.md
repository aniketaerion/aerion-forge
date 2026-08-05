# M3.6 Failure and Recovery

Recoverable failures pause the mission and persist a checkpoint.

Resume is allowed only when the repository fingerprint still matches, the workflow is unchanged, required stages remain registered, attempt limits are not exhausted, and approval policy has not weakened.