import datetime
import math

import num2words as num2words
from django.contrib.auth.models import User
from django.db import models, IntegrityError
from django.db.models.functions import Coalesce
from django.utils.datetime_safe import date
from num2words import num2words
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, ExpressionWrapper, F, DecimalField, Count, Max
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login
from django.views import View

from .decorators import allowed_users
from .forms import CustomAuthenticationForm, ModelBForm, ProducteurForm, ProduitForm, ClientForm, ModeRForm, \
    EntreeForm, SortieForm, FactureForm, PayementForm, SortieOneForm, StatistiqueForm
from .models import ModelB, Producteur, Produit, Client, ModeR, Mouvement, Facture, Payement, Historique
from .utils import render_to_pdf


# Table Historique pour la journalisation de toutes les actions des utilisateurs
# Authentification personnalisée
def custom_login(request):
    form = CustomAuthenticationForm()
    message = ""
    if request.user.is_authenticated:
        return HttpResponseRedirect('/')
    else:
        if request.method == 'POST':
            form = CustomAuthenticationForm(request.POST)
            if form.is_valid():
                username = form.cleaned_data['username']
                password = form.cleaned_data['password']
                user = authenticate(username=username, password=password)
                if user is not None:
                    Historique.objects.create(auteur=User.objects.get(username=username), action="Connexion",
                                              table="Authentification",
                                              contenu=User.objects.get(username=username))
                    login(request, user)
                    return redirect("/")
                else:
                    message = "Nom d'utilisateur ou mot de passe incorrectes"
            else:
                message = "Tous les champs ne sont pas correctement renseignés."

    context = {
        'form': form, 'message': message
    }
    return render(request, 'registration/login.html', context)


# Page d'accueil apres authentification
@login_required(login_url="/connexion")
def home(request):
    # Compte les clients au total
    total_clt_count = Client.objects.filter(active=True).count()
    # Compte les produits au total
    total_pdt_count = Produit.objects.filter(active=True).count()

    aujourd_hui = datetime.date.today()
    nombre_total_factures_aujourd_hui = Facture.objects.filter(date_facture=aujourd_hui).count()

    total_quantite_sortie_aujourd_hui = Mouvement.objects.filter(
        date_creation__date=aujourd_hui,
        type_op="OUT"
    ).aggregate(total_quantite_sortie=models.Sum('qte'))['total_quantite_sortie']

    # Si le total est None (pas de mouvements de type "OUT" aujourd'hui), alors on l'initialise à 0
    total_quantite_sortie_aujourd_hui = total_quantite_sortie_aujourd_hui or 0

    ## Listing Stock Général et Vente
    produits = Produit.objects.all()

    ## Liste pour stocker les résultats finaux
    resultats_produits = []

    for produit in produits:
        # Annotation pour la somme des quantités entrantes
        somme_quantite_entree = \
        Mouvement.objects.filter(produit=produit, type_op='ADD', active=True).aggregate(somme_quantite_entree=Sum('qte'))[
            'somme_quantite_entree'] or 0

        # Annotation pour la somme des quantités sortantes
        somme_quantite_sortie = \
        Mouvement.objects.filter(produit=produit, type_op='OUT', active=True).aggregate(somme_quantite_sortie=Sum('qte'))[
            'somme_quantite_sortie'] or 0

        # Calcul du reste (entrant - sortant)
        reste = somme_quantite_entree - somme_quantite_sortie

        # Ajout des résultats pour chaque produit
        resultats_produits.append({
            'produit': produit,
            'seuil': produit.seuil,
            'somme_quantite_entree': somme_quantite_entree,
            'somme_quantite_sortie': somme_quantite_sortie,
            'reste': reste,
        })

    # Liste pour stocker les produits dont le reste est inférieur ou égal au seuil
    produits_en_seuil = []

    # Parcourez tous les produits
    for produit in produits:
        # Obtenez la somme des quantités pour le produit actuel
        somme_quantites = produit.somme_quantites()

        # Vérifiez si le reste est inférieur ou égal au seuil
        if somme_quantites['reste'] <= produit.seuil:
            produits_en_seuil.append(produit)

    # Obtenez le nombre total de produits en seuil
    nombre_total_produits_en_seuil = len(produits_en_seuil)

    # Filtrer les encaissements en fonction de la date de paiement à ce jour
    encaissements_a_ce_jour = Payement.objects.filter(date_payement__lte=aujourd_hui, active=True)

    # Calculer le montant total encaissé à ce jour
    montant_total_encaisse_a_ce_jour = encaissements_a_ce_jour.aggregate(Sum('mt_encaisse'))['mt_encaisse__sum'] or 0

    context = {
        'total_clt_count': total_clt_count,
        'total_pdt_count': total_pdt_count,
        'resultats_produits': resultats_produits,
        'nombre_total_produits_en_seuil': nombre_total_produits_en_seuil,
        'nombre_total_factures_aujourd_hui': nombre_total_factures_aujourd_hui,
        'total_quantite_sortie_aujourd_hui': total_quantite_sortie_aujourd_hui,
        'montant_total_encaisse_a_ce_jour': montant_total_encaisse_a_ce_jour
    }
    return render(request, 'accueil/accueil.html', context)


# Gestion des Models
# Accès à certains types d'utilisateurs selon le role

# Affichage des models
@login_required(login_url="/connexion")
@allowed_users(allowed_roles=['GERANT', 'ADMINISTRATEUR', 'CAISSIER', 'FACTURATION'])
def gmodels(request):
    modelbs = ModelB.objects.filter(active=True).order_by('-id')
    context = {
        'modelbs': modelbs
    }
    return render(request, 'model/model.html', context)


# Création des models
@login_required(login_url="/connexion")
@allowed_users(allowed_roles=['GERANT','ADMINISTRATEUR'])
def create_gmodels(request):
    template_name = 'model/form.html'
    titre = "Enregistrement"
    if request.method == 'POST':
        form = ModelBForm(request.POST)
        code = request.POST.get('code')
        libelle = request.POST.get('libelle')

        if ModelB.objects.filter(libelle=libelle, active=True).exists():
            messages.error(request, "Il existe déja ce model dans la base", extra_tags='custom-warning')
            return redirect("/create-model")

        valid = form.is_valid()
        if valid:
            modelb = form.save(commit=False)
            modelb.auteur = request.user
            Historique.objects.create(auteur=request.user, action="Enregistrement", table="Gestion des Models", contenu=modelb)
            modelb.save()
            messages.success(request, "Enregistrement effectué", extra_tags='custom-success')
            return redirect("/create-model")
        else:
            messages.error(request, "Une erreur est survenue lors de l'opération.", extra_tags='custom-warning')
    else:
        form = ModelBForm()

    context = {
        'titre': titre,
        'form': form
    }

    return render(request, template_name,  context)


# Modification des models
@login_required(login_url="/connexion")
@allowed_users(allowed_roles=['GERANT','ADMINISTRATEUR'])
def update_gmodels(request, id):
    titre = "Modification"
    modelb = get_object_or_404(ModelB, id=id)
    form = ModelBForm(request.POST or None, instance=modelb)

    if form.is_valid():
        Historique.objects.create(auteur=request.user, action="Modification", table="Gestion des Models",
                                  contenu=modelb)
        form.save()
        messages.success(request, "Modification effectuée", extra_tags='custom-success')
        return redirect('/model')

    return render(request, 'model/form.html', {'form': form, "titre": titre})


# Suppression des models
@login_required(login_url="/connexion")
def delete_gmodels(request, id):
    modelb = get_object_or_404(ModelB, id=id)

    if modelb:
        Historique.objects.create(auteur=request.user, action="Suppression", table="Gestion des Models",
                                  contenu=modelb)
        modelb.delete()
        messages.success(request, "Suppression effectuée", extra_tags='custom-success')
        return redirect('/model')
    else:
        messages.error(request, "Une erreur est survenue lors de l'opération.", extra_tags='custom-warning')

    return redirect('/model')
# Gestion des Models - Fin


