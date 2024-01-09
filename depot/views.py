import datetime

import fpdf
import inflect
import num2words as num2words
from num2words import num2words
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, ExpressionWrapper, F, DecimalField, Count, Case, When, Value, FloatField
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login
from django.views import View
from fpdf import FPDF

from response import Response

from .decorators import allowed_users
from .forms import CustomAuthenticationForm, ModelBForm, ProducteurForm, ProduitForm, ClientForm, ModeRForm, \
    EntreeForm, SortieForm, FactureForm, PayementForm
from .models import ModelB, Producteur, Produit, Client, ModeR, Mouvement, Facture, Payement
from .utils import render_to_pdf


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
                    login(request, user)
                    return redirect("/")
                else:
                    message = "Nom d'utilisateur ou mot de passe incorrectes"

    context = {
        'form': form, 'message': message
    }
    return render(request, 'registration/login.html', context)


@login_required(login_url="/connexion")
def home(request):
    total_clt_count = Client.objects.filter(active=True).count()
    total_pdt_count = Produit.objects.filter(active=True).count()
    #produit_commande_bientot = LigneCommande.objects.filter(disponible=True, statut="LIVREE").count()
    pdt_sortie_stock = Mouvement.objects.filter(active=True).order_by('-id')
    facture_jour = Mouvement.objects.filter(active=True).order_by('-id')
    facture_jour_payee = Mouvement.objects.filter(active=True).order_by('-id')

    # Somme des quantités entrantes
    quantite_entrante = Mouvement.objects.filter(type_op='ADD', active=True).aggregate(quantite_entree=Sum('qte'))

    # Somme des quantités sortantes
    quantite_sortante = Mouvement.objects.filter(type_op='OUT', active=True).aggregate(quantite_sortie=Sum('qte'))

    # Somme des quantités disponibles (entrantes - sortantes)
    quantite_disponible = quantite_entrante['quantite_entree'] - quantite_sortante['quantite_sortie']

    # Récupération des produits avec annotation pour la somme des quantités par produit
    produits = Produit.objects.annotate(
        somme_quantite_entree=Sum(Case(When(mouvement__type_op='ADD', then=F('mouvement__qte')), default=Value(0),
                                       output_field=FloatField())),
        somme_quantite_sortie=Sum(Case(When(mouvement__type_op='OUT', then=F('mouvement__qte')), default=Value(0),
                                       output_field=FloatField())),
        quantite_disponible=F('somme_quantite_entree') - F('somme_quantite_sortie')
    )

    # Comparaison avec le seuil
    produits_avec_seuil = produits.filter(quantite_disponible__lte=F('seuil'))

    mouvements = 0

    ## Listing Stock Général et Vente
    produits = Produit.objects.all()

    # Liste pour stocker les résultats finaux
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

    context = {
        'total_clt_count': total_clt_count,
        'total_pdt_count': total_pdt_count,
        'resultats_produits': resultats_produits
    }
    return render(request, 'accueil/accueil.html', context)


@login_required(login_url="/connexion")
@allowed_users(allowed_roles=['GERANT','ADMINISTRATEUR','CAISSIER', 'FACTURATION'])
def gmodels(request):
    modelbs = ModelB.objects.filter(active=True).order_by('-id')
    context = {
        'modelbs': modelbs
    }
    return render(request, 'model/model.html', context)


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


@login_required(login_url="/connexion")
@allowed_users(allowed_roles=['GERANT','ADMINISTRATEUR'])
def update_gmodels(request, id):
    titre = "Modification"
    modelb = get_object_or_404(ModelB, id=id)
    form = ModelBForm(request.POST or None, instance=modelb)

    if form.is_valid():
        form.save()
        messages.success(request, "Modification effectuée", extra_tags='custom-success')
        return redirect('/model')

    return render(request, 'model/form.html', {'form': form, "titre": titre})


@login_required(login_url="/connexion")
def delete_gmodels(request, id):
    modelb = get_object_or_404(ModelB, id=id)

    if modelb:
        modelb.delete()
        messages.success(request, "Suppression effectuée", extra_tags='custom-success')
        return redirect('/model')
    else:
        messages.error(request, "Une erreur est survenue lors de l'opération.", extra_tags='custom-warning')

    return redirect('/model')


