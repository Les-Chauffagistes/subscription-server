from typing import cast
from prisma.models import Subscription as PrismaSubscription
from subscription_types.models import Subscription, SubscriptionStatus


def subscription_from_prisma(model: PrismaSubscription) -> Subscription:
    return Subscription(
        pool_address=model.poolAddress,
        started_at=model.startedAt,
        expires_at=model.expiresAt,
        status=cast(SubscriptionStatus, model.status),
        created_at=model.createdAt,
        updated_at=model.updatedAt,
    )