# Gestion des Producteurs
# Affichage des producteurs
@login_required(login_url="/connexion")
@allowed_users(allowed_roles=['GERANT','ADMINISTRATEUR','CAISSIER', 'FACTURATION'])
def producteurs(request):
    producteurs = Producteur.objects.filter(active=True).order_by('-id')
    context = {
        'producteurs': producteurs
    }
    return render(request, 'producteur/producteur.html', context)


# Création des producteurs
@login_required(login_url="/connexion")
@allowed_users(allowed_roles=['GERANT','ADMINISTRATEUR'])
def create_producteur(request):
    template_name = 'producteur/form.html'
    titre = "Enregistrement"
    if request.method == 'POST':
        form = ProducteurForm(request.POST)
        code = request.POST.get('code')
        libelle = request.POST.get('libelle')

        if Producteur.objects.filter(libelle=libelle, active=True).exists():
            messages.error(request, "Il existe déja ce producteur dans la base", extra_tags='custom-warning')
            return redirect("/create-producteur")

        valid = form.is_valid()
        if valid:
            producteur = form.save(commit=False)
            producteur.auteur = request.user
            Historique.objects.create(auteur=request.user, action="Enregistrement", table="Gestion des Producteurs",
                                      contenu=producteur)
            producteur.save()
            messages.success(request, "Enregistrement effectué", extra_tags='custom-success')
            return redirect("/create-producteur")
        else:
            messages.error(request, "Une erreur est survenue lors de l'opération.", extra_tags='custom-warning')
            return redirect("/create-producteur")
    else:
        form = ModelBForm()

    context = {
        'titre': titre,
        'form': form
    }

    return render(request, template_name,  context)


# Modification des producteurs
@login_required(login_url="/connexion")
@allowed_users(allowed_roles=['GERANT','ADMINISTRATEUR'])
def update_producteur(request, id):
    titre = "Modification"
    producteur = get_object_or_404(Producteur, id=id)
    form = ProducteurForm(request.POST or None, instance=producteur)

    if form.is_valid():
        Historique.objects.create(auteur=request.user, action="Modification", table="Gestion des Producteurs",
                                  contenu=producteur)
        form.save()
        messages.success(request, "Modification effectuée", extra_tags='custom-success')
        return redirect('/producteur')

    return render(request, 'producteur/form.html', {'form': form, "titre": titre})


# Suppression des producteurs
@login_required(login_url="/connexion")
@allowed_users(allowed_roles=['GERANT','ADMINISTRATEUR'])
def delete_producteur(request, id):
    producteur = get_object_or_404(Producteur, id=id)

    if producteur:
        Historique.objects.create(auteur=request.user, action="Suppression", table="Gestion des Producteurs",
                                  contenu=producteur)
        producteur.delete()
        messages.success(request, "Suppression effectuée", extra_tags='custom-success')
        return redirect('/producteur')
    else:
        messages.error(request, "Une erreur est survenue lors de l'opération. Veuillez l'administrateur",
                       extra_tags='custom-warning')

    return redirect('/producteur')
# Gestion des producteurs - Fin


# Gestion des produits
# Affichage des produits
@login_required(login_url="/connexion")
@allowed_users(allowed_roles=['GERANT','ADMINISTRATEUR','CAISSIER', 'FACTURATION'])
def produits(request):
    produits = Produit.objects.filter(active=True).order_by('-id')
    context = {
        'produits': produits
    }
    return render(request, 'produit/produit.html', context)


# Création des produits
@login_required(login_url="/connexion")
@allowed_users(allowed_roles=['GERANT','ADMINISTRATEUR'])
def create_produit(request):
    template_name = 'produit/form.html'
    titre = "Enregistrement"
    if request.method == 'POST':
        form = ProduitForm(request.POST)
        code = request.POST.get('code')

        if Produit.objects.filter(code=code, active=True).exists():
            messages.error(request, "Il existe déja ce code dans la base", extra_tags='custom-warning')
            return redirect("/create-produit")

        valid = form.is_valid()
        if valid:
            produit = form.save(commit=False)
            produit.auteur = request.user
            Historique.objects.create(auteur=request.user, action="Enregistrement", table="Gestion des Produits",
                                      contenu=produit)
            produit.save()
            messages.success(request, "Enregistrement effectué", extra_tags='custom-success')
            return redirect("/create-produit")
        else:
            messages.success(request, "Une erreur est survenue lors de l'opération.", extra_tags='custom-warning')
            return redirect("/create-produit")
    else:
        form = ProduitForm()

    context = {
        'titre': titre,
        'form': form
    }

    return render(request, template_name,  context)


# Modification des produits
@login_required(login_url="/connexion")
@allowed_users(allowed_roles=['GERANT','ADMINISTRATEUR'])
def update_produit(request, id):
    titre = "Modification"
    produit = get_object_or_404(Produit, id=id)
    form = ProduitForm(request.POST or None, instance=produit)

    if form.is_valid():
        Historique.objects.create(auteur=request.user, action="Modification", table="Gestion des Produits",
                                  contenu=produit)
        form.save()
        messages.success(request, "Modification effectuée", extra_tags='custom-success')
        return redirect('/produit')

    return render(request, 'produit/form.html', {'form': form, "titre": titre})


# Suppression des produits
@login_required(login_url="/connexion")
@allowed_users(allowed_roles=['GERANT','ADMINISTRATEUR'])
def delete_produit(request, id):
    produit = get_object_or_404(Produit, id=id)

    if produit:
        Historique.objects.create(auteur=request.user, action="Suppression", table="Gestion des Produits",
                                  contenu=produit)
        produit.delete()
        messages.success(request, "Suppression effectuée", extra_tags='custom-success')
        return redirect('/produit')
    else:
        messages.success(request, "Une erreur est survenue lors de l'opération.", extra_tags='custom-warning')

    return render(request, 'produit/form.html', {'produit': produit})
# Gestion des produits - Fin


# Gestion des clients
# Affichage des clients
@login_required(login_url="/connexion")
@allowed_users(allowed_roles=['GERANT','ADMINISTRATEUR','CAISSIER', 'FACTURATION'])
def clients(request):
    clients = Client.objects.filter(active=True).order_by('-id')
    context = {
        'clients': clients
    }
    return render(request, 'client/client.html', context)


# Création des clients
@login_required(login_url="/connexion")
@allowed_users(allowed_roles=['GERANT','ADMINISTRATEUR'])
def create_client(request):
    template_name = 'client/form.html'
    titre = "Enregistrement"
    if request.method == 'POST':
        form = ClientForm(request.POST)
        rs = request.POST.get('rs')

        if Client.objects.filter(rs=rs, active=True).exists():
            messages.error(request, "Il existe déja ce client dans la base", extra_tags='custom-warning')
            return redirect("/create-client")

        valid = form.is_valid()
        if valid:
            client = form.save(commit=False)
            client.auteur = request.user
            Historique.objects.create(auteur=request.user, action="Enregistrement", table="Gestion des Clients",
                                      contenu=client)
            client.save()
            messages.success(request, "Enregistrement effectué", extra_tags='custom-success')
            return redirect("/create-client")
        else:
            messages.error(request, "Une erreur est survenue lors de l'opération.", extra_tags='custom-warning')
            return redirect("/create-client")
    else:
        form = ClientForm()

    context = {
        'titre': titre,
        'form': form
    }

    return render(request, template_name,  context)


# Modification des clients
@login_required(login_url="/connexion")
@allowed_users(allowed_roles=['GERANT','ADMINISTRATEUR'])
def update_client(request, id):
    titre = "Modification"
    client = get_object_or_404(Client, id=id)
    form = ClientForm(request.POST or None, instance=client)

    if form.is_valid():
        Historique.objects.create(auteur=request.user, action="Modification", table="Gestion des Clients",
                                  contenu=client)
        form.save()
        messages.success(request, "Modification effectuée", extra_tags='custom-success')
        return redirect('/client')

    return render(request, 'client/form.html', {'form': form, "titre": titre})


