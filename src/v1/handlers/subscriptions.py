from ...middlewares.authorization import require_auth
from ...v1.services.subscriptions import get_all_subscriptions, get_current_subscription_for_address
from ...v1.services.rating import get_actual_ratting
from ...v1.services.invoice import get_invoice
from ..errors import *
from ..app import routes
from aiohttp.web_request import Request
from aiohttp.web import json_response, HTTPNotFound
from init import log


@routes.post("/{address}/subscribe")
async def get_invoice_for_address(request: Request):
    try:
        address = request.match_info["address"]
        invoice = await get_invoice(address)
        # TODO : Convertir en JSON
        return json_response(invoice)

    except:
        log.error
        raise

@routes.get("/rate")
async def get_rate(_: Request):
    return json_response({"rate": get_actual_ratting()})

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
