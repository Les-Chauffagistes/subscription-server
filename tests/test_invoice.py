from datetime import datetime, timezone
from uuid import uuid4
from prisma import Prisma
from prisma.enums import InvoiceStatus
from prisma.models import LightningInvoice as DbLightningInvoice
from unittest.mock import patch, AsyncMock

from src.v1.exceptions import NoPriceException
from src.v1.models.invoice import Invoice, LightningInvoice, ChainInvoice
from src.v1.services.invoice import create_invoice


def _make_opennode_invoice(
    charge_id: str | None = None,
    amount: int = 500,
    payreq: str = "lnbc500test",
) -> Invoice:
    now = int(datetime.now(timezone.utc).timestamp())
    charge_id = charge_id or str(uuid4())
    return Invoice(
        id=charge_id,
        description="Test",
        desc_hash=False,
        created_at=now,
        status="unpaid",
        amount=amount,
        callback_url="http://localhost/webhook",
        success_url=None,
        hosted_checkout_url="https://checkout.opennode.com/test",
        order_id="order-001",
        currency="BTC",
        source_fiat_value=0,
        fiat_value=0.0,
        auto_settle=False,
        notif_email=None,
        address="bc1qtest",
        metadata={},
        chain_invoice=ChainInvoice(address="bc1qtest"),
        uri="bitcoin:bc1qtest?amount=0.000005",
        ttl=1440,
        lightning_invoice=LightningInvoice(
            expires_at=now + 3600,
            payreq=payreq,
        ),
    )


# ─── create_invoice : pas de tarif → NoPriceException ────────────────────────

async def test_create_invoice_no_rate_raises(db: Prisma):
    """Sans tarif en BDD, create_invoice doit lever NoPriceException."""
    # Supprimer le tarif seedé (rollback après le test)
    await db.subscriptionrate.delete_many()

    try:
        await create_invoice(db, "bc1_no_rate", amount=500, order_id="o1")
        assert False, "NoPriceException attendue"
    except NoPriceException:
        pass


# ─── create_invoice : nouvelle adresse → crée subscription + invoice ─────────

async def test_create_invoice_new_address(db: Prisma):
    """Pour une adresse inconnue, doit créer un abonnement puis une invoice."""
    charge_id = str(uuid4())
    opennode_invoice = _make_opennode_invoice(charge_id=charge_id)

    with patch(
        "src.v1.services.invoice.opennode_create_invoice",
        new_callable=AsyncMock,
        return_value=opennode_invoice,
    ) as mock_api:
        invoice = await create_invoice(db, "bc1_new", amount=500, order_id="o2")

        assert isinstance(invoice, Invoice)
        assert invoice == opennode_invoice
        mock_api.assert_awaited_once()

    # L'abonnement a été créé en BDD
    sub = await db.subscription.find_unique(where={"poolAddress": "bc1_new"})
    assert sub is not None

    # L'invoice a été enregistrée en BDD
    inv = await db.lightninginvoice.find_first(
        where={"opennodeChargeId": charge_id}
    )
    assert inv is not None
    assert inv.amountSats == 500
    assert inv.status == InvoiceStatus.pending
    assert inv.subscriptionId == sub.id


# ─── create_invoice : adresse existante, pas d'invoice pending → nouvelle ────

async def test_create_invoice_existing_sub_no_pending(db: Prisma):
    """Abonnement existant mais aucune invoice pending → crée une nouvelle invoice."""
    # Créer un abonnement manuellement
    await db.subscription.create(data={"poolAddress": "bc1_existing"})
    opennode_invoice = _make_opennode_invoice(
        charge_id=str(uuid4()),
        payreq="lnbc_new_invoice",
    )

    with patch(
        "src.v1.services.invoice.opennode_create_invoice",
        new_callable=AsyncMock,
        return_value=opennode_invoice,
    ) as mock_api:
        invoice = await create_invoice(db, "bc1_existing", amount=500, order_id="o3")

        assert isinstance(invoice, Invoice)
        assert invoice.lightning_invoice.payreq == "lnbc_new_invoice"
        mock_api.assert_awaited_once()


# ─── create_invoice : invoice pending réutilisable → pas d'appel API ─────────

