from init import log
from datetime import datetime
from json import JSONDecodeError

from ..services.invoice import create_invoice
from ..services.subscriptions import get_all_subscriptions, get_current_subscription_for_address
from ..services.rating import get_actual_ratting
from ...middlewares.authorization import require_auth
from ..errors import INVALID_AMOUNT, JSON_PARSE_ERROR
from ..exceptions import NoPriceException
from ..app import routes

from aiohttp.web_request import Request
from aiohttp.web import json_response, HTTPNotFound, HTTPBadRequest, HTTPServiceUnavailable


@routes.post("/{address}/subscribe")
async def create_invoice_for_address(request: Request):
    try:
        address = request.match_info["address"]
        payload: dict = await request.json()
        amount = int(payload.get("amount", 0))

        if not amount:
            return json_response(INVALID_AMOUNT)
        
        invoice = await create_invoice(
            amount=amount,
            order_id=f"{address}-{amount}-{hex(int(datetime.now().timestamp()))}",
            description=payload.get("description"),
            ttl=payload.get("ttl"),
        )

        return json_response({"lnurl": invoice.lightning_invoice.payreq})

    except JSONDecodeError:
        return json_response(JSON_PARSE_ERROR)
    
    except NoPriceException:
        raise HTTPServiceUnavailable

    except Exception:
        log.error("Unhandled exception")
        raise HTTPBadRequest()

@routes.get("/rate")
async def get_rate(_: Request):
    try:
        return json_response({"rate": await get_actual_ratting()})
    except NoPriceException:
        raise HTTPServiceUnavailable

@routes.get("/subscriptions")
@require_auth
async def get_all_active_subscriptions(_: Request):
    subscriptions = await get_all_subscriptions()
    # TODO : Convertir en JSON
    return json_response(subscriptions)

@routes.get("/{address}/subsription")
async def get_address_subsription(request: Request):
    subscription = await get_current_subscription_for_address(request.match_info["address"])
    if subscription == None:
        return HTTPNotFound()
    
    # TODO : Convertir en JSON
    return json_response(subscription)
