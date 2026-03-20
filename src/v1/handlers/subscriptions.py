from prisma.models import LightningInvoice

from init import log
from datetime import datetime, timezone
from json import JSONDecodeError

from src.v1.mappers import subscription_from_prisma

from ..services.invoice import create_invoice
from ..services.subscriptions import get_all_subscriptions, get_current_subscription_for_address
from ..services.rating import get_actual_ratting
from ...middlewares.authorization import require_auth
from ..errors import INVALID_AMOUNT, JSON_PARSE_ERROR
from ..exceptions import NoPriceException
from ..app import routes

from aiohttp.web_request import Request
from aiohttp.web import json_response, HTTPNotFound, HTTPBadRequest, HTTPServiceUnavailable

log.debug("importing subscriptions handlers")
@routes.post("/{address}/subscribe")
async def create_invoice_for_address(request: Request):
    # TODO: Ajouter un paramètre pour forcer la création d'une nouvelle invoice même s'il en existe déjà une utilisable
    try:
        address = request.match_info["address"]
        payload: dict = await request.json()
        amount = int(payload.get("amount", 0))

        if not amount:
            return HTTPBadRequest(body=INVALID_AMOUNT)

        db = request.app["prisma"]
        invoice = await create_invoice(
            db=db,
            address=address,
            amount=amount,
            order_id=hex(int(datetime.now(timezone.utc).timestamp()))[2:],
            description=payload.get("description"),
            ttl=payload.get("ttl"),
        )

        if isinstance(invoice, LightningInvoice):
            return json_response({"lnurl": invoice.paymentRequest})
        
        else:
            return json_response({"lnurl": invoice.lightning_invoice.payreq})


    except JSONDecodeError:
        return json_response(JSON_PARSE_ERROR)
    
    except NoPriceException:
        raise HTTPServiceUnavailable

    except Exception:
        log.error("Unhandled exception")
        raise HTTPBadRequest()

@routes.get("/rate")
async def get_rate(request: Request):
    try:
        db = request.app["prisma"]
        return json_response({"rate": await get_actual_ratting(db)})
    except NoPriceException:
        raise HTTPServiceUnavailable

@routes.get("/subscriptions")
@require_auth
async def get_all_active_subscriptions(request: Request):
    db = request.app["prisma"]
    subscriptions = await get_all_subscriptions(db)
    return json_response([subscription_from_prisma(subscription).model_dump(mode='json') for subscription in subscriptions])

@routes.get("/{address}/subscription")
async def get_address_subsription(request: Request):
    db = request.app["prisma"]
    subscription = await get_current_subscription_for_address(db, request.match_info["address"])
    if subscription == None:
        raise HTTPNotFound

    return json_response(subscription_from_prisma(subscription).model_dump(mode='json'))