@login_required(login_url="/connexion")
@allowed_users(allowed_roles=['GERANT','ADMINISTRATEUR','CAISSIER', 'FACTURATION'])
def producteurs(request):
    producteurs = Producteur.objects.filter(active=True).order_by('-id')
    context = {
        'producteurs': producteurs
    }
    return render(request, 'producteur/producteur.html', context)


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


@login_required(login_url="/connexion")
@allowed_users(allowed_roles=['GERANT','ADMINISTRATEUR'])
def update_producteur(request, id):
    titre = "Modification"
    producteur = get_object_or_404(Producteur, id=id)
    form = ProducteurForm(request.POST or None, instance=producteur)

    if form.is_valid():
        form.save()
        messages.success(request, "Modification effectuée", extra_tags='custom-success')
        return redirect('/producteur')

    return render(request, 'producteur/form.html', {'form': form, "titre": titre})


@login_required(login_url="/connexion")
@allowed_users(allowed_roles=['GERANT','ADMINISTRATEUR'])
def delete_producteur(request, id):
    producteur = get_object_or_404(Producteur, id=id)

    if producteur:
        producteur.delete()
        messages.success(request, "Suppression effectuée", extra_tags='custom-success')
        return redirect('/producteur')
    else:
        messages.error(request, "Une erreur est survenue lors de l'opération. Veuillez l'administrateur",
                       extra_tags='custom-warning')

    return redirect('/producteur')


@login_required(login_url="/connexion")
@allowed_users(allowed_roles=['GERANT','ADMINISTRATEUR','CAISSIER', 'FACTURATION'])
def produits(request):
    produits = Produit.objects.filter(active=True).order_by('-id')
    context = {
        'produits': produits
    }
    return render(request, 'produit/produit.html', context)


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


@login_required(login_url="/connexion")
@allowed_users(allowed_roles=['GERANT','ADMINISTRATEUR'])
def update_produit(request, id):
    titre = "Modification"
    produit = get_object_or_404(Produit, id=id)
    form = ProduitForm(request.POST or None, instance=produit)

    if form.is_valid():
        form.save()
        messages.success(request, "Modification effectuée", extra_tags='custom-success')
        return redirect('/produit')

    return render(request, 'produit/form.html', {'form': form, "titre": titre})


@login_required(login_url="/connexion")
@allowed_users(allowed_roles=['GERANT','ADMINISTRATEUR'])
def delete_produit(request, id):
    produit = get_object_or_404(Produit, id=id)

    if produit:
        produit.delete()
        messages.success(request, "Suppression effectuée", extra_tags='custom-success')
        return redirect('/produit')
    else:
        messages.success(request, "Une erreur est survenue lors de l'opération.", extra_tags='custom-warning')

    return render(request, 'produit/form.html', {'produit': produit})


@login_required(login_url="/connexion")
@allowed_users(allowed_roles=['GERANT','ADMINISTRATEUR','CAISSIER', 'FACTURATION'])
def clients(request):
    clients = Client.objects.filter(active=True).order_by('-id')
    context = {
        'clients': clients
    }
    return render(request, 'client/client.html', context)


@login_required(login_url="/connexion")
@allowed_users(allowed_roles=['GERANT','ADMINISTRATEUR'])
def create_client(request):
    template_name = 'client/form.html'
    titre = "Enregistrement"
    if request.method == 'POST':
        form = ClientForm(request.POST)
        code = request.POST.get('code')

        if Client.objects.filter(code=code, active=True).exists():
            messages.error(request, "Il existe déja ce code dans la base", extra_tags='custom-warning')
            return redirect("/create-client")

        valid = form.is_valid()
        if valid:
            client = form.save(commit=False)
            client.auteur = request.user
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


@login_required(login_url="/connexion")
@allowed_users(allowed_roles=['GERANT','ADMINISTRATEUR'])
def update_client(request, id):
    titre = "Modification"
    client = get_object_or_404(Client, id=id)
    form = ClientForm(request.POST or None, instance=client)

    if form.is_valid():
        form.save()
        messages.success(request, "Modification effectuée", extra_tags='custom-success')
        return redirect('/client')

    return render(request, 'client/form.html', {'form': form, "titre": titre})


