from prisma import Prisma

from src.v1.exceptions import NoPriceException

async def get_actual_ratting(db: Prisma) -> float:
    price = await db.subscriptionrate.find_first(
        order={"validFrom": "desc"},
    )
    if not price:
        raise NoPriceException

    else:
        return price.satsPerDay