# Suppression des clients
@login_required(login_url="/connexion")
@allowed_users(allowed_roles=['GERANT', 'ADMINISTRATEUR'])
def delete_client(request, id):
    client = get_object_or_404(Client, id=id)

    if client:
        Historique.objects.create(auteur=request.user, action="Suppression", table="Gestion des Clients",
                                  contenu=client)
        client.delete()
        messages.success(request, "Suppression effectuée", extra_tags='custom-success')
        return redirect('/client')
    else:
        messages.success(request, "Une erreur est survenue lors de l'opération.", extra_tags='custom-warning')

    return redirect('/producteur')
# Gestion des clients - Fin


# Gestion des modes de reglements
# Affichage des modes de reglements
@login_required(login_url="/connexion")
@allowed_users(allowed_roles=['GERANT','ADMINISTRATEUR','CAISSIER', 'FACTURATION'])
def moders(request):
    moders = ModeR.objects.filter(active=True).order_by('-id')
    context = {
        'moders': moders
    }
    return render(request, 'moder/moder.html', context)


# Création des modes de reglements
@login_required(login_url="/connexion")
@allowed_users(allowed_roles=['GERANT','ADMINISTRATEUR'])
def create_moder(request):
    template_name = 'moder/form.html'
    titre = "Enregistrement"
    if request.method == 'POST':
        form = ModeRForm(request.POST)
        code = request.POST.get('code')

        if ModeR.objects.filter(code=code, active=True).exists():
            messages.error(request, "Il existe déja ce code dans la base", extra_tags='custom-warning')
            return redirect("/create-moder")

        valid = form.is_valid()
        if valid:
            moder = form.save(commit=False)
            moder.auteur = request.user
            Historique.objects.create(auteur=request.user, action="Enregistrement", table="Gestion des Models de Reglement",
                                      contenu=moder)
            moder.save()
            messages.success(request, "Enregistrement effectué", extra_tags='custom-success')
            return redirect("/create-moder")
        else:
            messages.error(request, "Une erreur est survenue lors de l'opération.", extra_tags='custom-warning')
            return redirect("/create-moder")
    else:
        form = ModeRForm()

    context = {
        'titre': titre,
        'form': form
    }

    return render(request, template_name,  context)


# Modification des modes de reglements
@login_required(login_url="/connexion")
@allowed_users(allowed_roles=['GERANT','ADMINISTRATEUR'])
def update_moder(request, id):
    titre = "Modification"
    moder = get_object_or_404(ModeR, id=id)
    form = ModeRForm(request.POST or None, instance=moder)

    if form.is_valid():
        Historique.objects.create(auteur=request.user, action="Modification", table="Gestion des Models de Reglement",
                                  contenu=moder)
        form.save()
        messages.success(request, "Modification effectuée", extra_tags='custom-success')
        return redirect('/moder')

    return render(request, 'moder/form.html', {'form': form, "titre": titre})


# Suppression des modes de reglements
@login_required(login_url="/connexion")
@allowed_users(allowed_roles=['GERANT','ADMINISTRATEUR'])
def delete_moder(request, id):
    moder = get_object_or_404(ModeR, id=id)

    if moder:
        Historique.objects.create(auteur=request.user, action="Suppression", table="Gestion des Models de Reglement",
                                  contenu=moder)
        moder.delete()
        messages.success(request, "Suppression effectuée", extra_tags='custom-success')
        return redirect('/moder')
    else:
        messages.success(request, "Une erreur est survenue lors de l'opération.", extra_tags='custom-warning')

    return redirect('/moder')
# Gestion des modes de reglements - Fin


# Gestion des entrees
# Affichage des entrees
@login_required(login_url="/connexion")
@allowed_users(allowed_roles=['GERANT','ADMINISTRATEUR','CAISSIER', 'FACTURATION'])
def entrees(request):
    entrees = Mouvement.objects.filter(active=True, type_op="ADD").order_by('-id')
    context = {
        'entrees': entrees
    }
    return render(request, 'entree/entree.html', context)


# Création des entrees
@login_required(login_url="/connexion")
@allowed_users(allowed_roles=['GERANT','ADMINISTRATEUR'])
def create_entree(request):
    template_name = 'entree/form.html'
    titre = "Enregistrement"
    if request.method == 'POST':
        form = EntreeForm(request.POST)

        valid = form.is_valid()
        if valid:
            entree = form.save(commit=False)
            entree.auteur = request.user
            entree.type_op = "ADD"
            Historique.objects.create(auteur=request.user, action="Enregistrement",
                                      table="Gestion du Stock Entrées",
                                      contenu=entree)
            entree.save()
            messages.success(request, "Enregistrement effectué", extra_tags='custom-success')
            return redirect("/create-entree")
        else:
            messages.error(request, "Une erreur est survenue lors de l'opération.", extra_tags='custom-warning')
            return redirect("/create-entree")
    else:
        form = EntreeForm()

    context = {
        'titre': titre,
        'form': form
    }

    return render(request, template_name,  context)


# Modification des entrees
@login_required(login_url="/connexion")
@allowed_users(allowed_roles=['GERANT','ADMINISTRATEUR'])
def update_entree(request, id):
    titre = "Modification"
    entree = get_object_or_404(Mouvement, id=id)
    form = EntreeForm(request.POST or None, instance=entree)

    if form.is_valid():
        Historique.objects.create(auteur=request.user, action="Modification",
                                  table="Gestion du Stock Entrées",
                                  contenu=entree)
        form.save()
        messages.success(request, "Modification effectuée", extra_tags='custom-success')
        return redirect('/entree')

    return render(request, 'entree/form.html', {'form': form, "titre": titre})


# Suppression des entrees
@login_required(login_url="/connexion")
@allowed_users(allowed_roles=['GERANT','ADMINISTRATEUR'])
def delete_entree(request, id):
    entree = get_object_or_404(Mouvement, id=id)

    if entree:
        Historique.objects.create(auteur=request.user, action="Suppression",
                                  table="Gestion du Stock Entrées",
                                  contenu=entree)
        entree.delete()
        messages.success(request, "Suppression effectuée", extra_tags='custom-success')
        return redirect('/entree')
    else:
        messages.success(request, "Une erreur est survenue lors de l'opération.", extra_tags='custom-warning')

    return redirect('/entree')
# Gestion des entrees - Fin


# Gestion des sorties - Facture
# Affichage des sorties
@login_required(login_url="/connexion")
@allowed_users(allowed_roles=['GERANT','ADMINISTRATEUR','CAISSIER', 'FACTURATION'])
def sorties(request):
    sorties = Mouvement.objects.filter(active=True, type_op="OUT").order_by('-id').annotate(
        montant=ExpressionWrapper(F('produit__pv') * F('qte'), output_field=DecimalField())
    )
    context = {
        'sorties': sorties
    }
    return render(request, 'sortie/sortie.html', context)


