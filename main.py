from fastapi import FastAPI
import time

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}


@app.post("/sleep")
async def sleep():
    slept_at = time.time()
    with open("data/sleeps.log", "a") as file:
        file.write(f"{slept_at}\n")
    return {"message": "Good night!", "slept_at": slept_at}


@app.get("/sleep/latest")
async def latest_sleep():
    with open("data/sleeps.log", "rb") as file:
        file.seek(-2, 2)  # Jump to the second last byte.
        while file.read(1) != b'\n':  # Until EOL is found...
            file.seek(-2, 1)  # ...jump back the read byte plus one more.
        last_line = file.readline().decode().strip()  # Read last line.
    return {"latest_sleep": last_line}
