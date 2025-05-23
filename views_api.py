from http import HTTPStatus

from fastapi import APIRouter, Depends, Query
from fastapi.exceptions import HTTPException
from lnbits.core.crud import get_standalone_payment, get_user
from lnbits.core.models import WalletTypeInfo
from lnbits.core.services import create_invoice
from lnbits.decorators import (
    require_admin_key,
    require_invoice_key,
)

from .crud import (
    create_appointment,
    create_schedule,
    create_unavailable_time,
    delete_schedule,
    delete_unavailable_time,
    get_appointments,
    get_appointments_wallets,
    get_schedule,
    get_schedules,
    get_unavailable_times,
    purge_appointments,
    set_appointment_paid,
    update_schedule,
)
from .models import CreateAppointment, CreateSchedule, CreateUnavailableTime

lncalendar_api_router = APIRouter()


@lncalendar_api_router.get("/api/v1/schedule")
async def api_schedules(
    wallet: WalletTypeInfo = Depends(require_invoice_key),
    all_wallets: bool = Query(False),
):
    wallet_ids = [wallet.wallet.id]

    if all_wallets:
        user = await get_user(wallet.wallet.user)
        wallet_ids = user.wallet_ids if user else []

    return [
        {**schedule.dict(), "available_days": schedule.available_days}
        for schedule in await get_schedules(wallet_ids)
    ]


@lncalendar_api_router.post("/api/v1/schedule")
async def api_schedule_create(
    data: CreateSchedule, wallet: WalletTypeInfo = Depends(require_admin_key)
):
    schedule = await create_schedule(wallet_id=wallet.wallet.id, data=data)
    return schedule.dict()


@lncalendar_api_router.put("/api/v1/schedule/{schedule_id}")
async def api_schedule_update(
    schedule_id: str,
    data: CreateSchedule,
    wallet: WalletTypeInfo = Depends(require_invoice_key),
):
    schedule = await get_schedule(schedule_id)

    if not schedule:
        raise HTTPException(HTTPStatus.NOT_FOUND, "Schedule does not exist.")

    if schedule.wallet != wallet.wallet.id:
        raise HTTPException(HTTPStatus.FORBIDDEN, "Not your schedule.")

    for k, v in data.dict().items():
        if v is not None:
            setattr(schedule, k, v)

    schedule = await update_schedule(schedule)
    return {**schedule.dict(), "available_days": schedule.available_days}


@lncalendar_api_router.delete("/api/v1/schedule/{schedule_id}")
async def api_schedule_delete(
    schedule_id: str, wallet: WalletTypeInfo = Depends(require_admin_key)
):
    schedule = await get_schedule(schedule_id)

    if not schedule:
        raise HTTPException(HTTPStatus.NOT_FOUND, "Schedule does not exist.")

    if schedule.wallet != wallet.wallet.id:
        raise HTTPException(HTTPStatus.FORBIDDEN, "Not your schedule.")

    await delete_schedule(schedule_id)
    return "", HTTPStatus.NO_CONTENT


## Appointment API
@lncalendar_api_router.post("/api/v1/appointment")
async def api_appointment_create(data: CreateAppointment):
    schedule = await get_schedule(data.schedule)
    if not schedule:
        raise HTTPException(HTTPStatus.NOT_FOUND, "Schedule does not exist.")

    payment = await create_invoice(
        wallet_id=schedule.wallet,
        amount=schedule.amount,  # type: ignore
        memo=f"{schedule.name}",
        currency=schedule.currency,
        extra={"tag": "lncalendar", "name": data.name, "email": data.email},
    )
    await create_appointment(
        schedule_id=data.schedule, payment_hash=payment.payment_hash, data=data
    )

    return {"payment_hash": payment.payment_hash, "payment_request": payment.bolt11}


@lncalendar_api_router.get("/api/v1/appointment/purge/{schedule_id}")
async def api_purge_appointments(schedule_id: str):
    schedule = await get_schedule(schedule_id)
    if not schedule:
        raise HTTPException(HTTPStatus.NOT_FOUND, "Schedule does not exist.")
    return await purge_appointments(schedule_id)


@lncalendar_api_router.get("/api/v1/appointment/{schedule_id}/{payment_hash}")
async def api_appointment_check_invoice(schedule_id: str, payment_hash: str):
    schedule = await get_schedule(schedule_id)
    if not schedule:
        raise HTTPException(HTTPStatus.NOT_FOUND, "Schedule does not exist.")
    payment = await get_standalone_payment(payment_hash, incoming=True)
    if not payment:
        raise HTTPException(HTTPStatus.NOT_FOUND, "Payment does not exist")
    if payment.success:
        await set_appointment_paid(payment_hash)
    return {"paid": payment.success}


@lncalendar_api_router.get("/api/v1/appointment/{schedule_id}")
async def api_get_appointments_schedule(schedule_id: str):
    return await get_appointments(schedule_id)


@lncalendar_api_router.get("/api/v1/appointment")
async def api_get_all_appointments(
    wallet: WalletTypeInfo = Depends(require_invoice_key),
):
    user = await get_user(wallet.wallet.user)
    wallet_ids = user.wallet_ids if user else []
    return await get_appointments_wallets(wallet_ids)


## Unavailable Time API
@lncalendar_api_router.post("/api/v1/unavailable")
async def api_unavailable_create(
    data: CreateUnavailableTime, wallet: WalletTypeInfo = Depends(require_admin_key)
):
    schedule = await get_schedule(data.schedule)
    if not schedule:
        raise HTTPException(HTTPStatus.NOT_FOUND, "Schedule does not exist.")
    if schedule.wallet != wallet.wallet.id:
        raise HTTPException(HTTPStatus.FORBIDDEN, "Not your schedule.")
    unavailable = await create_unavailable_time(data=data)
    assert unavailable, "Newly created unavailable time couldn't be retrieved"
    return unavailable


@lncalendar_api_router.get("/api/v1/unavailable/{schedule_id}")
async def api_unavailable_get(schedule_id: str):
    schedule = await get_schedule(schedule_id)
    if not schedule:
        raise HTTPException(HTTPStatus.NOT_FOUND, "Schedule does not exist.")
    return await get_unavailable_times(schedule_id)


@lncalendar_api_router.delete("/api/v1/unavailable/{schedule_id}/{unavailable_id}")
async def api_unavailable_delete(
    schedule_id: str,
    unavailable_id: str,
    wallet: WalletTypeInfo = Depends(require_admin_key),
):
    schedule = await get_schedule(schedule_id)
    if not schedule:
        raise HTTPException(HTTPStatus.NOT_FOUND, "Schedule does not exist.")
    if schedule.wallet != wallet.wallet.id:
        raise HTTPException(HTTPStatus.FORBIDDEN, "Not your schedule.")
    await delete_unavailable_time(unavailable_id)
    return "", HTTPStatus.NO_CONTENT
