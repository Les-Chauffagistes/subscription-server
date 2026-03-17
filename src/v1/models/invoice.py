from dataclasses import dataclass
from typing import Any, Optional, NotRequired


@dataclass
class ChainInvoice:
    address: str


@dataclass
class LightningInvoice:
    expires_at: int
    payreq: str


@dataclass
class Invoice:
    id: str
    description: str
    desc_hash: bool
    created_at: int
    status: str
    amount: int
    callback_url: str
    success_url: Optional[str]
    hosted_checkout_url: str
    order_id: str
    currency: str
    source_fiat_value: int
    fiat_value: float
    auto_settle: bool
    notif_email: Optional[str]
    address: str
    metadata: dict
    chain_invoice: ChainInvoice
    uri: str
    ttl: int
    lightning_invoice: LightningInvoice

    @classmethod
    def from_dict(cls, data: Any) -> "Invoice":
        payload = data["data"]
        return cls(
            **{
                **payload,
                "chain_invoice": ChainInvoice(**payload["chain_invoice"]),
                "lightning_invoice": LightningInvoice(**payload["lightning_invoice"]),
            }
        )