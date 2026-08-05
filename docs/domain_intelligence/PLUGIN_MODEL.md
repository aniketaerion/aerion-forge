# Phase 4 Plugin Model

Every domain plugin declares:

- stable identifier;
- name and version;
- domain kind;
- compatible Forge API version;
- declared capabilities;
- enabled state.

Plugins must not modify source code unless a later execution policy explicitly
authorizes it.