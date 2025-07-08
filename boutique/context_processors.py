from .models import Panier


def panier_context(request):
    """Ajoute les informations du panier au contexte global"""
    if request.user.is_authenticated:
        try:
            panier = Panier.objects.get(utilisateur=request.user)
            return {
                'panier_nombre_items': panier.nombre_items,
                'panier_total': panier.total,
            }
        except Panier.DoesNotExist:
            pass

    return {
        'panier_nombre_items': 0,
        'panier_total': 0,
    }