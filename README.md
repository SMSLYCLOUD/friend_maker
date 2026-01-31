# SocialGrowthAI Desktop Application

## Overview
A completely standalone Python desktop application for social media automation using local AI (Ollama).

## Features
- **Account Management**: Encrypted storage of session data.
- **Automation**: Playwright-based browser automation (Instagram).
- **AI Integration**: Local Ollama execution for profile classification and message generation.
- **Privacy**: Local SQLite database, no cloud servers.

## Build Instructions

### Prerequisites
- Python 3.12+
- `pip install -r requirements.txt`
- `playwright install chromium`

### Running Source
```bash
python main.py
```

### Building Executable
```bash
pyinstaller build.spec
```
The executable will be in the `dist/` folder.

## Architecture
- `app/`: Core application logic.
- `app/ui/`: CustomTkinter UI.
- `app/ai/`: Ollama integration.
- `app/automation/`: Background tasks and logic.
- `app/platforms/`: Platform adapters (Instagram).

## Testing
```bash
pytest
```
Note: Tests use mocks for Playwright and AI to run in headless/CI environments.
