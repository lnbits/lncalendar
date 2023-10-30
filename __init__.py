from fastapi import APIRouter

from lnbits.db import Database
from lnbits.helpers import template_renderer

db = Database("ext_lncalendar")

lncalendar_ext: APIRouter = APIRouter(prefix="/lncalendar", tags=["LNCalendar"])

lncalendar_static_files = [
    {
        "path": "/lncalendar/static",
        "name": "lncalendar_static",
    }
]


def lncalendar_renderer():
    return template_renderer(["lncalendar/templates"])


from .views import *  # noqa: F401,F403
from .views_api import *  # noqa: F401,F403
