from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse
from py_cachify import cached, init_cachify, once
from redis.asyncio import from_url
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel

from .db import User, engine, session_maker


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_cachify(
        async_client=from_url('redis://localhost:6379/0'),
    )
    # Create SQL Model tables
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield


# Database session dependency
async def get_session():
    async with session_maker() as session:
        yield session


app = FastAPI(lifespan=lifespan)


@app.post('/users/')
async def create_user(user: User, session: AsyncSession = Depends(get_session)) -> User:
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@app.get('/users/{user_id}')
@cached('read_user-{user_id}', ttl=300)
async def read_user(user_id: int, session: AsyncSession = Depends(get_session)) -> User | None:
    return await session.get(User, user_id)


@app.put('/users/{user_id}')
# Add the locking decorator
@once('update-user-{user_id}', return_on_locked=JSONResponse(content={'status': 'Update in progress'}, status_code=226))
async def update_user(user_id: int, new_user: User, session: AsyncSession = Depends(get_session)) -> User | None:
    user = await session.get(User, user_id)
    if not user:
        return None

    user.name = new_user.name
    user.email = new_user.email

    session.add(user)
    await session.commit()
    await session.refresh(user)

    # Reset cache for this user
    await read_user.reset(user_id=user_id)

    return user
