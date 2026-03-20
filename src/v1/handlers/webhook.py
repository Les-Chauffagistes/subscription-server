from json import JSONDecodeError, dumps
from ...v1.errors import INVALID_FIELDS, JSON_PARSE_ERROR
from ...v1.services.invoice import process_invoice
from ..models.InvoiceWebhook import InvoiceWebhook
from ..app import routes
from aiohttp.web_request import Request
from aiohttp.web import HTTPNotFound, HTTPOk, HTTPBadRequest
from aiofiles import open
from init import log
from ...utils.parse import parse_urlencoded

@routes.post("/webhook/opennode")
async def handle_webhook(request: Request):
    try:
        # Extract urlencoded payload
        raw = await request.text()

        async with open("raw.txt", "a") as f:
            await f.write(raw + "\n")
        
        # Parse it to json
        payload = parse_urlencoded(raw)
        async with open("payloads.jsonl", "a") as f:
            await f.write(dumps(payload) + "\n")

        invoice = InvoiceWebhook.from_dict(payload).verify()
        db = request.app["prisma"]
        result = await process_invoice(db, invoice)
        log.info("Process result", result, invoice.id)
        return HTTPOk()
    
    except PermissionError:
        raise HTTPNotFound

    except JSONDecodeError:
        raise HTTPBadRequest(body=JSON_PARSE_ERROR)

    except ValueError:
        raise HTTPBadRequest(body=INVALID_FIELDS)