from http import HTTPStatus

from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException
from fastapi.requests import Request
from lnbits.core.models import User
from lnbits.decorators import check_user_exists
from lnbits.helpers import template_renderer

from .crud import get_schedule

lncalendar_generic_router = APIRouter()


def lncalendar_renderer():
    return template_renderer(["lncalendar/templates"])


@lncalendar_generic_router.get("/")
async def index(request: Request, user: User = Depends(check_user_exists)):
    return lncalendar_renderer().TemplateResponse(
        "lncalendar/index.html", {"request": request, "user": user.json()}
    )


@lncalendar_generic_router.get("/{schedule_id}")
async def display(request: Request, schedule_id: str):
    schedule = await get_schedule(schedule_id)
    if not schedule:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Schedule does not exist."
        )
    return lncalendar_renderer().TemplateResponse(
        "lncalendar/display.html",
        {
            "request": request,
            "schedule": schedule.json(),
            "available_days": schedule.availabe_days,
        },
    )