@login_required(login_url="/connexion")
@allowed_users(allowed_roles=['GERANT','ADMINISTRATEUR'])
def delete_client(request, id):
    client = get_object_or_404(Client, id=id)

    if client:
        client.delete()
        messages.success(request, "Suppression effectuée", extra_tags='custom-success')
        return redirect('/client')
    else:
        messages.success(request, "Une erreur est survenue lors de l'opération.", extra_tags='custom-warning')

    return redirect('/producteur')


@login_required(login_url="/connexion")
@allowed_users(allowed_roles=['GERANT','ADMINISTRATEUR','CAISSIER', 'FACTURATION'])
def moders(request):
    moders = ModeR.objects.filter(active=True).order_by('-id')
    context = {
        'moders': moders
    }
    return render(request, 'moder/moder.html', context)


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


@login_required(login_url="/connexion")
@allowed_users(allowed_roles=['GERANT','ADMINISTRATEUR'])
def update_moder(request, id):
    titre = "Modification"
    moder = get_object_or_404(ModeR, id=id)
    form = ModeRForm(request.POST or None, instance=moder)

    if form.is_valid():
        form.save()
        messages.success(request, "Modification effectuée", extra_tags='custom-success')
        return redirect('/moder')

    return render(request, 'moder/form.html', {'form': form, "titre": titre})


@login_required(login_url="/connexion")
@allowed_users(allowed_roles=['GERANT','ADMINISTRATEUR'])
def delete_moder(request, id):
    moder = get_object_or_404(ModeR, id=id)

    if moder:
        moder.delete()
        messages.success(request, "Suppression effectuée", extra_tags='custom-success')
        return redirect('/moder')
    else:
        messages.success(request, "Une erreur est survenue lors de l'opération.", extra_tags='custom-warning')

    return redirect('/moder')


@login_required(login_url="/connexion")
@allowed_users(allowed_roles=['GERANT','ADMINISTRATEUR','CAISSIER', 'FACTURATION'])
def entrees(request):
    entrees = Mouvement.objects.filter(active=True, type_op="ADD").order_by('-id')
    context = {
        'entrees': entrees
    }
    return render(request, 'entree/entree.html', context)


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
            entree.save()
            # Mouvement.objects.create(auteur=request.user, date_creation=datetime.date, produit=Produit.objects.get(pk=form.cleaned_data['produit'].id), qte=form.cleaned_data['qte'], type_op="ADD")
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


@login_required(login_url="/connexion")
@allowed_users(allowed_roles=['GERANT','ADMINISTRATEUR'])
def update_entree(request, id):
    titre = "Modification"
    entree = get_object_or_404(Mouvement, id=id)
    form = EntreeForm(request.POST or None, instance=entree)

    if form.is_valid():
        # Mouvement.objects.update(id=id, auteur=request.user, date_creation=datetime.date,
        #                         produit=Produit.objects.get(pk=form.cleaned_data['produit'].id),
        #                         qte=form.cleaned_data['qte'], type_op="ADD")
        form.save()
        messages.success(request, "Modification effectuée", extra_tags='custom-success')
        return redirect('/entree')

    return render(request, 'entree/form.html', {'form': form, "titre": titre})


@login_required(login_url="/connexion")
@allowed_users(allowed_roles=['GERANT','ADMINISTRATEUR'])
def delete_entree(request, id):
    entree = get_object_or_404(Mouvement, id=id)

    if entree:
        entree.delete()
        messages.success(request, "Suppression effectuée", extra_tags='custom-success')
        return redirect('/entree')
    else:
        messages.success(request, "Une erreur est survenue lors de l'opération.", extra_tags='custom-warning')

    return redirect('/entree')


@login_required(login_url="/connexion")
@allowed_users(allowed_roles=['GERANT','ADMINISTRATEUR','CAISSIER', 'FACTURATION'])
def sorties(request):
    #sorties = Mouvement.objects.filter(active=True, type_op="OUT").order_by('-id')
    sorties = Mouvement.objects.filter(active=True, type_op="OUT").order_by('-id').annotate(
        montant=ExpressionWrapper(F('produit__pv') * F('qte'), output_field=DecimalField())
    )
    context = {
        'sorties': sorties
    }
    return render(request, 'sortie/sortie.html', context)


