"""Tests des handlers HTTP via aiohttp.test_utils.

Principe : on monte une Application aiohttp isolée avec les routes v1.
Le serveur démarre une seule fois (session), mais chaque test reçoit
une transaction Prisma isolée via `http_client_tx` — rollback automatique
après chaque test, zéro interférence entre eux, zéro mock drift sur les services.
Les seuls mocks sont les appels HTTP sortants vers OpenNode.
"""
from unittest.mock import AsyncMock, patch  # seul mock restant : appels HTTP OpenNode
from urllib.parse import urlencode
from uuid import uuid4

import pytest_asyncio
from aiohttp.test_utils import TestClient, TestServer
from aiohttp.web import Application
from prisma import Prisma
from prisma.enums import SubscriptionStatus
from datetime import datetime, timedelta

from src.settings import settings
from tools.webhook import create_webhook, sign_webhook


# ─── Fixtures ────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def http_client():
    """Serveur HTTP v1 partagé sur toute la session."""
    from src.v1.app import routes as v1_routes

    app = Application()
    app.add_routes(v1_routes)

    server = TestServer(app)
    client = TestClient(server)
    await client.start_server()
    yield client
    await client.close()


@pytest_asyncio.fixture(loop_scope="session")
async def http_client_tx(http_client: TestClient, db: Prisma):
    """Injecte la transaction du test dans l'app, rollback automatique après."""
    http_client.app["prisma"] = db
    yield http_client


# ─── POST /webhook/opennode ───────────────────────────────────────────────────


async def test_webhook_valid_signature_returns_200(http_client_tx: TestClient, db: Prisma):
    """Webhook signé valide → handler parse, vérifie, appelle process_invoice → 200."""
    from datetime import datetime, timezone
    from prisma.enums import InvoiceStatus

    rate = await db.subscriptionrate.find_first(order={"validFrom": "desc"})
    assert rate
    sub = await db.subscription.create(data={"poolAddress": "bc1q_handler_wh"})
    invoice_id = str(uuid4())
    await db.lightninginvoice.create(data={
        "id": invoice_id,
        "amountSats": 500,
        "createdAt": datetime.now(timezone.utc),
        "durationDays": 1,
        "expiresAt": datetime.now(timezone.utc),
        "opennodeChargeId": "charge-handler-wh",
        "rateId": rate.id,
        "satsPerDay": rate.satsPerDay,
        "paymentRequest": "lnbc_handler_wh",
        "subscriptionId": sub.id,
        "status": InvoiceStatus.pending,
    })

    webhook = sign_webhook(create_webhook(invoice_id))
    body = urlencode(webhook.__dict__)

    with patch("src.v1.handlers.webhook.open", return_value=AsyncMock()):
        resp = await http_client_tx.post("/webhook/opennode", data=body)

    assert resp.status == 200


async def test_webhook_invalid_signature_returns_404(http_client_tx: TestClient):
    """Signature HMAC incorrecte → PermissionError → 404."""
    invoice = create_webhook(str(uuid4()))
    invoice.hashed_order = "bad_signature"
    body = urlencode(invoice.__dict__)

    with patch("src.v1.handlers.webhook.open", return_value=AsyncMock()):
        resp = await http_client_tx.post("/webhook/opennode", data=body)

    assert resp.status == 404


async def test_webhook_missing_fields_returns_400(http_client_tx: TestClient):
    """Corps URL-encodé incomplet → ValueError → 400."""
    with patch("src.v1.handlers.webhook.open", return_value=AsyncMock()):
        resp = await http_client_tx.post("/webhook/opennode", data="incomplete=payload")

    assert resp.status == 400


# ─── POST /{address}/subscribe ───────────────────────────────────────────────


async def test_subscribe_missing_amount_returns_400(http_client_tx: TestClient):
    """amount absent ou nul → 400."""
    resp = await http_client_tx.post("/bc1q_handler_sub/subscribe", json={"amount": 0})
    assert resp.status == 400


