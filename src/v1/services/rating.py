from prisma import Prisma

from init import app
from src.v1.exceptions import NoPriceException

async def get_actual_ratting() -> float:
    prisma: Prisma = app["prisma"]
    price = await prisma.subscriptionrate.find_first(
        order={"validFrom": "desc"},
    )
    if not price:
        raise NoPriceException
    
    else:
        return price.satsPerDay