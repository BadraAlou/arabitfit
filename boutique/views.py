from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.db.models import Q, Sum, Count
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
import stripe
import json
import requests
import uuid
import re
import csv
from datetime import datetime, timedelta
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

from .models import (
    Produit, Categorie, Panier, ItemPanier, Commande, ItemCommande, AvisProduit,
    Employe, Presence, Conge, Evaluation
)
from .forms import InscriptionForm, CommandeForm, RechercheForm, AvisProduitForm

# Configuration Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

# Taux de conversion XOF vers EUR (pour Stripe qui n'accepte que EUR/USD)
TAUX_XOF_EUR = Decimal('0.00152449')  # 1 XOF = 0.00152449 EUR


def accueil(request):
    """Page d'accueil avec les produits populaires et témoignages clients"""
    produits_populaires = Produit.objects.filter(actif=True)[:6]
    categories = Categorie.objects.all()

    # Récupérer les vrais avis clients (les mieux notés et récents)
    avis_clients = AvisProduit.objects.filter(
        approuve=True,
        note__gte=4  # Avis 4 étoiles et plus
    ).select_related('utilisateur', 'produit').order_by('-date_creation')[:6]

    context = {
        'produits_populaires': produits_populaires,
        'categories': categories,
        'avis_clients': avis_clients,
    }
    return render(request, 'boutique/accueil.html', context)


def liste_produits(request):
    """Liste de tous les produits avec recherche et filtrage"""
    produits = Produit.objects.filter(actif=True)
    categories = Categorie.objects.all()

    form = RechercheForm(request.GET)

    if form.is_valid():
        q = form.cleaned_data.get('q')
        categorie = form.cleaned_data.get('categorie')

        if q:
            produits = produits.filter(
                Q(nom__icontains=q) | Q(description__icontains=q)
            )

        if categorie:
            produits = produits.filter(categorie_id=categorie)

    context = {
        'produits': produits,
        'categories': categories,
        'form': form,
    }
    return render(request, 'boutique/liste_produits.html', context)


def detail_produit(request, pk):
    """Détail d'un produit avec système d'avis"""
    produit = get_object_or_404(Produit, pk=pk, actif=True)
    produits_similaires = Produit.objects.filter(
        categorie=produit.categorie,
        actif=True
    ).exclude(pk=pk)[:4]

    # Récupérer les avis approuvés pour ce produit
    avis = AvisProduit.objects.filter(
        produit=produit,
        approuve=True
    ).select_related('utilisateur').order_by('-date_creation')

    # Vérifier si l'utilisateur connecté a déjà donné un avis
    avis_utilisateur = None
    if request.user.is_authenticated:
        try:
            avis_utilisateur = AvisProduit.objects.get(
                produit=produit,
                utilisateur=request.user
            )
        except AvisProduit.DoesNotExist:
            pass

    # Traitement du formulaire d'avis
    if request.method == 'POST' and request.user.is_authenticated:
        if not avis_utilisateur:  # L'utilisateur n'a pas encore donné d'avis
            form = AvisProduitForm(request.POST)
            if form.is_valid():
                avis_obj = form.save(commit=False)
                avis_obj.produit = produit
                avis_obj.utilisateur = request.user
                avis_obj.save()
                messages.success(request, 'Votre avis a été ajouté avec succès!')
                return redirect('boutique:detail_produit', pk=pk)
        else:
            messages.info(request, 'Vous avez déjà donné votre avis sur ce produit.')

    form = AvisProduitForm() if request.user.is_authenticated and not avis_utilisateur else None

    context = {
        'produit': produit,
        'produits_similaires': produits_similaires,
        'avis': avis,
        'avis_utilisateur': avis_utilisateur,
        'form': form,
    }
    return render(request, 'boutique/detail_produit.html', context)


def produits_par_categorie(request, pk):
    """Produits d'une catégorie spécifique"""
    categorie = get_object_or_404(Categorie, pk=pk)
    produits = Produit.objects.filter(categorie=categorie, actif=True)
    categories = Categorie.objects.all()

    context = {
        'categorie': categorie,
        'produits': produits,
        'categories': categories,
    }
    return render(request, 'boutique/produits_par_categorie.html', context)


def contact(request):
    """Page de contact"""
    if request.method == 'POST':
        # Traitement du formulaire de contact
        prenom = request.POST.get('prenom')
        nom = request.POST.get('nom')
        email = request.POST.get('email')
        telephone = request.POST.get('telephone')
        sujet = request.POST.get('sujet')
        message = request.POST.get('message')

        # Ici vous pouvez ajouter l'envoi d'email ou sauvegarder en base
        messages.success(request,
                         'Votre message a été envoyé avec succès! Nous vous répondrons dans les plus brefs délais.')
        return redirect('boutique:contact')

    return render(request, 'boutique/contact.html')


