from typing import Optional, cast
from aiohttp import ClientSession
from os import getenv
from constants import *
from init import log

HEADERS = {
    "accept": "application/json",
    "Content-Type": "application/json",
    "Authoriz"
    "ation": cast(str, getenv(OPENNODE_API_KEY))
}

async def create_invoice(
    amount: float | int,
    currency: str,
    order_id: str,
    description: Optional[str] = None,
    ttl: Optional[int] = None, 
):
    """
    Crée une invoice OpenNode via l'API

    # Params
    - amount `float` | `int` : Montant à payer
    - currency `str` : Le code ISO de la monnaie à utiliser. Ex: EUR, BTC, SAT... 
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
        "currency": currency,
        "order_id": order_id,
        "description": description,
        "ttl": ttl,
        "callback_url": getenv(CALLBACK_URL),
    }
    async with ClientSession(getenv(OPENNODE_API_URL), headers = HEADERS) as session:
        async with session.post("v1/charge", json = json) as response:
            try:
                payload: dict = await response.json()
                # TODO: Créer le modèle, renvoyer les données
                # TODO: Gérer les erreurs
                # TODO: Enregistrer en DB

            except:
                log.error()
                await session.close()