# Création des sorties
# Enregistrement de produits multiple sur facture
@login_required(login_url="/connexion")
@allowed_users(allowed_roles=['GERANT','ADMINISTRATEUR', 'FACTURATION'])
def create_sortie(request):
    template_name = 'sortie/form.html'
    date_facture_form = datetime.date.today().strftime("%Y-%m-%d")
    id_max = Facture.objects.aggregate(max_id=Max('id'))['max_id'] or 0
    #id_max = Facture.objects.filter(code_facture__isnull=False, active=True).count()
    today = datetime.date.today()
    annee = today.year
    mois = today.month
    if (id_max == 0):
        id_max = 1
    else:
        id_max = id_max + 1
    code_facture = f"CLAUDEX-{annee}-{mois}/{id_max}"

    form = SortieForm(request.POST or None)
    form1 = FactureForm(request.POST or None)

    if request.method == 'POST':
        date_facture = request.POST['date_facture']
        code_facture = request.POST['code_facture']
        client = request.POST['client']
        # Cas de nouveau client
        nouveau_client = request.POST['nouveau_client']
        nouveau_client_code = request.POST['nouveau_client_code']
        # Cas de nouveau client - Fin
        remise = request.POST['remise']
        tva = request.POST['tva']
        pdt = request.POST.getlist('pdtIds[]')
        qte = request.POST.getlist('qte[]')
        mt_ht = request.POST['mt_ht']
        ttc = mt_ht + tva + remise

        if pdt:
            if qte:
                if ttc:
                    # Création et Récuperation de nouveau client au cas contraire Sélection du client existant
                    if nouveau_client:
                        Historique.objects.create(auteur=request.user, action="Enregistrement Nouveau Client - Facture",
                                                  table="Gestion des Clients",
                                                  contenu=nouveau_client)
                        nouveau_client = Client.objects.create(auteur=request.user, code=nouveau_client_code,
                                                               rs=nouveau_client, type="DIVERS")
                        nouveau_client_id = nouveau_client.id
                        client_id = get_object_or_404(Client, id=nouveau_client_id)
                        client = nouveau_client_id
                    else:
                        client_id = get_object_or_404(Client, id=client)

                    code_facture_reel = f"CLAUDEX-{annee}-{mois}/{client_id.code}/{id_max}"
                    fact = Facture.objects.create(code_facture=code_facture_reel, date_facture=date_facture, client=Client.objects.get(pk=client), tva=tva, remise=remise, mt_ttc=ttc, auteur=request.user)
                    fact_id = fact.id
                    for i in range(len(pdt)):
                        Mouvement.objects.create(auteur=request.user, facture=Facture.objects.get(pk=fact_id),
                                                produit=Produit.objects.get(pk=pdt[i]),
                                                qte=qte[i],
                                                type_op="OUT")
                        Historique.objects.create(auteur=request.user, action="Enregistrement",
                                                  table="Gestion du Stock Sortie - Facture",
                                                  contenu=f"{Facture.objects.get(pk=fact_id)}-{Produit.objects.get(pk=pdt[i])}")
                    messages.success(request, "Enregistrement(s) effectué(s)")
                    return redirect('sortie')
                else:
                    messages.warning(request, "Erreur, montant ht, la taxe ou la remise ne sont pas correctes. Réessayez", extra_tags='custom-warning')
                    return render(request, 'sortie/form.html',
                                  {'form1': form1, 'form': form, 'code_facture': code_facture})
            else:
                messages.warning(request, "Erreur, La quantité n'est pas dans un bon format. Réessayez", extra_tags='custom-warning')
                return render(request, 'sortie/form.html',
                              {'form1': form1, 'form': form, 'code_facture': code_facture})
        else:
            messages.warning(request, "Svp, Veuillez ajouter au moins un produit sur la facture.",
                             extra_tags='custom-warning')
            return render(request, 'sortie/form.html',
                          {'form1': form1, 'form': form, 'code_facture': code_facture})

    context = {
        'form': form,
        'form1': form1,
        'code_facture': code_facture,
        'today': date_facture_form
    }

    return render(request, template_name,  context)


# Requete AJAX pour le chargement de la quantité du produit disponible et du prix de vente du produit - partie Facture
def load_qte_dispo(request):
    pdt_id = request.GET.get('pdt_id')

    if pdt_id:
        qte_in = \
            list(Mouvement.objects.filter(produit_id=pdt_id, type_op='ADD', active=True).aggregate(Sum('qte')).values())[
                0] or 0
        qte_out = \
        list(Mouvement.objects.filter(produit_id=pdt_id, type_op='OUT', active=True).aggregate(Sum('qte')).values())[
            0] or 0

        qte_dis = round(qte_in - qte_out, 1)
        pv_pdt = Produit.objects.filter(active=True, id=pdt_id).values_list('pv', flat=True).first()
        pv_pdt = int(pv_pdt)
        return JsonResponse([qte_dis, pv_pdt], safe=False)
    else:
        return JsonResponse([0, 0], safe=False)


# Ajout d'un produit unique sur une facture donnée à partir de la page détails facture
@login_required(login_url="/connexion")
@allowed_users(allowed_roles=['GERANT', 'ADMINISTRATEUR', 'FACTURATION'])
def create_one_sortie(request, id):
    template_name = 'sortie/form_add_produit_to_facture.html'
    titre = "Enregistrement"
    facture_id = get_object_or_404(Facture, id=id)

    if request.method == 'POST':
        form = SortieOneForm(request.POST)
        qteDispo = float(request.POST['qteDispo'])
        if form.is_valid():
            qte = float(form.cleaned_data['qte'])
            pdt = form.cleaned_data['produit']
            if qte <= qteDispo:
                Mouvement.objects.create(auteur=request.user, facture=Facture.objects.get(id=id),
                                         produit=Produit.objects.get(id=pdt.id),
                                         qte=qte,
                                         type_op="OUT")
                Historique.objects.create(auteur=request.user, action="Enregistrement",
                                          table="Gestion du Stock Sortie - Facture",
                                          contenu=f"{Facture.objects.get(id=id)}-{Produit.objects.get(id=pdt.id)}")
                messages.success(request, "Enregistrement effectué", extra_tags='custom-success')
                return redirect(f"/detail-facture/{facture_id.id}")
            else:
                messages.error(request, "Une erreur est survenue lors de l'opération, choisissez correctement la quantité.", extra_tags='custom-warning')
                return redirect(f"/create-one-sortie/{facture_id.id}")
        else:
            messages.error(request, "Tous les champs ne sont pas correctement renseignés.",
                           extra_tags='custom-warning')
            return redirect(f"/create-one-sortie/{facture_id.id}")
    else:
        form = SortieOneForm()

    context = {
        'titre': titre,
        'form': form,
        'fact_id': facture_id.id,
        'facture_code': facture_id
    }

    return render(request, template_name, context)


# Modification de facture selon la condition : si elle est en cours de reglement, ou déja réglé l'opération de
# modification de la facture est impossible
@login_required(login_url="/connexion")
@allowed_users(allowed_roles=['GERANT', 'ADMINISTRATEUR', 'FACTURATION'])
def update_sortie(request, id):
    titre = "Modification"
    sortie = get_object_or_404(Mouvement, id=id)
    form = SortieForm(request.POST or None, instance=sortie)
    facture = sortie.facture
    facture_id = sortie.facture.id

    if form.is_valid():
        check_facture = Payement.objects.filter(facture_id=facture_id, active=True).exists()
        if check_facture==False:
            Historique.objects.create(auteur=request.user, action="Modification",
                                      table="Gestion du Stock Sortie - Facture",
                                      contenu=sortie)
            form.save()
            messages.success(request, "Modification effectuée", extra_tags='custom-success')
            return redirect('/sortie')
        else:
            messages.warning(request, "Modification impossible, la facture a déja un reglement", extra_tags='custom-warning')
            return redirect('/sortie')

    return render(request, 'sortie/form_edit.html', {'form': form, "titre": titre, "facture": facture})


# Suppression de facture selon la condition : si elle est en cours de reglement, ou déja réglé l'opération de
# suppression de la facture est impossible
@login_required(login_url="/connexion")
@allowed_users(allowed_roles=['GERANT', 'ADMINISTRATEUR'])
def delete_sortie(request, id):
    sortie = get_object_or_404(Mouvement, id=id)
    facture = sortie.facture.id

    if sortie:
        check_facture = Payement.objects.filter(facture_id=facture, active=True).exists()
        if check_facture == False:
            Historique.objects.create(auteur=request.user, action="Suppression",
                                      table="Gestion du Stock Sortie - Facture",
                                      contenu=sortie)
            sortie.delete()
            messages.success(request, "Suppression effectuée", extra_tags='custom-success')
            return redirect('/sortie')
        else:
            messages.warning(request, "Suppression impossible, la facture a déja un reglement", extra_tags='custom-warning')
            return redirect('/sortie')
    else:
        messages.success(request, "Une erreur est survenue lors de l'opération.", extra_tags='custom-warning')