def a_propos(request):
    """Page à propos"""
    return render(request, 'boutique/a_propos.html')


def inscription(request):
    """Inscription d'un nouvel utilisateur"""
    if request.user.is_authenticated:
        return redirect('boutique:accueil')

    if request.method == 'POST':
        form = InscriptionForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Compte créé pour {username}!')
            return redirect('boutique:connexion')
    else:
        form = InscriptionForm()

    return render(request, 'boutique/inscription.html', {'form': form})


def connexion(request):
    """Connexion utilisateur avec redirection admin"""
    if request.user.is_authenticated:
        return redirect('boutique:accueil')

    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, 'Connexion réussie!')

            # Redirection vers le tableau de bord admin si l'utilisateur est admin
            if user.is_staff or user.is_superuser:
                return redirect('boutique:admin_dashboard')
            else:
                return redirect('boutique:accueil')
        else:
            messages.error(request, 'Nom d\'utilisateur ou mot de passe incorrect.')

    return render(request, 'boutique/connexion.html')


def deconnexion(request):
    """Déconnexion utilisateur"""
    logout(request)
    messages.success(request, 'Vous avez été déconnecté.')
    return redirect('boutique:accueil')


@login_required
def voir_panier(request):
    """Affichage du panier"""
    panier, created = Panier.objects.get_or_create(utilisateur=request.user)

    context = {
        'panier': panier,
    }
    return render(request, 'boutique/panier.html', context)


@login_required
def ajouter_au_panier(request, produit_id):
    """Ajouter un produit au panier"""
    produit = get_object_or_404(Produit, id=produit_id, actif=True)
    panier, created = Panier.objects.get_or_create(utilisateur=request.user)

    item, created = ItemPanier.objects.get_or_create(
        panier=panier,
        produit=produit,
        defaults={'quantite': 1}
    )

    if not created:
        if item.quantite < produit.stock:
            item.quantite += 1
            item.save()
            messages.success(request, f'{produit.nom} ajouté au panier!')
        else:
            messages.error(request, 'Stock insuffisant!')
    else:
        if produit.stock > 0:
            messages.success(request, f'{produit.nom} ajouté au panier!')
        else:
            item.delete()
            messages.error(request, 'Produit en rupture de stock!')

    return redirect('boutique:detail_produit', pk=produit_id)


@login_required
def modifier_panier(request, item_id):
    """Modifier la quantité d'un article dans le panier"""
    item = get_object_or_404(ItemPanier, id=item_id, panier__utilisateur=request.user)

    if request.method == 'POST':
        quantite = int(request.POST.get('quantite', 1))
        if quantite > 0 and quantite <= item.produit.stock:
            item.quantite = quantite
            item.save()
            messages.success(request, 'Panier mis à jour!')
        else:
            messages.error(request, 'Quantité invalide!')

    return redirect('boutique:voir_panier')


@login_required
def supprimer_du_panier(request, item_id):
    """Supprimer un article du panier"""
    item = get_object_or_404(ItemPanier, id=item_id, panier__utilisateur=request.user)
    nom_produit = item.produit.nom
    item.delete()
    messages.success(request, f'{nom_produit} retiré du panier!')
    return redirect('boutique:voir_panier')


@login_required
def commander(request):
    """Créer une commande"""
    panier, created = Panier.objects.get_or_create(utilisateur=request.user)

    if not panier.items.exists():
        messages.error(request, 'Votre panier est vide!')
        return redirect('boutique:voir_panier')

    if request.method == 'POST':
        form = CommandeForm(request.POST)
        if form.is_valid():
            # Créer la commande
            commande = form.save(commit=False)
            commande.utilisateur = request.user
            # Le total est déjà en XOF
            commande.total = panier.total
            commande.save()

            # Créer les items de commande
            for item in panier.items.all():
                ItemCommande.objects.create(
                    commande=commande,
                    produit=item.produit,
                    nom_produit=item.produit.nom,
                    prix_unitaire=item.produit.prix,  # Prix en XOF
                    quantite=item.quantite
                )

            # Vider le panier
            panier.items.all().delete()

            messages.success(request, 'Commande créée avec succès!')
            return redirect('boutique:paiement', numero=commande.numero)
    else:
        # Préremplir le formulaire avec les données utilisateur
        initial_data = {
            'nom_complet': f"{request.user.first_name} {request.user.last_name}".strip(),
            'email': request.user.email,
        }
        form = CommandeForm(initial=initial_data)

    context = {
        'form': form,
        'panier': panier,
    }
    return render(request, 'boutique/commander.html', context)