async def test_create_invoice_reuses_pending(db: Prisma):
    """Invoice pending avec même montant et tarif → réutilise sans appel OpenNode."""
    rate = await db.subscriptionrate.find_first(order={"validFrom": "desc"})
    assert rate is not None
    sub = await db.subscription.create(data={"poolAddress": "bc1_reuse"})

    # Insérer une invoice pending
    await db.lightninginvoice.create(
        data={
            "id": str(uuid4()),
            "amountSats": 500,
            "createdAt": datetime.now(timezone.utc),
            "durationDays": 1,
            "expiresAt": datetime.now(timezone.utc),
            "opennodeChargeId": "charge-reuse",
            "rateId": rate.id,
            "satsPerDay": rate.satsPerDay,
            "paymentRequest": "lnbc_reused",
            "subscriptionId": sub.id,
            "status": InvoiceStatus.pending,
        }
    )

    with patch(
        "src.v1.services.invoice.opennode_create_invoice",
        new_callable=AsyncMock,
    ) as mock_api:
        invoice = await create_invoice(db, "bc1_reuse", amount=500, order_id="o4")

        assert isinstance(invoice, DbLightningInvoice)
        assert invoice.paymentRequest == "lnbc_reused"
        mock_api.assert_not_awaited()


# ─── create_invoice : invoice pending avec montant différent → nouvelle ───────

async def test_create_invoice_different_amount_creates_new(db: Prisma):
    """Invoice pending existe mais avec un montant différent → crée une nouvelle."""
    rate = await db.subscriptionrate.find_first(order={"validFrom": "desc"})
    assert rate is not None
    sub = await db.subscription.create(data={"poolAddress": "bc1_diff_amount"})

    await db.lightninginvoice.create(
        data={
            "id": str(uuid4()),
            "amountSats": 500,
            "createdAt": datetime.now(timezone.utc),
            "durationDays": 1,
            "expiresAt": datetime.now(timezone.utc),
            "opennodeChargeId": "charge-diff-amount",
            "rateId": rate.id,
            "satsPerDay": rate.satsPerDay,
            "paymentRequest": "lnbc_old",
            "subscriptionId": sub.id,
            "status": InvoiceStatus.pending,
        }
    )

    opennode_invoice = _make_opennode_invoice(
        charge_id=str(uuid4()),
        amount=1000,
        payreq="lnbc_1000",
    )

    with patch(
        "src.v1.services.invoice.opennode_create_invoice",
        new_callable=AsyncMock,
        return_value=opennode_invoice,
    ) as mock_api:
        invoice = await create_invoice(db, "bc1_diff_amount", amount=1000, order_id="o5")

        assert isinstance(invoice, Invoice)
        assert invoice.lightning_invoice.payreq == "lnbc_1000"
        mock_api.assert_awaited_once()


# ─── create_invoice : invoice paid → ne doit pas la réutiliser ────────────────

async def test_create_invoice_ignores_paid_invoice(db: Prisma):
    """Une invoice déjà payée ne doit pas être réutilisée."""
    rate = await db.subscriptionrate.find_first(order={"validFrom": "desc"})
    assert rate is not None
    sub = await db.subscription.create(data={"poolAddress": "bc1_paid"})

    await db.lightninginvoice.create(
        data={
            "id": str(uuid4()),
            "amountSats": 500,
            "createdAt": datetime.now(timezone.utc),
            "durationDays": 1,
            "expiresAt": datetime.now(timezone.utc),
            "opennodeChargeId": "charge-paid",
            "rateId": rate.id,
            "satsPerDay": rate.satsPerDay,
            "paymentRequest": "lnbc_paid",
            "subscriptionId": sub.id,
            "status": InvoiceStatus.paid,
        }
    )

    opennode_invoice = _make_opennode_invoice(
        charge_id=str(uuid4()),
        payreq="lnbc_fresh",
    )

    with patch(
        "src.v1.services.invoice.opennode_create_invoice",
        new_callable=AsyncMock,
        return_value=opennode_invoice,
    ) as mock_api:
        invoice = await create_invoice(db, "bc1_paid", amount=500, order_id="o6")

        assert isinstance(invoice, Invoice)
        assert invoice.lightning_invoice.payreq == "lnbc_fresh"
        mock_api.assert_awaited_once()


# ─── create_invoice : doublon d'adresse → pas de 2e subscription ─────────────

async def test_create_invoice_no_duplicate_subscription(db: Prisma):
    """Appeler 2 fois avec la même adresse ne doit pas tenter de créer un 2e abonnement."""
    opennode_invoice_1 = _make_opennode_invoice(charge_id=str(uuid4()), payreq="lnbc_1")
    opennode_invoice_2 = _make_opennode_invoice(charge_id=str(uuid4()), payreq="lnbc_2")

    with patch(
        "src.v1.services.invoice.opennode_create_invoice",
        new_callable=AsyncMock,
        side_effect=[opennode_invoice_1, opennode_invoice_2],
    ):
        await create_invoice(db, "bc1_dup", amount=500, order_id="o7a")
        await create_invoice(db, "bc1_dup", amount=1000, order_id="o7b")

    subs = await db.subscription.find_many(where={"poolAddress": "bc1_dup"})
    assert len(subs) == 1
