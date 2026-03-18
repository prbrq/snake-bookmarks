# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run the server
uvicorn main:app --reload

# Lint
ruff check .
ruff format .

# Type check
mypy main.py
```

Dependencies are managed with `uv`. Python version: 3.13 (see `.python-version`).