@login_required
def detail_commande(request, numero):
    """Détail d'une commande"""
    commande = get_object_or_404(Commande, numero=numero, utilisateur=request.user)

    context = {
        'commande': commande,
    }
    return render(request, 'boutique/detail_commande.html', context)


@login_required
def mes_commandes(request):
    """Liste des commandes de l'utilisateur"""
    commandes = Commande.objects.filter(utilisateur=request.user)

    context = {
        'commandes': commandes,
    }
    return render(request, 'boutique/mes_commandes.html', context)


@login_required
def telecharger_facture(request, numero):
    """Générer et télécharger la facture PDF d'une commande"""
    commande = get_object_or_404(Commande, numero=numero, utilisateur=request.user)

    # Vérifier que la commande est confirmée
    if commande.statut not in ['confirmee', 'expediee', 'livree']:
        messages.error(request, 'La facture n\'est disponible que pour les commandes confirmées.')
        return redirect('boutique:mes_commandes')

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="facture_{commande.numero}.pdf"'

    # Créer le PDF avec ReportLab
    doc = SimpleDocTemplate(response, pagesize=A4, topMargin=1 * inch)
    styles = getSampleStyleSheet()
    story = []

    # Style personnalisé pour le titre
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=1,  # Centré
        textColor=colors.HexColor('#8B4513')
    )

    # Style pour les informations
    info_style = ParagraphStyle(
        'InfoStyle',
        parent=styles['Normal'],
        fontSize=12,
        spaceAfter=12,
        leftIndent=20
    )

    # En-tête avec logo et informations entreprise
    header_data = [
        ['BIODETOX MALI', f'FACTURE N° {commande.numero}'],
        ['Produits détox naturels', f'Date: {commande.date_creation.strftime("%d/%m/%Y")}'],
        ['Bamako, Mali', f'Statut: {commande.get_statut_display()}'],
        ['Tél: +223 83 69 11 15', ''],
        ['Email: contact@biodetoxmali.com', '']
    ]

    header_table = Table(header_data, colWidths=[3 * inch, 3 * inch])
    header_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#8B4513')),
        ('TEXTCOLOR', (1, 0), (1, 0), colors.HexColor('#228B22')),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))

    story.append(header_table)
    story.append(Spacer(1, 30))

    # Informations client
    client_title = Paragraph("INFORMATIONS CLIENT", styles['Heading2'])
    story.append(client_title)
    story.append(Spacer(1, 10))

    client_data = [
        ['Nom:', commande.nom_complet],
        ['Email:', commande.email],
        ['Téléphone:', commande.telephone],
        ['Adresse:', commande.adresse],
        ['Ville:', f"{commande.ville} {commande.code_postal}"],
    ]

    client_table = Table(client_data, colWidths=[1.5 * inch, 4 * inch])
    client_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ]))

    story.append(client_table)
    story.append(Spacer(1, 30))

    # Détail des articles
    items_title = Paragraph("DÉTAIL DE LA COMMANDE", styles['Heading2'])
    story.append(items_title)
    story.append(Spacer(1, 10))

    # En-tête du tableau des articles
    items_data = [['Article', 'Quantité', 'Prix unitaire (XOF)', 'Total (XOF)']]

    # Ajouter chaque article
    for item in commande.items.all():
        items_data.append([
            item.nom_produit,
            str(item.quantite),
            f"{item.prix_unitaire:,.0f}",
            f"{item.total:,.0f}"
        ])

    # Ligne de total
    items_data.append(['', '', 'TOTAL:', f"{commande.total:,.0f} XOF"])

    items_table = Table(items_data, colWidths=[3 * inch, 1 * inch, 1.5 * inch, 1.5 * inch])
    items_table.setStyle(TableStyle([
        # En-tête
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#98FB98')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#8B4513')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),

        # Corps du tableau
        ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -2), 10),
        ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
        ('ALIGN', (0, 1), (0, -1), 'LEFT'),

        # Ligne de total
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#F0F0F0')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, -1), (-1, -1), 12),
        ('TEXTCOLOR', (0, -1), (-1, -1), colors.HexColor('#228B22')),

        # Bordures
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#CCCCCC')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
    ]))

    story.append(items_table)
    story.append(Spacer(1, 30))

    # Informations de paiement
    payment_title = Paragraph("INFORMATIONS DE PAIEMENT", styles['Heading2'])
    story.append(payment_title)
    story.append(Spacer(1, 10))

    payment_data = [
        ['Méthode de paiement:', commande.get_methode_paiement_display()],
        ['Montant total:', f"{commande.total:,.0f} XOF"],
        ['Date de paiement:',
         commande.date_confirmation.strftime("%d/%m/%Y à %H:%M") if commande.date_confirmation else 'En attente'],
        ['Statut:', commande.get_statut_display()],
    ]

    payment_table = Table(payment_data, colWidths=[2 * inch, 3 * inch])
    payment_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ]))

    story.append(payment_table)
    story.append(Spacer(1, 40))

    # Pied de page
    footer_text = f"""
    <para align="center">
    <b>Merci pour votre confiance !</b><br/>
    Cette facture a été générée automatiquement le {timezone.now().strftime('%d/%m/%Y à %H:%M')}<br/>
    Pour toute question, contactez-nous : contact@biodetoxmali.com | +223 83 69 11 15<br/>
    <br/>
    <i>Biodetox Mali - Le goût du bien être</i>
    </para>
    """

    footer = Paragraph(footer_text, styles['Normal'])
    story.append(footer)

    doc.build(story)
    return response


