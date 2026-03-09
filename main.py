from fastapi import FastAPI
from sqlmodel import SQLModel, Field, create_engine, Session, select
from datetime import datetime
from fastapi.responses import RedirectResponse

app = FastAPI()

engine = create_engine("sqlite:///snake-bookmarks.db")


class Bookmark(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    url: str
    title: str
    description: str | None = None
    created_at: datetime = Field(default_factory=datetime.now)


class Tag(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(unique=True)


class Bookmark_Tag(SQLModel, table=True):
    bookmark_id: int = Field(primary_key=True, foreign_key="bookmark.id")
    tag_id: int = Field(primary_key=True, foreign_key="tag.id")


class BookmarkCreate(SQLModel):
    url: str
    title: str
    description: str | None = None
    tags: list[str] | None = None


SQLModel.metadata.create_all(engine)


@app.post("/bookmarks", status_code=201)
def create_bookmark(bookmark_create: BookmarkCreate):
    with Session(engine) as session:
        with session.begin():
            bookmark = Bookmark(
                url=bookmark_create.url,
                title=bookmark_create.title,
                description=bookmark_create.description,
            )

            session.add(bookmark)

            session.flush()

            tag_list = []

            for tag_name in bookmark_create.tags:
                existing = session.exec(select(Tag).where(Tag.name == tag_name)).first()
                if existing:
                    tag_list.append(existing)
                else:
                    tag = Tag(name=tag_name)
                    session.add(tag)
                    session.flush()
                    tag_list.append(tag)

            bookmark_tag_list = []

            for tag in tag_list:
                bookmark_tag_list.append(
                    Bookmark_Tag(bookmark_id=bookmark.id, tag_id=tag.id)
                )

            for bookmark_tag in bookmark_tag_list:
                session.add(bookmark_tag)

        session.refresh(bookmark)
        return {"id": bookmark.id}


# @app.get("/items")
# def get_items():
#     with Session(engine) as session:
#         return session.exec(select(Item)).all()


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")
