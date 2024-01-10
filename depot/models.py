from datetime import datetime

from django.contrib.auth.models import User
from django.db import models
from django.db.models import Sum


# Create your models here.
class ModelB(models.Model):
    auteur = models.ForeignKey(User, on_delete=models.PROTECT)
    code = models.CharField(max_length=10, blank=False, null=False, unique=True)
    libelle = models.CharField(max_length=30, blank=False, null=False)

    active = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.libelle

    class Meta:
        verbose_name_plural = "GESTION DES MODELS"


class ModeR(models.Model):
    auteur = models.ForeignKey(User, on_delete=models.PROTECT)
    code = models.CharField(max_length=10, blank=False, null=False, unique=True)
    libelle = models.CharField(max_length=30, blank=False, null=False)

    active = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.libelle

    class Meta:
        verbose_name_plural = "GESTION DES MODES DE REGLEMENT"


class Producteur(models.Model):
    auteur = models.ForeignKey(User, on_delete=models.PROTECT)
    code = models.CharField(max_length=10, blank=False, null=False, unique=True)
    libelle = models.CharField(max_length=30, blank=False, null=False)

    active = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.libelle

    class Meta:
        verbose_name_plural = "GESTION DES PRODUCTEURS"


class Produit(models.Model):
    auteur = models.ForeignKey(User, on_delete=models.PROTECT)
    modelb = models.ForeignKey(ModelB, on_delete=models.PROTECT)
    producteur = models.ForeignKey(Producteur, on_delete=models.PROTECT)
    code = models.CharField(max_length=40, blank=False, null=False, unique=True)
    libelle = models.CharField(max_length=80, blank=False, null=False)
    pv = models.IntegerField()
    seuil = models.FloatField()

    active = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.libelle}-{self.modelb}"

    def somme_quantites(self):
        # Annotation pour la somme des quantités entrantes
        somme_quantite_entree = \
        Mouvement.objects.filter(produit=self, type_op='ADD', active=True).aggregate(somme_quantite_entree=Sum('qte'))[
            'somme_quantite_entree'] or 0

        # Annotation pour la somme des quantités sortantes
        somme_quantite_sortie = \
        Mouvement.objects.filter(produit=self, type_op='OUT', active=True).aggregate(somme_quantite_sortie=Sum('qte'))[
            'somme_quantite_sortie'] or 0

        # Calcul du reste (entrant - sortant)
        reste = somme_quantite_entree - somme_quantite_sortie

        return {
            'somme_quantite_entree': somme_quantite_entree,
            'somme_quantite_sortie': somme_quantite_sortie,
            'reste': reste,
        }

    class Meta:
        verbose_name_plural = "GESTION DES PRODUITS"


class Client(models.Model):
    auteur = models.ForeignKey(User, on_delete=models.PROTECT)
    code = models.CharField(max_length=20, blank=False, null=False, unique=True)
    rs = models.CharField(max_length=80, blank=False, null=False)
    ville = models.CharField(max_length=30, blank=False, null=False)
    tel = models.CharField(max_length=30, blank=False, null=False)
    mail = models.EmailField(max_length=40, blank=False, null=False)

    active = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.rs}"

    class Meta:
        verbose_name_plural = "GESTION DES CLIENTS"


class Facture(models.Model):
    auteur = models.ForeignKey(User, on_delete=models.PROTECT)
    code_facture = models.CharField(max_length=80, unique=True)
    date_facture = models.DateField()
    client = models.ForeignKey(Client, on_delete=models.PROTECT)
    type_client = models.CharField(max_length=30, blank=True, null=True)
    remise = models.IntegerField(default=0)
    tva = models.IntegerField(default=0)
    mt_ttc = models.IntegerField(default=0)
    situation = models.CharField(max_length=30, default="NON", blank=True, null=True)

    active = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.code_facture}"

    class Meta:
        verbose_name_plural = "GESTION DES FACTURES"

    def calcul_montant_total(self):
        montant_ht = sum(
            mouvement.sous_total() for mouvement in self.mouvement_set.filter(active=True)
        )
        montant_ttc = montant_ht * (1 + self.tva) + (-1 * self.remise)
        self.mt_ttc = montant_ttc
        self.save()
        return montant_ttc


class Mouvement(models.Model):
    auteur = models.ForeignKey(User, on_delete=models.PROTECT)
    facture = models.ForeignKey(Facture, on_delete=models.PROTECT, null=True)
    produit = models.ForeignKey(Produit, on_delete=models.PROTECT)
    qte = models.FloatField()
    type_op = models.CharField(max_length=5, blank=False, null=False)

    active = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.facture}-{self.produit}"

    def sous_total(self):
        return self.produit.pv * self.qte


class Payement(models.Model):
    auteur = models.ForeignKey(User, on_delete=models.PROTECT)
    code_payement = models.CharField(max_length=80, unique=True)
    date_payement = models.DateField()
    facture = models.ForeignKey(Facture, on_delete=models.PROTECT)
    mt_encaisse = models.IntegerField(default=0)
    mt_restant = models.IntegerField(default=0)
    reliquat = models.IntegerField(default=0)

    active = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.code_payement}"

    def total_encaisse_for_facture(self):
        related_payments = Payement.objects.filter(facture=self.facture)
        return related_payments.aggregate(Sum('mt_encaisse'))['mt_encaisse__sum'] or 0

    def total_encaisse_for_facture_a_ce_jour(self):
        # Obtenez la date actuelle
        aujourd_hui = datetime.date.today()

        # Filtrer les paiements en fonction de la date de paiement
        paiements_a_ce_jour = self.facture.payement_set.filter(date_payement__date__lte=aujourd_hui, active=True)

        # Calculer le montant total encaissé à ce jour
        montant_total_encaisse_a_ce_jour = paiements_a_ce_jour.aggregate(Sum('mt_encaisse'))['mt_encaisse__sum'] or 0

        return montant_total_encaisse_a_ce_jour

    class Meta:
        verbose_name_plural = "GESTION DES PAYEMENTS"