@login_required
def paiement(request, numero):
    """Page de paiement"""
    commande = get_object_or_404(Commande, numero=numero, utilisateur=request.user)

    context = {
        'commande': commande,
        'stripe_publishable_key': settings.STRIPE_PUBLISHABLE_KEY,
    }
    return render(request, 'boutique/paiement.html', context)


@login_required
def paiement_stripe(request, numero):
    """Traitement du paiement Stripe"""
    commande = get_object_or_404(Commande, numero=numero, utilisateur=request.user)

    try:
        # Convertir le montant XOF en EUR pour Stripe
        montant_eur = commande.total * TAUX_XOF_EUR

        # Créer une session de paiement Stripe
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'eur',
                    'product_data': {
                        'name': f'Commande Biodetox Mali {commande.numero}',
                        'description': f'Commande de produits minceur naturels - {commande.total} XOF',
                    },
                    'unit_amount': int(montant_eur * 100),  # Stripe utilise les centimes
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=request.build_absolute_uri(f'/paiement-succes/{commande.numero}/'),
            cancel_url=request.build_absolute_uri(f'/paiement-echec/{commande.numero}/'),
            metadata={
                'commande_numero': commande.numero,
                'user_id': request.user.id,
                'montant_xof': str(commande.total),
            }
        )

        commande.paiement_id = session.id
        commande.save()

        return redirect(session.url)

    except Exception as e:
        messages.error(request, f'Erreur lors du paiement: {str(e)}')
        return redirect('boutique:paiement', numero=numero)


@login_required
def paiement_cinetpay(request, numero):
    """Traitement du paiement CinetPay - Mode développement simplifié"""
    commande = get_object_or_404(Commande, numero=numero, utilisateur=request.user)

    if request.method == 'POST':
        operator = request.POST.get('operator')
        phone_number = request.POST.get('phone_number', '').replace(' ', '')

        # Validation du numéro de téléphone malien
        if not re.match(r'^[0-9]{8}$', phone_number):
            messages.error(request, 'Numéro de téléphone invalide. Veuillez entrer 8 chiffres.')
            return redirect('boutique:paiement', numero=numero)

        # Mode développement : simulation du paiement réussi
        if settings.DEBUG:
            # Simuler un paiement réussi automatiquement
            commande.statut = 'confirmee'
            commande.date_confirmation = timezone.now()
            commande.paiement_id = f"DEV_PAYMENT_{uuid.uuid4().hex[:8]}"
            commande.save()

            # Décrémenter le stock des produits
            for item in commande.items.all():
                produit = item.produit
                if produit.stock >= item.quantite:
                    produit.stock -= item.quantite
                    produit.save()

            messages.success(request, f'Paiement {operator.title()} Money simulé avec succès (mode développement)!')
            return redirect('boutique:paiement_succes', numero=numero)

        # Code de production CinetPay (désactivé en mode dev)
        else:
            try:
                # Configuration CinetPay
                cinetpay_data = {
                    'apikey': settings.CINETPAY_API_KEY,
                    'site_id': settings.CINETPAY_SITE_ID,
                    'transaction_id': f"BIODETOXMALI_{commande.numero}_{uuid.uuid4().hex[:8]}",
                    'amount': int(commande.total),
                    'currency': 'XOF',
                    'description': f'Commande Biodetox Mali {commande.numero} - {commande.total} XOF',
                    'return_url': request.build_absolute_uri(f'/paiement-succes/{commande.numero}/'),
                    'notify_url': request.build_absolute_uri(f'/webhook/cinetpay/'),
                    'customer_name': commande.nom_complet,
                    'customer_email': commande.email,
                    'customer_phone_number': f'+223{phone_number}',
                    'channels': 'MOBILE_MONEY',
                }

                # Appel API CinetPay
                response = requests.post(
                    'https://api-checkout.cinetpay.com/v2/payment',
                    json=cinetpay_data,
                    headers={'Content-Type': 'application/json'}
                )

                if response.status_code == 200:
                    result = response.json()
                    if result.get('code') == '201':
                        # Paiement initié avec succès
                        commande.paiement_id = result.get('data', {}).get('transaction_id')
                        commande.save()

                        payment_url = result.get('data', {}).get('payment_url')
                        if payment_url:
                            return redirect(payment_url)
                        else:
                            messages.success(request,
                                             f'Paiement {operator.title()} Money initié. Suivez les instructions sur votre téléphone.')
                            return redirect('boutique:paiement_succes', numero=numero)
                    else:
                        messages.error(request, f'Erreur CinetPay: {result.get("message", "Erreur inconnue")}')
                else:
                    messages.error(request, 'Erreur de connexion avec CinetPay')

            except Exception as e:
                messages.error(request, f'Erreur lors du paiement: {str(e)}')

    return redirect('boutique:paiement', numero=numero)


