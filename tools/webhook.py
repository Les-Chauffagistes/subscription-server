from os import getenv, urandom
from dotenv import load_dotenv
import hmac
import hashlib
import requests

load_dotenv(".env")

id = "40e540be-cf60-4cb4-8eff-3619521fc6ea"
BYTES_API_KEY = bytes(getenv("OPENNODE_API_KEY"), "utf-8") # pyright: ignore[reportArgumentType]
invoice = dict(
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

generated_signature = hmac.new(BYTES_API_KEY, invoice["id"].encode('utf-8'), hashlib.sha256).hexdigest() # pyright: ignore[reportAttributeAccessIssue]

invoice["hashed_order"] = generated_signature

requests.post("https://premium.swakraft.fr/webhook/opennode", invoice)
