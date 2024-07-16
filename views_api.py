from http import HTTPStatus

from fastapi import Depends, Query
from fastapi.exceptions import HTTPException

from loguru import logger

from lnbits.core.crud import get_user
from lnbits.core.services import create_invoice
from lnbits.core.views.api import api_payment
from lnbits.decorators import (
    WalletTypeInfo,
    require_admin_key,
    require_invoice_key,
)

from . import lncalendar_ext
from .crud import (
    get_schedules,
    get_schedule,
    create_schedule,
    delete_schedule,
    update_schedule,
    create_appointment,
    set_appointment_paid,
    get_appointments,
    get_appointments_wallets,
    purge_appointments,
    create_unavailable_time,
    get_unavailable_times,
    delete_unavailable_time,
)
from .models import Schedule, CreateSchedule, CreateUnavailableTime, CreateAppointment


## Schedule API
@lncalendar_ext.get("/api/v1/schedule")
async def api_schedules(
    wallet: WalletTypeInfo = Depends(require_invoice_key),
    all_wallets: bool = Query(False),
):
    wallet_ids = [wallet.wallet.id]

    if all_wallets:
        user = await get_user(wallet.wallet.user)
        wallet_ids = user.wallet_ids if user else []

    return [
        {**schedule.dict(), "available_days": schedule.availabe_days}
        for schedule in await get_schedules(wallet_ids)
    ]


@lncalendar_ext.post("/api/v1/schedule")
async def api_schedule_create(
    data: CreateSchedule, wallet: WalletTypeInfo = Depends(require_admin_key)
):
    schedule = await create_schedule(wallet_id=wallet.wallet.id, data=data)
    return schedule.dict()


@lncalendar_ext.put("/api/v1/schedule/{schedule_id}")
async def api_schedule_update(
    schedule_id: str,
    data: CreateSchedule,
    wallet: WalletTypeInfo = Depends(require_invoice_key),
):
    schedule = await get_schedule(schedule_id)

    if not schedule:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Schedule does not exist."
        )

    if schedule.wallet != wallet.wallet.id:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN, detail="Not your schedule."
        )

    schedule = await update_schedule(schedule_id, data)
    return {**schedule.dict(), "available_days": schedule.availabe_days}


@lncalendar_ext.delete("/api/v1/schedule/{schedule_id}")
async def api_schedule_delete(
    schedule_id: str, wallet: WalletTypeInfo = Depends(require_admin_key)
):
    schedule = await get_schedule(schedule_id)

    if not schedule:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Schedule does not exist."
        )

    if schedule.wallet != wallet.wallet.id:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN, detail="Not your schedule."
        )

    await delete_schedule(schedule_id)
    return "", HTTPStatus.NO_CONTENT


## Appointment API
@lncalendar_ext.post("/api/v1/appointment")
async def api_appointment_create(data: CreateAppointment):
    schedule = await get_schedule(data.schedule)
    if not schedule:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Schedule does not exist."
        )
    try:
        payment_hash, payment_request = await create_invoice(
            wallet_id=schedule.wallet,
            amount=schedule.amount,  # type: ignore
            memo=f"{schedule.name}",
            extra={"tag": "lncalendar", "name": data.name, "email": data.email},
        )
        await create_appointment(
            schedule_id=data.schedule, payment_hash=payment_hash, data=data
        )
        print(payment_hash, payment_request)
    except Exception as e:
        raise HTTPException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=str(e))
    return {"payment_hash": payment_hash, "payment_request": payment_request}


@lncalendar_ext.get("/api/v1/appointment/purge/{schedule_id}")
async def api_purge_appointments(schedule_id: str):
    schedule = await get_schedule(schedule_id)
    if not schedule:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Schedule does not exist."
        )
    return await purge_appointments(schedule_id)


@lncalendar_ext.get("/api/v1/appointment/{schedule_id}/{payment_hash}")
async def api_appointment_check_invoice(schedule_id: str, payment_hash: str):
    schedule = await get_schedule(schedule_id)
    if not schedule:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Schedule does not exist."
        )

    try:
        status = await api_payment(payment_hash)
        if status["paid"]:
            await set_appointment_paid(payment_hash)
            return {"paid": True}

    except Exception:
        return {"paid": False}
    return {"paid": False}


@lncalendar_ext.get("/api/v1/appointment/{schedule_id}")
async def api_get_appointments_schedule(schedule_id: str):
    appointments = await get_appointments(schedule_id)

    if not appointments:
        return []
    return appointments


@lncalendar_ext.get("/api/v1/appointment")
async def api_get_all_appointments(
    wallet: WalletTypeInfo = Depends(require_invoice_key),
):
    user = await get_user(wallet.wallet.user)
    wallet_ids = user.wallet_ids if user else []
    return await get_appointments_wallets(wallet_ids)


## Unavailable Time API
@lncalendar_ext.post("/api/v1/unavailable")
async def api_unavailable_create(
    data: CreateUnavailableTime, wallet: WalletTypeInfo = Depends(require_admin_key)
):
    schedule = await get_schedule(data.schedule)
    if not schedule:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Schedule does not exist."
        )
    if schedule.wallet != wallet.wallet.id:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN, detail="Not your schedule."
        )
    unavailable = await create_unavailable_time(data=data)
    assert unavailable, "Newly created unavailable time couldn't be retrieved"
    return unavailable


@lncalendar_ext.get("/api/v1/unavailable/{schedule_id}")
async def api_unavailable_get(schedule_id: str):
    schedule = await get_schedule(schedule_id)
    if not schedule:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Schedule does not exist."
        )
    return await get_unavailable_times(schedule_id)


@lncalendar_ext.delete("/api/v1/unavailable/{schedule_id}/{unavailable_id}")
async def api_unavailable_delete(
    schedule_id: str,
    unavailable_id: str,
    wallet: WalletTypeInfo = Depends(require_admin_key),
):
    schedule = await get_schedule(schedule_id)
    if not schedule:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Schedule does not exist."
        )
    if schedule.wallet != wallet.wallet.id:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN, detail="Not your schedule."
        )
    await delete_unavailable_time(unavailable_id)
    return "", HTTPStatus.NO_CONTENT