@login_required
def paiement_succes(request, numero):
    """Page de succès après paiement"""
    commande = get_object_or_404(Commande, numero=numero, utilisateur=request.user)

    # Marquer la commande comme confirmée et décrémenter le stock
    if commande.statut == 'en_attente':
        commande.statut = 'confirmee'
        commande.date_confirmation = timezone.now()
        commande.save()

        # Décrémenter le stock des produits
        for item in commande.items.all():
            produit = item.produit
            if produit.stock >= item.quantite:
                produit.stock -= item.quantite
                produit.save()

    messages.success(request, 'Paiement réussi! Votre commande a été confirmée.')

    context = {
        'commande': commande,
    }
    return render(request, 'boutique/paiement_succes.html', context)


@login_required
def paiement_echec(request, numero):
    """Page d'échec après paiement"""
    commande = get_object_or_404(Commande, numero=numero, utilisateur=request.user)

    messages.error(request, 'Le paiement a échoué. Veuillez réessayer.')

    context = {
        'commande': commande,
    }
    return render(request, 'boutique/paiement_echec.html', context)


@csrf_exempt
def webhook_stripe(request):
    """Webhook pour les notifications Stripe"""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET  # À ajouter dans settings

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError:
        return JsonResponse({'error': 'Invalid payload'}, status=400)
    except stripe.error.SignatureVerificationError:
        return JsonResponse({'error': 'Invalid signature'}, status=400)

    # Traitement des événements Stripe
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        commande_numero = session['metadata']['commande_numero']

        try:
            commande = Commande.objects.get(numero=commande_numero)
            commande.statut = 'confirmee'
            commande.date_confirmation = timezone.now()
            commande.save()

            # Décrémenter le stock
            for item in commande.items.all():
                produit = item.produit
                if produit.stock >= item.quantite:
                    produit.stock -= item.quantite
                    produit.save()

        except Commande.DoesNotExist:
            pass

    return JsonResponse({'status': 'success'})


