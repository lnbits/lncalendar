from http import HTTPStatus

from fastapi import APIRouter, Depends, Query
from fastapi.exceptions import HTTPException

from lnbits.core.crud import get_standalone_payment, get_user
from lnbits.core.models import User, WalletTypeInfo
from lnbits.core.services import create_invoice
from lnbits.decorators import (
    check_admin,
    check_user_exists,
    require_admin_key,
    require_invoice_key,
)
from lnbits.utils.exchange_rates import (
    allowed_currencies,
    fiat_amount_as_satoshis,
)

from .crud import (
    create_appointment,
    create_schedule,
    create_unavailable_time,
    delete_appointment,
    delete_calendar_settings,
    delete_schedule,
    delete_unavailable_time,
    get_appointment,
    get_appointments,
    get_appointments_wallets,
    get_or_create_calendar_settings,
    get_schedule,
    get_schedules,
    get_unavailable_times,
    purge_appointments,
    set_appointment_paid,
    update_appointment,
    update_calendar_settings,
    update_schedule,
)
from .helpers import normalize_public_key, parse_nostr_private_key
from .models import (
    CalendarSettings,
    CreateAppointment,
    CreateSchedule,
    CreateUnavailableTime,
    UpdateAppointment,
)
from .services import nostr_send_msg

lncalendar_api_router = APIRouter()


@lncalendar_api_router.get("/api/v1/schedule")
async def api_schedules(
    user: User = Depends(check_user_exists),
    all_wallets: bool = Query(False),
):
    # wallet_ids = [wallet.wallet.id]

    # if all_wallets:
    # user = await get_user(wallet.wallet.user)
    # wallet_ids = user.wallet_ids if user else []
    return [
        {**schedule.dict(), "available_days": schedule.availabe_days}
        for schedule in await get_schedules(user.wallet_ids)
    ]


@lncalendar_api_router.post("/api/v1/schedule")
async def api_schedule_create(
    data: CreateSchedule, user: User = Depends(check_user_exists)
):
    if data.wallet not in user.wallet_ids:
        raise HTTPException(status_code=HTTPStatus.FORBIDDEN, detail="Not your wallet.")

    schedule = await create_schedule(wallet_id=data.wallet, data=data)
    return {**schedule.dict(), "available_days": schedule.availabe_days}


@lncalendar_api_router.put("/api/v1/schedule/{schedule_id}")
async def api_schedule_update(
    schedule_id: str,
    data: CreateSchedule,
    user: User = Depends(check_user_exists),
    # wallet: WalletTypeInfo = Depends(require_invoice_key),
):
    schedule = await get_schedule(schedule_id)

    if not schedule:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Schedule does not exist."
        )

    # if schedule.wallet != wallet.wallet.id:
    #     raise HTTPException(
    #         status_code=HTTPStatus.FORBIDDEN, detail="Not your schedule."
    #     )
    if schedule.wallet not in user.wallet_ids:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN, detail="Not your schedule."
        )

    for k, v in data.dict().items():
        if v is not None:
            setattr(schedule, k, v)

    schedule = await update_schedule(schedule)
    return {**schedule.dict(), "available_days": schedule.availabe_days}


@lncalendar_api_router.delete("/api/v1/schedule/{schedule_id}")
async def api_schedule_delete(
    schedule_id: str, user: User = Depends(check_user_exists),
):
    schedule = await get_schedule(schedule_id)

    if not schedule:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Schedule does not exist."
        )

    if schedule.wallet not in user.wallet_ids:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN, detail="Not your schedule."
        )

    await delete_schedule(schedule_id)
    return "", HTTPStatus.NO_CONTENT


@lncalendar_api_router.get("/api/v1/schedule/{schedule_id}")
async def api_schedule_get(schedule_id: str):
    schedule = await get_schedule(schedule_id)
    if not schedule:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Schedule does not exist."
        )
    return {**schedule.dict(), "available_days": schedule.availabe_days}


## Appointment API
@lncalendar_api_router.post("/api/v1/appointment")
async def api_appointment_create(data: CreateAppointment):
    schedule = await get_schedule(data.schedule)
    if not schedule:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Schedule does not exist."
        )
    try:
        payment = await create_invoice(
            wallet_id=schedule.wallet,
            amount=amount,  # type: ignore
            memo=f"{schedule.name}",
            extra={"tag": "lncalendar", "name": data.name, "email": data.email},
        )
        
        await create_appointment(
            schedule_id=data.schedule, payment_hash=payment.payment_hash, data=data
        )
    except Exception as exc:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=str(exc)
        ) from exc
    return {"payment_hash": payment.payment_hash, "payment_request": payment.bolt11}


