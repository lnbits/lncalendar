import asyncio

from loguru import logger

from lnbits.core.models import Payment
from lnbits.helpers import get_current_extension_name
from lnbits.tasks import register_invoice_listener
from lnbits.utils.exchange_rates import fiat_amount_as_satoshis

from .crud import (
    get_appointment,
    get_or_create_calendar_settings,
    get_schedule,
    set_appointment_paid,
)
from .helpers import normalize_public_key
from .services import nostr_send_msg


async def wait_for_paid_invoices():
    invoice_queue = asyncio.Queue()
    register_invoice_listener(invoice_queue, get_current_extension_name())

    while True:
        payment = await invoice_queue.get()
        await on_invoice_paid(payment)


async def on_invoice_paid(payment: Payment) -> None:
    if not payment.extra or payment.extra.get("tag") != "lncalendar":
        # not a lncalendar invoice
        return
    appointment = await get_appointment(payment.checking_id)
    if not appointment:
        logger.error("this should never happen", payment)
        return

    schedule = await get_schedule(appointment.schedule)
    assert schedule

    price = (
        schedule.amount * 1000
        if schedule.currency == "sat"
        else await fiat_amount_as_satoshis(schedule.amount, schedule.currency)
        * 1000
    )

    lower_bound = price * 0.99  # 1% decrease

    if abs(payment.amount) >= lower_bound:  # allow 1% error
        await set_appointment_paid(payment.payment_hash)
        settings = await get_or_create_calendar_settings()
        if not settings or not settings.nostr_private_key:
            return

        if schedule.public_key and appointment.nostr_pubkey:

            # notify the user that the appointment has been paid
            pubkey = schedule.pubkey_hex
            assert pubkey

            msg = f"""
            [DO NOT REPLY TO THIS MESSAGE]

            An appointment with {appointment.name} has been booked and paid for.

            Date: {appointment.start_time}
            Nostr contact: {appointment.nostr_pubkey}
            """
            await nostr_send_msg(pubkey, msg)

            # notify client that the appointment has been paid
            pubkey = normalize_public_key(appointment.nostr_pubkey)
            msg = f"""
            [DO NOT REPLY TO THIS MESSAGE]

            The appointment for {schedule.name} is booked.

            Date: {appointment.start_time}
            Nostr contact: {schedule.public_key}
            """
            await nostr_send_msg(pubkey, msg)

