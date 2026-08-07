# M5.8 Verification Model

Verification must use the actual project toolchain.

Examples include:

- Python: Ruff, MyPy, Pytest;
- React/Node: lint, type checking, unit tests, build;
- PostgreSQL: migration and schema validation;
- Flutter: analyzer, tests, build checks;
- C/C++: compiler, CMake, unit tests;
- PX4: SITL and PX4 test tooling where configured;
- ROS2: colcon build and test where configured;
- embedded: compiler, static analysis, unit or hardware-in-loop checks where available.

A mission cannot complete unless required verification passes or an approved exception is recorded.