import json
import os
import sys 
import requests 
from datetime import datetime

nom_fichier = 'list_serveur.json'
log_fichier ='check_log.txt'

if os.path.exists(nom_fichier):
    with open(nom_fichier, 'r', encoding='utf-8') as fichier:
        sites = json.load(fichier)
        print(f"Fichier chargé avec {len(sites)} sites existants.")
else:
    sites = []

def sauvegarder():
    with open(nom_fichier, 'w', encoding='utf-8') as fichier:
        json.dump(sites, fichier, indent=4, ensure_ascii=False)

def afficher_sites():
    if not sites:
        print("Aucun site enregistré.")
    else:
        print("\nListe des sites enregistrés :")
        for i, site in enumerate(sites):
            webhook = site.get('webhook', 'aucun')
            print(f"{i} : {site['nom']} ({site['url']}) - Webhook : {webhook}")

def verifier_sites():
    with open(log_fichier, 'a', encoding='utf-8') as log:
        for site in sites:
            url = site['url']
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            try:
                response = requests.get(url, timeout=5)
                code = response.status_code
                statut = "UP" if 200 <= code < 400 else "DOWN"
                log.write(f"[{now}] {url} - HTTP {code} - {statut}\n")
                print(f"{url} - HTTP {code} - {statut}")
            except requests.RequestException as e:
                log.write(f"[{now}] {url} - ERROR - DOWN ({e})\n")
                print(f"{url} - ERROR - DOWN ({e})")
                
if len(sys.argv) > 1 and sys.argv[1] == 'check':
    if not sites:
        print("Aucun site à vérifier.")
    else:
        print("Vérification des sites...")
        verifier_sites()
    sys.exit()

while True:
    action = input("\nTapez 'ajouter' pour ajouter un site, 'webhook' pour modifier un webhook, 'supprimer' pour retirer un site, ou 'stop' pour quitter : ").lower()

    if action == 'ajouter':
        nom = input('Entrez le nom du site : ')
        url = input('Entrez l\'URL : ')
        webhook = input('Entrez le webhook (laissez vide si aucun) : ')
        site = {'nom': nom, 'url': url}
        if webhook.strip():
            site['webhook'] = webhook
        sites.append(site)
        sauvegarder()
        print("Site ajouté avec succès.")
        afficher_sites()

    elif action == 'list':
        afficher_sites()

    elif action == 'webhook':
        if not sites:
            print("Aucun site à modifier.")
            continue
        afficher_sites()
        try:
            index = int(input("Entrez le numéro du site à modifier : "))
            if 0 <= index < len(sites):
                new_webhook = input("Entrez le nouveau webhook (laissez vide pour supprimer le webhook) : ").strip()
                if new_webhook:
                    sites[index]['webhook'] = new_webhook
                    print("Webhook mis à jour.")
                else:
                    sites[index].pop('webhook', None)
                    print("Webhook supprimé.")
                sauvegarder()
                afficher_sites()
            else:
                print("Index invalide.")
        except ValueError:
            print("Entrée non valide. Veuillez entrer un numéro.")

    elif action == 'supprimer':
        if not sites:
            print("La liste est vide. Rien à supprimer.")
            continue
        afficher_sites()
        try:
            index = int(input("Entrez le numéro du site à supprimer : "))
            if 0 <= index < len(sites):
                supprimé = sites.pop(index)
                sauvegarder()
                print(f"Site '{supprimé['nom']}' supprimé.")
                afficher_sites()
            else:
                print("Index invalide.")
        except ValueError:
            print("Entrée non valide. Veuillez entrer un numéro.")

    elif action == 'stop':
        print("Fin du programme.")
        break

    else:
        print("Commande inconnue.")
