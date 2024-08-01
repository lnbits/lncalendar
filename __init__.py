from fastapi import APIRouter

from .crud import db
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

__all__ = ["db", "lncalendar_ext", "lncalendar_static_files"]