# Modification de ligne produit spécifique sur la facture, selon la condition : si la facture est en cours de reglement, ou déja réglé l'opération de
# modification de la ligne produit de la facture est impossible
@login_required(login_url="/connexion")
@allowed_users(allowed_roles=['GERANT', 'ADMINISTRATEUR', 'FACTURATION'])
def update_sortie_facture(request, id):
    titre = "Modification"
    sortie = get_object_or_404(Mouvement, id=id)
    form = SortieForm(request.POST or None, instance=sortie)
    facture = sortie.facture.id

    if form.is_valid():
        check_facture = Payement.objects.filter(facture_id=facture, active=True).exists()
        if check_facture==False:
            Historique.objects.create(auteur=request.user, action="Modification",
                                      table="Gestion du Stock Sorties - Facture",
                                      contenu=sortie)
            form.save()
            messages.success(request, "Modification effectuée", extra_tags='custom-success')
            return redirect(f"/detail-facture/{facture}")
        else:
            messages.warning(request, "Modification impossible, la facture a déja un reglement", extra_tags='custom-warning')
            return redirect(f"/detail-facture/{facture}")

    return render(request, 'sortie/form_edit.html', {'form': form, "titre": titre, "facture": facture})


# Suppression de ligne produit spécifique sur la facture, selon la condition : si la facture est en cours de reglement, ou déja réglé l'opération de
# suppression de la ligne produit de la facture est impossible
@login_required(login_url="/connexion")
@allowed_users(allowed_roles=['GERANT', 'ADMINISTRATEUR'])
def delete_sortie_facture(request, id):
    sortie = get_object_or_404(Mouvement, id=id)
    facture = sortie.facture.id

    if sortie:
        check_facture = Payement.objects.filter(facture_id=facture, active=True).exists()
        if check_facture == False:
            Historique.objects.create(auteur=request.user, action="Suppression",
                                      table="Gestion du Stock Sorties - Facture",
                                      contenu=sortie)
            sortie.delete()
            messages.success(request, "Suppression effectuée", extra_tags='custom-success')
            return redirect(f"/detail-facture/{facture}")
        else:
            messages.warning(request, "Suppression impossible, la facture a déja un reglement",
                             extra_tags='custom-warning')
            return redirect(f"/detail-facture/{facture}")
    else:
        messages.success(request, "Une erreur est survenue lors de l'opération.", extra_tags='custom-warning')

    return redirect(f"/detail-facture/{facture}")
# Gestion des sorties - Facture - Fin


# Gestion des Factures - Simple Affichage
@login_required(login_url="/connexion")
@allowed_users(allowed_roles=['GERANT', 'ADMINISTRATEUR', 'FACTURATION', 'CAISSIER'])
def factures(request):
    factures = Facture.objects.filter(active=True).annotate(nombre_de_produits=Count('mouvement')).order_by('-id')
    context = {
        'factures': factures
    }
    return render(request, 'facture/facture.html', context)


# Gestion des Factures - Détail avec les produits associés - Bouton Impression
@login_required(login_url="/connexion")
@allowed_users(allowed_roles=['GERANT', 'ADMINISTRATEUR', 'FACTURATION', 'CAISSIER'])
def detail_facture(request, id):
    facture = get_object_or_404(Facture, id=id)
    mouvements = Mouvement.objects.filter(facture=facture, active=True).order_by('id')
    tva = facture.tva
    remise = facture.remise
    mt_tva = tva + remise
    montant_ht = sum(mouvement.produit.pv * mouvement.qte for mouvement in mouvements)
    montant_total = montant_ht - mt_tva
    recap_types_facture = facture.recap_types_produits()

    context = {
        'facture': facture,
        'mouvements': mouvements,
        'montant_ht': montant_ht,
        'montant_total': montant_total,
        'recap_types_facture': recap_types_facture,
        'remise': remise,
        'tva': tva,
    }
    return render(request, 'facture/detail.html', context)


# Gestion des Factures - Détail avec les produits associés - Facture réglée - Bouton Impression
@login_required(login_url="/connexion")
@allowed_users(allowed_roles=['GERANT', 'ADMINISTRATEUR', 'CAISSIER', 'FACTURATION'])
def detail_facture_payee(request, id):
    # Infos Payement
    info_payement = get_object_or_404(Payement, id=id)
    total_reglee_for_facture = Payement.objects.filter(facture=info_payement.facture, active=True).aggregate(Sum('mt_encaisse'))['mt_encaisse__sum'] or 0

    facture = get_object_or_404(Facture, id=info_payement.facture.id)
    mouvements = Mouvement.objects.filter(facture=facture, active=True).order_by('id')
    tva = facture.tva
    remise = facture.remise
    mt_tva = tva + remise
    montant_ht = sum(mouvement.produit.pv * mouvement.qte for mouvement in mouvements)
    montant_total = montant_ht - mt_tva
    montant_restant = montant_total - total_reglee_for_facture

    # Récap par type produit en fonction de la quantité pour éventuel remise
    recap_types_facture = facture.recap_types_produits()

    context = {
        'facture': facture,
        'mouvements': mouvements,
        'montant_ht': montant_ht,
        'montant_total': montant_total,
        'remise': remise,
        'tva': tva,
        'info_payement': info_payement,
        'total_reglee_for_facture': total_reglee_for_facture,
        'montant_restant': montant_restant,
        'recap_types_facture': recap_types_facture,
    }
    return render(request, 'payement/detail.html', context)


# Modification de facture, selon la condition : si la facture est en cours de reglement, ou déja réglé l'opération de
# modification de la facture est impossible
@login_required(login_url="/connexion")
@allowed_users(allowed_roles=['GERANT', 'ADMINISTRATEUR', 'FACTURATION'])
def update_facture(request, id):
    titre = "Modification"
    facture = get_object_or_404(Facture, id=id)
    form = FactureForm(request.POST or None, instance=facture)

    if form.is_valid():
        ## Controle si payement deja enregistree
        check_facture = Payement.objects.filter(facture_id=facture, active=True).exists()
        if check_facture == False:
            Historique.objects.create(auteur=request.user, action="Modification",
                                      table="Gestion des Factures",
                                      contenu=facture)
            form.save()
            messages.success(request, "Modification effectuée", extra_tags='custom-success')
            return redirect('/facture')
        else:
            messages.warning(request, "Modification impossible, la facture a déja un reglement",
                             extra_tags='custom-warning')

    return render(request, 'facture/form_facture.html', {'form': form, "titre": titre})


# Facture à remettre au client - generation en PDF
class generate_facture_a_payer(View):
    def get(self, request, id, *args, **kwargs):
        facture = get_object_or_404(Facture, id=id)
        mouvements = Mouvement.objects.filter(facture=facture, active=True).order_by('id')
        tva = facture.tva
        remise = facture.remise
        mt_tva = tva + remise
        montant_ht = sum(mouvement.produit.pv * mouvement.qte for mouvement in mouvements)
        montant_total = montant_ht - mt_tva
        montant_total_lettre = num2words(int(montant_total), lang="fr")
        nombre_de_mouvements = Mouvement.objects.filter(facture=facture, active=True).order_by('id').count()
        recap_types_facture = facture.recap_types_produits()
        data = {
            "facturateur": request.user,
            "facture": facture,
            "tva": tva,
            "mouvements": mouvements,
            "remise": remise,
            "montant_ht": montant_ht,
            "montant_total": montant_total,
            "montant_total_lettre": montant_total_lettre,
            "recap_types_facture": recap_types_facture,
        }
        if nombre_de_mouvements > 10:
            pdf = render_to_pdf('pdf/facture_a_payer_unique.html', data)
        else:
            pdf = render_to_pdf('pdf/facture_a_payer.html', data)

        if pdf:
            response=HttpResponse(pdf, content_type='application/pdf')
            filename = "Facture_%s.pdf" %(data['facture'].code_facture)
            content = "inline; filename= %s" %(filename)
            response['Content-Disposition']=content
            return response
        return HttpResponse("Page Not Found")


