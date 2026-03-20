from datetime import datetime, timedelta, timezone
from prisma import Prisma
from prisma.enums import SubscriptionStatus

from src.v1.services.subscriptions import (
    compute_extension,
    get_all_subscriptions,
    get_current_subscription_for_address,
)


async def test_get_current_subscription_found(db: Prisma):
    """Retourne l'abonnement correspondant à l'adresse."""
    await db.subscription.create(data={"poolAddress": "bc1_find_me"})

    sub = await get_current_subscription_for_address(db, "bc1_find_me")
    assert sub is not None
    assert sub.poolAddress == "bc1_find_me"


async def test_get_current_subscription_not_found(db: Prisma):
    """Retourne None pour une adresse inconnue."""
    sub = await get_current_subscription_for_address(db, "bc1_unknown")
    assert sub is None


async def test_get_all_subscriptions_active_only(db: Prisma):
    """Ne retourne que les abonnements actifs et non expirés."""
    future = datetime.now(timezone.utc) + timedelta(days=30)
    past = datetime.now(timezone.utc) - timedelta(days=1)

    await db.subscription.create(
        data={"poolAddress": "bc1_active", "status": SubscriptionStatus.active, "expiresAt": future}
    )
    await db.subscription.create(
        data={"poolAddress": "bc1_expired", "status": SubscriptionStatus.active, "expiresAt": past}
    )
    await db.subscription.create(
        data={"poolAddress": "bc1_inactive", "status": SubscriptionStatus.inactive, "expiresAt": future}
    )

    results = await get_all_subscriptions(db)
    addresses = [s.poolAddress for s in results]

    assert "bc1_active" in addresses
    assert "bc1_expired" not in addresses
    assert "bc1_inactive" not in addresses

def test_new_subscription():
    now = datetime(2025, 1, 1, tzinfo=timezone.utc)
    result = compute_extension(expires_at=None, duration_days=30, now=now)
    assert result.extended_from == now
    assert result.extended_until == datetime(2025, 1, 31, tzinfo=timezone.utc)

def test_extend_active_subscription():
    now = datetime(2025, 1, 1, tzinfo=timezone.utc)
    expires_at = datetime(2025, 2, 1, tzinfo=timezone.utc)  # encore 1 mois
    result = compute_extension(expires_at=expires_at, duration_days=30, now=now)
    assert result.extended_from == expires_at  # on repart de la fin actuelle
    assert result.extended_until == datetime(2025, 3, 3, tzinfo=timezone.utc)

def test_extend_expired_subscription():
    now = datetime(2025, 3, 1, tzinfo=timezone.utc)
    expires_at = datetime(2025, 1, 1, tzinfo=timezone.utc)  # expiré depuis 2 mois
    result = compute_extension(expires_at=expires_at, duration_days=7, now=now)
    assert result.extended_from == now  # on repart de maintenant, pas de la vieille date
    assert result.extended_until == datetime(2025, 3, 8, tzinfo=timezone.utc)
