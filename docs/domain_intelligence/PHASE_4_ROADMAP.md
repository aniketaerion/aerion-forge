# Phase 4 — Domain Intelligence Framework

## Objective

Keep Aerion Forge domain-agnostic while allowing it to acquire
technology-stack and business-domain intelligence through typed,
versioned, validated plugins.

## Milestones

- M4.1 Frontend and UI Intelligence
- M4.2 Backend and Service Intelligence
- M4.3 Database and Migration Intelligence
- M4.4 API Contract Intelligence
- M4.5 Business Domain Plugin Framework
- M4.6 Embedded, PX4 and ROS2 Intelligence
- M4.7 Domain Knowledge Loader
- M4.8 Phase Validation and Release

## Architectural Rule

Forge Core must not contain ERP-, CRM-, PX4-, ROS2-, React-, Node-,
PostgreSQL-, Flutter-, or other domain-specific business logic.

All domain intelligence must be loaded through explicit plugins,
knowledge packs, analyzers, or adapters.

## First Production Domain

ERP will be the first production domain pack and pilot, but it will not
define or constrain the Forge Core architecture.