from django.test import TestCase
from django.contrib.auth.models import User
from decimal import Decimal
from .models import Categorie, Produit, Panier, ItemPanier, Commande


class ModelesTest(TestCase):
    def setUp(self):
        """Configuration initiale pour les tests"""
        self.utilisateur = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        self.categorie = Categorie.objects.create(
            nom='Thé Minceur',
            description='Thés naturels pour la perte de poids'
        )

        self.produit = Produit.objects.create(
            nom='Thé Arabigum Classic',
            description='Thé minceur naturel à base d\'Arabigum',
            prix=Decimal('29.99'),
            stock=50,
            categorie=self.categorie,
            actif=True
        )

    def test_creation_produit(self):
        """Test de création d'un produit"""
        self.assertEqual(self.produit.nom, 'Thé Arabigum Classic')
        self.assertEqual(self.produit.prix, Decimal('29.99'))
        self.assertTrue(self.produit.est_en_stock)
        self.assertEqual(str(self.produit), 'Thé Arabigum Classic')

    def test_creation_panier(self):
        """Test de création et manipulation du panier"""
        panier = Panier.objects.create(utilisateur=self.utilisateur)

        # Ajouter un item au panier
        item = ItemPanier.objects.create(
            panier=panier,
            produit=self.produit,
            quantite=2
        )

        self.assertEqual(panier.nombre_items, 2)
        self.assertEqual(panier.total, Decimal('59.98'))
        self.assertEqual(item.total, Decimal('59.98'))

    def test_creation_commande(self):
        """Test de création d'une commande"""
        commande = Commande.objects.create(
            utilisateur=self.utilisateur,
            nom_complet='Test User',
            email='test@example.com',
            telephone='0123456789',
            adresse='123 Rue Test',
            ville='Paris',
            code_postal='75001',
            total=Decimal('29.99'),
            methode_paiement='stripe'
        )

        self.assertTrue(commande.numero.startswith('CMD-'))
        self.assertEqual(commande.statut, 'en_attente')
        self.assertEqual(str(commande), f'Commande {commande.numero}')


class VuesTest(TestCase):
    def setUp(self):
        """Configuration initiale pour les tests des vues"""
        self.utilisateur = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        self.categorie = Categorie.objects.create(
            nom='Thé Minceur',
            description='Thés naturels pour la perte de poids'
        )

        self.produit = Produit.objects.create(
            nom='Thé Arabigum Classic',
            description='Thé minceur naturel à base d\'Arabigum',
            prix=Decimal('29.99'),
            stock=50,
            categorie=self.categorie,
            actif=True
        )

    def test_page_accueil(self):
        """Test de la page d'accueil"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ArabiFit')

    def test_liste_produits(self):
        """Test de la page de liste des produits"""
        response = self.client.get('/produits/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Thé Arabigum Classic')

    def test_detail_produit(self):
        """Test de la page de détail d'un produit"""
        response = self.client.get(f'/produit/{self.produit.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.produit.nom)
        self.assertContains(response, str(self.produit.prix))

    def test_connexion_utilisateur(self):
        """Test de connexion utilisateur"""
        response = self.client.post('/connexion/', {
            'username': 'testuser',
            'password': 'testpass123'
        })
        self.assertRedirects(response, '/')

    def test_panier_necessite_connexion(self):
        """Test que le panier nécessite une connexion"""
        response = self.client.get('/panier/')
        self.assertRedirects(response, '/connexion/?next=/panier/')

    def test_ajout_au_panier_avec_connexion(self):
        """Test d'ajout au panier avec utilisateur connecté"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(f'/ajouter-au-panier/{self.produit.id}/')
        self.assertRedirects(response, f'/produit/{self.produit.id}/')

        # Vérifier que l'item a été ajouté au panier
        panier = Panier.objects.get(utilisateur=self.utilisateur)
        self.assertEqual(panier.nombre_items, 1)


class FormulaireTest(TestCase):
    def test_formulaire_inscription_valide(self):
        """Test du formulaire d'inscription avec données valides"""
        from .forms import InscriptionForm

        form_data = {
            'username': 'nouveautilisateur',
            'prenom': 'Nouveau',
            'nom': 'Utilisateur',
            'email': 'nouveau@example.com',
            'password1': 'motdepasse123!',
            'password2': 'motdepasse123!'
        }

        form = InscriptionForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_formulaire_recherche(self):
        """Test du formulaire de recherche"""
        from .forms import RechercheForm

        form_data = {
            'q': 'thé',
            'categorie': ''
        }

        form = RechercheForm(data=form_data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['q'], 'thé')