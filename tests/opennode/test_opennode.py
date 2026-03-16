from json import dumps

import pytest
from src.api.opennode import create_invoice

@pytest.mark.asyncio
async def test_invoice_creation_sucess():
    invoice = await create_invoice(
        amount=500,
        order_id="e8ca195b9eff5",
        description="Payer chez Chauffagistes"
    )
    open("test", "w").write(dumps(invoice, indent = 4))
    print(invoice)
    assert invoice is not None