@login_required(login_url="/connexion")
@allowed_users(allowed_roles=['GERANT','ADMINISTRATEUR', 'FACTURATION'])
def create_sortie(request):
    template_name = 'sortie/form.html'
    titre = "Enregistrement"
    d = datetime.date.today().strftime("%d%m%Y")
    id_max = Facture.objects.filter(code_facture__isnull=False, active=True).count()
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
        type_client = request.POST['type_client']
        remise = request.POST['remise']
        tva = request.POST['tva']
        pdt = request.POST.getlist('pdtIds[]')
        qte = request.POST.getlist('qte[]')
        mt_ht = request.POST['mt_ht']
        ttc = mt_ht + tva + remise

        if pdt:
            client_id = get_object_or_404(Client, id=client)
            print('ok')
            code_facture_reel = f"CLAUDEX-{annee}-{mois}/{client_id.code}/{id_max}"
            fact = Facture.objects.create(code_facture=code_facture_reel, date_facture=date_facture, client=Client.objects.get(pk=client), type_client=type_client, tva=tva, remise=remise, mt_ttc=ttc, auteur=request.user)
            fact_id = fact.id
            for i in range(len(pdt)):
                Mouvement.objects.create(auteur=request.user, facture=Facture.objects.get(pk=fact_id),
                                        produit=Produit.objects.get(pk=pdt[i]),
                                        qte=qte[i],
                                        type_op="OUT")
            messages.success(request, "Enregistrement(s) effectué(s)")
            return redirect('sortie')
        else:
            messages.warning(request, "Svp, Veuillez ajouter au moins un produit sur la facture.", extra_tags='custom-warning')
            return render(request, 'sortie/form.html',
                          {'form1': form1, 'form': form, 'code_facture': code_facture})

    context = {
        'form': form,
        'form1': form1,
        'code_facture': code_facture,
    }

    return render(request, template_name,  context)


def load_qte_dispo(request):
    pdt_id = request.GET.get('pdt_id')

    if pdt_id:
        qte_in = \
            list(Mouvement.objects.filter(produit_id=pdt_id, type_op='ADD', active=True).aggregate(Sum('qte')).values())[
                0] or 0
        qte_out = \
        list(Mouvement.objects.filter(produit_id=pdt_id, type_op='OUT', active=True).aggregate(Sum('qte')).values())[
            0] or 0
        qte_dis = qte_in - qte_out
        pv_pdt = Produit.objects.filter(active=True, id=pdt_id).values_list('pv', flat=True).first()
        pv_pdt = int(pv_pdt)
        return JsonResponse([qte_dis, pv_pdt], safe=False)
    else:
        return JsonResponse([0, 0], safe=False)


@login_required(login_url="/connexion")
@allowed_users(allowed_roles=['GERANT','ADMINISTRATEUR', 'FACTURATION'])
def create_one_sortie(request, id):
    template_name = 'sortie/form_add_produit_to_facture.html'
    titre = "Enregistrement"
    facture_id = get_object_or_404(Facture, id=id)

    if request.method == 'POST':
        form = SortieForm(request.POST)

        if form.is_valid():
            facture_saisi = form.cleaned_data['facture']
            if facture_saisi == facture_id:
                sortie = form.save(commit=False)
                sortie.auteur = request.user
                sortie.type_op = "OUT"
                sortie.save()
                messages.success(request, "Enregistrement effectué", extra_tags='custom-success')
                return redirect(f"/detail-facture/{facture_id.id}")
            else:
                messages.error(request, "Une erreur est survenue lors de l'opération, choisissez correctement la facture.", extra_tags='custom-warning')
                return redirect(f"/create-one-sortie/{facture_id.id}")
    else:
        form = SortieForm()

    context = {
        'titre': titre,
        'form': form,
        'fact_id': facture_id.id,
        'facture_code': facture_id
    }

    return render(request, template_name, context)

