from collections import Counter
from datetime import datetime, date

from django.contrib.auth.models import User
from django.db import models
from django.db.models import Sum
from django.utils import timezone


# Table Model
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


# Table Mode de Reglement
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


# Table Producteur
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


# Table Produit
class Produit(models.Model):
    auteur = models.ForeignKey(User, on_delete=models.PROTECT)
    # clé etrangere pour model de produit
    modelb = models.ForeignKey(ModelB, on_delete=models.PROTECT)
    producteur = models.ForeignKey(Producteur, on_delete=models.PROTECT)
    code = models.CharField(max_length=40, blank=False, null=False, unique=True)
    libelle = models.CharField(max_length=80, blank=False, null=False)
    # prix de vente
    pv = models.IntegerField()
    # seuil pour chaque produit
    seuil = models.FloatField()

    active = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.libelle}-{self.modelb}"

    # Fonction utilisée pour le mouvement des produits en fonction de leurs quantités et le reste final
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


# Table Client
class Client(models.Model):
    auteur = models.ForeignKey(User, on_delete=models.PROTECT)
    code = models.CharField(max_length=20, blank=False, null=False)
    # raison sociale client
    rs = models.CharField(max_length=80, blank=False, null=False)
    type = models.CharField(max_length=30, blank=True, null=True, default="DIPI")
    ville = models.CharField(max_length=30, blank=True, null=True)
    tel = models.CharField(max_length=30, blank=True, null=True)
    mail = models.EmailField(max_length=40, blank=True, null=True)

    active = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.rs}"

    class Meta:
        verbose_name_plural = "GESTION DES CLIENTS"

    # Fonction pour cumuler le montant des factures impayees par client
    def montant_factures_impayees(self):
        # Récupérer toutes les factures associées à ce client
        factures = self.facture_set.filter(active=True)

        # Initialiser la somme totale des factures impayées
        montant_impaye_total = 0

        # Parcourir toutes les factures et ajouter le montant impayé
        for facture in factures:
            montant_impaye_total += facture.montant_restant()

        return montant_impaye_total


