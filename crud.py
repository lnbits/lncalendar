from datetime import datetime, timedelta
from typing import Optional, Union

from lnbits.db import Database
from lnbits.helpers import urlsafe_short_hash

from .models import (
    Appointment,
    CreateAppointment,
    CreateSchedule,
    CreateUnavailableTime,
    Schedule,
    UnavailableTime,
)

db = Database("ext_lncalendar")


async def create_schedule(wallet_id: str, data: CreateSchedule) -> Schedule:
    schedule_id = urlsafe_short_hash()
    # hardcode timeslot for now
    timeslot = 30
    schedule = Schedule(
        id=schedule_id,
        wallet=wallet_id,
        name=data.name,
        start_day=data.start_day,
        end_day=data.end_day,
        start_time=data.start_time,
        end_time=data.end_time,
        amount=data.amount,
        timeslot=timeslot,
    )
    await db.insert("lncalendar.schedule", schedule)
    return schedule


async def update_schedule(schedule: Schedule) -> Schedule:
    await db.update("lncalendar.schedule", schedule)
    return schedule


async def get_schedule(schedule_id: str) -> Optional[Schedule]:
    return await db.fetchone(
        "SELECT * FROM lncalendar.schedule WHERE id = :id",
        {"id": schedule_id},
        Schedule,
    )


async def get_schedules(wallet_ids: Union[str, list[str]]) -> list[Schedule]:
    if isinstance(wallet_ids, str):
        wallet_ids = [wallet_ids]
    q = ",".join([f"'{wallet_id}'" for wallet_id in wallet_ids])
    return await db.fetchall(
        f"SELECT * FROM lncalendar.schedule WHERE wallet IN ({q})", model=Schedule
    )


async def delete_schedule(schedule_id: str) -> None:
    await db.execute(
        "DELETE FROM lncalendar.schedule WHERE id = :id", {"id": schedule_id}
    )


async def create_appointment(
    schedule_id: str, payment_hash: str, data: CreateAppointment
) -> Appointment:
    appointment_id = payment_hash
    appointment = Appointment(
        id=appointment_id,
        name=data.name,
        email=data.email,
        info=data.info,
        start_time=data.start_time,
        end_time=data.end_time,
        schedule=schedule_id,
        paid=False,
        created_at=datetime.now(),
    )
    await db.insert("lncalendar.appointment", appointment)
    return appointment


async def get_appointment(appointment_id: str) -> Optional[Appointment]:
    return await db.fetchone(
        "SELECT * FROM lncalendar.appointment WHERE id = :id",
        {"id": appointment_id},
        Appointment,
    )


async def get_appointments(schedule_id: str) -> list[Appointment]:
    return await db.fetchall(
        "SELECT * FROM lncalendar.appointment WHERE schedule = :schedule",
        {"schedule": schedule_id},
        Appointment,
    )


async def get_appointments_wallets(
    wallet_ids: Union[str, list[str]],
) -> list[Appointment]:
    if isinstance(wallet_ids, str):
        wallet_ids = [wallet_ids]

    schedules = await get_schedules(wallet_ids)
    if not schedules:
        return []

    schedule_ids = [schedule.id for schedule in schedules]

    q = ",".join([f"'{schedule_id}'" for schedule_id in schedule_ids])
    return await db.fetchall(
        f"SELECT * FROM lncalendar.appointment WHERE schedule IN ({q})",
        model=Appointment,
    )


async def set_appointment_paid(appointment_id: str) -> None:
    await db.execute(
        "UPDATE lncalendar.appointment SET paid = true WHERE id = :id",
        {"id": appointment_id},
    )


async def purge_appointments(schedule_id: str) -> None:
    time_diff = datetime.now() - timedelta(hours=24)
    tsph = db.timestamp_placeholder("diff")
    await db.execute(
        f"""
        DELETE FROM lncalendar.appointment
        WHERE schedule = :schedule AND paid = false AND time < {tsph}
        """,
        {"schedule": schedule_id, "diff": time_diff.timestamp()},
    )


async def delete_appointment(appointment_id: str) -> None:
    await db.execute(
        "DELETE FROM lncalendar.appointment WHERE id = :id", {"id": appointment_id}
    )


## UnavailableTime CRUD
async def create_unavailable_time(data: CreateUnavailableTime) -> UnavailableTime:
    unavailable_time_id = urlsafe_short_hash()
    unavailable_time = UnavailableTime(
        id=unavailable_time_id,
        name=data.name or "",
        start_time=data.start_time,
        end_time=data.end_time or data.start_time,
        schedule=data.schedule,
        created_at=datetime.now(),
    )
    await db.insert("lncalendar.unavailable", unavailable_time)
    return unavailable_time


async def get_unavailable_time(unavailable_time_id: str) -> Optional[UnavailableTime]:
    return await db.fetchone(
        "SELECT * FROM lncalendar.unavailable WHERE id = :id",
        {"id": unavailable_time_id},
        UnavailableTime,
    )


async def get_unavailable_times(schedule_id: str) -> list[UnavailableTime]:
    return await db.fetchall(
        "SELECT * FROM lncalendar.unavailable WHERE schedule = :schedule",
        {"schedule": schedule_id},
        UnavailableTime,
    )


async def delete_unavailable_time(unavailable_time_id: str) -> None:
    await db.execute(
        "DELETE FROM lncalendar.unavailable WHERE id = :id", {"id": unavailable_time_id}
    )
