from json import JSONDecodeError
from ...v1.errors import INVALID_FIELDS, JSON_PARSE_ERROR
from ...v1.services.invoice import process_invoice
from ..models.InvoiceWebhook import InvoiceWebhook
from ..app import routes
from aiohttp.web_request import Request
from aiohttp.web import HTTPNotFound, HTTPOk, HTTPBadRequest

@routes.post("/webhook/opennode")
async def handle_webhook(request: Request):
    try:
        raw_payload = await request.json()
        invoice = InvoiceWebhook.from_dict(raw_payload).verify()
        await process_invoice(invoice)
        return HTTPOk()
    
    except PermissionError:
        raise HTTPNotFound

    except JSONDecodeError:
        raise HTTPBadRequest(body=JSON_PARSE_ERROR)

    except ValueError:
        raise HTTPBadRequest(body=INVALID_FIELDS)