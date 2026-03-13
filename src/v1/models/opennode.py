from dataclasses import dataclass
from typing import Any, Literal, cast
from os import getenv
import hmac, hashlib


@dataclass
class InvoiceWebhook:
    id: str
    callback_url: str
    success_url: str
    status: Literal["paid", "expired"]
    order_id: str
    description: str
    price: float
    fee: float
    auto_settle: bool
    hashed_order: str

    def verify(self) -> "InvoiceWebhook":
        received = self.hashed_order
        calculated = hmac.new(cast(str, getenv("OPENNODE_API_KEY")).encode(), self.id.encode(), hashlib.sha256).hexdigest()
        if received == calculated:
            return self
        raise PermissionError("Signature missmatch")

    @classmethod
    def from_dict(cls, data: Any) -> "InvoiceWebhook":
        try:
            return cls(**data)

        except Exception as e:
            raise ValueError("Cannot parse webhook", e)