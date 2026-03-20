from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from prisma import Prisma
from prisma.enums import SubscriptionStatus
from prisma.models import LightningInvoice


async def get_all_subscriptions(db: Prisma):
    return await db.subscription.find_many(
        where={
            "expiresAt": {"gt": datetime.now(timezone.utc)},
            "status": SubscriptionStatus.active,
        }
    )

async def get_current_subscription_for_address(db: Prisma, address: str):
    return await db.subscription.find_unique(
        where={
            "poolAddress": address,
        }
    )

@dataclass
class ExtensionResult:
    extended_from: datetime
    extended_until: datetime
    duration_days: int


def compute_extension(
    expires_at: datetime | None,
    duration_days: int,
    now: datetime | None = None,  # injectable pour les tests
) -> ExtensionResult:
    if now is None:
        now = datetime.now(timezone.utc)

    # Jamais lésé : on part du MAX entre l'expiration actuelle et maintenant
    extended_from = max(expires_at, now) if expires_at else now
    extended_until = extended_from + timedelta(days=duration_days)

    return ExtensionResult(
        extended_from=extended_from,
        extended_until=extended_until,
        duration_days=duration_days,
    )


async def activate_subscription(db: Prisma, invoice: LightningInvoice) -> None:
    subscription = await db.subscription.find_unique(
        where={"id": invoice.subscriptionId}
    )
    assert subscription

    extension = compute_extension(
        expires_at=subscription.expiresAt,
        duration_days=invoice.durationDays,
    )

    now = datetime.now(timezone.utc)

    await db.subscriptionpayment.create(
        data={
            "subscriptionId": subscription.id,
            "invoiceId": invoice.id,
            "amountSats": invoice.amountSats,
            "durationDays": extension.duration_days,
            "extendedFrom": extension.extended_from,
            "extendedUntil": extension.extended_until,
        }
    )

    await db.subscription.update(
        where={"id": subscription.id},
        data={
            "status": SubscriptionStatus.active,
            "expiresAt": extension.extended_until,
            "startedAt": subscription.startedAt or now,  # ne pas écraser si déjà défini
        },
    )
