from fastapi import FastAPI

from routes import accounts_router

app = FastAPI()

app.include_router(accounts_router, prefix="/accounts", tags=["accounts"])


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}
