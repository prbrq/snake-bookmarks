from fastapi import FastAPI
from sqlmodel import SQLModel, Field, create_engine, Session, select, func, col
from datetime import datetime
from urllib.parse import urlparse
from fastapi.responses import RedirectResponse
from fastapi import HTTPException
from pydantic import field_validator

app = FastAPI()

engine = create_engine("sqlite:///snake-bookmarks.db")


class Bookmark(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    url: str = Field(unique=True)
    title: str
    description: str | None = None
    created_at: datetime = Field(default_factory=datetime.now)


class Tag(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(unique=True)


class Bookmark_Tag(SQLModel, table=True):
    bookmark_id: int = Field(primary_key=True, foreign_key="bookmark.id")
    tag_id: int = Field(primary_key=True, foreign_key="tag.id")


def _validate_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("Invalid URL: must start with http:// or https://")
    return url


class BookmarkCreate(SQLModel):
    url: str
    title: str = Field(min_length=1)
    description: str | None = None
    tags: list[str] = []

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        return _validate_url(v)


class BookmarkUpdate(SQLModel):
    url: str | None = None
    title: str | None = Field(default=None, min_length=1)
    description: str | None = None
    tags: list[str] | None = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        return _validate_url(v)


class BookmarkRead(SQLModel):
    id: int
    url: str
    title: str
    description: str | None = None
    created_at: datetime
    tags: list[str] = []


class BookmarkList(SQLModel):
    items: list[BookmarkRead]
    total: int


class TagRead(SQLModel):
    name: str
    bookmarks_count: int


def _get_tags(session: Session, bookmark_id: int | None) -> list[str]:
    if bookmark_id is None:
        return []
    return [
        tag.name
        for tag in session.exec(
            select(Tag)
            .join(Bookmark_Tag)
            .where(Bookmark_Tag.bookmark_id == bookmark_id)
        ).all()
    ]


def _to_read(bookmark: Bookmark, tags: list[str]) -> BookmarkRead:
    return BookmarkRead(
        id=bookmark.id,
        url=bookmark.url,
        title=bookmark.title,
        description=bookmark.description,
        created_at=bookmark.created_at,
        tags=tags,
    )


def _upsert_tags(session: Session, tag_names: list[str]) -> list[Tag]:
    tags = []
    seen: set[str] = set()
    for name in tag_names:
        name = name.lower()
        if name in seen:
            continue
        seen.add(name)
        tag = session.exec(select(Tag).where(Tag.name == name)).first()
        if not tag:
            tag = Tag(name=name)
            session.add(tag)
            session.flush()
        tags.append(tag)
    return tags


@app.get("/tags", response_model=list[TagRead])
def get_tags():
    with Session(engine) as session:
        rows = session.exec(
            select(Tag.name, func.count(Bookmark_Tag.bookmark_id).label("bookmarks_count"))
            .join(Bookmark_Tag, isouter=True)
            .group_by(Tag.id)
            .order_by(col(Tag.name))
        ).all()
        return [TagRead(name=name, bookmarks_count=count) for name, count in rows]


@app.post("/bookmarks", status_code=201)
def create_bookmark(bookmark_create: BookmarkCreate):
    with Session(engine) as session:
        with session.begin():
            bookmark_with_existing_url = session.exec(
                select(Bookmark).where(Bookmark.url == bookmark_create.url)
            ).first()

            if bookmark_with_existing_url:
                raise HTTPException(
                    status_code=409, detail="Bookmark with this URL already exists"
                )

            bookmark = Bookmark(
                url=bookmark_create.url,
                title=bookmark_create.title,
                description=bookmark_create.description,
            )

            session.add(bookmark)

            session.flush()

            for tag in _upsert_tags(session, bookmark_create.tags):
                session.add(Bookmark_Tag(bookmark_id=bookmark.id, tag_id=tag.id))

        session.refresh(bookmark)
        return {"id": bookmark.id}


@app.get("/bookmarks", response_model=BookmarkList)
def get_bookmarks(tag: str | None = None, limit: int = 20, offset: int = 0):
    with Session(engine) as session:
        if tag:
            base = select(Bookmark).join(Bookmark_Tag).join(Tag).where(Tag.name == tag.lower())
        else:
            base = select(Bookmark)

        total = session.exec(select(func.count()).select_from(base.subquery())).one()
        bookmarks = session.exec(
            base.order_by(col(Bookmark.created_at).desc()).offset(offset).limit(limit)
        ).all()

        return BookmarkList(
            items=[_to_read(b, _get_tags(session, b.id)) for b in bookmarks],
            total=total,
        )


@app.get("/bookmarks/search", response_model=BookmarkList)
def search_bookmarks(q: str, limit: int = 20, offset: int = 0):
    if not q.strip():
        raise HTTPException(status_code=400, detail="Search query cannot be empty")
    pattern = f"%{q}%"
    with Session(engine) as session:
        base = select(Bookmark).where(
            col(Bookmark.title).ilike(pattern) | col(Bookmark.description).ilike(pattern)
        )
        total = session.exec(select(func.count()).select_from(base.subquery())).one()
        bookmarks = session.exec(
            base.order_by(col(Bookmark.created_at).desc()).offset(offset).limit(limit)
        ).all()
        return BookmarkList(
            items=[_to_read(b, _get_tags(session, b.id)) for b in bookmarks],
            total=total,
        )


@app.get("/bookmarks/{bookmark_id}", response_model=BookmarkRead)
def get_bookmark(bookmark_id: int):
    with Session(engine) as session:
        bookmark = session.get(Bookmark, bookmark_id)
        if not bookmark:
            raise HTTPException(status_code=404, detail="Bookmark not found")
        return _to_read(bookmark, _get_tags(session, bookmark.id))


@app.put("/bookmarks/{bookmark_id}", response_model=BookmarkRead)
def update_bookmark(bookmark_id: int, bookmark_update: BookmarkUpdate):
    with Session(engine) as session:
        with session.begin():
            bookmark = session.get(Bookmark, bookmark_id)
            if not bookmark:
                raise HTTPException(status_code=404, detail="Bookmark not found")

            if bookmark_update.url is not None:
                bookmark.url = bookmark_update.url
            if bookmark_update.title is not None:
                bookmark.title = bookmark_update.title
            if bookmark_update.description is not None:
                bookmark.description = bookmark_update.description

            if bookmark_update.tags is not None:
                for link in session.exec(
                    select(Bookmark_Tag).where(Bookmark_Tag.bookmark_id == bookmark.id)
                ).all():
                    session.delete(link)

                session.add_all(
                    [
                        Bookmark_Tag(bookmark_id=bookmark.id, tag_id=tag.id)
                        for tag in _upsert_tags(session, bookmark_update.tags)
                    ]
                )

            session.flush()

        session.refresh(bookmark)
        return _to_read(bookmark, _get_tags(session, bookmark.id))


@app.delete("/bookmarks/{bookmark_id}", status_code=204)
def delete_bookmark(bookmark_id: int):
    with Session(engine) as session:
        with session.begin():
            bookmark = session.get(Bookmark, bookmark_id)
            if not bookmark:
                raise HTTPException(status_code=404, detail="Bookmark not found")

            links = session.exec(
                select(Bookmark_Tag).where(Bookmark_Tag.bookmark_id == bookmark_id)
            ).all()
            for link in links:
                session.delete(link)

            session.delete(bookmark)


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")