@login_required(login_url="/connexion")
@allowed_users(allowed_roles=['GERANT','ADMINISTRATEUR', 'FACTURATION'])
def update_sortie(request, id):
    titre = "Modification"
    sortie = get_object_or_404(Mouvement, id=id)
    form = SortieForm(request.POST or None, instance=sortie)
    facture = sortie.facture.id
    #print(facture)
    if form.is_valid():
        check_facture = Payement.objects.filter(facture_id=facture, active=True).exists()
        if check_facture==False:
            form.save()
            messages.success(request, "Modification effectuée", extra_tags='custom-success')
            return redirect('/sortie')
        else:
            messages.warning(request, "Modification impossible, la facture est en cours de payement", extra_tags='custom-warning')
            return redirect('/sortie')

    return render(request, 'sortie/form_edit.html', {'form': form, "titre": titre, "facture": facture})

@login_required(login_url="/connexion")
@allowed_users(allowed_roles=['GERANT','ADMINISTRATEUR'])
def delete_sortie(request, id):
    sortie = get_object_or_404(Mouvement, id=id)
    facture = sortie.facture.id

    if sortie:
        check_facture = Payement.objects.filter(facture_id=facture, active=True).exists()
        if check_facture == False:
            sortie.delete()
            messages.success(request, "Suppression effectuée", extra_tags='custom-success')
            return redirect('/sortie')
        else:
            messages.warning(request, "Suppression impossible, la facture est en cours de payement", extra_tags='custom-warning')
            return redirect('/sortie')
    else:
        messages.success(request, "Une erreur est survenue lors de l'opération.", extra_tags='custom-warning')


@login_required(login_url="/connexion")
@allowed_users(allowed_roles=['GERANT','ADMINISTRATEUR','FACTURATION'])
def update_sortie_facture(request, id):
    titre = "Modification"
    sortie = get_object_or_404(Mouvement, id=id)
    form = SortieForm(request.POST or None, instance=sortie)
    facture = sortie.facture.id
    #print(facture)
    if form.is_valid():
        check_facture = Payement.objects.filter(facture_id=facture, active=True).exists()
        if check_facture==False:
            form.save()
            messages.success(request, "Modification effectuée", extra_tags='custom-success')
            return redirect(f"/detail-facture/{facture}")
        else:
            messages.warning(request, "Modification impossible, la facture est en cours de payement", extra_tags='custom-warning')
            return redirect(f"/detail-facture/{facture}")

    return render(request, 'sortie/form_edit.html', {'form': form, "titre": titre, "facture": facture})


@login_required(login_url="/connexion")
@allowed_users(allowed_roles=['GERANT','ADMINISTRATEUR'])
def delete_sortie_facture(request, id):
    sortie = get_object_or_404(Mouvement, id=id)
    facture = sortie.facture.id

    if sortie:
        check_facture = Payement.objects.filter(facture_id=facture, active=True).exists()
        if check_facture == False:
            sortie.delete()
            messages.success(request, "Suppression effectuée", extra_tags='custom-success')
            return redirect(f"/detail-facture/{facture}")
        else:
            messages.warning(request, "Suppression impossible, la facture est en cours de payement",
                             extra_tags='custom-warning')
            return redirect(f"/detail-facture/{facture}")
    else:
        messages.success(request, "Une erreur est survenue lors de l'opération.", extra_tags='custom-warning')

    return redirect(f"/detail-facture/{facture}")


@login_required(login_url="/connexion")
@allowed_users(allowed_roles=['GERANT','ADMINISTRATEUR', 'FACTURATION', 'CAISSIER'])
def factures(request):
    factures = Facture.objects.filter(active=True).annotate(nombre_de_produits=Count('mouvement'))
    context = {
        'factures': factures
    }
    return render(request, 'facture/facture.html', context)


@login_required(login_url="/connexion")
@allowed_users(allowed_roles=['GERANT','ADMINISTRATEUR','FACTURATION', 'CAISSIER'])
def detail_facture(request, id):
    facture = get_object_or_404(Facture, id=id)
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


@login_required(login_url="/connexion")
@allowed_users(allowed_roles=['GERANT','ADMINISTRATEUR','CAISSIER', 'FACTURATION'])
def detail_facture_payee(request, id):
    # Payement
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
    }
    return render(request, 'payement/detail.html', context)