# Table Facture
class Facture(models.Model):
    auteur = models.ForeignKey(User, on_delete=models.PROTECT)
    code_facture = models.CharField(max_length=80, unique=True)
    date_facture = models.DateField()
    client = models.ForeignKey(Client, on_delete=models.PROTECT)
    remise = models.IntegerField(default=0)
    tva = models.IntegerField(default=0)
    # montant total facture - mise a jour dynamiquement selon le crud des produits associés
    mt_ttc = models.IntegerField(default=0)
    situation = models.CharField(max_length=30, default="NON", blank=True, null=True)

    active = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.code_facture}"

    class Meta:
        verbose_name_plural = "GESTION DES FACTURES"

    # Fonction pour afficher le montant total de la facture dynamiquement
    # c'est-a-dire qu'il tient compte des ajouts, modification et suppression de produit
    # sur une facture specifique
    # et met à jour dynamiquement le mt_ttc(montant facture lors de la creation)
    def calcul_montant_total(self):
        montant_ht = sum(
            mouvement.sous_total() for mouvement in self.mouvement_set.filter(active=True)
        )
        montant_ttc = montant_ht * (1 + self.tva) + (-1 * self.remise)
        self.mt_ttc = montant_ttc
        self.save()
        return montant_ttc or 0

    # Calcule le montant restant en soustrayant le montant encaissé de la somme totale
    def montant_restant_par_rapport_total_facture(self):
        montant_encaisse = sum(paiement.mt_encaisse for paiement in self.payement_set.filter(active=True))
        montant_restant = self.calcul_montant_total() - montant_encaisse

        self.montant_restant = montant_restant
        self.save()
        return montant_restant

    # Calcule le montant restant en soustrayant le montant encaissé de la somme totale
    # Et applique la penalité sur le montant restant restant
    def montant_restant(self):
        # Calcule le montant restant en soustrayant le montant encaissé de la somme totale
        montant_encaisse = sum(paiement.mt_encaisse for paiement in self.payement_set.filter(active=True))
        montant_restant = self.calcul_montant_total() - montant_encaisse

        # Vérifie si la date de la facture dépasse 7 jours
        jours_diff = (date.today() - self.date_facture).days
        if jours_diff > 7:
            # Applique une pénalité de 0.2% au montant restant
            nb_jours_impaye = jours_diff - 7
            penalite = 0.002 * nb_jours_impaye  # 0.2%
            montant_restant += montant_restant * penalite

        self.montant_restant = montant_restant
        self.save()
        return montant_restant

    # Créer un récapitulatif des types de produits avec le producteur associé et leurs quantités
    def recap_types_produits(self):
        # Récupérer tous les mouvements associés à cette facture
        mouvements = self.mouvement_set.filter(active=True)

        recap_types = Counter()
        for mouvement in mouvements:
            type_produit = (
                mouvement.produit.producteur.libelle,
                mouvement.produit.modelb.libelle,
            )
            recap_types[type_produit] += mouvement.qte

        return dict(recap_types)

    # Statisque Caisse Mensuelle
    def montant_total_encaisse(self):
        return Payement.objects.filter(facture=self, active=True).aggregate(Sum('mt_encaisse'))['mt_encaisse__sum'] or 0

    @classmethod
    def montant_total_factures_par_mois(cls):
        result = cls.objects.filter(active=True).values('date_facture__year', 'date_facture__month').annotate(
            Sum('mt_ttc'))
        return [{'mois': f"{item['date_facture__year']}-{item['date_facture__month']:02}",
                 'montant_total': item['mt_ttc__sum'] or 0} for item in result]

    @classmethod
    def montant_total_encaisse_par_mois(cls):
        result = cls.objects.filter(active=True).values('date_facture__year', 'date_facture__month').annotate(
            Sum('payement__mt_encaisse'))
        return [{'mois': f"{item['date_facture__year']}-{item['date_facture__month']:02}",
                 'montant_encaisse': item['payement__mt_encaisse__sum'] or 0} for item in result]

    @classmethod
    def montant_total_restant_par_mois(cls):
        factures_par_mois = cls.montant_total_factures_par_mois()
        encaisse_par_mois = cls.montant_total_encaisse_par_mois()
        montant_restant_par_mois = []

        for facture in factures_par_mois:
            mois = facture['mois']
            montant_total = facture['montant_total']
            montant_encaisse = next((x['montant_encaisse'] for x in encaisse_par_mois if x['mois'] == mois), 0)
            montant_restant = montant_total - montant_encaisse

            montant_restant_par_mois.append({'mois': mois, 'montant_restant': montant_restant})

        return montant_restant_par_mois
    # Fin

    @property
    def date_echeance(self):
        # Calculer la date d'échéance comme la date_facture + 7 jours
        return self.date_facture + timezone.timedelta(days=7)

    @classmethod
    def factures_pour_periode(cls, debut_periode, fin_periode):
        return cls.objects.filter(date_facture__range=[debut_periode, fin_periode], active=True)


# Table Mouvement
class Mouvement(models.Model):
    auteur = models.ForeignKey(User, on_delete=models.PROTECT)
    facture = models.ForeignKey(Facture, on_delete=models.PROTECT, null=True)
    produit = models.ForeignKey(Produit, on_delete=models.PROTECT)
    qte = models.FloatField()
    # type d'operation : ADD = entree, OUT = sortie
    type_op = models.CharField(max_length=5, blank=False, null=False)

    active = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.facture}-{self.produit}"

    # Fonction pour faire le sous-total (montant hors taxe) facture sans la remise et la tva
    def sous_total(self):
        return self.produit.pv * self.qte


# Table Historique
class Historique(models.Model):
    auteur = models.ForeignKey(User, on_delete=models.PROTECT)
    action = models.CharField(max_length=90, blank=False, null=False)
    table = models.CharField(max_length=80, blank=False, null=False)
    contenu = models.TextField(blank=False, null=False)

    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.auteur}"

    class Meta:
        verbose_name_plural = "GESTION DES HISTORIQUES"


# Table Payement
class Payement(models.Model):
    auteur = models.ForeignKey(User, on_delete=models.PROTECT)
    code_payement = models.CharField(max_length=100, unique=True)
    moder = models.ForeignKey(ModeR, on_delete=models.PROTECT, default=1)
    date_payement = models.DateField()
    facture = models.ForeignKey(Facture, on_delete=models.PROTECT)
    mt_restant = models.IntegerField(default=0)
    mt_recu = models.IntegerField(default=0)
    mt_encaisse = models.IntegerField(default=0)
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

    # important
    @classmethod
    def paiements_pour_periode(cls, debut_periode, fin_periode):
        return cls.objects.filter(date_payement__range=[debut_periode, fin_periode], active=True)

    class Meta:
        verbose_name_plural = "GESTION DES PAYEMENTS"
