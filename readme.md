# CLAUDEX - Système de gestion de Dépots de Boissons


# Fonctionnalités

CLAUDEX est un logiciel de gestion du stock des dépots de boissons et dispose des fonctionnalités pour la gestion des ventes aux bars et la production des états. Son usage dans ce cadre est destiné à être installé sur le réseau local d'une entreprise spécifique. Il est conçu pour :

- éviter le surstockage des fournitures au stock
- optimiser le temps de traitement des activités lié à la gestion du stock des produits dans un dépôt de boissons
- optimiser les états mensuels du stock
- analyser l'utilisation fréquente de certains produits du dépot de boisson en vue des prédictions sur une période donnée


1- Enregistrement des produits

2- Création des commandes de factures

3- Opérations sur les entrees et sorties de produits

4- Productions des états mensuels relatif aux mouvements dans les dépôts

5- Bien d'autres..

# Getting started

1- Clone or down the repo

2- Install python : https://www.python.org/downloads/

3- Create a virtual environment :

```python
   python3 -m venv myenv
```

4- Activate virtual environment on windows :

```python
   myenv\Scripts\activate
```

5- Activate virtual environment on macOS and linux :

```python
    source myenv/bin/activate
```

6- Install the dependencies:

```python
   pip install -r requirements.txt
``` 

6- Apply the migrations:

```python
   python manage.py migrate
``` 

## Development Example

```python
   python manage.py runserver
```