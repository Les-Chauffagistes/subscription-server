from prisma import Prisma

from src.v1.exceptions import NoPriceException
from src.v1.services.rating import get_actual_ratting


async def test_get_actual_ratting_returns_latest(db: Prisma):
    """Retourne le satsPerDay du tarif le plus récent."""
    rate = await get_actual_ratting(db)
    assert isinstance(rate, int)
    assert rate == 100  # seedé dans conftest


async def test_get_actual_ratting_no_rate_raises(db: Prisma):
    """Sans tarif en BDD, lève NoPriceException."""
    await db.subscriptionrate.delete_many()

    try:
        await get_actual_ratting(db)
        assert False, "NoPriceException attendue"
    except NoPriceException:
        pass
