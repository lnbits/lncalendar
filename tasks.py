import asyncio

from loguru import logger

from lnbits.core.models import Payment
from lnbits.helpers import get_current_extension_name
from lnbits.tasks import register_invoice_listener

from .crud import get_appointment, get_schedule, set_appointment_paid


async def wait_for_paid_invoices():
    invoice_queue = asyncio.Queue()
    register_invoice_listener(invoice_queue, get_current_extension_name())

    while True:
        payment = await invoice_queue.get()
        await on_invoice_paid(payment)


async def on_invoice_paid(payment: Payment) -> None:
    logger.debug(f"Processing paid invoice: {payment}")
    if not payment.extra or payment.extra.get("tag") != "lncalendar":
        # not a lncalendar invoice
        return
    appointment = await get_appointment(payment.checking_id)
    if not appointment:
        logger.error("this should never happen", payment)
        return

    schedule = await get_schedule(appointment.schedule)
    assert schedule

    if payment.amount == schedule.amount * 1000:
        await set_appointment_paid(payment.payment_hash)
