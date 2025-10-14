# XSArena Configuration Reference

## Configuration File Location
- Main config: `.xsarena/config.yml`
- Default location if missing: auto-generated with defaults

## Configuration Keys

### backend
- **Type**: string
- **Default**: "bridge"
- **Description**: Backend provider to use (bridge or openrouter)

### base_url
- **Type**: string
- **Default**: "http://127.0.0.1:8080/v1"
- **Description**: URL endpoint for the backend API

### model
- **Type**: string
- **Default**: "default"
- **Description**: Model identifier to use

### window
- **Type**: integer
- **Default**: 100
- **Description**: Window size for history context

## CLI Options Override
All configuration values can be overridden via command-line options:
- `--backend`: Override backend setting
- `--model`: Override model setting
- `--window`: Override window size setting

## Environment Variables
Configuration can also be controlled via environment variables:
- `XSA_BACKEND`: Sets the backend
- `XSA_MODEL`: Sets the model
- `XSA_WINDOW`: Sets the window size