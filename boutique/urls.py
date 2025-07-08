from django.urls import path
from . import views

app_name = 'boutique'

urlpatterns = [
    # Pages principales
    path('', views.accueil, name='accueil'),
    path('produits/', views.liste_produits, name='liste_produits'),
    path('produit/<int:pk>/', views.detail_produit, name='detail_produit'),
    path('categorie/<int:pk>/', views.produits_par_categorie, name='produits_par_categorie'),

    # Pages institutionnelles
    path('contact/', views.contact, name='contact'),
    path('a-propos/', views.a_propos, name='a_propos'),

    # Authentification
    path('inscription/', views.inscription, name='inscription'),
    path('connexion/', views.connexion, name='connexion'),
    path('deconnexion/', views.deconnexion, name='deconnexion'),

    # Panier
    path('panier/', views.voir_panier, name='voir_panier'),
    path('ajouter-au-panier/<int:produit_id>/', views.ajouter_au_panier, name='ajouter_au_panier'),
    path('modifier-panier/<int:item_id>/', views.modifier_panier, name='modifier_panier'),
    path('supprimer-du-panier/<int:item_id>/', views.supprimer_du_panier, name='supprimer_du_panier'),

    # Commandes
    path('commander/', views.commander, name='commander'),
    path('commande/<str:numero>/', views.detail_commande, name='detail_commande'),
    path('mes-commandes/', views.mes_commandes, name='mes_commandes'),
    path('telecharger-facture/<str:numero>/', views.telecharger_facture, name='telecharger_facture'),

    # Paiement
    path('paiement/<str:numero>/', views.paiement, name='paiement'),
    path('paiement-stripe/<str:numero>/', views.paiement_stripe, name='paiement_stripe'),
    path('paiement-cinetpay/<str:numero>/', views.paiement_cinetpay, name='paiement_cinetpay'),
    path('paiement-succes/<str:numero>/', views.paiement_succes, name='paiement_succes'),
    path('paiement-echec/<str:numero>/', views.paiement_echec, name='paiement_echec'),

    # Webhooks
    path('webhook/stripe/', views.webhook_stripe, name='webhook_stripe'),
    path('webhook/cinetpay/', views.webhook_cinetpay, name='webhook_cinetpay'),

    # Administration
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-commandes/', views.admin_commandes, name='admin_commandes'),
    path('admin-modifier-commande/<str:numero>/', views.admin_modifier_commande, name='admin_modifier_commande'),
    path('admin-rh/', views.admin_rh, name='admin_rh'),
    path('admin-approuver-conge/<int:conge_id>/', views.admin_approuver_conge, name='admin_approuver_conge'),

    # Nouvelles fonctionnalités admin
    path('admin-export-employees/', views.export_employees, name='export_employees'),
    path('admin-employee-details/<int:employee_id>/', views.employee_details, name='employee_details'),
    path('admin-print-employee-card/<int:employee_id>/', views.print_employee_card, name='print_employee_card'),
    path('admin-export-orders/', views.export_orders, name='export_orders'),
]