from fastapi import FastAPI
import time
import uvicorn

DEFAULT_ALARM_TIME = {"alarm_time": "9:00"}

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


@app.get("/alarm/time")
async def alarm_time(date: float):
    slept_at = await latest_sleep()

    if slept_at is None or "latest_sleep" not in slept_at:
        return DEFAULT_ALARM_TIME

    # get 24 hour time from seconds from epoch
    slept_clock_time = time.localtime(float(slept_at["latest_sleep"]))
    requested_date = time.localtime(date)

    if (requested_date.tm_hour > 9
            or slept_clock_time.tm_yday >= requested_date.tm_yday
            or slept_clock_time.tm_yday < (requested_date.tm_yday - 1)):
        return DEFAULT_ALARM_TIME
    else:
        slept_hour = slept_clock_time.tm_hour
        if 9 <= slept_hour <= 23:
            calc_alarm_time = "6:30"
        elif slept_hour >= 0 and (slept_hour + 7) < 9:
            calc_alarm_time = slept_hour + 7
        else:
            return DEFAULT_ALARM_TIME
        return { "alarm_time": f"{calc_alarm_time}:00"}


def start():
    """Launched with `poetry run start` at root level"""
    uvicorn.run("main:app", reload=True)