@csrf_exempt
def webhook_cinetpay(request):
    """Webhook pour les notifications CinetPay"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            transaction_id = data.get('cpm_trans_id')
            status = data.get('cpm_result')

            if status == '00':  # Paiement réussi
                # Extraire le numéro de commande du transaction_id
                if transaction_id and 'BIODETOXMALI_' in transaction_id:
                    parts = transaction_id.split('_')
                    if len(parts) >= 2:
                        commande_numero = parts[1]

                        try:
                            commande = Commande.objects.get(numero=commande_numero)
                            commande.statut = 'confirmee'
                            commande.date_confirmation = timezone.now()
                            commande.save()

                            # Décrémenter le stock
                            for item in commande.items.all():
                                produit = item.produit
                                if produit.stock >= item.quantite:
                                    produit.stock -= item.quantite
                                    produit.save()

                        except Commande.DoesNotExist:
                            pass

        except json.JSONDecodeError:
            pass

    return JsonResponse({'status': 'success'})


# Vues d'administration

@staff_member_required
def admin_dashboard(request):
    """Tableau de bord administrateur"""
    today = timezone.now().date()

    # Statistiques des commandes
    stats_commandes = {
        'total_commandes': Commande.objects.count(),
        'commandes_aujourd_hui': Commande.objects.filter(date_creation__date=today).count(),
        'commandes_en_attente': Commande.objects.filter(statut='en_attente').count(),
        'commandes_confirmees': Commande.objects.filter(statut='confirmee').count(),
        'commandes_expediees': Commande.objects.filter(statut='expediee').count(),
        'revenus_total': Commande.objects.filter(statut__in=['confirmee', 'expediee', 'livree']).aggregate(
            total=Sum('total'))['total'] or 0,
        'revenus_aujourd_hui': Commande.objects.filter(
            date_creation__date=today,
            statut__in=['confirmee', 'expediee', 'livree']
        ).aggregate(total=Sum('total'))['total'] or 0,
    }

    # Statistiques RH
    stats_rh = {
        'total_employes': Employe.objects.filter(statut='actif').count(),
        'employes_presents_aujourd_hui': Presence.objects.filter(date=today).count(),
        'conges_en_attente': Conge.objects.filter(statut='en_attente').count(),
        'employes_en_conge': Conge.objects.filter(
            statut='approuve',
            date_debut__lte=today,
            date_fin__gte=today
        ).count(),
    }

    # Commandes récentes
    commandes_recentes = Commande.objects.select_related('utilisateur').order_by('-date_creation')[:10]

    # Congés en attente
    conges_en_attente = Conge.objects.filter(statut='en_attente').select_related('employe__user')[:5]

    # Présences d'aujourd'hui
    presences_aujourd_hui = Presence.objects.filter(date=today).select_related('employe__user')

    context = {
        'stats_commandes': stats_commandes,
        'stats_rh': stats_rh,
        'commandes_recentes': commandes_recentes,
        'conges_en_attente': conges_en_attente,
        'presences_aujourd_hui': presences_aujourd_hui,
    }
    return render(request, 'boutique/admin_dashboard.html', context)


@staff_member_required
def admin_commandes(request):
    """Gestion des commandes pour l'admin"""
    commandes = Commande.objects.select_related('utilisateur').order_by('-date_creation')

    # Filtrage par statut
    statut_filtre = request.GET.get('statut')
    if statut_filtre:
        commandes = commandes.filter(statut=statut_filtre)

    # Recherche
    search = request.GET.get('search')
    if search:
        commandes = commandes.filter(
            Q(numero__icontains=search) |
            Q(utilisateur__username__icontains=search) |
            Q(email__icontains=search) |
            Q(nom_complet__icontains=search)
        )

    # Filtrage par date
    date_debut = request.GET.get('date_debut')
    date_fin = request.GET.get('date_fin')
    if date_debut:
        commandes = commandes.filter(date_creation__date__gte=date_debut)
    if date_fin:
        commandes = commandes.filter(date_creation__date__lte=date_fin)

    context = {
        'commandes': commandes,
        'statut_filtre': statut_filtre,
        'statuts': Commande.STATUT_CHOICES,
    }
    return render(request, 'boutique/admin_commandes.html', context)


@staff_member_required
def admin_modifier_commande(request, numero):
    """Modifier le statut d'une commande"""
    commande = get_object_or_404(Commande, numero=numero)

    if request.method == 'POST':
        nouveau_statut = request.POST.get('statut')
        numero_suivi = request.POST.get('numero_suivi', '')
        notes_admin = request.POST.get('notes_admin', '')

        if nouveau_statut in dict(Commande.STATUT_CHOICES):
            ancien_statut = commande.statut
            commande.statut = nouveau_statut
            commande.numero_suivi = numero_suivi
            commande.notes_admin = notes_admin

            # Mettre à jour les dates selon le statut
            if nouveau_statut == 'expediee' and ancien_statut != 'expediee':
                commande.date_expedition = timezone.now()
            elif nouveau_statut == 'livree' and ancien_statut != 'livree':
                commande.date_livraison = timezone.now()

            commande.save()
            messages.success(request, f'Commande {numero} mise à jour avec succès!')
            return redirect('boutique:admin_commandes')

    context = {
        'commande': commande,
        'statuts': Commande.STATUT_CHOICES,
    }
    return render(request, 'boutique/admin_modifier_commande.html', context)


