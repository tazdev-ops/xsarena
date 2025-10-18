# Configuration Files

This document explains the distinct roles of the different configuration files used in xsarena.

## config.yml

The `config.yml` file contains global configuration settings for xsarena. This includes:

- Default settings for all projects
- Global preferences and options
- System-wide configurations
- Default backend transport settings
- General tool configurations (e.g., LLM settings, logging levels)

## project.yml

The `project.yml` file contains project-specific configuration settings. This includes:

- Project-specific settings that override global defaults
- Project structure and metadata
- Project-specific tool configurations
- Environment-specific settings
- Project-specific workflow configurations

## session_state.json

The `session_state.json` file contains temporary state information for the current session. This includes:

- Current session state and progress
- Temporary data for ongoing operations
- Session-specific variables and settings
- Information about running jobs or tasks
- Transient data that should not persist between sessions
