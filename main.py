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
    slept_clock_time = time.localtime(float(slept_at))
    # check_permissions(SLEEPS_LOG_PATH)
    if not os.path.exists(SLEEPS_LOG_PATH):
        os.makedirs(os.path.dirname(SLEEPS_LOG_PATH), exist_ok=True)
        with open(SLEEPS_LOG_PATH, 'a') as file:
            # write two empty lines so reading becomes easier
            file.write("\n")
            file.write("\n")
    with open(SLEEPS_LOG_PATH, "a") as file:
        file.write(f"{slept_at}\n")
    return {"message": "Good night!", "slept_at": slept_at, "slept_clock_time": slept_clock_time}


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
    slept_clock_time = time.localtime(float(last_line))
    return {"latest_sleep": last_line, "slept_clock_time": slept_clock_time}


@app.get("/alarm/time/{date}")
async def alarm_time(date: str):
    """
    Endpoint to calculate the alarm time based on the latest sleep time and the requested date.
    :param date: The requested date in the format YYYYMMDD.
    """
    slept_at = await latest_sleep()

    requested_date = time.strptime(date, "%Y%m%d")
    if slept_at is None or "latest_sleep" not in slept_at:
        print("couldn't find latest sleep time")
        return {**DEFAULT_ALARM_TIME, "reason": "No sleep time found", "slept_clock_time": "None", "requested_date": requested_date}

    # get 24 hour time from seconds from epoch
    slept_clock_time = time.localtime(float(slept_at["latest_sleep"]))

    # Check if the requested date is valid for calculating the alarm time
    slept_after_requested_day = slept_clock_time.tm_yday > requested_date.tm_yday
    slept_before_one_day_requested_day = slept_clock_time.tm_yday < requested_date.tm_yday - 1
    if slept_after_requested_day or slept_before_one_day_requested_day:
        print("invalid date")
        return {**DEFAULT_ALARM_TIME, "reason": "Invalid date", "slept_clock_time": slept_clock_time, "requested_date": requested_date}
    else:
        slept_hour = slept_clock_time.tm_hour
        # Determine the alarm time based on the hour the user went to sleep
        if 9 <= slept_hour <= 23:
            calc_alarm_time = "6:30"
            reason = "Slept early enough, default to earliest time"
        elif slept_hour >= 0 and (slept_hour + 7) < 9:
            if slept_clock_time.tm_yday == requested_date.tm_yday:
                # slept after midnight
                minute = slept_clock_time.tm_min if slept_clock_time.tm_min >= 10 else f"0{slept_clock_time.tm_min}"
                calc_alarm_time = f"{slept_hour + 7}:{minute}"
                reason = "gotta sleep 7 hours"
            else:
                reason = "Slept after midnight, but on another day"
                return {**DEFAULT_ALARM_TIME, "reason": reason, "slept_clock_time": slept_clock_time, "requested_date": requested_date}
        else:
            reason = "couldn't recognize case. use default."
            return {**DEFAULT_ALARM_TIME, "reason": reason, slept_clock_time: slept_clock_time}
        return { "alarm_time": f"{calc_alarm_time}", "reason": reason, "slept_clock_time": slept_clock_time, "requested_date": requested_date }



def start():
    """
    Launched with `poetry run start` at root level.
    Starts the Uvicorn server to run the FastAPI application.
    """
    uvicorn.run("main:app", reload=True)
