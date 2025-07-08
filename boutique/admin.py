from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from .models import (
    Categorie, Produit, Panier, ItemPanier, Commande, ItemCommande, AvisProduit,
    Employe, Presence, Conge, Evaluation
)


# Personnalisation de l'admin User pour inclure les employés
class EmployeInline(admin.StackedInline):
    model = Employe
    can_delete = False
    verbose_name_plural = 'Informations Employé'
    fields = ['numero_employe', 'poste', 'salaire', 'date_embauche', 'statut', 'telephone', 'adresse', 'photo']


class CustomUserAdmin(UserAdmin):
    inlines = (EmployeInline,)


# Réenregistrer UserAdmin
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


@admin.register(Categorie)
class CategorieAdmin(admin.ModelAdmin):
    list_display = ['nom', 'date_creation']
    search_fields = ['nom']
    prepopulated_fields = {'nom': ('nom',)}


class ItemCommandeInline(admin.TabularInline):
    model = ItemCommande
    readonly_fields = ['nom_produit', 'prix_unitaire', 'quantite', 'total']
    extra = 0


@admin.register(Produit)
class ProduitAdmin(admin.ModelAdmin):
    list_display = ['nom', 'categorie', 'prix', 'stock', 'actif', 'note_moyenne', 'nombre_avis', 'date_creation']
    list_filter = ['categorie', 'actif', 'date_creation']
    search_fields = ['nom', 'description']
    list_editable = ['prix', 'stock', 'actif']
    ordering = ['-date_creation']

    def note_moyenne(self, obj):
        return f"{obj.note_moyenne:.1f}/5" if obj.note_moyenne > 0 else "Aucun avis"

    note_moyenne.short_description = "Note moyenne"

    def nombre_avis(self, obj):
        return obj.nombre_avis

    nombre_avis.short_description = "Nombre d'avis"


@admin.register(AvisProduit)
class AvisProduitAdmin(admin.ModelAdmin):
    list_display = ['produit', 'utilisateur', 'note', 'date_creation', 'approuve']
    list_filter = ['note', 'approuve', 'date_creation']
    search_fields = ['produit__nom', 'utilisateur__username', 'commentaire']
    list_editable = ['approuve']
    ordering = ['-date_creation']


@admin.register(Commande)
class CommandeAdmin(admin.ModelAdmin):
    list_display = ['numero', 'utilisateur', 'total', 'statut', 'methode_paiement', 'date_creation']
    list_filter = ['statut', 'methode_paiement', 'date_creation']
    search_fields = ['numero', 'utilisateur__username', 'email']
    readonly_fields = ['numero', 'total', 'date_creation', 'date_modification']
    inlines = [ItemCommandeInline]
    ordering = ['-date_creation']

    fieldsets = (
        ('Informations de base', {
            'fields': ('numero', 'utilisateur', 'total', 'methode_paiement', 'paiement_id')
        }),
        ('Informations client', {
            'fields': ('nom_complet', 'email', 'telephone', 'adresse', 'ville', 'code_postal')
        }),
        ('Statut et suivi', {
            'fields': ('statut', 'numero_suivi', 'date_confirmation', 'date_expedition', 'date_livraison')
        }),
        ('Notes administratives', {
            'fields': ('notes_admin',),
            'classes': ('collapse',)
        }),
        ('Dates', {
            'fields': ('date_creation', 'date_modification'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # Si le statut passe à "confirmée", décrémenter le stock
        if change and obj.statut == 'confirmee':
            for item in obj.items.all():
                produit = item.produit
                if produit.stock >= item.quantite:
                    produit.stock -= item.quantite
                    produit.save()


@admin.register(Panier)
class PanierAdmin(admin.ModelAdmin):
    list_display = ['utilisateur', 'nombre_items', 'total', 'date_creation']
    readonly_fields = ['total', 'nombre_items']


@admin.register(ItemPanier)
class ItemPanierAdmin(admin.ModelAdmin):
    list_display = ['panier', 'produit', 'quantite', 'total', 'date_ajout']
    list_filter = ['date_ajout']


# Administration RH

@admin.register(Employe)
class EmployeAdmin(admin.ModelAdmin):
    list_display = ['user', 'numero_employe', 'poste', 'statut', 'date_embauche']
    list_filter = ['poste', 'statut', 'date_embauche']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'numero_employe']
    readonly_fields = ['numero_employe']

    fieldsets = (
        ('Informations utilisateur', {
            'fields': ('user', 'numero_employe')
        }),
        ('Informations professionnelles', {
            'fields': ('poste', 'salaire', 'date_embauche', 'statut')
        }),
        ('Coordonnées', {
            'fields': ('telephone', 'adresse', 'photo')
        }),
    )


@admin.register(Presence)
class PresenceAdmin(admin.ModelAdmin):
    list_display = ['employe', 'date', 'heure_arrivee', 'heure_depart', 'heures_travaillees']
    list_filter = ['date', 'employe__poste']
    search_fields = ['employe__user__username', 'employe__user__first_name', 'employe__user__last_name']
    date_hierarchy = 'date'

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if obj.heure_depart:
            obj.calculer_heures_travaillees()


@admin.register(Conge)
class CongeAdmin(admin.ModelAdmin):
    list_display = ['employe', 'type_conge', 'date_debut', 'date_fin', 'nombre_jours', 'statut']
    list_filter = ['type_conge', 'statut', 'date_debut']
    search_fields = ['employe__user__username', 'employe__user__first_name', 'employe__user__last_name']
    date_hierarchy = 'date_debut'

    fieldsets = (
        ('Informations de base', {
            'fields': ('employe', 'type_conge', 'date_debut', 'date_fin', 'nombre_jours')
        }),
        ('Demande', {
            'fields': ('motif',)
        }),
        ('Approbation', {
            'fields': ('statut', 'approuve_par', 'date_approbation', 'commentaire_admin')
        }),
    )

    readonly_fields = ['nombre_jours']


@admin.register(Evaluation)
class EvaluationAdmin(admin.ModelAdmin):
    list_display = ['employe', 'evaluateur', 'periode_debut', 'periode_fin', 'note_moyenne', 'date_evaluation']
    list_filter = ['periode_debut', 'note_performance']
    search_fields = ['employe__user__username', 'employe__user__first_name', 'employe__user__last_name']
    date_hierarchy = 'date_evaluation'

    fieldsets = (
        ('Informations de base', {
            'fields': ('employe', 'evaluateur', 'periode_debut', 'periode_fin')
        }),
        ('Notes', {
            'fields': ('note_performance', 'note_ponctualite', 'note_qualite_travail', 'note_relation_equipe')
        }),
        ('Commentaires', {
            'fields': ('commentaires', 'objectifs_suivants')
        }),
    )