from datetime import datetime
from typing import Optional
from prisma import Prisma
from src.v1.exceptions import NoPriceException
from src.v1.models.InvoiceWebhook import InvoiceWebhook
from src.api.opennode import create_invoice as opennode_create_invoice
from init import app
from src.v1.models.invoice import Invoice

async def create_invoice(
    amount: int,
    order_id: str,
    description: Optional[str] = None,
    ttl: Optional[int] = None,
) -> Invoice:
    prisma: Prisma = app["prisma"]
    ratting = await prisma.subscriptionrate.find_first(
        order={"validFrom": "desc"},
    )
    if not ratting:
        raise NoPriceException("Impossible de créer l'invoice sans tarif")
    
    invoice = await opennode_create_invoice(amount, order_id, description, ttl)

    await prisma.lightninginvoice.create(
        data={
            "amountSats": invoice.amount,
            "createdAt": datetime.fromtimestamp(invoice.created_at),
            "durationDays": invoice.ttl // 1440,
            "expiresAt": datetime.fromtimestamp(invoice.lightning_invoice.expires_at),
            "opennodeChargeId": invoice.id,
            "rateId": ratting.id,
            "satsPerDay": ratting.satsPerDay,
            "paymentRequest": invoice.lightning_invoice.payreq
        }
    )

    return invoice

async def process_invoice(invoice: InvoiceWebhook):

    # TODO : Logger l'invoice dans opennode_webhooks_logs
    # TODO : Récupérer l'invoice enregistrée en DB
    # TODO : Vérifier le taux associé à l'invoice
    # TODO : Récupérer l'abonnement lié
    # TODO : Créditer/Démarrer l'abonnement


    pass