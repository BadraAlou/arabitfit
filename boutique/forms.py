from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Commande, AvisProduit


class InscriptionForm(UserCreationForm):
    email = forms.EmailField(required=True)
    prenom = forms.CharField(max_length=30, required=True)
    nom = forms.CharField(max_length=30, required=True)

    class Meta:
        model = User
        fields = ['username', 'prenom', 'nom', 'email', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['prenom']
        user.last_name = self.cleaned_data['nom']
        if commit:
            user.save()
        return user


class CommandeForm(forms.ModelForm):
    class Meta:
        model = Commande
        fields = [
            'nom_complet', 'email', 'telephone',
            'adresse', 'ville', 'code_postal', 'methode_paiement'
        ]
        widgets = {
            'nom_complet': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Votre nom complet'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'votre@email.com'
            }),
            'telephone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+223 XX XX XX XX'
            }),
            'adresse': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Adresse complète de livraison'
            }),
            'ville': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Bamako, Sikasso, Mopti...'
            }),
            'code_postal': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Code postal (optionnel)'
            }),
            'methode_paiement': forms.RadioSelect(attrs={
                'class': 'form-check-input'
            }),
        }


class AvisProduitForm(forms.ModelForm):
    class Meta:
        model = AvisProduit
        fields = ['note', 'commentaire']
        widgets = {
            'note': forms.Select(attrs={
                'class': 'form-select',
            }),
            'commentaire': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Partagez votre expérience avec ce produit...'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['note'].label = "Note"
        self.fields['commentaire'].label = "Votre avis"


class RechercheForm(forms.Form):
    q = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Rechercher un produit...'
        })
    )
    categorie = forms.ChoiceField(
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import Categorie
        categories = [('', 'Toutes les catégories')]
        categories.extend([(cat.id, cat.nom) for cat in Categorie.objects.all()])
        self.fields['categorie'].choices = categories