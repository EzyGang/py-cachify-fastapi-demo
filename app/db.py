from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    email: str


sqlite_file_name = 'database.db'
sqlite_url = f'sqlite+aiosqlite:///{sqlite_file_name}'
engine = create_async_engine(sqlite_url, echo=True)
session_maker = async_sessionmaker(engine)
