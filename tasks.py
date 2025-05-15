import asyncio

from lnbits.core.models import Payment
from lnbits.helpers import get_current_extension_name
from lnbits.tasks import register_invoice_listener
from loguru import logger

from .crud import (
    get_appointment,
    get_schedule,
    purge_appointments,
    set_appointment_paid,
    update_appointment,
)

payment_lock = asyncio.Lock()


async def wait_for_paid_invoices():
    invoice_queue = asyncio.Queue()
    register_invoice_listener(invoice_queue, get_current_extension_name())

    while True:
        try:
            payment = await invoice_queue.get()
            await on_invoice_paid(payment)
        except Exception as ex:
            logger.error(f"Error processing invoice: {ex}")
            await asyncio.sleep(1)


async def on_invoice_paid(payment: Payment) -> None:
    if not payment.extra or payment.extra.get("tag") != "lncalendar":
        # not a lncalendar invoice
        return

    async with payment_lock:
        await _confirm_appointment(payment.checking_id)


async def run_by_the_minute_task():
    minute_counter = 0
    while True:
        await asyncio.sleep(60)
        try:
            await purge_appointments()
        except Exception as ex:
            logger.error(ex)

        minute_counter += 1


async def _confirm_appointment(appointment_id: str) -> None:
    appointment = await get_appointment(appointment_id)
    if not appointment:
        logger.warning(f"Appoiment not found: '{appointment_id}'.")
        return

    if appointment.paid:
        logger.warning(f"Appoiment already paid: '{appointment_id}'.")
        appointment.extra.must_refund = True
        await update_appointment(appointment)
        return

    schedule = await get_schedule(appointment.schedule)
    assert schedule

    await set_appointment_paid(appointment_id)
