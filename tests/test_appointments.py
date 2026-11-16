from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from lnbits.decorators import require_invoice_key

from .. import lncalendar_ext, views_api
from ..models import Appointment


@pytest.fixture
def appointment():
    return Appointment(
        id="synthetic-payment-hash",
        name="Synthetic Booker",
        email="booker@example.invalid",
        info="Private appointment notes",
        start_time="2026/11/17 09:00",
        end_time="2026/11/17 09:30",
        schedule="public-schedule",
        paid=False,
    )


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(lncalendar_ext)
    with TestClient(app) as client:
        yield client


@pytest.mark.parametrize("paid", [False, True])
def test_public_appointments_only_expose_slot_times(
    monkeypatch, client, appointment, paid
):
    appointment.paid = paid
    get_appointments = AsyncMock(return_value=[appointment])
    monkeypatch.setattr(views_api, "get_appointments", get_appointments)

    response = client.get("/lncalendar/api/v1/appointment/public-schedule")

    assert response.status_code == 200
    assert response.json() == [
        {"start_time": "2026/11/17 09:00", "end_time": "2026/11/17 09:30"}
    ]
    get_appointments.assert_awaited_once_with("public-schedule")


def test_appointments_require_invoice_key(client):
    response = client.get("/lncalendar/api/v1/appointment")

    assert response.status_code == 401


def test_authenticated_appointments_retain_details(monkeypatch, client, appointment):
    client.app.dependency_overrides[require_invoice_key] = lambda: SimpleNamespace(
        wallet=SimpleNamespace(user="owner")
    )
    get_user = AsyncMock(return_value=SimpleNamespace(wallet_ids=["owner-wallet"]))
    monkeypatch.setattr(views_api, "get_user", get_user)
    get_appointments = AsyncMock(return_value=[appointment])
    monkeypatch.setattr(views_api, "get_appointments_wallets", get_appointments)

    response = client.get("/lncalendar/api/v1/appointment")

    assert response.status_code == 200
    assert response.json() == [appointment.model_dump()]
    get_user.assert_awaited_once_with("owner")
    get_appointments.assert_awaited_once_with(["owner-wallet"])
