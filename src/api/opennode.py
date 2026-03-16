from typing import Optional
from aiohttp import ClientSession

from src.settings import settings
from init import log
from src.v1.models.invoice import Invoice

HEADERS = {
    "accept": "application/json",
    "Content-Type": "application/json",
    "Authorization": settings.opennode_api_key,
}

async def create_invoice(
    amount: float | int,
    order_id: str,
    description: Optional[str] = None,
    ttl: Optional[int] = None, 
) -> Invoice:
    """
    Crée une invoice OpenNode via l'API

    # Params
    - amount `float` | `int` : Montant à payer
    - order_id `str` : Identifiant interne de l'invoice
    - description `str` : Description à afficher sur le wallet de l'utilisateur
    - ttl `int` : Durée de vie de l'invoice en minutes. 1440 par défaut. Min: 10, max: 4320 (72h)

    # Exemple
    ```python
    invoice = await create_invoice(5000, "SAT", "e8ca195b9eff5", "Payer chez Chauffagistes")
    ```
    """
    json = {
        "amount": amount,
        "order_id": order_id,
        "callback_url": settings.callback_url,
    }
    if description is not None:
        json["description"] = description
    if ttl is not None:
        json["ttl"] = ttl
    async with ClientSession(settings.opennode_api_url, headers = HEADERS) as session:
        async with session.post("/v1/charges", json = json) as response:
            try:
                response.raise_for_status()

                payload: dict = await response.json()
                invoice = Invoice.from_dict(payload)
                
                return invoice

            except KeyError:
                log.error("Payload invalide")
                raise
                

            except Exception:
                log.error("Erreur inconnue pendant l'appel d'API OpenNode")
                raise
            
            finally:
                await session.close()
