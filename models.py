from datetime import datetime
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
    amount: float = Query(..., ge=0)
    timeslot: int = Query(30, ge=5)
    currency: str = Query('sat')


class CreateUnavailableTime(BaseModel):
    start_time: str = Query(...)
    end_time: Optional[str] = Query(None)
    schedule: str = Query(...)
    name: Optional[str] = Query(None)


class CreateAppointment(BaseModel):
    name: str = Query(...)
    email: str = Query(None)
    nostr_pubkey: str = Query(None)
    info: str = Query(None)
    start_time: str = Query(...)
    end_time: str = Query(...)
    schedule: str = Query(...)

class UpdateAppointment(BaseModel):
    name: Optional[str] = Query(None)
    email: Optional[str] = Query(None)
    nostr_pubkey: Optional[str] = Query(None)
    info: Optional[str] = Query(None)
    start_time: Optional[str] = Query(None)
    end_time: Optional[str] = Query(None)
    schedule: Optional[str] = Query(None)


class Schedule(BaseModel):
    id: str
    wallet: str
    name: str
    start_day: int
    end_day: int
    start_time: str
    end_time: str
    amount: float
    timeslot: int
    currency: str

    @property
    def availabe_days(self):
        return list(range(self.start_day, self.end_day + 1))


class UnavailableTime(BaseModel):
    id: str
    name: str
    start_time: str
    end_time: str
    schedule: str
    created_at: datetime


class Appointment(BaseModel):
    id: str
    name: str
    email: Optional[str]
    nostr_pubkey: Optional[str]
    info: Optional[str]
    start_time: str
    end_time: str
    schedule: str
    paid: bool
    created_at: datetime
