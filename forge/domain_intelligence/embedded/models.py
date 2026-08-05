"""Immutable contracts for M4.6 Embedded Domain Intelligence."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EmbeddedPlatformKind(StrEnum):
    PX4 = "px4"
    ARDUPILOT = "ardupilot"
    ROS2 = "ros2"
    STM32 = "stm32"
    GENERIC = "generic"
    UNKNOWN = "unknown"


class EmbeddedComponentKind(StrEnum):
    FLIGHT_STACK = "flight_stack"
    AUTOPILOT_MODULE = "autopilot_module"
    ROS2_NODE = "ros2_node"
    DRIVER = "driver"
    FIRMWARE = "firmware"
    BOARD_SUPPORT = "board_support"
    SENSOR = "sensor"
    ACTUATOR = "actuator"
    COMMUNICATION = "communication"
    BUILD_SYSTEM = "build_system"
    UNKNOWN = "unknown"


class EmbeddedInterfaceKind(StrEnum):
    MAVLINK = "mavlink"
    DDS = "dds"
    ROS_TOPIC = "ros_topic"
    ROS_SERVICE = "ros_service"
    ROS_ACTION = "ros_action"
    UART = "uart"
    CAN = "can"
    I2C = "i2c"
    SPI = "spi"
    GPIO = "gpio"
    ETHERNET = "ethernet"
    UNKNOWN = "unknown"


class EmbeddedFindingSeverity(StrEnum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ImmutableEmbeddedModel(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        str_strip_whitespace=True,
    )


class EmbeddedAnalysisRequest(ImmutableEmbeddedModel):
    repository_root: str = Field(min_length=1)
    project_root: str = Field(default=".", min_length=1)
    max_files: int = Field(default=10000, ge=1, le=100000)


class EmbeddedComponent(ImmutableEmbeddedModel):
    component_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    kind: EmbeddedComponentKind
    platform: EmbeddedPlatformKind
    source_paths: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()


class EmbeddedInterface(ImmutableEmbeddedModel):
    interface_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    kind: EmbeddedInterfaceKind
    producer: str | None = None
    consumers: tuple[str, ...] = ()
    source_path: str | None = None


class EmbeddedMessage(ImmutableEmbeddedModel):
    message_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    protocol: str = Field(min_length=1)
    fields: tuple[str, ...] = ()
    source_path: str | None = None


class EmbeddedProject(ImmutableEmbeddedModel):
    project_id: str = Field(min_length=1)
    root: str = Field(min_length=1)
    platforms: tuple[EmbeddedPlatformKind, ...] = ()
    source_files: tuple[str, ...] = ()
    configuration_files: tuple[str, ...] = ()
    build_files: tuple[str, ...] = ()
    detected_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )

    @field_validator("platforms")
    @classmethod
    def ensure_unique_platforms(
        cls,
        platforms: tuple[EmbeddedPlatformKind, ...],
    ) -> tuple[EmbeddedPlatformKind, ...]:
        if len(platforms) != len(set(platforms)):
            raise ValueError("embedded platforms must be unique")
        return platforms


class EmbeddedFinding(ImmutableEmbeddedModel):
    finding_id: str = Field(min_length=1)
    category: str = Field(min_length=1)
    severity: EmbeddedFindingSeverity
    message: str = Field(min_length=1)
    path: str | None = None
    evidence: dict[str, str] = Field(default_factory=dict)


class EmbeddedAnalysisReport(ImmutableEmbeddedModel):
    report_id: str = Field(min_length=1)
    project: EmbeddedProject
    components: tuple[EmbeddedComponent, ...] = ()
    interfaces: tuple[EmbeddedInterface, ...] = ()
    messages: tuple[EmbeddedMessage, ...] = ()
    findings: tuple[EmbeddedFinding, ...] = ()
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )

    @field_validator("findings")
    @classmethod
    def ensure_unique_findings(
        cls,
        findings: tuple[EmbeddedFinding, ...],
    ) -> tuple[EmbeddedFinding, ...]:
        identifiers = [finding.finding_id for finding in findings]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError(
                "embedded finding identifiers must be unique"
            )
        return findings