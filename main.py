import os
import os.path
import time
from datetime import datetime, timedelta
from sqlite3 import connect, Error

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Default alarm time to be used if no specific alarm time is calculated
DEFAULT_ALARM_TIME = {"alarm_time": "09:00", "reason": "Using default alarm time"}
# Path to the log file where sleep times are recorded
JHOP_DB_PATH = os.getenv("JHOP_DB_PATH", "data/sleeps.db")
NECESSARY_SLEEP_HOURS = 7

class AlarmData(BaseModel):
    date: str
    time: str

app = FastAPI()
db_connection = None


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


def init_db():
    global db_connection
    print(f"Checking for db file at {JHOP_DB_PATH}...")
    if not os.path.exists(os.path.dirname(JHOP_DB_PATH)):
        print(f"Creating db file at {JHOP_DB_PATH}...")
        os.makedirs(os.path.dirname(JHOP_DB_PATH), exist_ok=True)
        print(f"Created db file at {JHOP_DB_PATH}...")
    db_connection = connect(JHOP_DB_PATH, check_same_thread=False)
    print("Creating tables")
    cursor = db_connection.cursor()
    # Add table for capturing sleep start times
    cursor.execute("""
            CREATE TABLE IF NOT EXISTS sleep_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sleep_time REAL,
                type TEXT,
                expected_duration INTEGER,
                actual_duration INTEGER
            )
        """)
    # Add table for capturing alarm times
    cursor.execute("""
            CREATE TABLE IF NOT EXISTS alarm_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                alarm_time FLOAT,
                UNIQUE(date, alarm_time)
            )
        """)
    db_connection.commit()
    print("Tables created")

init_db()

@app.post("/sleep")
async def sleep(sleep_type: str = None):
    """
    Endpoint to log the current time as the time the user went to sleep.
    """
    slept_at = time.time()
    slept_clock_time = time.localtime(float(slept_at))
    expected_duration = 0
    if sleep_type is None or sleep_type == "night":
        expected_duration = 7 * 60
    elif sleep_type == "short_nap":
        expected_duration = 30
    elif sleep_type == "long_nap":
        expected_duration = 60
    try:
        cursor = db_connection.cursor()
        cursor.execute("INSERT INTO sleep_data (sleep_time, type, expected_duration) VALUES (?, ?, ?)", (slept_at, "night" if sleep_type is None else sleep_type, expected_duration, ))
        db_connection.commit()

        alarm_date, alarm_time_to_set = determine_alarm_time(slept_at, slept_clock_time, sleep_type, expected_duration)

        print(f"Setting alarm to {alarm_date} {alarm_time_to_set}")
        alarm_data = AlarmData(date=alarm_date, time=str(alarm_time_to_set))
        await set_alarm(alarm_data)

        return {"message": "Good night!", "slept_at": slept_at, "slept_clock_time": slept_clock_time,
                "expected_duration": expected_duration,
                "alarm_date": alarm_date, "alarm_time_to_set": alarm_time_to_set, "sleep_type": sleep_type}
    except Error as e:
        return {"error": str(e)}

def determine_alarm_time(slept_at, slept_clock_time, sleep_type, expected_duration):
    """
    Determines the appropriate alarm date and time based on sleep type and duration.
    """
    if sleep_type is None or sleep_type == "night":
        # If the user went to sleep between midnight and 9 AM, the alarm_date is the same day
        # Otherwise, the alarm_date is the next day
        alarm_hour = slept_clock_time.tm_hour
        if 0 <= alarm_hour < 9:
            alarm_date = time.strftime("%Y%m%d", slept_clock_time)  # Same date as slept_clock_time
        else:
            alarm_date = time.strftime("%Y%m%d", time.localtime(slept_at + 24 * 60 * 60))  # Next day

        # Calculate the alarm time based on sleep duration and logic
        calculated_alarm_time, _ = calculate_alarm_time(slept_clock_time, time.strptime(alarm_date, "%Y%m%d"))
        if calculated_alarm_time is None:
            alarm_time_to_set = DEFAULT_ALARM_TIME["alarm_time"]
        else:
            alarm_time_to_set = calculated_alarm_time
    else:
        alarm_target_time = slept_at + (expected_duration * 60)
        alarm_date = time.strftime("%Y%m%d", time.localtime(alarm_target_time))
        alarm_time_to_set = time.strftime("%H:%M", time.localtime(alarm_target_time))

    return alarm_date, alarm_time_to_set