@staff_member_required
def admin_rh(request):
    """Tableau de bord RH"""
    today = timezone.now().date()

    # Statistiques
    stats = {
        'total_employes': Employe.objects.filter(statut='actif').count(),
        'presences_aujourd_hui': Presence.objects.filter(date=today).count(),
        'conges_en_attente': Conge.objects.filter(statut='en_attente').count(),
        'employes_en_conge': Conge.objects.filter(
            statut='approuve',
            date_debut__lte=today,
            date_fin__gte=today
        ).count(),
    }

    # Données récentes
    employes = Employe.objects.filter(statut='actif').select_related('user')
    conges_en_attente = Conge.objects.filter(statut='en_attente').select_related('employe__user')[:10]
    presences_aujourd_hui = Presence.objects.filter(date=today).select_related('employe__user')

    context = {
        'stats': stats,
        'employes': employes,
        'conges_en_attente': conges_en_attente,
        'presences_aujourd_hui': presences_aujourd_hui,
    }
    return render(request, 'boutique/admin_rh.html', context)


@staff_member_required
def admin_approuver_conge(request, conge_id):
    """Approuver ou refuser un congé"""
    conge = get_object_or_404(Conge, id=conge_id)

    if request.method == 'POST':
        action = request.POST.get('action')
        commentaire = request.POST.get('commentaire', '')

        if action == 'approuver':
            conge.statut = 'approuve'
            conge.approuve_par = request.user
            conge.date_approbation = timezone.now()
            conge.commentaire_admin = commentaire
            conge.save()
            messages.success(request, f'Congé de {conge.employe.user.get_full_name()} approuvé!')
        elif action == 'refuser':
            conge.statut = 'refuse'
            conge.approuve_par = request.user
            conge.date_approbation = timezone.now()
            conge.commentaire_admin = commentaire
            conge.save()
            messages.warning(request, f'Congé de {conge.employe.user.get_full_name()} refusé!')

        return redirect('boutique:admin_rh')

    context = {
        'conge': conge,
    }
    return render(request, 'boutique/admin_approuver_conge.html', context)


# Nouvelles fonctionnalités admin

@staff_member_required
def export_employees(request):
    """Exporter la liste des employés en CSV"""
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="employes_biodetox.csv"'

    # Ajouter BOM pour Excel
    response.write('\ufeff')

    writer = csv.writer(response)
    writer.writerow(
        ['Nom', 'Prénom', 'Email', 'Poste', 'Numéro Employé', 'Date Embauche', 'Salaire (XOF)', 'Statut', 'Téléphone'])

    employes = Employe.objects.select_related('user').all()
    for employe in employes:
        writer.writerow([
            employe.user.last_name,
            employe.user.first_name,
            employe.user.email,
            employe.get_poste_display(),
            employe.numero_employe,
            employe.date_embauche.strftime('%d/%m/%Y'),
            f"{employe.salaire:,.0f}",
            employe.get_statut_display(),
            employe.telephone
        ])

    return response


@staff_member_required
def employee_details(request, employee_id):
    """Détails complets d'un employé en JSON"""
    try:
        employe = get_object_or_404(Employe, id=employee_id)

        # Statistiques de l'employé
        today = timezone.now().date()
        current_month = today.month
        current_year = today.year

        presences_ce_mois = Presence.objects.filter(
            employe=employe,
            date__month=current_month,
            date__year=current_year
        )

        conges_pris = Conge.objects.filter(
            employe=employe,
            statut='approuve',
            date_fin__lt=today
        )

        conges_en_cours = Conge.objects.filter(
            employe=employe,
            statut='approuve',
            date_debut__lte=today,
            date_fin__gte=today
        )

        # Présences récentes
        presences_recentes = Presence.objects.filter(employe=employe).order_by('-date')[:10]

        # Congés récents
        conges_recents = Conge.objects.filter(employe=employe).order_by('-date_creation')[:5]

        # Calculer les heures travaillées ce mois
        heures_totales = sum([p.heures_travaillees or 0 for p in presences_ce_mois])

        data = {
            'employe': {
                'id': employe.id,
                'nom_complet': employe.user.get_full_name(),
                'email': employe.user.email,
                'numero_employe': employe.numero_employe,
                'poste': employe.get_poste_display(),
                'telephone': employe.telephone,
                'date_embauche': employe.date_embauche.strftime('%d/%m/%Y'),
                'salaire': f"{employe.salaire:,.0f} XOF",
                'statut': employe.get_statut_display(),
                'photo_url': employe.photo.url if employe.photo else None,
            },
            'statistiques': {
                'presences_ce_mois': presences_ce_mois.count(),
                'heures_travaillees_mois': f"{heures_totales:.1f}h",
                'conges_pris_total': conges_pris.count(),
                'conges_en_cours': conges_en_cours.count(),
                'taux_presence': f"{(presences_ce_mois.count() / 22 * 100):.1f}%" if presences_ce_mois.count() <= 22 else "100%"
            },
            'presences_recentes': [
                {
                    'date': p.date.strftime('%d/%m/%Y'),
                    'heure_arrivee': p.heure_arrivee.strftime('%H:%M'),
                    'heure_depart': p.heure_depart.strftime('%H:%M') if p.heure_depart else 'En cours',
                    'heures_travaillees': f"{p.heures_travaillees:.1f}h" if p.heures_travaillees else 'N/A'
                }
                for p in presences_recentes
            ],
            'conges_recents': [
                {
                    'type': c.get_type_conge_display(),
                    'date_debut': c.date_debut.strftime('%d/%m/%Y'),
                    'date_fin': c.date_fin.strftime('%d/%m/%Y'),
                    'nombre_jours': c.nombre_jours,
                    'statut': c.get_statut_display(),
                    'motif': c.motif[:100] + '...' if len(c.motif) > 100 else c.motif
                }
                for c in conges_recents
            ]
        }

        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@staff_member_required
