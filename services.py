import asyncio
import time
from threading import Thread
from typing import List

from loguru import logger
from websocket import WebSocketApp

from .crud import get_or_create_calendar_settings
from .nostr.event import EncryptedDirectMessage


# Helper function to handle WebSocket communication in a separate thread
def open_websocket_and_send_message(relay: str, event: EncryptedDirectMessage):
    def send_event(_):
        logger.debug(f"Sending message to {ws.url}")
        ws.send(event.to_message())
        time.sleep(2)
        ws.close()

    ws = WebSocketApp(relay, on_open=send_event)
    thread = Thread(target=ws.run_forever, name=f"Calendar MSG {relay}", daemon=True)
    thread.start()

    return ws, thread

# Function to send direct messages using websockets
async def send_dm(event: EncryptedDirectMessage, relays: List[str]):
    logger.debug(f"Sending DM {event}")

    # Limit relays to a maximum of 50
    relays = relays[:50] if len(relays) > 50 else relays

    # Track active websockets and threads
    websockets, threads = [], []

    for relay in relays:
        ws, thread = open_websocket_and_send_message(relay, event)
        websockets.append(ws)
        threads.append(thread)

    # Keep websockets open for 10 seconds
    await asyncio.sleep(10)

    # Close all websockets and join threads
    for ws, thread in zip(websockets, threads):
        logger.debug(f"Closing websocket {ws.url}")
        ws.close()
        thread.join()

async def nostr_send_msg(pubkey: str, msg: str = ""):
    event = EncryptedDirectMessage(
        recipient_pubkey=pubkey,
        cleartext_content=msg,
    )

    # Get calendar settings and prepare the event
    settings = await get_or_create_calendar_settings()
    settings.private_key.sign_event(event)

    # Send the direct message to the recipient via relays
    await send_dm(event, relays=settings.relays_list)
