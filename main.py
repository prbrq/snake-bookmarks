from fastapi import FastAPI
from sqlmodel import SQLModel, Field, create_engine, Session, select 

app = FastAPI()

engine = create_engine("sqlite:///snake-bookmarks.db")

class Item(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    price: float

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