# Facture réglé à remettre au client - generation en PDF
class generate_facture_payer(View):
    def get(self, request, id, *args, **kwargs):
        # Payement
        info_payement = get_object_or_404(Payement, id=id)
        total_reglee_for_facture = Payement.objects.filter(facture=info_payement.facture, active=True).aggregate(Sum('mt_encaisse'))['mt_encaisse__sum'] or 0

        facture = get_object_or_404(Facture, id=info_payement.facture.id)
        recap_types_facture = facture.recap_types_produits()
        mouvements = Mouvement.objects.filter(facture=facture, active=True).order_by('id')
        tva = facture.tva
        remise = facture.remise
        mt_tva = tva + remise
        montant_ht = sum(mouvement.produit.pv * mouvement.qte for mouvement in mouvements)
        montant_total = montant_ht - mt_tva

        montant_restant = montant_total - total_reglee_for_facture

        montant_total_lettre = num2words(int(montant_total), lang="fr")

        date_echeance = facture.date_facture + datetime.timedelta(days=7)

        nombre_de_mouvements = Mouvement.objects.filter(facture=facture, active=True).order_by('id').count()

        data = {
            "facturateur": request.user,
            "facture": facture,
            "tva": tva,
            "mouvements": mouvements,
            "remise": remise,
            "montant_ht": montant_ht,
            "montant_total": montant_total,
            "montant_total_lettre": montant_total_lettre,
            'info_payement': info_payement,
            'total_reglee_for_facture': total_reglee_for_facture,
            'montant_restant': montant_restant,
            'date_echeance': date_echeance,
            'recap_types_facture': recap_types_facture,

        }
        if nombre_de_mouvements > 10:
            pdf = render_to_pdf('pdf/facture_payer_unique.html', data)
        else:
            pdf = render_to_pdf('pdf/facture_payer.html', data)

        if pdf:
            response=HttpResponse(pdf, content_type='application/pdf')
            filename = "Facture_Payer_%s.pdf" %(data['facture'].code_facture)
            content = "inline; filename= %s" %(filename)
            response['Content-Disposition']=content
            return response
        return HttpResponse("Page Not Found")


# Gestion des payements
# Affichage des payements
@login_required(login_url="/connexion")
@allowed_users(allowed_roles=['GERANT', 'ADMINISTRATEUR', 'CAISSIER', 'FACTURATION'])
def payements(request):
    #payements = Payement.objects.filter(active=True).annotate(nombre_de_payements_facture=Count('facture'))
    payements = Payement.objects.filter(active=True).order_by('-id')
    context = {
        'payements': payements
    }
    return render(request, 'payement/payement.html', context)


# Création des payements
@login_required(login_url="/connexion")
@allowed_users(allowed_roles=['GERANT', 'ADMINISTRATEUR', 'CAISSIER'])
def create_payement(request):
    template_name = 'payement/form.html'
    titre = "Enregistrement"
    date_paiement_form = datetime.date.today().strftime("%Y-%m-%d")
    id_max = Payement.objects.aggregate(max_id=Max('id'))['max_id'] or 0
    # id_max = Payement.objects.filter(active=True).aggregate(max_id=Coalesce(Max('id'), 0))['max_id']
    today = datetime.date.today()
    annee = today.year
    mois = today.month
    if (id_max == 0):
        id_max = 1
    else:
        id_max = id_max + 1
    code_payement = f"PAYE-{annee}-{mois}/{id_max}"
    if request.method == 'POST':
        form = PayementForm(request.POST)

        valid = form.is_valid()
        if valid:
            payement = form.save(commit=False)
            payement.auteur = request.user
            payement.code_payement = code_payement

            montant_facture_restant = Facture.objects.get(pk=form.cleaned_data['facture'].id).montant_restant()
            payement.mt_recu = form.cleaned_data['mt_recu']
            payement.mt_encaisse = form.cleaned_data['mt_encaisse']

            payement.mt_restant = montant_facture_restant - payement.mt_encaisse

            if montant_facture_restant > 0 and payement.mt_encaisse <= montant_facture_restant and payement.mt_encaisse <= payement.mt_recu:
                Historique.objects.create(auteur=request.user, action="Enregistrement",
                                          table="Gestion des Payements",
                                          contenu=payement)
                payement.save()
                messages.success(request, "Enregistrement effectué", extra_tags='custom-success')
                return redirect("/create-payement")
            else:
                messages.warning(request, "Facture Déja Reglée ou Erreur de montant saisie",
                                 extra_tags='custom-warning')
                return redirect("/create-payement")

        else:
            messages.error(request, "Une erreur est survenue lors de l'opération.", extra_tags='custom-warning')
            return redirect("/create-payement")
    else:
        form = PayementForm()

    context = {
        'titre': titre,
        'date_paiement_form': date_paiement_form,
        'code_payement': code_payement,
        'form': form
    }

    return render(request, template_name,  context)

# Requete AJAX pour le chargement du montant restant de la facture et montant intial de la facture
def load_mt_facture(request):
    factId = request.GET.get('fact_id')

    if factId:
        facture_instance = Facture.objects.get(id=factId, active=True)
        total_amount = facture_instance.calcul_montant_total()
        total_restant = facture_instance.montant_restant()
        mt_fact = total_amount or 0
        mt_fact_rest = total_restant or 0
        return JsonResponse([mt_fact, mt_fact_rest], safe=False)
    else:
        return JsonResponse([0, 0], safe=False)


# Détail de payement - Bouton impression
@login_required(login_url="/connexion")
@allowed_users(allowed_roles=['GERANT', 'ADMINISTRATEUR', 'CAISSIER', 'FACTURATION'])
def detail_payement(request, id):
    facture = get_object_or_404(Payement, facture_id=id)
    mouvements = Mouvement.objects.filter(facture=facture, active=True).order_by('id')
    tva = facture.tva
    remise = facture.remise
    mt_tva = tva + remise
    montant_ht = sum(mouvement.produit.pv * mouvement.qte for mouvement in mouvements)
    montant_total = montant_ht - mt_tva

    context = {
        'facture': facture,
        'mouvements': mouvements,
        'montant_ht': montant_ht,
        'montant_total': montant_total,
        'remise': remise,
        'tva': tva,
    }
    return render(request, 'facture/detail.html', context)


# Suppression de payement
@login_required(login_url="/connexion")
@allowed_users(allowed_roles=['GERANT', 'ADMINISTRATEUR'])
def delete_payement(request, id):
    payement = get_object_or_404(Payement, id=id)

    if payement:
        Historique.objects.create(auteur=request.user, action="Suppression",
                                  table="Gestion des Payements",
                                  contenu=payement)
        payement.delete()
        messages.success(request, "Suppression effectuée", extra_tags='custom-success')
        return redirect('/payement')
    else:
        messages.success(request, "Une erreur est survenue lors de l'opération.", extra_tags='custom-warning')

    return redirect('/payement')


# Listing - Etat - generation en PDF

class generate_stock_general_vente(View):
    def get(self, request, *args, **kwargs):
        produits = Produit.objects.all()

        # Liste pour stocker les résultats finaux
        resultats_produits = []

        for produit in produits:
            # Annotation pour la somme des quantités entrantes
            somme_quantite_entree = \
                Mouvement.objects.filter(produit=produit, type_op='ADD', active=True).aggregate(
                    somme_quantite_entree=Sum('qte'))[
                    'somme_quantite_entree'] or 0

            # Annotation pour la somme des quantités sortantes
            somme_quantite_sortie = \
                Mouvement.objects.filter(produit=produit, type_op='OUT', active=True).aggregate(
                    somme_quantite_sortie=Sum('qte'))[
                    'somme_quantite_sortie'] or 0

            # Calcul du reste (entrant - sortant)
            reste = somme_quantite_entree - somme_quantite_sortie

            # Ajout des résultats pour chaque produit
            resultats_produits.append({
                'produit': produit,
                'seuil': produit.seuil,
                'somme_quantite_entree': somme_quantite_entree,
                'somme_quantite_sortie': somme_quantite_sortie,
                'reste': reste,
            })

        data = {
            "resultats_produits": resultats_produits,
            'today': datetime.date.today().strftime("%d-%m-%Y"),

        }

        pdf = render_to_pdf('pdf/stock_general_vente.html', data)

        if pdf:
            response=HttpResponse(pdf, content_type='application/pdf')
            filename = "Listing_Stock_General_Vente_%s.pdf" %(data['today'])
            content = "inline; filename= %s" %(filename)
            response['Content-Disposition']=content
            return response
        return HttpResponse("Page Not Found")


