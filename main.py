from fastapi import FastAPI
from sqlmodel import SQLModel, Field, create_engine, Session, select 
from datetime import datetime

app = FastAPI()

engine = create_engine("sqlite:///snake-bookmarks.db")

class Item(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    price: float

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


SQLModel.metadata.create_all(engine)

@app.post("/items")
def create_item(item: Item):
    with Session(engine) as session:
        session.add(item)
        session.commit()
        session.refresh(item)
        return item

@app.get("/items")
def get_items():
    with Session(engine) as session:
        return session.exec(select(Item)).all()