"""Recherche bornée de la structure de C3 : nombre de champs × type de destinataire.

Les essais du 09 au 14 octobre n'ont joué que 1, 5, 8 et 12 champs. La facture de test de la
DGI montre un client à six champs (type, nom, IFU, RCCM, adresse, contact). Chaque type officiel
(tableau de la note 2025-0889) est répété à toutes les places d'une trame : une trame couvre
toutes les positions du type pour ce nombre de champs.

Rien n'est envoyé par défaut.

Résultat du 2026-10-15 : la trame 7 (PPx7, sept champs) a donné « l'adresse e-mail du destinataire
n'est pas valide », premier message nouveau de C3 ; elle le redonne après un rallumage, sans rituel.
Il n'y a pas d'état caché : la réponse dépend de la charge utile (le « R » est celui d'un C3 vide).
La suite est dans appareil/carte_client.py.

Usage :
  python3 -m appareil.recherche_structure --liste
  python3 -m appareil.recherche_structure --jumeau
  python3 -m appareil.recherche_structure --port /dev/ttyACM0 --seq B0

Sur l'appareil : une trame toutes les 3 s, 80 au plus, arrêt au premier message nouveau, au NAK,
au silence ou à la déconnexion. EazSell au premier plan, aucune facture ouverte, accord de
l'opérateur, une séance à la fois.
"""
import argparse
import sys
import time

from appareil.recherche_bornee import (
    DELAI, PLAFOND, borne, envoyer_jumeau, jouer, pousser, suivant,
)

TYPES = ("PP", "PM", "PC", "CC")
NOMBRES = tuple(range(2, 17))

# Déjà joués à ce nombre de champs (2026-10-12) : 5 (quatre types), 8 (CC), 12 (PP, PM, PC).
CONNUS = (
    {(5, t) for t in TYPES} | {(8, "CC")} | {(12, t) for t in ("PP", "PM", "PC")}
)

# Le bloc client de la facture de test : type, nom, IFU, RCCM, adresse, contact.
NATURELLES = (
    ("type-en-1re-place", "PP,CLIENT TEST,,,,"),
    ("ordre-niger-etendu", ",CLIENT TEST,PP,,,"),
)


def grille(connus=CONNUS):
    """(nom, données) : les deux formes naturelles, puis chaque type à toutes les places.

    Les nombres de champs viennent par distance à six, le nombre du bloc client.
    """
    yield from NATURELLES
    for n in sorted(NOMBRES, key=lambda n: (abs(n - 6), n)):
        for t in TYPES:
            if (n, t) not in connus:
                yield "%sx%d" % (t, n), ",".join([t] * n)


def main(argv=None, mcf=None):
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("--liste", action="store_true", help="afficher la grille, ne rien envoyer")
    a.add_argument("--jumeau", action="store_true", help="jouer contre le jumeau FIS, pas l'appareil")
    a.add_argument("--port", help="port série de l'appareil ; sans --jumeau ni --liste, exige ce port")
    a.add_argument("--seq", default="B0", help="séquence hexadécimale de départ (défaut B0)")
    a.add_argument("--depuis", type=int, default=1, help="numéro affiché de la première trame (1 = début)")
    a.add_argument("--delai", type=float, default=DELAI)
    a.add_argument("--plafond", type=int, default=PLAFOND)
    o = a.parse_args(argv)
    if o.plafond < 1:
        print("plafond nul : rien envoyé.")
        return 2
    try:
        depart = int(o.seq, 16)
    except ValueError:
        print("séquence illisible : rien envoyé.")
        return 2
    complet = list(grille())
    if o.depuis < 1 or o.depuis > len(complet) + 1:
        print("départ %d hors grille (trames 1–%d) : rien envoyé." % (o.depuis, len(complet)))
        return 2
    envoi = (o.jumeau or o.port) and not o.liste
    if envoi and o.plafond > PLAFOND:
        print("plafond %d au-dessus de %d : rien envoyé." % (o.plafond, PLAFOND))
        return 2
    if envoi and not (0x20 <= depart <= 0xFF):
        print("séquence hors 20–FF : rien envoyé.")
        return 2
    plafond = min(o.plafond, PLAFOND) if not envoi else o.plafond
    serie = borne(complet[o.depuis - 1:o.depuis - 1 + plafond], plafond)
    if not envoi:
        for i, (nom, donnees) in enumerate(complet, 1):
            print("%03d %s  %s" % (i, nom, donnees))
        print("%d trames à la grille. Séance %03d–%03d. Rien envoyé."
              % (len(complet), o.depuis, o.depuis + len(serie) - 1))
        return 0
    seq = [depart]
    if o.jumeau:
        if mcf is None:
            from simulateur.faux_mcf import FauxMCF
            mcf = FauxMCF(variante="FIS")
        envoyer = envoyer_jumeau(mcf, seq)
        delai = 0.0
    else:
        def envoyer(donnees):
            r = pousser(o.port, seq[0], donnees)
            seq[0] = suivant(seq[0])
            return r
        delai = o.delai

    def heure():
        return time.strftime("%H:%M:%S")

    print("%s GRILLE : %d trames, une toutes les %.0f s. Arrêt au premier écart."
          % (heure(), len(serie), delai), flush=True)

    def tracer(i, nom, motif):
        print("%s %03d %s  %s" % (heure(), o.depuis + i, nom, motif), flush=True)

    resultat = jouer(serie, envoyer, delai, tracer=tracer)
    if resultat is None:
        print("terminé : %d trames, message connu partout." % len(serie))
        prochain = o.depuis + len(serie)
        if prochain <= len(complet):
            print("suite : --depuis %d" % prochain)
        return 0
    print("ARRÊT %s  données=%r  %s" % resultat)
    return 1


if __name__ == "__main__":
    sys.exit(main())
