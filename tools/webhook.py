from os import getenv
from typing import Literal
from dotenv import load_dotenv
import hmac
import hashlib
import requests
from src.settings import settings
from src.v1.models.InvoiceWebhook import InvoiceWebhook

load_dotenv(".env")

def create_webhook(id: str, status: Literal["paid", "expired"] = "paid"):
    return InvoiceWebhook(
        id,
        "",
        "",
        status,
        "",
        "",
        0.0,
        0.0,
        False,
        ""
    )

def sign_webhook(invoice: InvoiceWebhook):
    BYTES_API_KEY = bytes(getenv("OPENNODE_API_KEY"), "utf-8") # pyright: ignore[reportArgumentType]
    generated_signature = hmac.new(BYTES_API_KEY, invoice.id.encode('utf-8'), hashlib.sha256).hexdigest() # pyright: ignore[reportAttributeAccessIssue]
    invoice.hashed_order = generated_signature
    return invoice

def send_webhook(invoice: InvoiceWebhook):
    return requests.post(f"http://localhost:{settings.server_port}/webhook/opennode", invoice.__dict__)