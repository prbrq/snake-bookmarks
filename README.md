# snake-bookmarks

A simple bookmark manager REST API built to explore FastAPI and Python.

## Stack

- **FastAPI** — web framework
- **SQLModel** — ORM (SQLAlchemy + Pydantic)
- **SQLite** — database
- **Alembic** — migrations
- **uv** — package manager

## API

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/bookmarks` | List bookmarks (paginated, filterable by tag) |
| `POST` | `/bookmarks` | Create a bookmark |
| `GET` | `/bookmarks/search` | Search by title and description |
| `GET` | `/bookmarks/{id}` | Get a bookmark |
| `PUT` | `/bookmarks/{id}` | Update a bookmark |
| `DELETE` | `/bookmarks/{id}` | Delete a bookmark |
| `GET` | `/tags` | List tags with bookmark counts |

Interactive docs available at `/docs`.

## Getting started

```bash
uv sync
uv run alembic upgrade head
uv run uvicorn main:app --reload
```
