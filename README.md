# Tutorial Source Code

This repository contains the source code for the tutorial article 
"Maximize Your FastAPI Efficiency: Blazingly  
Fast Implementation of Caching and Locking with py-cachify",
which demonstrates how to integrate py-cachify with FastAPI.

The full guide can be found in **[GUIDE.md](./GUIDE.md)**

It was also published on:
- [Medium](https://medium.com/@galtozzy/maximize-your-fastapi-efficiency-with-py-cachify-b2bc0f51c976)
- [dev.to](https://dev.to/galtozzy/maximize-your-fastapi-efficiency-blazingly-fast-implementation-of-caching-and-locking-with-4pgj)


## Prerequisites

- Python 3.12+
- Poetry
- Local Redis instance (docker works also)

## Installation

Set up the project locally with the following steps:

1. Clone the repository:

   ```bash
   git clone https://github.com/EzyGang/py-cachify-fastapi-demo
   ```

2. Change into the directory:

   ```bash
   cd py-cachify-fastapi-demo
   ```

3. Install the dependencies with Poetry:

   ```bash
   poetry install
   ```

## Usage

Run the project using:

```bash
poetry run fastapi dev app/main.py
```

## Contact

For questions or feedback, reach out via:

- [GitHub](https://github.com/Galtozzy)
- Twitter/X: [@Kekzzy](https://x.com/Galtozzy)
