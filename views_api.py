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
    get_appointments_for_time_slot,
    get_appointments_for_wallets,
    get_schedule,
    get_schedules,
    get_unavailable_times,
    set_appointment_paid,
    update_schedule,
)
from .models import (
    Appointment,
    AppointmentPaymentRequest,
    AppointmentPaymentStatus,
    CreateAppointment,
    CreateSchedule,
    CreateUnavailableTime,
    Schedule,
    UnavailableTime,
)

lncalendar_api_router = APIRouter()


###################################### Schedule API ####################################
@lncalendar_api_router.get(
    "/api/v1/schedule",
    name="Get Schedules",
    summary="get paginated list of schedules for user",
    response_description="list of schedules",
    response_model=list[Schedule],
    # openapi_extra=generate_filter_params_openapi(ScheduleFilters),
)
async def api_get_schedules(
    wallet: WalletTypeInfo = Depends(require_invoice_key),
    all_wallets: bool = Query(False),
) -> list[Schedule]:
    wallet_ids = [wallet.wallet.id]

    if all_wallets:
        user = await get_user(wallet.wallet.user)
        wallet_ids = user.wallet_ids if user else []

    return await get_schedules(wallet_ids)


@lncalendar_api_router.post(
    "/api/v1/schedule",
    name="Create Schedule",
    summary="create a new schedule",
    response_description="list of schedules",
    response_model=Schedule,
)
async def api_schedule_create(
    data: CreateSchedule, wallet: WalletTypeInfo = Depends(require_admin_key)
) -> Schedule:
    schedule = await create_schedule(wallet_id=wallet.wallet.id, data=data)
    return schedule


@lncalendar_api_router.put(
    "/api/v1/schedule/{schedule_id}",
    name="Update Schedule",
    summary="update an existing schedule",
    response_description="the updated schedule",
    response_model=Schedule,
)
async def api_schedule_update(
    schedule_id: str,
    data: CreateSchedule,
    wallet: WalletTypeInfo = Depends(require_invoice_key),
) -> Schedule:
    schedule = await get_schedule(schedule_id)

    if not schedule:
        raise HTTPException(HTTPStatus.NOT_FOUND, "Schedule does not exist.")

    if schedule.wallet != wallet.wallet.id:
        raise HTTPException(HTTPStatus.FORBIDDEN, "Not your schedule.")

    for k, v in data.dict().items():
        if v is not None:
            setattr(schedule, k, v)

    schedule = await update_schedule(schedule)
    return schedule


@lncalendar_api_router.delete(
    "/api/v1/schedule/{schedule_id}",
    name="Delete Schedule",
    summary="delete an existing schedule",
)
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


###################################### Appointment API #################################
@lncalendar_api_router.post(
    "/api/v1/appointment",
    name="Create Appointment",
    summary="create a new appointment",
    response_description="the payment details for that appointment",
    response_model=AppointmentPaymentRequest,
)
async def api_appointment_create(data: CreateAppointment) -> AppointmentPaymentRequest:
    schedule = await get_schedule(data.schedule)
    if not schedule:
        raise HTTPException(HTTPStatus.NOT_FOUND, "Schedule does not exist.")

    appoiments = await get_appointments_for_time_slot(
        schedule_id=data.schedule,
        start_time=data.start_time,
        paid=True,
    )
    if len(appoiments) > 0:
        raise HTTPException(
            HTTPStatus.CONFLICT,
            "Appointment already exists for the time slot.",
        )
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

    return AppointmentPaymentRequest(
        payment_hash=payment.payment_hash, payment_request=payment.bolt11
    )


@lncalendar_api_router.get(
    "/api/v1/appointment/{schedule_id}/{payment_hash}",
    name="Check Appointment",
    summary="check if an appointment is paid",
    response_description="the payment status for that appointment",
    response_model=AppointmentPaymentStatus,
)
async def api_appointment_check_invoice(
    schedule_id: str, payment_hash: str
) -> AppointmentPaymentStatus:
    schedule = await get_schedule(schedule_id)
    if not schedule:
        raise HTTPException(HTTPStatus.NOT_FOUND, "Schedule does not exist.")
    payment = await get_standalone_payment(payment_hash, incoming=True)
    if not payment:
        raise HTTPException(HTTPStatus.NOT_FOUND, "Payment does not exist")
    if payment.success:
        await set_appointment_paid(payment_hash)
    return AppointmentPaymentStatus(paid=payment.success)


@lncalendar_api_router.get(
    "/api/v1/appointment/{schedule_id}",
    name="Get Appointments for schedule",
    summary="get paginated list of appointments for schedule",
    response_description="list of appointments",
    response_model=list[Appointment],
    # openapi_extra=generate_filter_params_openapi(AppointmentFilters),
)
async def api_get_appointments_for_schedule(schedule_id: str):
    return await get_appointments(schedule_id)


@lncalendar_api_router.get(
    "/api/v1/appointment",
    name="Get User Appointments",
    summary="get paginated list of appointments for a user",
    response_description="list of appointments",
    response_model=list[Appointment],
    # openapi_extra=generate_filter_params_openapi(AppointmentFilters),
)
async def api_get_all_appointments(
    wallet: WalletTypeInfo = Depends(require_invoice_key),
):
    user = await get_user(wallet.wallet.user)
    wallet_ids = user.wallet_ids if user else []
    return await get_appointments_for_wallets(wallet_ids)


###################################### Unavailable Time API ############################
@lncalendar_api_router.post(
    "/api/v1/unavailable",
    name="Create Unavailable Time",
    summary="create a new unavailable time",
    response_description="the unavailable time",
    response_model=UnavailableTime,
)
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


@lncalendar_api_router.get(
    "/api/v1/unavailable/{schedule_id}",
    name="Get Unavailable Times for schedule",
    summary="get paginated list of unavailable times for schedule",
    response_description="list of unavailable times",
    response_model=list[UnavailableTime],
)
async def api_unavailable_get(schedule_id: str) -> list[UnavailableTime]:
    schedule = await get_schedule(schedule_id)
    if not schedule:
        raise HTTPException(HTTPStatus.NOT_FOUND, "Schedule does not exist.")
    return await get_unavailable_times(schedule_id)


@lncalendar_api_router.delete(
    "/api/v1/unavailable/{schedule_id}/{unavailable_id}",
    name="Delete Unavailable Time",
    summary="delete an existing unavailable time",
)
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
