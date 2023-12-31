from datetime import datetime

from django import forms
from django.contrib.auth.models import User
from django.forms import ModelChoiceField

from .models import ModelB, Producteur, Produit, Client, ModeR, Mouvement, Facture, Payement


class CustomAuthenticationForm(forms.Form):
    """Authentication form which uses boostrap CSS."""
    username = forms.CharField(max_length=100,
                               widget=forms.TextInput(attrs={
                                   'class': 'form-control',
                                   'placeholder': 'Nom'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
                                   'class': 'form-control',
                                   'placeholder':'Password'}))


class ModelBForm(forms.ModelForm):
    code = forms.CharField(required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'autofocus': 'true', 'autocomplete': 'off'}))
    libelle = forms.CharField(required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))

    class Meta:
        model = ModelB
        fields = ['code', 'libelle']


class ModeRForm(forms.ModelForm):
    code = forms.CharField(required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'autofocus': 'true', 'autocomplete': 'off'}))
    libelle = forms.CharField(required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))

    class Meta:
        model = ModeR
        fields = ['code', 'libelle']


class ProducteurForm(forms.ModelForm):
    code = forms.CharField(required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'autofocus': 'true', 'autocomplete': 'off'}))
    libelle = forms.CharField(required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))

    class Meta:
        model = Producteur
        fields = ['code', 'libelle']


class ProduitForm(forms.ModelForm):
    code = forms.CharField(required=True, max_length=80, widget=forms.TextInput(attrs={'class': 'form-control', 'autofocus': 'true', 'autocomplete': 'off'}))
    libelle = forms.CharField(required=True, max_length=80, widget=forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'off'}))
    modelb = forms.ModelChoiceField(queryset=ModelB.objects.filter(active=True).order_by('-id'),
                                       required=True,
                                       widget=forms.Select(attrs={'class': 'form-control'}))
    producteur = forms.ModelChoiceField(queryset=Producteur.objects.filter(active=True).order_by('-id'),
                                       required=True,
                                       widget=forms.Select(attrs={'class': 'form-control'}))
    pv = forms.IntegerField(required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    seuil = forms.FloatField(required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))

    class Meta:
        model = Produit
        fields = ['code', 'libelle', 'modelb', 'producteur', 'pv', 'seuil']


class ClientForm(forms.ModelForm):
    code = forms.CharField(required=True, max_length=20, widget=forms.TextInput(attrs={'class': 'form-control', 'autofocus': 'true', 'autocomplete': 'off'}))
    rs = forms.CharField(required=True, max_length=80, widget=forms.TextInput(attrs={'class': 'form-control'}))
    ville = forms.CharField(required=True, max_length=30, widget=forms.TextInput(attrs={'class': 'form-control'}))
    tel = forms.CharField(required=True, max_length=30, widget=forms.TextInput(attrs={'class': 'form-control'}))
    mail = forms.EmailField(required=True, max_length=40, widget=forms.TextInput(attrs={'class': 'form-control'}))

    class Meta:
        model = Client
        fields = ['code', 'rs', 'ville', 'tel', 'mail']


class EntreeForm(forms.ModelForm):
    produit = forms.ModelChoiceField(queryset=Produit.objects.filter(active=True).order_by('-id'),
                                    required=True, widget=forms.Select(attrs={'class': 'form-control'}))
    qte = forms.FloatField(required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'off'}))

    class Meta:
        model = Mouvement
        fields = ['produit', 'qte']


class MenuModelChoiceField(ModelChoiceField):
    def label_from_instance(self, obj):
        return "%s %s %s" % (obj.libelle,obj.modelb.libelle,obj.producteur.libelle)


class MenuModelChoiceField1(ModelChoiceField):
    def label_from_instance(self, obj):
        return "%s %s %s" % (obj.code_facture, obj.client, obj.date_facture)


class FactureForm(forms.ModelForm):
    NULL = ''
    DIPI = 'DIPI'
    DIVERS = 'DIVERS'
    TOUS = 'TOUS'
    CHOIX = [
        (NULL, ''),
        (DIPI, 'DIPI'),
        (DIVERS, 'DIVERS'),
        (TOUS, 'TOUS'),
    ]
    code_facture = forms.CharField(required=True, max_length=50, widget=forms.TextInput(attrs={'class': 'form-control'}))
    date_facture = forms.DateField(widget=forms.DateInput(attrs={'class': 'form-control'}))
    client = forms.ModelChoiceField(queryset=Client.objects.filter(active=True).order_by('-id'),
                                    required=True, widget=forms.Select(attrs={'class': 'form-control'}))
    type_client = forms.ChoiceField(choices=CHOIX, required=True, widget=forms.Select(attrs={'class': 'form-control'}))
    remise = forms.IntegerField(required=True, initial=0, widget=forms.TextInput(attrs={'class': 'form-control'}))
    tva = forms.IntegerField(required=True, initial=0, widget=forms.TextInput(attrs={'class': 'form-control'}))

    class Meta:
        model = Facture
        fields = ['code_facture', 'date_facture', 'client', 'type_client', 'remise', 'tva']


class SortieForm(forms.ModelForm):
    produit = MenuModelChoiceField(queryset=Produit.objects.filter(active=True).order_by('-id'),
                                    required=False, widget=forms.Select(attrs={'class': 'form-control', 'id': 'pdtAdder', 'name': 'pdtAdder'}))
    qte = forms.FloatField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'off', 'id': 'qteAdder', 'name': 'qte'}))
    facture = forms.ModelChoiceField(queryset=Facture.objects.filter(active=True).order_by('-id'),
                                    required=False, widget=forms.Select(attrs={'class': 'form-control'}))

    class Meta:
        model = Mouvement
        fields = ['produit', 'qte', 'facture']


class RealisationPayement(forms.ModelForm):
    facture = forms.ModelChoiceField(queryset=Facture.objects.filter(active=True).order_by('-id'),
                                    required=False, widget=forms.Select(attrs={'class': 'form-control'}))

    class Meta:
        model = Payement
        fields = ['facture']


class PayementForm(forms.ModelForm):
    code_payement = forms.CharField(required=True, max_length=50,
                                   widget=forms.TextInput(attrs={'class': 'form-control','autofocus': 'true', 'autocomplete': 'off'}))
    facture = MenuModelChoiceField1(queryset=Facture.objects.filter(active=True).order_by('-id'),
                                    required=False, widget=forms.Select(attrs={'class': 'form-control'}))
    # mt_facture = forms.IntegerField(required=True, initial=0, widget=forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'off', 'readonly':'on'}))
    # mt_reglee = forms.IntegerField(required=True, initial=0, widget=forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'off', 'readonly':'on'}))
    mt_encaisse = forms.IntegerField(required=True, initial=0, widget=forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'off'}))
    reliquat = forms.IntegerField(required=True, initial=0, widget=forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'off'}))

    class Meta:
        model = Payement
        fields = ['date_payement', 'code_payement', 'facture', 'mt_encaisse', 'reliquat']
