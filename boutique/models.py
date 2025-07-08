from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from PIL import Image
import uuid


class Categorie(models.Model):
    nom = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Catégorie'
        verbose_name_plural = 'Catégories'
        ordering = ['nom']

    def __str__(self):
        return self.nom


class Produit(models.Model):
    nom = models.CharField(max_length=200)
    description = models.TextField()
    prix = models.DecimalField(max_digits=12, decimal_places=2)  # Prix en XOF
    image = models.ImageField(upload_to='produits/')
    stock = models.PositiveIntegerField(default=0)
    categorie = models.ForeignKey(Categorie, on_delete=models.CASCADE, related_name='produits')
    actif = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Produit'
        verbose_name_plural = 'Produits'
        ordering = ['-date_creation']

    def __str__(self):
        return self.nom

    def get_absolute_url(self):
        return reverse('boutique:detail_produit', kwargs={'pk': self.pk})

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.image:
            img = Image.open(self.image.path)
            if img.height > 500 or img.width > 500:
                output_size = (500, 500)
                img.thumbnail(output_size)
                img.save(self.image.path)

    @property
    def est_en_stock(self):
        return self.stock > 0

    @property
    def note_moyenne(self):
        avis = self.avis.all()
        if avis:
            return sum(avis_item.note for avis_item in avis) / len(avis)
        return 0

    @property
    def nombre_avis(self):
        return self.avis.count()


class AvisProduit(models.Model):
    NOTES_CHOICES = [
        (1, '1 étoile'),
        (2, '2 étoiles'),
        (3, '3 étoiles'),
        (4, '4 étoiles'),
        (5, '5 étoiles'),
    ]

    produit = models.ForeignKey(Produit, on_delete=models.CASCADE, related_name='avis')
    utilisateur = models.ForeignKey(User, on_delete=models.CASCADE)
    note = models.IntegerField(choices=NOTES_CHOICES)
    commentaire = models.TextField()
    date_creation = models.DateTimeField(auto_now_add=True)
    approuve = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Avis Produit'
        verbose_name_plural = 'Avis Produits'
        unique_together = ['produit', 'utilisateur']  # Un avis par utilisateur par produit
        ordering = ['-date_creation']

    def __str__(self):
        return f"Avis de {self.utilisateur.username} sur {self.produit.nom} - {self.note}/5"


class Panier(models.Model):
    utilisateur = models.OneToOneField(User, on_delete=models.CASCADE)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Panier'
        verbose_name_plural = 'Paniers'

    def __str__(self):
        return f"Panier de {self.utilisateur.username}"

    @property
    def total(self):
        return sum(item.total for item in self.items.all())

    @property
    def nombre_items(self):
        return sum(item.quantite for item in self.items.all())


class ItemPanier(models.Model):
    panier = models.ForeignKey(Panier, on_delete=models.CASCADE, related_name='items')
    produit = models.ForeignKey(Produit, on_delete=models.CASCADE)
    quantite = models.PositiveIntegerField(default=1)
    date_ajout = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Article du panier'
        verbose_name_plural = 'Articles du panier'
        unique_together = ['panier', 'produit']

    def __str__(self):
        return f"{self.quantite} x {self.produit.nom}"

    @property
    def total(self):
        return self.quantite * self.produit.prix


