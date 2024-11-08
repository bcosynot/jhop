from fastapi import FastAPI
import time
import uvicorn
import os
import os.path


# Default alarm time to be used if no specific alarm time is calculated
DEFAULT_ALARM_TIME = {"alarm_time": "9:00"}
# Path to the log file where sleep times are recorded
SLEEPS_LOG_PATH = os.getenv("SLEEPS_LOG_PATH", "data/sleeps.log")

app = FastAPI()


@app.get("/")
async def root():
    """
    Root endpoint that returns a simple greeting message.
    """
    return {"message": "Hello World"}


@app.get("/hello/{name}")
async def say_hello(name: str):
    """
    Endpoint that returns a personalized greeting message.
    :param name: The name to include in the greeting message.
    """
    return {"message": f"Hello {name}"}


@app.post("/sleep")
async def sleep():
    """
    Endpoint to log the current time as the time the user went to sleep.
    Creates the log file if it does not exist.
    """
    slept_at = time.time()
    # check_permissions(SLEEPS_LOG_PATH)
    if not os.path.exists(SLEEPS_LOG_PATH):
        os.makedirs(os.path.dirname(SLEEPS_LOG_PATH), exist_ok=True)
        open(SLEEPS_LOG_PATH, 'a').close()
    with open(SLEEPS_LOG_PATH, "a") as file:
        file.write(f"{slept_at}\n")
    return {"message": "Good night!", "slept_at": slept_at}


@app.get("/sleep/latest")
async def latest_sleep():
    """
    Endpoint to retrieve the latest recorded sleep time.
    Creates the log file if it does not exist.
    """
    # check_permissions(SLEEPS_LOG_PATH)
    if not os.path.exists(SLEEPS_LOG_PATH):
        os.makedirs(os.path.dirname(SLEEPS_LOG_PATH), exist_ok=True)
        open(SLEEPS_LOG_PATH, 'a').close()
    if os.path.getsize(SLEEPS_LOG_PATH) < 2:
        return {"latest_sleep": None}
    with open(SLEEPS_LOG_PATH, "rb") as file:
        file.seek(-2, 2)  # Jump to the second last byte.
        while file.read(1) != b'\n':  # Until EOL is found...
            file.seek(-2, 1)  # ...jump back the read byte plus one more.
        last_line = file.readline().decode().strip()  # Read last line.
    return {"latest_sleep": last_line}


@app.get("/alarm/time/{date}")
async def alarm_time(date: str):
    """
    Endpoint to calculate the alarm time based on the latest sleep time and the requested date.
    :param date: The requested date in the format YYYYMMDD.
    """
    slept_at = await latest_sleep()

    if slept_at is None or "latest_sleep" not in slept_at:
        return DEFAULT_ALARM_TIME

    # get 24 hour time from seconds from epoch
    slept_clock_time = time.localtime(float(slept_at["latest_sleep"]))
    requested_date = time.strptime(date, "%Y%m%d")

    # Check if the requested date is valid for calculating the alarm time
    if (slept_clock_time.tm_yday >= requested_date.tm_yday
            or slept_clock_time.tm_yday < (requested_date.tm_yday - 1)):
        return DEFAULT_ALARM_TIME
    else:
        slept_hour = slept_clock_time.tm_hour
        # Determine the alarm time based on the hour the user went to sleep
        if 9 <= slept_hour <= 23:
            calc_alarm_time = "6:30"
        elif slept_hour >= 0 and (slept_hour + 7) < 9:
            calc_alarm_time = f"{slept_hour + 7}:00"
        else:
            return DEFAULT_ALARM_TIME
        return { "alarm_time": f"{calc_alarm_time}"}

    return {"message":"shouldn't be here"}


def start():
    """
    Launched with `poetry run start` at root level.
    Starts the Uvicorn server to run the FastAPI application.
    """
    uvicorn.run("main:app", reload=True)