async def test_subscribe_new_invoice_returns_lnurl(http_client_tx: TestClient):
    """Nouvelle adresse → service appelé pour de vrai → retourne lnurl."""
    from datetime import datetime, timezone
    from src.v1.models.invoice import ChainInvoice, Invoice, LightningInvoice

    now = int(datetime.now(timezone.utc).timestamp())
    fake_opennode_invoice = Invoice(
        id=str(uuid4()), description="Test", desc_hash=False,
        created_at=now, status="unpaid", amount=500,
        callback_url="", success_url=None, hosted_checkout_url="",
        order_id="o1", currency="BTC", source_fiat_value=0,
        fiat_value=0.0, auto_settle=False, notif_email=None,
        address="bc1q_handler_new", metadata={},
        chain_invoice=ChainInvoice(address="bc1q_handler_new"),
        uri="", ttl=1440,
        lightning_invoice=LightningInvoice(expires_at=now + 3600, payreq="lnbc_handler_new"),
    )

    with patch("src.v1.services.invoice.opennode_create_invoice", new_callable=AsyncMock, return_value=fake_opennode_invoice):
        resp = await http_client_tx.post("/bc1q_handler_new/subscribe", json={"amount": 500})

    assert resp.status == 200
    data = await resp.json()
    assert data["lnurl"] == "lnbc_handler_new"


async def test_subscribe_reuses_pending_invoice(http_client_tx: TestClient, db: Prisma):
    """Invoice pending existante avec même montant → réutilisée, retourne payreq."""
    from datetime import datetime, timezone
    from prisma.enums import InvoiceStatus

    rate = await db.subscriptionrate.find_first(order={"validFrom": "desc"})
    assert rate
    sub = await db.subscription.create(data={"poolAddress": "bc1q_handler_reuse"})
    await db.lightninginvoice.create(data={
        "id": str(uuid4()),
        "amountSats": 500,
        "createdAt": datetime.now(timezone.utc),
        "durationDays": 1,
        "expiresAt": datetime.now(timezone.utc),
        "opennodeChargeId": "charge-handler-reuse",
        "rateId": rate.id,
        "satsPerDay": rate.satsPerDay,
        "paymentRequest": "lnbc_handler_reuse",
        "subscriptionId": sub.id,
        "status": InvoiceStatus.pending,
    })

    with patch("src.v1.services.invoice.opennode_create_invoice", new_callable=AsyncMock) as mock_api:
        resp = await http_client_tx.post("/bc1q_handler_reuse/subscribe", json={"amount": 500})
        mock_api.assert_not_awaited()

    assert resp.status == 200
    data = await resp.json()
    assert data["lnurl"] == "lnbc_handler_reuse"


# ─── GET /rate ────────────────────────────────────────────────────────────────


async def test_get_rate_returns_value(http_client_tx: TestClient):
    """GET /rate → retourne le taux seedé en base."""
    resp = await http_client_tx.get("/rate")

    assert resp.status == 200
    data = await resp.json()
    assert data["rate"] == 100  # valeur seedée dans conftest


# ─── GET /subscriptions ───────────────────────────────────────────────────────


async def test_get_subscriptions_without_token_returns_401(http_client_tx: TestClient):
    """Sans X-Api-Key → 401."""
    resp = await http_client_tx.get("/subscriptions")
    assert resp.status == 401


async def test_get_subscriptions_with_valid_token_returns_list(http_client_tx: TestClient, db: Prisma):
    """Avec X-Api-Key valide → 200 avec la liste des abonnements actifs."""
    await db.subscription.create(data={"poolAddress": "bc1q_handler_list", "expiresAt": datetime.now() + timedelta(days=30), "status": SubscriptionStatus.active})

    resp = await http_client_tx.get("/subscriptions", headers={"X-Api-Key": settings.api_token})

    assert resp.status == 200
    data = await resp.json()
    assert isinstance(data, list)
    addresses = [s["pool_address"] for s in data]
    assert "bc1q_handler_list" in addresses


# ─── GET /{address}/subscription ─────────────────────────────────────────────


async def test_get_subscription_not_found_returns_404(http_client_tx: TestClient):
    """Adresse sans abonnement → 404."""
    resp = await http_client_tx.get("/bc1q_handler_unknown/subscription")
    assert resp.status == 404


async def test_get_subscription_found_returns_200(http_client_tx: TestClient, db: Prisma):
    """Adresse avec abonnement → 200 avec les données de l'abonnement."""
    await db.subscription.create(data={"poolAddress": "bc1q_handler_found"})

    resp = await http_client_tx.get("/bc1q_handler_found/subscription")

    assert resp.status == 200
    data = await resp.json()
    assert data["pool_address"] == "bc1q_handler_found"
