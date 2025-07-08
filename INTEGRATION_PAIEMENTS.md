# 🚀 Guide d'Intégration des Moyens de Paiement - ArabiFit

## 📋 Table des Matières

1. [Vue d'ensemble](#vue-densemble)
2. [Prérequis](#prérequis)
3. [Configuration Stripe](#configuration-stripe)
4. [Configuration CinetPay](#configuration-cinetpay)
5. [Configuration Django](#configuration-django)
6. [Tests et Validation](#tests-et-validation)
7. [Déploiement en Production](#déploiement-en-production)
8. [Dépannage](#dépannage)
9. [Sécurité](#sécurité)

---

## 🎯 Vue d'ensemble

ArabiFit intègre deux solutions de paiement complémentaires :

- **Stripe** : Pour les paiements par carte bancaire (international)
- **CinetPay** : Pour les paiements Mobile Money (Afrique de l'Ouest)

### Architecture du Système

```
Client → Django → Stripe/CinetPay → Webhook → Confirmation Commande
```

---

## ⚙️ Prérequis

### 1. Comptes Requis

- ✅ Compte Stripe (https://stripe.com)
- ✅ Compte CinetPay (https://cinetpay.com)
- ✅ Serveur avec HTTPS (obligatoire pour les webhooks)

### 2. Dépendances Python

```bash
pip install stripe==7.8.0
pip install requests==2.31.0
pip install python-decouple==3.8
```

### 3. Variables d'Environnement

Créez un fichier `.env` à la racine du projet :

```env
# Django
SECRET_KEY=your-super-secret-key-here
DEBUG=False

# Stripe
STRIPE_PUBLISHABLE_KEY=pk_live_your_publishable_key
STRIPE_SECRET_KEY=sk_live_your_secret_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret

# CinetPay
CINETPAY_API_KEY=your_cinetpay_api_key
CINETPAY_SITE_ID=your_cinetpay_site_id

# Email (optionnel)
EMAIL_HOST=smtp.gmail.com
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

---

## 💳 Configuration Stripe

### Étape 1 : Création du Compte Stripe

1. **Inscription** : Allez sur https://stripe.com et créez un compte
2. **Vérification** : Complétez la vérification de votre identité
3. **Activation** : Activez votre compte pour les paiements en direct

### Étape 2 : Récupération des Clés API

1. Connectez-vous au **Dashboard Stripe**
2. Allez dans **Développeurs > Clés API**
3. Copiez :
   - **Clé publique** (`pk_live_...` ou `pk_test_...`)
   - **Clé secrète** (`sk_live_...` ou `sk_test_...`)

### Étape 3 : Configuration des Webhooks

1. Dans le Dashboard Stripe, allez dans **Développeurs > Webhooks**
2. Cliquez sur **Ajouter un endpoint**
3. URL du webhook : `https://votre-domaine.com/webhook/stripe/`
4. Événements à écouter :
   ```
   checkout.session.completed
   payment_intent.succeeded
   payment_intent.payment_failed
   ```
5. Copiez le **Secret de signature** (`whsec_...`)

### Étape 4 : Test avec Cartes de Test

```python
# Cartes de test Stripe
CARTES_TEST = {
    'visa_success': '4242424242424242',
    'visa_declined': '4000000000000002',
    'mastercard': '5555555555554444',
    'amex': '378282246310005'
}
```

---

## 📱 Configuration CinetPay

### Étape 1 : Création du Compte CinetPay

1. **Inscription** : Allez sur https://cinetpay.com
2. **Vérification** : Soumettez vos documents d'identité
3. **Validation** : Attendez la validation de votre compte

### Étape 2 : Récupération des Identifiants

1. Connectez-vous au **Dashboard CinetPay**
2. Allez dans **Paramètres > API**
3. Notez :
   - **API Key** : Votre clé d'API
   - **Site ID** : Identifiant de votre site

### Étape 3 : Configuration des Webhooks

1. Dans le Dashboard CinetPay, allez dans **Paramètres > Notifications**
2. URL de notification : `https://votre-domaine.com/webhook/cinetpay/`
3. Activez les notifications pour :
   - Paiements réussis
   - Paiements échoués

### Étape 4 : Test avec Numéros de Test

```python
# Numéros de test CinetPay (Mali)
NUMEROS_TEST = {
    'orange_success': '70000000',  # Orange Money
    'moov_success': '60000000',    # Moov Money
    'orange_failed': '70000001',   # Échec simulé
}
```

---

## 🔧 Configuration Django

### 1. Settings.py

```python
# arabifit/settings.py

from decouple import config

# Stripe Configuration
STRIPE_PUBLISHABLE_KEY = config('STRIPE_PUBLISHABLE_KEY')
STRIPE_SECRET_KEY = config('STRIPE_SECRET_KEY')
STRIPE_WEBHOOK_SECRET = config('STRIPE_WEBHOOK_SECRET')

# CinetPay Configuration
CINETPAY_API_KEY = config('CINETPAY_API_KEY')
CINETPAY_SITE_ID = config('CINETPAY_SITE_ID')

# Taux de conversion (mis à jour régulièrement)
TAUX_XOF_EUR = Decimal('0.00152449')  # 1 XOF = 0.00152449 EUR

# URLs de base
BASE_URL = config('BASE_URL', default='https://votre-domaine.com')

# Security pour la production
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
```

### 2. URLs Configuration

```python
# boutique/urls.py

urlpatterns = [
    # ... autres URLs ...
    
    # Paiements
    path('paiement/<str:numero>/', views.paiement, name='paiement'),
    path('paiement-stripe/<str:numero>/', views.paiement_stripe, name='paiement_stripe'),
    path('paiement-cinetpay/<str:numero>/', views.paiement_cinetpay, name='paiement_cinetpay'),
    
    # Webhooks (IMPORTANT : pas de décorateur login_required)
    path('webhook/stripe/', views.webhook_stripe, name='webhook_stripe'),
    path('webhook/cinetpay/', views.webhook_cinetpay, name='webhook_cinetpay'),
    
    # Pages de résultat
    path('paiement-succes/<str:numero>/', views.paiement_succes, name='paiement_succes'),
    path('paiement-echec/<str:numero>/', views.paiement_echec, name='paiement_echec'),
]
```

### 3. Modèles de Base de Données

```python
# boutique/models.py

class Commande(models.Model):
    METHODE_PAIEMENT_CHOICES = [
        ('stripe', 'Stripe (Carte bancaire)'),
        ('cinetpay', 'CinetPay (Mobile Money)'),
    ]
    
    STATUT_CHOICES = [
        ('en_attente', 'En attente de paiement'),
        ('confirmee', 'Confirmée et payée'),
        ('expediee', 'Expédiée'),
        ('livree', 'Livrée'),
        ('annulee', 'Annulée'),
    ]
    
    # ... autres champs ...
    methode_paiement = models.CharField(max_length=20, choices=METHODE_PAIEMENT_CHOICES)
    paiement_id = models.CharField(max_length=200, blank=True)  # ID de transaction
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='en_attente')
```

---

## 🧪 Tests et Validation

### 1. Tests Stripe

```python
# Test de paiement Stripe
def test_stripe_payment():
    # Utiliser la carte de test : 4242424242424242
    # Expiration : 12/25
    # CVC : 123
    
    # Vérifier :
    # 1. Redirection vers Stripe Checkout
    # 2. Paiement réussi
    # 3. Webhook reçu
    # 4. Commande confirmée
    # 5. Stock décrémenté
```

### 2. Tests CinetPay

```python
# Test de paiement CinetPay
def test_cinetpay_payment():
    # Utiliser un numéro de test : 70000000
    
    # Vérifier :
    # 1. Redirection vers CinetPay
    # 2. Simulation de paiement Mobile Money
    # 3. Webhook reçu
    # 4. Commande confirmée
```

### 3. Script de Test Complet

```bash
# test_payments.py
python manage.py test boutique.tests.PaymentTests
```

---

## 🚀 Déploiement en Production

### 1. Checklist Pré-Déploiement

- [ ] **HTTPS activé** (obligatoire pour les webhooks)
- [ ] **Clés de production** configurées
- [ ] **Webhooks testés** en environnement de staging
- [ ] **Logs configurés** pour le monitoring
- [ ] **Sauvegardes** de la base de données

### 2. Configuration Serveur

```nginx
# Configuration Nginx pour les webhooks
location /webhook/ {
    proxy_pass http://django;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    
    # Timeout plus long pour les webhooks
    proxy_read_timeout 30s;
    proxy_connect_timeout 30s;
}
```

### 3. Monitoring et Logs

```python
# settings.py - Configuration des logs
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': '/var/log/arabifit/payments.log',
        },
    },
    'loggers': {
        'boutique.payments': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

### 4. Variables d'Environnement Production

```bash
# .env.production
DEBUG=False
SECRET_KEY=your-super-secure-production-key

# Stripe Production
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...

# CinetPay Production
CINETPAY_API_KEY=your_production_api_key
CINETPAY_SITE_ID=your_production_site_id

# Base URL
BASE_URL=https://arabifit.com
```

---

## 🔍 Dépannage

### Problèmes Courants Stripe

#### 1. Webhook non reçu
```bash
# Vérifier les logs Stripe
curl -H "Authorization: Bearer sk_live_..." \
     https://api.stripe.com/v1/events
```

**Solutions :**
- Vérifier que l'URL du webhook est accessible en HTTPS
- Contrôler la signature du webhook
- Vérifier les logs Django

#### 2. Paiement refusé
```python
# Codes d'erreur Stripe courants
STRIPE_ERRORS = {
    'card_declined': 'Carte refusée par la banque',
    'insufficient_funds': 'Fonds insuffisants',
    'expired_card': 'Carte expirée',
    'incorrect_cvc': 'Code CVC incorrect'
}
```

### Problèmes Courants CinetPay

#### 1. API non accessible
```python
# Test de connectivité CinetPay
import requests

response = requests.get('https://api-checkout.cinetpay.com/v2/payment/check')
print(f"Status: {response.status_code}")
```

#### 2. Paiement Mobile Money échoué
**Causes fréquentes :**
- Solde insuffisant
- Numéro de téléphone incorrect
- Service Mobile Money indisponible

### Logs de Débogage

```python
# views.py - Ajout de logs détaillés
import logging

logger = logging.getLogger('boutique.payments')

def paiement_stripe(request, numero):
    logger.info(f"Début paiement Stripe pour commande {numero}")
    try:
        # ... code de paiement ...
        logger.info(f"Paiement Stripe réussi pour {numero}")
    except Exception as e:
        logger.error(f"Erreur paiement Stripe {numero}: {str(e)}")
```

---

## 🔒 Sécurité

### 1. Protection des Clés API

```python
# ❌ JAMAIS faire cela
STRIPE_SECRET_KEY = "sk_live_abc123..."

# ✅ Toujours utiliser les variables d'environnement
STRIPE_SECRET_KEY = config('STRIPE_SECRET_KEY')
```

### 2. Validation des Webhooks

```python
# Validation signature Stripe
def validate_stripe_webhook(payload, signature, secret):
    try:
        stripe.Webhook.construct_event(payload, signature, secret)
        return True
    except ValueError:
        return False
```

### 3. Protection CSRF

```python
# Exemption CSRF pour les webhooks uniquement
@csrf_exempt
def webhook_stripe(request):
    # Validation de la signature remplace la protection CSRF
    pass
```

### 4. Limitation de Taux

```python
# Limitation des tentatives de paiement
from django.core.cache import cache

def rate_limit_payment(user_id):
    key = f"payment_attempts_{user_id}"
    attempts = cache.get(key, 0)
    
    if attempts >= 5:  # Max 5 tentatives par heure
        return False
    
    cache.set(key, attempts + 1, 3600)  # 1 heure
    return True
```

---

## 📊 Monitoring et Analytics

### 1. Métriques Importantes

```python
# Métriques à surveiller
METRICS = {
    'taux_conversion': 'Commandes payées / Commandes créées',
    'temps_paiement': 'Temps moyen pour finaliser un paiement',
    'echecs_paiement': 'Nombre de paiements échoués par méthode',
    'revenus_journaliers': 'Revenus par jour et par méthode'
}
```

### 2. Dashboard de Monitoring

```python
# views.py - Vue pour le monitoring
@staff_member_required
def payment_dashboard(request):
    today = timezone.now().date()
    
    stats = {
        'commandes_aujourd_hui': Commande.objects.filter(
            date_creation__date=today
        ).count(),
        'revenus_stripe': Commande.objects.filter(
            date_creation__date=today,
            methode_paiement='stripe',
            statut='confirmee'
        ).aggregate(total=Sum('total'))['total'] or 0,
        'revenus_cinetpay': Commande.objects.filter(
            date_creation__date=today,
            methode_paiement='cinetpay',
            statut='confirmee'
        ).aggregate(total=Sum('total'))['total'] or 0,
    }
    
    return render(request, 'admin/payment_dashboard.html', {'stats': stats})
```

---

## 🎯 Optimisations Avancées

### 1. Cache des Taux de Change

```python
# utils.py - Cache des taux de change
from django.core.cache import cache
import requests

def get_exchange_rate():
    rate = cache.get('xof_eur_rate')
    if not rate:
        # API pour récupérer le taux actuel
        response = requests.get('https://api.exchangerate-api.com/v4/latest/XOF')
        rate = response.json()['rates']['EUR']
        cache.set('xof_eur_rate', rate, 3600)  # Cache 1 heure
    return rate
```

### 2. Retry Logic pour les Webhooks

```python
# Retry automatique pour les webhooks échoués
from celery import shared_task

@shared_task(bind=True, max_retries=3)
def process_webhook(self, webhook_data):
    try:
        # Traitement du webhook
        process_payment_webhook(webhook_data)
    except Exception as exc:
        # Retry avec délai exponentiel
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
```

### 3. Notifications en Temps Réel

```python
# WebSocket pour notifications temps réel
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

def notify_payment_success(user_id, commande_numero):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"user_{user_id}",
        {
            "type": "payment_notification",
            "message": f"Paiement confirmé pour la commande {commande_numero}"
        }
    )
```

---

## 📞 Support et Ressources

### Documentation Officielle

- **Stripe** : https://stripe.com/docs
- **CinetPay** : https://docs.cinetpay.com

### Contacts Support

- **Stripe Support** : https://support.stripe.com
- **CinetPay Support** : support@cinetpay.com

### Communautés

- **Stripe Discord** : https://discord.gg/stripe
- **Django Payments** : https://github.com/mirumee/django-payments

---

## ✅ Checklist de Déploiement Final

### Avant le Lancement

- [ ] Tests complets en environnement de staging
- [ ] Validation des webhooks Stripe et CinetPay
- [ ] Configuration HTTPS et certificats SSL
- [ ] Sauvegarde de la base de données
- [ ] Monitoring et alertes configurés
- [ ] Documentation équipe mise à jour

### Après le Lancement

- [ ] Surveillance des logs pendant 24h
- [ ] Test de quelques transactions réelles
- [ ] Vérification des notifications par email
- [ ] Monitoring des performances
- [ ] Formation équipe support client

---

**🎉 Félicitations ! Votre système de paiement ArabiFit est maintenant opérationnel !**

Pour toute question ou problème, consultez la section dépannage ou contactez l'équipe technique.