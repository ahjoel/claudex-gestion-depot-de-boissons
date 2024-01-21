from django.urls import path
from . import views
from .views import generate_facture_a_payer, generate_facture_payer, generate_stock_general_vente, statistique_vente_periode,\
    statistique_vente_periode_mensuelle, statistique_facture_reste_avec_penalite, liste_clients, liste_produits, liste_archivage_facture

urlpatterns = [
    path('', views.home, name='home'),
    path('model', views.gmodels, name='model'),
    path('create-model', views.create_gmodels, name='create-model'),
    path('update-model/<int:id>', views.update_gmodels, name='update-model'),
    path('delete-model/<int:id>', views.delete_gmodels, name='delete-model'),
    path('producteur', views.producteurs, name='producteur'),
    path('create-producteur', views.create_producteur, name='create-producteur'),
    path('update-producteur/<int:id>', views.update_producteur, name='update-producteur'),
    path('delete-producteur/<int:id>', views.delete_producteur, name='delete-producteur'),
    path('produit', views.produits, name='produit'),
    path('create-produit', views.create_produit, name='create-produit'),
    path('update-produit/<int:id>', views.update_produit, name='update-produit'),
    path('delete-produit/<int:id>', views.delete_produit, name='delete-produit'),
    path('client', views.clients, name='client'),
    path('create-client', views.create_client, name='create-client'),
    path('update-client/<int:id>', views.update_client, name='update-client'),
    path('delete-client/<int:id>', views.delete_client, name='delete-client'),
    path('moder', views.moders, name='moder'),
    path('create-moder', views.create_moder, name='create-moder'),
    path('update-moder/<int:id>', views.update_moder, name='update-moder'),
    path('delete-moder/<int:id>', views.delete_moder, name='delete-moder'),
    path('entree', views.entrees, name='entree'),
    path('create-entree', views.create_entree, name='create-entree'),
    path('update-entree/<int:id>', views.update_entree, name='update-entree'),
    path('delete-entree/<int:id>', views.delete_entree, name='delete-entree'),
    path('sortie', views.sorties, name='sortie'),
    path('create-sortie', views.create_sortie, name='create-sortie'),
    path('create-one-sortie/<int:id>', views.create_one_sortie, name='create-one-sortie'),
    path('update-one-sortie/<int:id>', views.update_sortie_facture, name='update-one-sortie'),
    path('delete-one-sortie/<int:id>', views.delete_sortie_facture, name='delete-one-sortie'),
    path('update-sortie/<int:id>', views.update_sortie, name='update-sortie'),
    path('delete-sortie/<int:id>', views.delete_sortie, name='delete-sortie'),
    path('ajax_load_qte/', views.load_qte_dispo, name='ajax_load_qte'),
    path('ajax_load_mt_fact/', views.load_mt_facture, name='ajax_load_mt_fact'),
    path('facture', views.factures, name='facture'),
    path('update-facture/<int:id>', views.update_facture, name='update-facture'),
    path('detail-facture/<int:id>', views.detail_facture, name='detail-facture'),
    path('generate-facture/<int:id>', generate_facture_a_payer.as_view(), name='generate-facture'),
    path('generate-facture-payer/<int:id>', generate_facture_payer.as_view(), name='generate-facture-payer'),
    path('generate-stock-general-vente', generate_stock_general_vente.as_view(), name='generate-stock-general-vente'),
    path('payement', views.payements, name='payement'),
    path('create-payement', views.create_payement, name='create-payement'),
    path('delete-payement/<int:id>', views.delete_payement, name='delete-payement'),
    path('detail-payement/<int:id>', views.detail_facture_payee, name='detail-payement'),
    path('statistique-vente-periode/', views.statistique_ventes, name='statistique-vente-periode'),
    path('statistique-vente-periode/<start_date>/<end_date>', statistique_vente_periode.as_view(), name='statistique-vente-periode'),
    path('statistique-vente-periode-mensuelle', statistique_vente_periode_mensuelle.as_view(), name='statistique-vente-periode-mensuelle'),
    path('statistique-facture-reste-penalite', statistique_facture_reste_avec_penalite.as_view(), name='statistique-facture-reste-penalite'),
    path('liste-client', liste_clients.as_view(), name='liste-client'),
    path('liste-produit', liste_produits.as_view(), name='liste-produit'),
    path('liste-facture', liste_archivage_facture.as_view(), name='liste-facture'),
    path('connexion', views.custom_login, name='connexion'),
]
