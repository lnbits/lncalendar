from datetime import datetime
from typing import Optional

from fastapi import Query
from lnbits.utils.exchange_rates import allowed_currencies
from pydantic import BaseModel, Field
from zoneinfo import available_timezones

# A set of all available time zone names
TIMEZONES = sorted(available_timezones())

print("### Available timezones:", TIMEZONES)


class CreateSchedule(BaseModel):
    wallet: str = Query(...)
    name: str = Query(...)
    timezone: str = Query(..., examples=TIMEZONES)
    start_day: int = Query(..., ge=0, le=6)
    end_day: int = Query(..., ge=0, le=6)
    start_time: str = Query(...)
    end_time: str = Query(...)
    amount: int = Query(..., ge=1)
    currency: str = Query("sat", regex="^[a-zA-Z]{3}$")

    def check(self):
        if self.amount <= 0:
            raise ValueError("Amount must be greater than 0.")
        if not (0 <= self.start_day <= 6):
            raise ValueError(f"Invalid start_day: {self.start_day}")
        if not (0 <= self.end_day <= 6):
            raise ValueError(f"Invalid end_day: {self.end_day}")
        if not (self.start_day <= self.end_day):
            raise ValueError("Start day must be less than or equal to end day.")

        if self.timezone not in TIMEZONES:
            raise ValueError(f"Invalid timezone: {self.timezone}")

        t1 = datetime.strptime(self.start_time, "%H:%M").time()
        t2 = datetime.strptime(self.end_time, "%H:%M").time()

        if t1 >= t2:
            raise ValueError("Start time must be less than end time.")

        currencies = allowed_currencies()
        currencies.append("SAT")
        if self.currency.upper() not in currencies:
            raise ValueError(f"Currency {self.currency} not allowed.")


class CreateUnavailableTime(BaseModel):
    start_time: str = Query(...)
    end_time: Optional[str] = Query(None)
    schedule: str = Query(...)


class CreateAppointment(BaseModel):
    name: str = Query(...)
    email: str = Query(None)
    info: str = Query(None)
    start_time: str = Query(...)
    end_time: str = Query(...)
    schedule: str = Query(...)

    def check(self, apoiment_duration_minutes: int):
        t1 = datetime.strptime(self.start_time, "%Y/%m/%d %H:%M").time()
        t2 = datetime.strptime(self.end_time, "%Y/%m/%d %H:%M").time()

        if t1 >= t2:
            raise ValueError("Start time must be less than end time.")

        t1_total_seconds = t1.hour * 60 + t1.minute
        t2_total_seconds = t2.hour * 60 + t2.minute

        if t2_total_seconds - t1_total_seconds != apoiment_duration_minutes:
            raise ValueError(
                f"Appointment duration must be {apoiment_duration_minutes} minutes."
            )


class ScheduleExtra(BaseModel):
    currency: str = "sat"
    timezone: str = "UTC"
    apoiment_duration_minutes: int = 30


class Schedule(BaseModel):
    id: str
    wallet: str
    name: str
    start_day: int
    end_day: int
    start_time: str
    end_time: str
    amount: int
    available_days: list[int] = Field(default=[], no_database=True)

    extra: ScheduleExtra = ScheduleExtra()

    def __init__(self, **data):
        super().__init__(**data)
        self.available_days = list(range(self.start_day, self.end_day + 1))


class UnavailableTime(BaseModel):
    id: str
    start_time: str
    end_time: str
    schedule: str


class Appointment(BaseModel):
    id: str
    name: str
    email: Optional[str]
    info: Optional[str]
    start_time: str
    end_time: str
    schedule: str
    paid: bool


class AppointmentPaymentRequest(BaseModel):
    payment_hash: str
    payment_request: str


class AppointmentPaymentStatus(BaseModel):
    paid: bool