# Caisse
def statistique_caisses(request):
    start_date = datetime.date.today().strftime("%Y-%m-%d")
    end_date = datetime.date.today().strftime("%Y-%m-%d")
    total_montant_factures, total_montant_encaisses, total_montant_restants = 0, 0, 0
    if request.method == 'POST':
        form = StatistiqueForm(request.POST)
        start_date = request.POST['start_date']
        end_date = request.POST['end_date']
        if form.is_valid():
            statistiques_ventes = Payement.paiements_pour_periode(start_date, end_date)
            # Grouper par facture et calculer les sommes des montants encaissés et restants
            factures_sommes = {}
            for paiement in statistiques_ventes:
                facture_id = paiement.facture.id
                if facture_id not in factures_sommes:
                    factures_sommes[facture_id] = {
                        'payement_id': paiement.id,
                        'facture': paiement.facture,
                        'code_facture': paiement.facture.code_facture,
                        'date_payement': paiement.date_payement,
                        'client': paiement.facture.client,
                        'date_facture': paiement.facture.date_facture,
                        'montant_facture': paiement.facture.calcul_montant_total(),
                        'montant_encaisse': 0,
                        'montant_restant': 0,
                    }

                factures_sommes[facture_id]['montant_encaisse'] += paiement.mt_encaisse
                factures_sommes[facture_id]['montant_restant'] = factures_sommes[facture_id]['montant_facture'] - factures_sommes[facture_id]['montant_encaisse']

            for facture_id, values in factures_sommes.items():
                total_montant_factures += values['montant_facture']
                total_montant_encaisses += values['montant_encaisse']
                total_montant_restants += values['montant_restant']

    else:
        factures_sommes = None
        form = StatistiqueForm()
        # 'today': datetime.date.today().strftime("%d-%m-%Y"),

    context = {
        'start_date': start_date,
        'end_date': end_date,
        'factures_sommes': factures_sommes,
        'total_montant_factures': total_montant_factures,
        'total_montant_encaisses': total_montant_encaisses,
        'total_montant_restants': total_montant_restants,
        'form': form,
    }
    return render(request, 'listings/statistique_caisse.html', context)


class statistique_caisse_periode(View):
    def get(self, request, start_date, end_date, *args, **kwargs):
        total_montant_factures, total_montant_encaisses, total_montant_restants = 0, 0, 0
        statistiques_ventes = Payement.paiements_pour_periode(start_date, end_date)
        # Grouper par facture et calculer les sommes des montants encaissés et restants
        factures_sommes = {}
        for paiement in statistiques_ventes:
            facture_id = paiement.facture.id
            if facture_id not in factures_sommes:
                factures_sommes[facture_id] = {
                    'payement_id': paiement.id,
                    'facture': paiement.facture,
                    'code_facture': paiement.facture.code_facture,
                    'date_payement': paiement.date_payement,
                    'client': paiement.facture.client,
                    'date_facture': paiement.facture.date_facture,
                    'montant_facture': paiement.facture.calcul_montant_total(),
                    'montant_encaisse': 0,
                    'montant_restant': 0,
                }

            factures_sommes[facture_id]['montant_encaisse'] += paiement.mt_encaisse
            factures_sommes[facture_id]['montant_restant'] = factures_sommes[facture_id]['montant_facture'] - \
                                                             factures_sommes[facture_id]['montant_encaisse']

        for facture_id, values in factures_sommes.items():
            total_montant_factures += values['montant_facture']
            total_montant_encaisses += values['montant_encaisse']
            total_montant_restants += values['montant_restant']

        data = {
            "start_date": start_date,
            "end_date": end_date,
            'today': datetime.date.today().strftime("%d-%m-%Y"),
            'factures_sommes': factures_sommes,
            'total_montant_factures': total_montant_factures,
            'total_montant_encaisses': total_montant_encaisses,
            'total_montant_restants': total_montant_restants,
        }

        pdf = render_to_pdf('pdf/statistique_caisse_periode.html', data)

        if pdf:
            response=HttpResponse(pdf, content_type='application/pdf')
            filename = "Statistique_caisses_%s.pdf" %(data['today'])
            content = "inline; filename= %s" %(filename)
            response['Content-Disposition']=content
            return response
        return HttpResponse("Page Not Found")


class statistique_caisse_periode_mensuelle(View):
    def get(self, request, *args, **kwargs):
        start_date = "2024-02-01"
        end_date = datetime.date.today().strftime("%Y-%m-%d")

        # Test - Statistique Mensuelle
        montant_total_factures_par_mois = Facture.montant_total_factures_par_mois()
        montant_total_encaisse_par_mois = Facture.montant_total_encaisse_par_mois()
        montant_total_restant_par_mois = Facture.montant_total_restant_par_mois()

        total_montant_total = sum(item['montant_total'] for item in montant_total_factures_par_mois)
        total_montant_encaisse = sum(item['montant_encaisse'] for item in montant_total_encaisse_par_mois)
        total_montant_restant = sum(item['montant_restant'] for item in montant_total_restant_par_mois)

        # End Test

        data = {
            "start_date": start_date,
            "end_date": end_date,
            'today': datetime.date.today().strftime("%d-%m-%Y"),
            'montant_total_factures_par_mois': montant_total_factures_par_mois,
            'montants': [
                {
                    'mois': item['mois'],
                    'montant_total': item['montant_total'],
                    'montant_encaisse': next(
                        (x['montant_encaisse'] for x in montant_total_encaisse_par_mois if x['mois'] == item['mois']),
                        0),
                    'montant_restant': next(
                        (x['montant_restant'] for x in montant_total_restant_par_mois if x['mois'] == item['mois']), 0),
                }
                for item in montant_total_factures_par_mois
            ],
            'total_montant_total': total_montant_total,
            'total_montant_encaisse': total_montant_encaisse,
            'total_montant_restant': total_montant_restant,
        }

        pdf = render_to_pdf('pdf/statistique_caisse_periode_mensuelle.html', data)

        if pdf:
            response=HttpResponse(pdf, content_type='application/pdf')
            filename = "Statistique_caisses_periode_%s.pdf" %(data['today'])
            content = "inline; filename= %s" %(filename)
            response['Content-Disposition']=content
            return response
        return HttpResponse("Page Not Found")
# Fin Caisse


# Vente - Facture editees
def statistique_ventes(request):
    start_date = datetime.date.today().strftime("%Y-%m-%d")
    end_date = datetime.date.today().strftime("%Y-%m-%d")
    total_montant_factures, total_montant_encaisses, total_montant_restants = 0, 0, 0
    if request.method == 'POST':
        form = StatistiqueForm(request.POST)
        start_date = request.POST['start_date']
        end_date = request.POST['end_date']
        if form.is_valid():
            # Obtenez la liste de toutes les factures
            toutes_les_factures = Facture.factures_pour_periode(start_date, end_date)

            # Créez un dictionnaire pour stocker les informations pour chaque facture
            informations_factures = []

            for facture in toutes_les_factures:
                montant_facture = facture.calcul_montant_total()
                montant_encaisse = sum(paiement.mt_encaisse for paiement in facture.payement_set.filter(active=True))
                montant_restant = facture.montant_restant_par_rapport_total_facture()

                informations_factures.append({
                    'facture_id': facture.id,
                    'code_facture': facture.code_facture,
                    'client': facture.client,
                    'date_facture': facture.date_facture,
                    'montant_facture': montant_facture,
                    'montant_restant': montant_restant,
                    'montant_encaisse': montant_encaisse
                })

            for values in informations_factures:
                total_montant_factures += values['montant_facture']
                total_montant_encaisses += values['montant_encaisse']
                total_montant_restants += values['montant_restant']

    else:
        informations_factures = None
        form = StatistiqueForm()
        # 'today': datetime.date.today().strftime("%d-%m-%Y"),

    context = {
        'start_date': start_date,
        'end_date': end_date,
        'informations_factures': informations_factures,
        'total_montant_factures': total_montant_factures,
        'total_montant_encaisses': total_montant_encaisses,
        'total_montant_restants': total_montant_restants,
        'form': form,
    }
    return render(request, 'listings/statistique_vente.html', context)


