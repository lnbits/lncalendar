import asyncio

from fastapi import APIRouter
from loguru import logger

from .crud import db
from .tasks import wait_for_paid_invoices
from .views import lncalendar_generic_router
from .views_api import lncalendar_api_router

lncalendar_ext: APIRouter = APIRouter(prefix="/lncalendar", tags=["LNCalendar"])
lncalendar_ext.include_router(lncalendar_generic_router)
lncalendar_ext.include_router(lncalendar_api_router)

lncalendar_static_files = [
    {
        "path": "/lncalendar/static",
        "name": "lncalendar_static",
    }
]

scheduled_tasks: list[asyncio.Task] = []

def lncalendar_stop():
    for task in scheduled_tasks:
        try:
            task.cancel()
        except Exception as ex:
            logger.warning(ex)


def lncalendar_start():
    from lnbits.tasks import create_permanent_unique_task

    task = create_permanent_unique_task("ext_lncalendar", wait_for_paid_invoices)
    scheduled_tasks.append(task)

__all__ = ["db", "lncalendar_ext", "lncalendar_static_files", "lncalendar_start", "lncalendar_stop"]