class Commande(models.Model):
    STATUT_CHOICES = [
        ('en_attente', 'En attente de paiement'),
        ('confirmee', 'Confirmée et payée'),
        ('en_preparation', 'En préparation'),
        ('expediee', 'Expédiée'),
        ('en_livraison', 'En cours de livraison'),
        ('livree', 'Livrée'),
        ('annulee', 'Annulée'),
    ]

    METHODE_PAIEMENT_CHOICES = [
        ('stripe', 'Stripe'),
        ('cinetpay', 'CinetPay'),
    ]

    numero = models.CharField(max_length=20, unique=True)
    utilisateur = models.ForeignKey(User, on_delete=models.CASCADE, related_name='commandes')
    nom_complet = models.CharField(max_length=200)
    email = models.EmailField()
    telephone = models.CharField(max_length=20)
    adresse = models.TextField()
    ville = models.CharField(max_length=100)
    code_postal = models.CharField(max_length=10)
    total = models.DecimalField(max_digits=15, decimal_places=2)  # Total en XOF
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='en_attente')
    methode_paiement = models.CharField(max_length=20, choices=METHODE_PAIEMENT_CHOICES)
    paiement_id = models.CharField(max_length=200, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    # Champs pour le suivi
    date_confirmation = models.DateTimeField(null=True, blank=True)
    date_expedition = models.DateTimeField(null=True, blank=True)
    date_livraison = models.DateTimeField(null=True, blank=True)
    numero_suivi = models.CharField(max_length=100, blank=True)
    notes_admin = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Commande'
        verbose_name_plural = 'Commandes'
        ordering = ['-date_creation']

    def __str__(self):
        return f"Commande {self.numero}"

    def save(self, *args, **kwargs):
        if not self.numero:
            self.numero = f"CMD-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('boutique:detail_commande', kwargs={'numero': self.numero})


class ItemCommande(models.Model):
    commande = models.ForeignKey(Commande, on_delete=models.CASCADE, related_name='items')
    produit = models.ForeignKey(Produit, on_delete=models.CASCADE)
    nom_produit = models.CharField(max_length=200)  # Sauvegarde le nom au moment de la commande
    prix_unitaire = models.DecimalField(max_digits=15, decimal_places=2)  # Prix en XOF
    quantite = models.PositiveIntegerField()

    class Meta:
        verbose_name = 'Article de commande'
        verbose_name_plural = 'Articles de commande'

    def __str__(self):
        return f"{self.quantite} x {self.nom_produit}"

    @property
    def total(self):
        return self.quantite * self.prix_unitaire


# Modèles pour la gestion des ressources humaines

class Employe(models.Model):
    STATUT_CHOICES = [
        ('actif', 'Actif'),
        ('inactif', 'Inactif'),
        ('conge', 'En congé'),
        ('suspendu', 'Suspendu'),
    ]

    POSTE_CHOICES = [
        ('manager', 'Manager'),
        ('vendeur', 'Vendeur'),
        ('preparateur', 'Préparateur de commandes'),
        ('livreur', 'Livreur'),
        ('service_client', 'Service client'),
        ('comptable', 'Comptable'),
        ('marketing', 'Marketing'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    numero_employe = models.CharField(max_length=20, unique=True)
    poste = models.CharField(max_length=50, choices=POSTE_CHOICES)
    salaire = models.DecimalField(max_digits=12, decimal_places=2)
    date_embauche = models.DateField()
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='actif')
    telephone = models.CharField(max_length=20)
    adresse = models.TextField()
    photo = models.ImageField(upload_to='employes/', blank=True, null=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Employé'
        verbose_name_plural = 'Employés'
        ordering = ['user__last_name', 'user__first_name']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.get_poste_display()}"

    def save(self, *args, **kwargs):
        if not self.numero_employe:
            self.numero_employe = f"EMP-{uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)


class Presence(models.Model):
    employe = models.ForeignKey(Employe, on_delete=models.CASCADE, related_name='presences')
    date = models.DateField()
    heure_arrivee = models.TimeField()
    heure_depart = models.TimeField(null=True, blank=True)
    heures_travaillees = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Présence'
        verbose_name_plural = 'Présences'
        unique_together = ['employe', 'date']
        ordering = ['-date']

    def __str__(self):
        return f"{self.employe.user.get_full_name()} - {self.date}"

    def calculer_heures_travaillees(self):
        if self.heure_arrivee and self.heure_depart:
            from datetime import datetime, timedelta
            arrivee = datetime.combine(self.date, self.heure_arrivee)
            depart = datetime.combine(self.date, self.heure_depart)
            if depart < arrivee:  # Si le départ est le lendemain
                depart += timedelta(days=1)
            duree = depart - arrivee
            self.heures_travaillees = duree.total_seconds() / 3600
            self.save()


class Conge(models.Model):
    TYPE_CHOICES = [
        ('annuel', 'Congé annuel'),
        ('maladie', 'Congé maladie'),
        ('maternite', 'Congé maternité'),
        ('paternite', 'Congé paternité'),
        ('sans_solde', 'Congé sans solde'),
        ('formation', 'Formation'),
        ('autre', 'Autre'),
    ]

    STATUT_CHOICES = [
        ('en_attente', 'En attente'),
        ('approuve', 'Approuvé'),
        ('refuse', 'Refusé'),
        ('annule', 'Annulé'),
    ]

    employe = models.ForeignKey(Employe, on_delete=models.CASCADE, related_name='conges')
    type_conge = models.CharField(max_length=20, choices=TYPE_CHOICES)
    date_debut = models.DateField()
    date_fin = models.DateField()
    nombre_jours = models.PositiveIntegerField()
    motif = models.TextField()
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='en_attente')
    approuve_par = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='conges_approuves')
    date_approbation = models.DateTimeField(null=True, blank=True)
    commentaire_admin = models.TextField(blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Congé'
        verbose_name_plural = 'Congés'
        ordering = ['-date_creation']

    def __str__(self):
        return f"{self.employe.user.get_full_name()} - {self.get_type_conge_display()} ({self.date_debut} au {self.date_fin})"

    def save(self, *args, **kwargs):
        if self.date_debut and self.date_fin:
            self.nombre_jours = (self.date_fin - self.date_debut).days + 1
        super().save(*args, **kwargs)


class Evaluation(models.Model):
    employe = models.ForeignKey(Employe, on_delete=models.CASCADE, related_name='evaluations')
    evaluateur = models.ForeignKey(User, on_delete=models.CASCADE)
    periode_debut = models.DateField()
    periode_fin = models.DateField()
    note_performance = models.IntegerField(choices=[(i, i) for i in range(1, 6)])  # 1 à 5
    note_ponctualite = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    note_qualite_travail = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    note_relation_equipe = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    commentaires = models.TextField()
    objectifs_suivants = models.TextField()
    date_evaluation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Évaluation'
        verbose_name_plural = 'Évaluations'
        ordering = ['-date_evaluation']

    def __str__(self):
        return f"Évaluation de {self.employe.user.get_full_name()} - {self.periode_debut} à {self.periode_fin}"

    @property
    def note_moyenne(self):
        return (self.note_performance + self.note_ponctualite +
                self.note_qualite_travail + self.note_relation_equipe) / 4