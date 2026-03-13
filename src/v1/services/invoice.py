from src.v1.models.opennode import InvoiceWebhook


async def get_invoice(address: str):
    # TODO: Vérifier si une invoice valide existe déjà pour l'adresse

    # TODO: S'il n'y en a pas, en générer une avec le taux actuel

    pass

async def process_invoice(invoice: InvoiceWebhook):

    # TODO : Logger l'invoice dans opennode_webhooks_logs
    # TODO : Récupérer l'invoice enregistrée en DB
    # TODO : Vérifier le taux associé à l'invoice
    # TODO : Récupérer l'abonnement lié
    # TODO : Créditer/Démarrer l'abonnement


    pass