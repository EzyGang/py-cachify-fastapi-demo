# Maximize Your FastAPI Efficiency: Blazingly Fast Implementation of Caching and Locking with py-cachify

In the fast-paced world of web development, performance is paramount. Efficient caching mechanisms can significantly enhance the responsiveness of your API by reducing redundant computations and database queries. In this article, we’ll explore how to integrate the `py-cachify` library into a FastAPI application using SQLModel and Redis to implement caching and concurrency control.


## Table of Contents:
- [Introduction](#introduction)
- [Project Setup](#project-setup)
- [Creating Database Models with SQLModel](#creating-database-models-with-sqlmodel)
- [Building FastAPI Endpoints](#building-fastapi-endpoints)
- [Caching Endpoint Results](#caching-endpoint-results)
- [Locking Execution of Update Endpoints](#locking-execution-of-update-endpoints)
- [Running the Application](#running-the-application)
- [Conclusion](#conclusion)

## Introduction
Caching is a powerful technique to improve the performance of web applications by storing the results of expensive operations and serving them from a quick-access storage. With py-cachify, we can seamlessly add caching to our FastAPI applications, utilizing Redis for storage. Additionally, py-cachify provides tools for concurrency control, preventing race conditions during critical operations.

In this tutorial, we’ll walk through setting up the py-cachify library in a FastAPI application with SQLModel for ORM and Redis for caching.

## Project Setup
Let’s start by setting up our project environment.

### Prerequisites

- Python 3.12
- Poetry (you can use any package manager you like)
- Redis server running locally or accessible remotely

### Install Dependencies

Start a new project via poetry:

```bash
# create new project
poetry new --name app py-cachify-fastapi-demo

# enter the directory
cd py-cachify-fastapi-demo

# point poetry to use python3.12
poetry env use python3.12

# add dependencies
poetry add "fastapi[standard]" sqlmodel aiosqlite redis py-cachify
```

- **FastAPI**: The web framework for building our API.
- **SQLModel + aiosqlite**: Combines SQLAlchemy and Pydantic for ORM and data validation.
- **Redis**: Python client for interacting with Redis.
- **py-cachify**: Caching and locking utilities.


### Initializing py-cachify

Before we can use py-cachify, we need to initialize it with our Redis clients. We’ll do this using FastAPI’s lifespan parameter.

```python
# app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from py_cachify import init_cachify
from redis.asyncio import from_url


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_cachify(
        # Replace with your redis url if it differs
        async_client=from_url('redis://localhost:6379/0'),
    )
    yield


app = FastAPI(lifespan=lifespan)
```

Inside the `lifespan`, we:

- Create an asynchronous Redis client.
- Initialize py-cachify with this client.

## Creating Database Models with SQLModel
We’ll create a simple User model to interact with our database.

```python
# app/db.py
from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    email: str
```

Set up the database engine and create the tables in the `lifespan` function:

```python
# app/db.py

# Adjust imports
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


# Add the following at the end of the file
sqlite_file_name = 'database.db'
sqlite_url = f'sqlite+aiosqlite:///{sqlite_file_name}'
engine = create_async_engine(sqlite_url, echo=True)
session_maker = async_sessionmaker(engine)


# app/main.py
# Adjust imports and lifespan function
from sqlmodel import SQLModel

from .db import engine


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_cachify(
        async_client=from_url('redis://localhost:6379/0'),
    )
    # Create SQL Model tables
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    yield
```

*Note: We’re using SQLite for simplicity, but you can use any database supported by SQLAlchemy.*

## Building FastAPI Endpoints
Let’s create endpoints to interact with our User model.

```python
# app/main.py

# Adjust imports
from fastapi import Depends, FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from .db import User, engine, session_maker


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
async def read_user(user_id: int, session: AsyncSession = Depends(get_session)) -> User | None:
    return await session.get(User, user_id)


@app.put('/users/{user_id}')
async def update_user(user_id: int, new_user: User, session: AsyncSession = Depends(get_session)) -> User | None:
    user = await session.get(User, user_id)
    if not user:
        return None

    user.name = new_user.name
    user.email = new_user.email

    session.add(user)
    await session.commit()
    await session.refresh(user)

    return user
```

## Caching Endpoint Results
Now, let’s cache the results of the `read_user` endpoint to avoid unnecessary database queries.

The endpoint code will look like this:

```python
# app/main.py

# Add the import
from py_cachify import cached


@app.get('/users/{user_id}')
@cached('read_user-{user_id}', ttl=300)  # New decorator
async def read_user(user_id: int, session: AsyncSession = Depends(get_session)) -> User | None:
    return await session.get(User, user_id)
```

With the `@cached` decorator:

- We specify a unique key using the `user_id`.
- Set the TTL (time-to-live) to 5 minutes (300 seconds).
- Subsequent calls to this endpoint with the same `user_id` within 5 minutes will return the cached result.

### Resetting Cache on Updates

When a user’s data is updated, we need to reset the cache to ensure clients receive the latest information. To make it happen, let’s modify the `update_user` endpoint.

```python
# app/main.py

@app.put('/users/{user_id}')
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
```

By calling `read_user.reset(user_id=user_id)`, we:

- Clear the cached data for the specific `user_id`.
- Ensure subsequent GET requests fetch fresh data from the database.

Underneath, the cached decorator dynamically wraps your function, adding the `.reset` method. This method mimics the function’s signature, and type, this way it will be either sync or async depending on the original function and will accept the same arguments.

The `.reset` method uses the same key generation logic defined in the cached decorator to identify which cached entry to invalidate. For example, if your caching key pattern is `user-{user_id}`, calling `await read_user.reset(user_id=123)` will specifically target and delete the cache entry for `user_id=123`.

## Locking Execution of Update Endpoints
To prevent race conditions during updates, we’ll use the `once` decorator to lock the execution of the update endpoint.

```python
# app/main.py

from py_cachify import once
from fastapi.responses import JSONResponse


@app.put('/users/{user_id}', response_model=User)
# Add the locking decorator
@once('update-user-{user_id}', return_on_locked=JSONResponse(content={'status': 'Update in progress'}, status_code=226))
async def update_user(user_id: int, new_user: User, session: AsyncSession = Depends(get_session)) -> User | None:
    user = await session.get(User, user_id)
    user.name = new_user.name
    user.email = new_user.email

    session.add(user)
    await session.commit()
    await session.refresh(user)

    # Reset cache for this user
    await read_user.reset(user_id=user_id)
    return user
```

With `once`:

- We lock the function based on `user_id`.
- If another request tries to update the same user concurrently, it will immediately return the response with a **226 IM Used** status code.
- This prevents simultaneous updates that could result in inconsistent data.

Optionally, you can configure `@once` to raise an exception or return a specific value if the lock is already acquired.

## Running the Application
Now it’s time to run and test our app!

1) **Start the Redis Server:**

Ensure your Redis server is running locally or is accessible remotely. You can start a local Redis server using Docker:

```bash
docker run --name redis -p 6379:6379 -d redis
```

2) **Run the FastAPI Application:**

With everything set up, you can launch your FastAPI application using Poetry. Navigate to the root directory of your project and execute the following command:

```bash
poetry run fastapi dev app/main.py
```

3) **Testing and Playing with Caching and Locking:**

**Caching:** Add delay (e.g., using `asyncio.sleep`) in the `read_user` function to simulate a long-running computation. Observe how the response time drastically improves once the result is cached.

Example:
```python
import asyncio

async def read_user(user_id: int, session: AsyncSession = Depends(get_session)) -> User | None:
    await asyncio.sleep(2)  # Simulate expensive computation or database call
    return await session.get(User, user_id)
 ```

**Concurrency and Locking:** Similarly, introduce a delay in the `update_user` function to observe the behavior of locks when concurrent update attempts are made.

Example:
```python
async def update_user(user_id: int, new_user: User, session: AsyncSession = Depends(get_session)) -> User | None:
    await asyncio.sleep(2)  # Simulate update delay
    # update logic here…
```

These delays can help you see the effectiveness of caching and locking mechanisms in action, as subsequent reads should be faster due to caching, and concurrent writes to the same resource should be managed effectively through locking.

Now, you can test your endpoints using a tool like Postman or by going to `http://127.0.0.1:8000/docs` (when the app is running!), and observe the performance improvements and concurrency controls in action.

Enjoy experimenting with your enhanced FastAPI app!

## Conclusion

By integrating `py-cachify` into our FastAPI application, we’ve unlocked a plethora of benefits that enhance both the performance and reliability of our API.

Let’s recap some of the key strengths:

- **Enhanced Performance:** Caching repetitive function calls reduces redundant computations and database hits, drastically improving response times.
- **Concurrency Control:** With built-in locking mechanisms, py-cachify prevents race conditions and ensures data consistency — crucial for applications with high concurrent access.
- **Flexibility:** Whether you’re working with synchronous or asynchronous operations, py-cachify seamlessly adapts, making it a versatile choice for modern web applications.
- **Ease of Use:** The library integrates smoothly with popular Python frameworks like FastAPI, allowing you to get started with minimal friction.
- **Full Type Annotations:** py-cachify is fully type-annotated, aiding in writing better, more maintainable code with minimal effort.
- **Minimal Setup:** As demonstrated in this tutorial, adding py-cachify requires just a couple of additional lines on top of your existing setup to leverage its capabilities fully.

For those eager to explore further, check out **[py-cachify’s GitHub repository](https://github.com/EzyGang/py-cachify)** and **[the official documentation](https://py-cachify.readthedocs.io/latest/)** for more in-depth guidance, tutorials, and examples.

You can access the full code for this tutorial on GitHub **[here](https://github.com/EzyGang/py-cachify-fastapi-demo)**. Feel free to clone the repository and play around with the implementation to suit your project’s needs.

If you find **py-cachify** beneficial, consider supporting the project by giving it a star on GitHub! Your support helps drive further improvements and new features.

Happy coding!
