from datetime import datetime
from typing import Optional
from prisma import Json, Prisma
from prisma.enums import InvoiceStatus
from prisma.models import LightningInvoice
from src.v1.exceptions import NoPriceException
from src.v1.models.InvoiceWebhook import InvoiceWebhook
from src.api.opennode import create_invoice as opennode_create_invoice
from init import log
from src.v1.models.invoice import Invoice
from src.v1.services.subscriptions import activate_subscription, get_current_subscription_for_address

async def create_invoice(
    db: Prisma,
    address: str,
    amount: int,
    order_id: str,
    description: Optional[str] = None,
    ttl: Optional[int] = None,
) -> Invoice | LightningInvoice:
    """Renvoie soit un objet Invoice lorsque l'invoice a été créée, soit un objet prisma LightningInvoice si l'invoice a été récupérée depuis la bd."""
    ratting = await db.subscriptionrate.find_first(
        order={"validFrom": "desc"},
    )
    if not ratting:
        raise NoPriceException("Impossible de créer l'invoice sans tarif")

    subscription = await get_current_subscription_for_address(db, address)
    if subscription:
        # Chercher une invoice valide pour cette adresse (avec le même montant et le même tarif)
        old_invoice = await db.lightninginvoice.find_first(
            where={
                "rateId": ratting.id,
                "amountSats": amount,
                "status": InvoiceStatus.pending
            }
        )
        if old_invoice:
            log.debug("Reusing invoice for address", address)
            return old_invoice

    else:
        log.debug("Creating new subscription for address", address)
        subscription = await db.subscription.create(
            data={
                "poolAddress": address,
            }
        )

    invoice = await opennode_create_invoice(amount, order_id, description, ttl)

    await db.lightninginvoice.create(
        data={
            "id": invoice.id,
            "amountSats": invoice.amount,
            "createdAt": datetime.fromtimestamp(invoice.created_at),
            "durationDays": invoice.ttl // 1440,
            "expiresAt": datetime.fromtimestamp(invoice.lightning_invoice.expires_at),
            "opennodeChargeId": invoice.id,
            "rateId": ratting.id,
            "satsPerDay": ratting.satsPerDay,
            "paymentRequest": invoice.lightning_invoice.payreq,
            "subscriptionId": subscription.id
        }
    )

    return invoice

async def process_invoice(db: Prisma, payment_webhook: InvoiceWebhook):
    await db.opennodewebhooklog.create(
        data={
            "opennodeChargeId": payment_webhook.id,
            "payload": Json(payment_webhook.__dict__),
            "status": "paid",
            "processed": True,
        }
    )
    
    invoice_id = payment_webhook.id
    log.debug("Processing invoice", invoice_id)
    invoice = await db.lightninginvoice.find_unique(where={"id": invoice_id})
    if not invoice or invoice.status != InvoiceStatus.pending:
        log.warn("Invoice not found or already processed")
        return
    
    await db.lightninginvoice.update(
        where={"id": invoice_id},
        data={"status": InvoiceStatus.paid}
    )

    await activate_subscription(db, invoice)