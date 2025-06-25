import json
import os
import sys 
import requests 
from datetime import datetime
import ssl
import socket
from urllib.parse import urlparse
from datetime import timezone
import csv
import html 
from typing import List


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

def envoyer_webhook(url, message):
    try:
        requests.post(url, json={"content": message})
    except Exception as e:
        print(f"Erreur envoi webhook : {e}")

def verifier_certificat_ssl(url):
    try :
        parsed = urlparse(url)
        if parsed.scheme != 'https' :
            return None 
        
        host = parsed.hostname
        port = parsed.port or 443

        context = ssl.create_default_context()
        with socket.create_connection((host, port), timeout=5) as sock:
            with context.wrap_socket(sock, server_hostname=host) as ssock:
                cert = ssock.getpeercert()
                expire_str = cert['notAfter']
                expire_date = datetime.strptime(expire_str, '%b %d %H:%M:%S %Y %Z').replace(tzinfo=timezone.utc)
                jours_restant = (expire_date - datetime.now(timezone.utc)).days
                return jours_restant
    except Exception as e:
        return f"Erreur certificat : {e}"

etat_sites = {}

import csv
import html
from typing import List

def exporter_historique(noms_sites: List[str], format_export: str = 'csv') -> None:
    """
    Exporte l'historique des vérifications pour un ou plusieurs sites sélectionnés.

    Args:
        noms_sites (List[str]): Liste des noms des sites à exporter.
        format_export (str): 'csv' ou 'html'.

    Returns:
        None
    """
    if not os.path.exists(log_fichier):
        print("Fichier de log introuvable.")
        return

    lignes_trouvees = []
    try:
        with open(log_fichier, 'r', encoding='utf-8') as f:
            for ligne in f:
                for nom in noms_sites:
                    if f"] {nom} (" in ligne:
                        try:
                            horodatage, reste = ligne.split("] ", 1)
                            horodatage = horodatage.strip("[]")
                            lignes_trouvees.append((horodatage, nom, reste.strip()))
                        except ValueError:
                            continue
    except Exception as e:
        print(f"Erreur de lecture du fichier : {e}")
        return

    if not lignes_trouvees:
        print("Aucune donnée trouvée pour les sites sélectionnés.")
        return

    fichier_export = f"historique_export.{format_export}"
    try:
        if format_export == 'csv':
            with open(fichier_export, 'w', newline='', encoding='utf-8') as f_csv:
                writer = csv.writer(f_csv)
                writer.writerow(['Horodatage', 'Nom du Site', 'Détails'])
                writer.writerows(lignes_trouvees)
            print(f"Export CSV effectué : {fichier_export}")
        elif format_export == 'html':
            with open(fichier_export, 'w', encoding='utf-8') as f_html:
                f_html.write("<html><head><meta charset='utf-8'><title>Historique</title></head><body>\n")
                f_html.write("<h2>Historique des vérifications</h2>\n")
                f_html.write("<table border='1'><tr><th>Horodatage</th><th>Nom du Site</th><th>Détails</th></tr>\n")
                for date, nom, details in lignes_trouvees:
                    f_html.write(f"<tr><td>{html.escape(date)}</td><td>{html.escape(nom)}</td><td>{html.escape(details)}</td></tr>\n")
                f_html.write("</table></body></html>")
            print(f"Export HTML effectué : {fichier_export}")
        else:
            print("Format non pris en charge. Utilisez 'csv' ou 'html'.")
    except Exception as e:
        print(f"Erreur lors de l'écriture du fichier : {e}")


def verifier_sites():
    with open(log_fichier, 'a', encoding='utf-8') as log:
        for site in sites:
            url = site['url']
            nom = site['nom']
            webhook = site.get('webhook')
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            try:
                response = requests.get(url, timeout=5)
                code = response.status_code
                statut = "UP" if 200 <= code < 400 else "DOWN"
            except requests.RequestException:
                code = 'ERROR'
                statut = "DOWN"
            
            jours_certificat = verifier_certificat_ssl(url)

            if isinstance(jours_certificat, int):
                cert_info = f" - SSL expire dans {jours_certificat} jours"
                if jours_certificat <= 15:
                    cert_info += " -  Attention, expiration proche"
            else:
                cert_info = f" - {jours_certificat}" if jours_certificat else ""


            print(f"{nom} ({url}) - HTTP {code} - {statut}{cert_info}")
            log.write(f"[{now}] {nom} ({url}) - HTTP {code} - {statut}{cert_info}\n")


            precedent = etat_sites.get(url)
            if webhook and precedent != statut:
                if statut == "DOWN":
                    envoyer_webhook(webhook, f" **{nom}** est DOWN  (HTTP {code})")
                elif statut == "UP":
                    envoyer_webhook(webhook, f" **{nom}** est revenu UP  (HTTP {code})")
            etat_sites[url] = statut


if len(sys.argv) > 1:
    if sys.argv[1] == 'check':
        if not sites:
            print("Aucun site à vérifier.")
        else:
            print("Vérification des sites...")
            verifier_sites()
        sys.exit()

    elif sys.argv[1] == 'export':
        if not sites:
            print("Aucun site enregistré.")
            sys.exit()

        afficher_sites()
        choix = input("Entrez les numéros des sites à exporter (ex: 0,1,2) ou 'all' pour tout exporter : ").strip()

        if choix.lower() == 'all':
            noms_sites = [site['nom'] for site in sites]
        else:
            try:
                indices = [int(i.strip()) for i in choix.split(',')]
                noms_sites = [sites[i]['nom'] for i in indices if 0 <= i < len(sites)]
            except ValueError:
                print("Entrée invalide. Veuillez entrer des numéros séparés par des virgules.")
                sys.exit()

        format_export = input("Format d'export (csv/html) : ").strip().lower()
        if format_export not in ['csv', 'html']:
            print("Format non pris en charge.")
            sys.exit()

        exporter_historique(noms_sites, format_export)
        sys.exit()


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
