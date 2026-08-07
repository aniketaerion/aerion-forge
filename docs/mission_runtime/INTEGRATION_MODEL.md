# M5.8 Integration Model

## Existing Forge Core

M5.8 consumes:

- workspace management;
- repository discovery;
- indexing;
- knowledge graph;
- capability registry;
- domain intelligence;
- safe change planning;
- safe code editing;
- build verification;
- Git and review package capabilities;
- documentation generation.

## M5.5 Memory

M5.8 retrieves relevant context and may persist validated mission lessons.

It does not reimplement memory storage or learning.

## M5.6 Planning

M5.8 invokes `AutonomousPlanningService` to create, validate, approve, or reject plans.

It does not synthesize a second planning model.

## M5.7 Execution

M5.8 invokes `AutonomousExecutionService` to register and execute controlled runs.

It does not bypass execution authority, evidence, retry, or recovery controls.

## Project and Domain Capabilities

M5.8 selects capabilities based on detected project technologies and domain.

Examples:

- React, Node, PostgreSQL and ERP capabilities;
- CRM and web-service capabilities;
- Flutter and Dart capabilities;
- C++, Qt, MAVLink, PX4 and ROS2 capabilities;
- embedded C/C++, CMake and firmware capabilities.