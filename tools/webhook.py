from os import getenv
from dotenv import load_dotenv
import hmac
import hashlib
import requests
from src.v1.models.InvoiceWebhook import InvoiceWebhook

load_dotenv(".env")

def sign_webhook(id: str):
    BYTES_API_KEY = bytes(getenv("OPENNODE_API_KEY"), "utf-8") # pyright: ignore[reportArgumentType]
    invoice = InvoiceWebhook(
        id=id,
        callback_url="",
        success_url="",
        status="paid",
        order_id="",
        description="",
        price=0,
        fee=0,
        auto_settle=False,
        hashed_order="",
    )

    generated_signature = hmac.new(BYTES_API_KEY, invoice.id.encode('utf-8'), hashlib.sha256).hexdigest() # pyright: ignore[reportAttributeAccessIssue]
    invoice.hashed_order = generated_signature
    return invoice

if __name__ == "__main__":
    invoice = sign_webhook("")
    print(requests.post("https://premium.swakraft.fr/webhook/opennode", invoice.__dict__).text)
