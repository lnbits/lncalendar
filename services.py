import json

from .models import Appointment
from .nostr.event import EncryptedDirectMessage


async def send_dm():
    pass


async def notify_appointment_paid(appointment: Appointment):
    dm_content = ""
    dm_content = f"""
    An appointment with {appointment.name} has been paid for.

    Date: {appointment.start_time}
    """

# async def notify_client_of_order_status(
#     order: Order, merchant: Merchant, success: bool, message: str
# ):
#     dm_content = ""
#     if success:
#         order_status = OrderStatusUpdate(
#             id=order.id,
#             message="Payment received.",
#             paid=True,
#             shipped=order.shipped,
#         )
#         dm_content = json.dumps(
#             {
#                 "type": DirectMessageType.ORDER_PAID_OR_SHIPPED.value,
#                 **order_status.dict(),
#             },
#             separators=(",", ":"),
#             ensure_ascii=False,
#         )
#     else:
#         dm_content = f"Order cannot be fulfilled. Reason: {message}"

#     dm_type = (
#         DirectMessageType.ORDER_PAID_OR_SHIPPED.value
#         if success
#         else DirectMessageType.PLAIN_TEXT.value
#     )
#     await send_dm(merchant, order.public_key, dm_type, dm_content)