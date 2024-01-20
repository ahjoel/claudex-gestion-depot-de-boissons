from django.contrib import admin
from django.contrib.admin import AdminSite
from django.http import HttpResponseRedirect

from depot import views
from depot.models import ModelB, Producteur, ModeR, Produit, Client, Facture, Mouvement, Payement, Historique

# Register your models here.
admin.site.site_header = "CLAUDEX-ADMIN"
admin.site.site_title = "ADMIN"
admin.site.index_title = "CLAUDEX"


@admin.register(ModelB)
class ModelBAdmin(admin.ModelAdmin):
    list_display = ('auteur', 'code', 'libelle', 'active', 'date_creation', 'date_modification')


@admin.register(ModeR)
class ModeRAdmin(admin.ModelAdmin):
    list_display = ('auteur', 'code', 'libelle', 'active', 'date_creation', 'date_modification')


@admin.register(Producteur)
class ProducteurAdmin(admin.ModelAdmin):
    list_display = ('auteur', 'code', 'libelle', 'active', 'date_creation', 'date_modification')


@admin.register(Produit)
class ProduitAdmin(admin.ModelAdmin):
    list_display = ('auteur', 'code', 'libelle', 'active', 'modelb', 'producteur', 'pv', 'seuil', 'date_creation', 'date_modification')


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('auteur', 'code', 'rs', 'ville', 'tel', 'mail', 'date_creation', 'date_modification')

    def rs(self, obj):
        return f"Raison Sociale"


@admin.register(Facture)
class FactureAdmin(admin.ModelAdmin):
    list_display = ('auteur', 'code_facture', 'date_facture', 'client', 'type_client', 'remise', 'tva', 'mt_ttc', 'date_creation', 'date_modification')

    def code_facture(self, obj):
        return f"Code Fact"

    def date_facture(self, obj):
        return f"Date Fact"

    def client(self, obj):
        return f"Client"

    def type_client(self, obj):
        return f"Type Client"


@admin.register(Payement)
class PayementAdmin(admin.ModelAdmin):
    list_display = ('auteur', 'code_payement', 'date_payement', 'facture', 'mt_encaisse', 'mt_restant', 'reliquat', 'active', 'date_creation', 'date_modification')


@admin.register(Historique)
class HistoriqueAdmin(admin.ModelAdmin):
    list_display = ('auteur', 'action', 'table', 'contenu', 'date_creation', 'date_modification')