class statistique_vente_periode(View):
    def get(self, request, start_date, end_date, *args, **kwargs):
        total_montant_factures, total_montant_encaisses, total_montant_restants = 0, 0, 0

        # Obtenez la liste de toutes les factures
        toutes_les_factures = Facture.factures_pour_periode(start_date, end_date)

        # Créez un dictionnaire pour stocker les informations pour chaque facture
        informations_factures = []

        for facture in toutes_les_factures:
            montant_facture = facture.calcul_montant_total()
            montant_encaisse = sum(
                paiement.mt_encaisse for paiement in facture.payement_set.filter(active=True))
            montant_restant = facture.montant_restant_par_rapport_total_facture()

            informations_factures.append({
                'facture_id': facture.id,
                'code_facture': facture.code_facture,
                'client': facture.client,
                'date_facture': facture.date_facture,
                'montant_facture': montant_facture,
                'montant_restant': montant_restant,
                'montant_encaisse': montant_encaisse
            })

        for values in informations_factures:
            total_montant_factures += values['montant_facture']
            total_montant_encaisses += values['montant_encaisse']
            total_montant_restants += values['montant_restant']

        data = {
            "start_date": start_date,
            "end_date": end_date,
            'today': datetime.date.today().strftime("%d-%m-%Y"),
            'informations_factures': informations_factures,
            'total_montant_factures': total_montant_factures,
            'total_montant_encaisses': total_montant_encaisses,
            'total_montant_restants': total_montant_restants,
        }

        pdf = render_to_pdf('pdf/statistique_vente_periode.html', data)

        if pdf:
            response=HttpResponse(pdf, content_type='application/pdf')
            filename = "Statistique_ventes_%s.pdf" %(data['today'])
            content = "inline; filename= %s" %(filename)
            response['Content-Disposition']=content
            return response
        return HttpResponse("Page Not Found")
# Fin Vente - Facture editees


class statistique_caisse_periode_mensuelle(View):
    def get(self, request, *args, **kwargs):
        start_date = "2024-02-01"
        end_date = datetime.date.today().strftime("%Y-%m-%d")

        # Test - Statistique Mensuelle
        montant_total_factures_par_mois = Facture.montant_total_factures_par_mois()
        montant_total_encaisse_par_mois = Facture.montant_total_encaisse_par_mois()
        montant_total_restant_par_mois = Facture.montant_total_restant_par_mois()

        total_montant_total = sum(item['montant_total'] for item in montant_total_factures_par_mois)
        total_montant_encaisse = sum(item['montant_encaisse'] for item in montant_total_encaisse_par_mois)
        total_montant_restant = sum(item['montant_restant'] for item in montant_total_restant_par_mois)

        # End Test

        data = {
            "start_date": start_date,
            "end_date": end_date,
            'today': datetime.date.today().strftime("%d-%m-%Y"),
            'montant_total_factures_par_mois': montant_total_factures_par_mois,
            'montants': [
                {
                    'mois': item['mois'],
                    'montant_total': item['montant_total'],
                    'montant_encaisse': next(
                        (x['montant_encaisse'] for x in montant_total_encaisse_par_mois if x['mois'] == item['mois']),
                        0),
                    'montant_restant': next(
                        (x['montant_restant'] for x in montant_total_restant_par_mois if x['mois'] == item['mois']), 0),
                }
                for item in montant_total_factures_par_mois
            ],
            'total_montant_total': total_montant_total,
            'total_montant_encaisse': total_montant_encaisse,
            'total_montant_restant': total_montant_restant,
        }

        pdf = render_to_pdf('pdf/statistique_caisse_periode_mensuelle.html', data)

        if pdf:
            response=HttpResponse(pdf, content_type='application/pdf')
            filename = "Statistique_caisses_periode_%s.pdf" %(data['today'])
            content = "inline; filename= %s" %(filename)
            response['Content-Disposition']=content
            return response
        return HttpResponse("Page Not Found")


class statistique_facture_reste_avec_penalite(View):
    def get(self, request, *args, **kwargs):

        # Obtenez la liste de toutes les factures
        toutes_les_factures = Facture.objects.all()

        # Créez un dictionnaire pour stocker les informations pour chaque facture
        informations_factures = []

        for facture in toutes_les_factures:
            montant_restant = facture.montant_restant_par_rapport_total_facture()
            # Check if montant_restant is 0 and skip the facture
            if montant_restant == 0:
                continue
            jours_diff = (date.today() - facture.date_facture).days
            nb_jours_impaye = jours_diff - 7
            penalite = 0.002 * nb_jours_impaye  # 0.2%
            montant_penalite = math.ceil(round(montant_restant * penalite, 4)) if jours_diff > 7 else 0
            montant_a_payer = math.ceil(montant_restant + montant_penalite)
            montant_encaisse = sum(paiement.mt_encaisse for paiement in facture.payement_set.filter(active=True))

            informations_factures.append({
                'code_facture': facture.code_facture,
                'date_facture': facture.date_facture,
                'montant_restant': montant_restant,
                'jours_diff': jours_diff,
                'montant_penalite': montant_penalite,
                'montant_a_payer': montant_a_payer,
                'montant_encaisse': montant_encaisse
            })

        data = {
            'today': datetime.date.today().strftime("%d-%m-%Y"),
            'informations_factures': informations_factures,

        }

        pdf = render_to_pdf('pdf/statistique_facture_reste_penalite.html', data)

        if pdf:
            response=HttpResponse(pdf, content_type='application/pdf')
            filename = "Statistique_Reste_Penalite_%s.pdf" %(data['today'])
            content = "inline; filename= %s" %(filename)
            response['Content-Disposition']=content
            return response
        return HttpResponse("Page Not Found")


class liste_clients(View):
    def get(self, request, *args, **kwargs):

        clients = Client.objects.filter(active=True).all()

        data = {
            'today': datetime.date.today().strftime("%d-%m-%Y"),
            'clients': clients,

        }

        pdf = render_to_pdf('pdf/liste_clients.html', data)

        if pdf:
            response=HttpResponse(pdf, content_type='application/pdf')
            filename = "Liste_clients_%s.pdf" %(data['today'])
            content = "inline; filename= %s" %(filename)
            response['Content-Disposition']=content
            return response
        return HttpResponse("Page Not Found")


class liste_produits(View):
    def get(self, request, *args, **kwargs):

        produits = Produit.objects.all().order_by('producteur')

        data = {
            'today': datetime.date.today().strftime("%d-%m-%Y"),
            'produits': produits,
        }

        pdf = render_to_pdf('pdf/liste_produits.html', data)

        if pdf:
            response=HttpResponse(pdf, content_type='application/pdf')
            filename = "Liste_produits_%s.pdf" %(data['today'])
            content = "inline; filename= %s" %(filename)
            response['Content-Disposition']=content
            return response
        return HttpResponse("Page Not Found")


class liste_archivage_facture(View):
    def get(self, request, *args, **kwargs):

        # factures = Facture.objects.filter(payement__mt_encaisse__gt=0).distinct()
        factures = Facture.objects.all()
        print('facture', factures)
        data = {
            'today': datetime.date.today().strftime("%d-%m-%Y"),
            'factures': factures,
        }

        pdf = render_to_pdf('pdf/liste_factures.html', data)

        if pdf:
            response=HttpResponse(pdf, content_type='application/pdf')
            filename = "Liste_factures_%s.pdf" %(data['today'])
            content = "inline; filename= %s" %(filename)
            response['Content-Disposition']=content
            return response
        return HttpResponse("Page Not Found")


# Gestion des erreurs et Autorisation
def custom_404(request, exception):
    return render(request, 'accueil/404.html', status=404)


def custom_500(request):
    return render(request, 'accueil/500.html', status=500)