@login_required(login_url="/connexion")
@allowed_users(allowed_roles=['GERANT','ADMINISTRATEUR','FACTURATION'])
def update_facture(request, id):
    titre = "Modification"
    facture = get_object_or_404(Facture, id=id)
    form = FactureForm(request.POST or None, instance=facture)

    if form.is_valid():
        ## Controle si payement deja enregistree
        form.save()
        if form.save():
            messages.success(request, "Modification effectuée", extra_tags='custom-success')
            return redirect('/facture')
        else:
            messages.warning(request, "Erreur veuillez remplir correctement tous les champs", extra_tags='custom-warning')

    return render(request, 'facture/form_facture.html', {'form': form, "titre": titre})


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
        data = {
            "facturateur": request.user,
            "facture": facture,
            "tva": tva,
            "mouvements": mouvements,
            "remise": remise,
            "montant_ht": montant_ht,
            "montant_total": montant_total,
            "montant_total_lettre": montant_total_lettre,
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


class generate_facture_payer(View):
    def get(self, request, id, *args, **kwargs):
        # Payement
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

@login_required(login_url="/connexion")
@allowed_users(allowed_roles=['GERANT','ADMINISTRATEUR','CAISSIER', 'FACTURATION'])
def payements(request):
    #payements = Payement.objects.filter(active=True).annotate(nombre_de_payements_facture=Count('facture'))
    payements = Payement.objects.filter(active=True).order_by('-id')
    context = {
        'payements': payements
    }
    return render(request, 'payement/payement.html', context)


@login_required(login_url="/connexion")
@allowed_users(allowed_roles=['GERANT','ADMINISTRATEUR','CAISSIER'])
def create_payement(request):
    template_name = 'payement/form.html'
    titre = "Enregistrement"
    if request.method == 'POST':
        form = PayementForm(request.POST)

        valid = form.is_valid()
        if valid:
            payement = form.save(commit=False)
            payement.auteur = request.user
            total_reglee_for_facture = Payement.objects.filter(facture_id=form.cleaned_data['facture'].id, active=True).aggregate(Sum('mt_encaisse'))['mt_encaisse__sum'] or 0
            montant_facture = Facture.objects.get(pk=form.cleaned_data['facture'].id).calcul_montant_total()
            payement.mt_encaisse = form.cleaned_data['mt_encaisse']
            payement.mt_restant = montant_facture - payement.mt_encaisse - total_reglee_for_facture
            print(montant_facture, payement.mt_encaisse, total_reglee_for_facture, payement.mt_restant)
            if payement.mt_encaisse <= montant_facture and form.cleaned_data['reliquat'] <= montant_facture:
                if total_reglee_for_facture < montant_facture:
                    payement.save()
                    messages.success(request, "Enregistrement effectué", extra_tags='custom-success')
                    return redirect("/create-payement")
                else:
                    messages.warning(request, "Facture Déja Reglée", extra_tags='custom-warning')
                    return redirect("/create-payement")
            else:
                messages.warning(request, "Reliquat incorrect", extra_tags='custom-warning')
                return redirect("/create-payement")
        else:
            messages.error(request, "Une erreur est survenue lors de l'opération.", extra_tags='custom-warning')
            return redirect("/create-payement")
    else:
        form = PayementForm()

    context = {
        'titre': titre,
        'form': form
    }

    return render(request, template_name,  context)


def load_mt_facture(request):
    factId = request.GET.get('fact_id')

    if factId:
        facture_instance = Facture.objects.get(id=factId, active=True)
        total_amount = facture_instance.calcul_montant_total()

        mt_fact = total_amount or 0
        return JsonResponse([mt_fact], safe=False)
    else:
        return JsonResponse([0], safe=False)


@login_required(login_url="/connexion")
@allowed_users(allowed_roles=['GERANT','ADMINISTRATEUR'])
def delete_payement(request, id):
    payement = get_object_or_404(Payement, id=id)

    if payement:
        payement.delete()
        messages.success(request, "Suppression effectuée", extra_tags='custom-success')
        return redirect('/payement')
    else:
        messages.success(request, "Une erreur est survenue lors de l'opération.", extra_tags='custom-warning')

    return redirect('/payement')


@login_required(login_url="/connexion")
@allowed_users(allowed_roles=['GERANT','ADMINISTRATEUR','CAISSIER', 'FACTURATION'])
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


def custom_404(request, exception):
    return render(request, 'accueil/404.html', status=404)