def print_employee_card(request, employee_id):
    """Générer une carte d'employé en PDF"""
    employe = get_object_or_404(Employe, id=employee_id)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="carte_employe_{employe.numero_employe}.pdf"'

    # Créer le PDF avec ReportLab
    doc = SimpleDocTemplate(response, pagesize=A4, topMargin=1 * inch)
    styles = getSampleStyleSheet()
    story = []

    # Style personnalisé pour le titre
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=1,  # Centré
        textColor=colors.HexColor('#667eea')
    )

    # Style pour les informations
    info_style = ParagraphStyle(
        'InfoStyle',
        parent=styles['Normal'],
        fontSize=12,
        spaceAfter=12,
        leftIndent=20
    )

    # Titre
    title = Paragraph("CARTE D'EMPLOYÉ", title_style)
    story.append(title)
    story.append(Spacer(1, 20))

    # Logo ou en-tête entreprise
    company_header = Paragraph("Biodetox Mali", styles['Heading2'])
    story.append(company_header)
    story.append(Spacer(1, 30))

    # Informations employé dans un tableau
    data = [
        ['Nom complet:', employe.user.get_full_name()],
        ['N° Employé:', employe.numero_employe],
        ['Poste:', employe.get_poste_display()],
        ['Date d\'embauche:', employe.date_embauche.strftime('%d/%m/%Y')],
        ['Email:', employe.user.email],
        ['Téléphone:', employe.telephone],
        ['Statut:', employe.get_statut_display()],
    ]

    table = Table(data, colWidths=[2.5 * inch, 4 * inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8f9fa')),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#495057')),
        ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#212529')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))

    story.append(table)
    story.append(Spacer(1, 40))

    # Pied de page
    footer_text = f"Carte générée le {timezone.now().strftime('%d/%m/%Y à %H:%M')}"
    footer = Paragraph(footer_text, styles['Normal'])
    story.append(footer)

    # QR Code ou code-barres (simulation)
    qr_text = f"ID: {employe.numero_employe} | Valide jusqu'au 31/12/{timezone.now().year + 1}"
    qr_para = Paragraph(f"<font size=8>{qr_text}</font>", styles['Normal'])
    story.append(Spacer(1, 20))
    story.append(qr_para)

    doc.build(story)
    return response


@staff_member_required
def export_orders(request):
    """Exporter les commandes en CSV"""
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="commandes_biodetox.csv"'

    # Ajouter BOM pour Excel
    response.write('\ufeff')

    writer = csv.writer(response)
    writer.writerow([
        'Numéro', 'Date', 'Client', 'Email', 'Téléphone',
        'Total (XOF)', 'Statut', 'Méthode Paiement', 'Ville',
        'Nombre Articles', 'Date Confirmation', 'Date Expédition'
    ])

    commandes = Commande.objects.select_related('utilisateur').prefetch_related('items').all()
    for commande in commandes:
        writer.writerow([
            commande.numero,
            commande.date_creation.strftime('%d/%m/%Y %H:%M'),
            commande.nom_complet,
            commande.email,
            commande.telephone,
            f"{commande.total:,.0f}",
            commande.get_statut_display(),
            commande.get_methode_paiement_display(),
            commande.ville,
            commande.items.count(),
            commande.date_confirmation.strftime('%d/%m/%Y %H:%M') if commande.date_confirmation else '',
            commande.date_expedition.strftime('%d/%m/%Y %H:%M') if commande.date_expedition else ''
        ])

    return response