@app.get("/sleep/latest")
async def latest_sleep():
    """
    Endpoint to retrieve the latest recorded sleep time from the database.
    """
    try:
        cursor = db_connection.cursor()
        cursor.execute("SELECT sleep_time FROM sleep_data ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        if row is None:
            return {"latest_sleep": None}
        slept_at = row[0]
        slept_clock_time = time.localtime(float(slept_at))
        return {"latest_sleep": slept_at, "slept_clock_time": slept_clock_time}
    except Error as e:
        return {"error": str(e)}


@app.post("/alarm/")
async def set_alarm(alarm_data: AlarmData):
    """
    Endpoint to set an alarm for a specified date.
    :param alarm_data: The alarm data to set.
    """
    await validate_alarm_input(alarm_data)
    # Convert provided str time to epoch
    provided_time_as_epoch = await get_provided_time_as_epoch(alarm_data)
    try:
        cursor = db_connection.cursor()
        cursor.execute("""
            INSERT INTO alarm_data (date, alarm_time)
            VALUES (?, ?)
        """, (alarm_data.date, provided_time_as_epoch))
        db_connection.commit()
        return {"message": "Alarm set successfully", "date": alarm_data.date, "alarm_time": alarm_data.time}
    except Error as e:
        return {"error": str(e)}


async def get_provided_time_as_epoch(alarm_data):
    provided_time_as_epoch = time.mktime(time
                                         .strptime(f"{alarm_data.date} {alarm_data.time}", "%Y%m%d %H:%M"))
    return provided_time_as_epoch


@app.delete("/alarm/")
async def delete_alarm(alarm_data: AlarmData):
    """
    Deletes an alarm record from the system. This endpoint handles the deletion
    of specific alarm entries provided via the `alarm_data` object. It ensures
    that the specified alarm is properly identified and removed based on the
    information provided.

    :param alarm_data: Data object containing details of the alarm to be deleted.
    :type alarm_data: AlarmData
    :return: Response indicating the success or failure of the deletion process.
    :rtype: JSONResponse
    """
    await validate_alarm_input(alarm_data)

    provided_time_as_epoch = await get_provided_time_as_epoch(alarm_data)
    try:
        # Delete the record if it exists
        cursor = db_connection.cursor()
        cursor.execute("""
            DELETE FROM alarm_data
            WHERE date = ?
            AND alarm_time = ?
        """, (alarm_data.date, provided_time_as_epoch))
        # Get number of deleted rows
        deleted_rows = cursor.rowcount
        if deleted_rows == 0:
            return {"message": "Alarm not found", "success": False}
        db_connection.commit()
        return {"message": "Alarm deleted successfully", "success": True, "date": alarm_data.date, "alarm_time": alarm_data.time}
    except Error as e:
        return {"error": str(e)}


async def validate_alarm_input(alarm_data):
    if alarm_data.date is None or len(alarm_data.date) != 8:
        raise HTTPException(status_code=400, detail=f"Invalid date. Provided date: {alarm_data.date}")
    if alarm_data.time is None or len(alarm_data.time) != 5:
        raise HTTPException(status_code=400, detail=f"Invalid time. Provided time: {alarm_data.time}")


def calculate_alarm_time(slept_clock_time, requested_date):
    slept_hour = slept_clock_time.tm_hour
    slept_minute = slept_clock_time.tm_min
    if 9 <= slept_hour < 23:
        return "6:30", "Slept early enough, default to earliest time"
    elif slept_hour == 23 or (0 <= (slept_hour + NECESSARY_SLEEP_HOURS) < 9 and slept_clock_time.tm_yday == requested_date.tm_yday):
        minute = f"{slept_minute}"
        return f"{slept_hour + 7}:{minute}", "Slept after midnight, calculated 7 hours"
    return None, "Couldn't recognize the case, using default."


@app.get("/alarm/time/{date}")
async def alarm_time(date: str) -> dict:
    """
    Fetches or calculates an appropriate alarm time for a given date based on user sleep patterns and prior alarm data.
    """

    def fetch_existing_alarm(cursor, date, adjusted_time):
        cursor.execute("""
            SELECT alarm_time
            FROM alarm_data
            WHERE date = ?
            AND (alarm_time >= ?)
            ORDER BY alarm_time DESC
        """, (date, adjusted_time))
        return cursor.fetchone()

    def is_invalid_date(slept_clock_time, requested_date):
        slept_day = slept_clock_time.tm_yday
        requested_day = requested_date.tm_yday
        return slept_day > requested_day or slept_day < requested_day - 1


    try:
        cursor = db_connection.cursor()
    except Error as e:
        return {"error": "Database cursor initialization failed", "details": str(e)}

    current_time = time.time()
    try:
        requested_date = time.strptime(date, "%Y%m%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Expected YYYYMMDD.")

    adjusted_time = (datetime.fromtimestamp(current_time) - timedelta(minutes=15)).timestamp()
    existing_alarm = fetch_existing_alarm(cursor, date, adjusted_time)
    if existing_alarm is not None:
        return {
            "alarm_time": existing_alarm[0],
            "requested_date": requested_date,
            "reason": "Existing alarm",
        }

    # Fetch sleep data
    try:
        slept_at = await latest_sleep()
    except Exception as e:
        return {"error": "Failed to fetch latest sleep time", "details": str(e)}


    if not isinstance(slept_at, dict) or "latest_sleep" not in slept_at:
        return {**DEFAULT_ALARM_TIME, "reason": "No sleep time found", "slept_clock_time": "None",
                "requested_date": requested_date}

    # Process sleep time
    slept_clock_time = time.localtime(float(slept_at["latest_sleep"]))
    if is_invalid_date(slept_clock_time, requested_date):
        return {**DEFAULT_ALARM_TIME, "reason": "Invalid date", "slept_clock_time": slept_clock_time,
                "requested_date": requested_date}

    # Calculate alarm time
    calculated_alarm_time, reason = calculate_alarm_time(slept_clock_time, requested_date)
    if calculated_alarm_time:
        return {
            "alarm_time": calculated_alarm_time,
            "reason": reason,
            "slept_clock_time": slept_clock_time,
            "requested_date": requested_date,
        }

    return {**DEFAULT_ALARM_TIME, "reason": reason, "slept_clock_time": slept_clock_time,
            "requested_date": requested_date}

def close_db():
    """
    Closes the database connection when the application stops.
    """
    if db_connection is not None:
        db_connection.close()

def start():
    """
    Launched with `poetry run start` at root level.
    Starts the Uvicorn server to run the FastAPI application.
    """
    import atexit
    atexit.register(close_db)
    uvicorn.run("main:app", reload=True)