@lncalendar_api_router.put("/api/v1/appointment/{appointment_id}")
async def api_appointment_update(
    appointment_id: str,
    data: UpdateAppointment,
    user: User = Depends(check_user_exists),
):
    appointment = await get_appointment(appointment_id)
    if not appointment:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Appointment does not exist."
        )
    schedule = await get_schedule(appointment.schedule)
    if not schedule:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Schedule does not exist."
        )
    if schedule.wallet not in user.wallet_ids:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN, detail="Not your schedule."
        )
    
    for k, v in data.dict().items():
        if v is not None:
            setattr(appointment, k, v)

    appointment = await update_appointment(appointment)

    # Notify client that the appointment has been updated
    if appointment.nostr_pubkey:
        pubkey = normalize_public_key(appointment.nostr_pubkey)
        msg = f"""
        [DO NOT REPLY TO THIS MESSAGE]

        The appointment for {schedule.name} has been updated.
        New date: {appointment.start_time}
        """
        await nostr_send_msg(pubkey, msg)
    return appointment.dict()

@lncalendar_api_router.get("/api/v1/appointment/purge/{schedule_id}")
async def api_purge_appointments(schedule_id: str):
    schedule = await get_schedule(schedule_id)
    if not schedule:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Schedule does not exist."
        )
    return await purge_appointments(schedule_id)


@lncalendar_api_router.get("/api/v1/appointment/{schedule_id}/{payment_hash}")
async def api_appointment_check_invoice(schedule_id: str, payment_hash: str):
    schedule = await get_schedule(schedule_id)
    if not schedule:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Schedule does not exist."
        )
    payment = await get_standalone_payment(payment_hash, incoming=True)
    if not payment:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Payment does not exist"
        )
    if payment.success:
        await set_appointment_paid(payment_hash)
    return {"paid": payment.success}


@lncalendar_api_router.get("/api/v1/appointment/{schedule_id}")
async def api_get_appointments_schedule(schedule_id: str):
    appointments = await get_appointments(schedule_id)

    if not appointments:
        return []
    return appointments


@lncalendar_api_router.get("/api/v1/appointment")
async def api_get_all_appointments(
    wallet: WalletTypeInfo = Depends(require_invoice_key),
):
    user = await get_user(wallet.wallet.user)
    wallet_ids = user.wallet_ids if user else []
    return await get_appointments_wallets(wallet_ids)


@lncalendar_api_router.delete("/api/v1/appointment/{appointment_id}")
async def api_appointment_delete(
    appointment_id: str, user: User = Depends(check_user_exists)
):
    appointment = await get_appointment(appointment_id)
    if not appointment:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Appointment does not exist."
        )
    schedule = await get_schedule(appointment.schedule)
    if not schedule:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Schedule does not exist."
        )
    if schedule.wallet not in user.wallet_ids:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN, detail="Not your schedule."
        )
    await delete_appointment(appointment_id)

    # Notify client that the appointment has been deleted
    if appointment.nostr_pubkey:
        pubkey = normalize_public_key(appointment.nostr_pubkey)
        msg = f"""
        [DO NOT REPLY TO THIS MESSAGE]

        The appointment for {schedule.name} has been deleted.
        """
        await nostr_send_msg(pubkey, msg)
    return "", HTTPStatus.NO_CONTENT


## Unavailable Time API
@lncalendar_api_router.post("/api/v1/unavailable")
async def api_unavailable_create(
    data: CreateUnavailableTime, user: User = Depends(check_user_exists)
):
    schedule = await get_schedule(data.schedule)
    if not schedule:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Schedule does not exist."
        )
    if schedule.wallet not in user.wallet_ids:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN, detail="Not your schedule."
        )
    unavailable = await create_unavailable_time(data=data)
    assert unavailable, "Newly created unavailable time couldn't be retrieved"
    return unavailable


@lncalendar_api_router.get("/api/v1/unavailable/{schedule_id}")
async def api_unavailable_get(schedule_id: str):
    schedule = await get_schedule(schedule_id)
    if not schedule:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Schedule does not exist."
        )
    return await get_unavailable_times(schedule_id)


@lncalendar_api_router.delete("/api/v1/unavailable/{schedule_id}/{unavailable_id}")
async def api_unavailable_delete(
    schedule_id: str,
    unavailable_id: str,
    user: User = Depends(check_user_exists),
):
    schedule = await get_schedule(schedule_id)
    if not schedule:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Schedule does not exist."
        )
    if schedule.wallet not in user.wallet_ids:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN, detail="Not your schedule."
        )
    await delete_unavailable_time(unavailable_id)
    return "", HTTPStatus.NO_CONTENT

## Currency API
@lncalendar_api_router.get("/api/v1/currencies")
async def api_get_currencies():
    return allowed_currencies()

## SETTINGS
@lncalendar_api_router.get("/api/v1/settings", dependencies=[Depends(check_admin)])
async def api_get_settings() -> CalendarSettings:
    return await get_or_create_calendar_settings()

@lncalendar_api_router.put("/api/v1/settings", dependencies=[Depends(check_admin)])
async def api_update_settings(settings: CalendarSettings) -> CalendarSettings:
    try:
        parse_nostr_private_key(settings.nostr_private_key)
    except Exception as exc:
        raise HTTPException(
            detail="Invalid Nostr private key.", status_code=HTTPStatus.BAD_REQUEST
        ) from exc
    return await update_calendar_settings(settings)

@lncalendar_api_router.delete("/api/v1/settings", dependencies=[Depends(check_admin)])
async def api_delete_settings() -> None:
    await delete_calendar_settings()