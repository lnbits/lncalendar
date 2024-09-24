from typing import Optional

from fastapi import Query
from pydantic import BaseModel


class CreateSchedule(BaseModel):
    wallet: str = Query(...)
    name: str = Query(...)
    start_day: int = Query(..., ge=0, le=6)
    end_day: int = Query(..., ge=0, le=6)
    start_time: str = Query(...)
    end_time: str = Query(...)
    amount: int = Query(..., ge=1)


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


class Schedule(BaseModel):
    id: str
    wallet: str
    name: str
    start_day: int
    end_day: int
    start_time: str
    end_time: str
    amount: int

    @property
    def availabe_days(self):
        return list(range(self.start_day, self.end_day + 1))


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
    time: int
