# M3.4 Validation and Repair Specification

Supported validation tools are Ruff, MyPy and Pytest.

Every execution captures:

- command identity;
- tool and arguments;
- timeout;
- exit code;
- standard output;
- standard error;
- duration;
- normalized findings.

Repair execution must use M3.2 planning and M3.3 safe editing. Applied repairs require explicit approval and unsuccessful attempts must be rolled back when policy requires it.