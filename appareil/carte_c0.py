"""Carte des contrôles de C0 : un jeton à chaque place, puis types, modes et nombres de champs.

La carte de C3 (2026-10-15) a montré que les contrôles de valeur d'un champ répondent par un message
à part, alors que 31 n'en a qu'un. C0 n'a pas été cartographié : il accepte le format Niger à sept
champs, un huitième champ, et refuse les formes béninoises. Si C0 attend un champ de plus pour que
31 soit « compatible », un contrôle de valeur de C0 peut le dire.

Base : `1,Essai,{IFU},FV,TTC,ISF-ESSAI,ESSAI-0015` (opérateur, nom, IFU, type, mode, ISF, référence).
Chaque trame écarte la base d'un seul endroit. Ce n'est pas une chasse : aucun arrêt sur un message
nouveau, tous sont à relever. Arrêt au NAK, au silence, à la déconnexion ou à une trame illisible.
Attention : le 2026-10-09, un premier refus de C0 a été suivi d'un départ de l'appareil de l'USB
pendant deux heures (cause non établie) ; le script s'arrête alors sur « déconnexion ».

Rien n'est envoyé par défaut. {IFU} est remplacé par MCF_IFU (9 caractères), comme trame.py.

Usage :
  python3 -m appareil.carte_c0 --liste
  python3 -m appareil.carte_c0 --jumeau
  python3 -m appareil.carte_c0 --port /dev/ttyACM0 --seq 50

Sur l'appareil : une trame toutes les 3 s, 30 au plus. EazSell au premier plan, accord de l'opérateur.
"""
import argparse
import sys
import time

from appareil.carte_client import jouer
from appareil.recherche_bornee import DELAI, envoyer_jumeau, pousser, suivant

BASE = ["1", "Essai", "{IFU}", "FV", "TTC", "ISF-ESSAI", "ESSAI-0015"]
TYPES = ("FT", "FA", "EV", "ET", "EA")
PLAFOND = 30


def sondes():
    """(nom, données) : un écart à la base par trame."""
    for place in range(1, 8):
        champs = list(BASE)
        champs[place - 1] = "x"
        yield "x@%d" % place, ",".join(champs)
    for t in TYPES:
        champs = list(BASE)
        champs[3] = t
        yield "type=%s" % t, ",".join(champs)
    for nom, place, valeur in (("mode=HT", 5, "HT"), ("mode=vide", 5, ""),
                               ("isf=vide", 6, ""), ("ref=vide", 7, "")):
        champs = list(BASE)
        champs[place - 1] = valeur
        yield nom, ",".join(champs)
    for n in (5, 6):
        yield "champs=%d" % n, ",".join(BASE[:n])
    for n in (8, 9, 10, 12):
        yield "champs=%d" % n, ",".join(BASE + ["x"] * (n - 7))


def main(argv=None, mcf=None):
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("--liste", action="store_true", help="afficher la carte, ne rien envoyer")
    a.add_argument("--jumeau", action="store_true", help="jouer contre le jumeau FIS, pas l'appareil")
    a.add_argument("--port", help="port série de l'appareil ; sans --jumeau ni --liste, exige ce port")
    a.add_argument("--seq", default="50", help="séquence hexadécimale de départ (défaut 50)")
    a.add_argument("--delai", type=float, default=DELAI)
    o = a.parse_args(argv)
    try:
        depart = int(o.seq, 16)
    except ValueError:
        print("séquence illisible : rien envoyé.")
        return 2
    serie = list(sondes())
    envoi = (o.jumeau or o.port) and not o.liste
    if envoi and not (0x20 <= depart <= 0xFF):
        print("séquence hors 20–FF : rien envoyé.")
        return 2
    if len(serie) > PLAFOND:
        print("%d trames, plafond %d : rien envoyé." % (len(serie), PLAFOND))
        return 2
    if not envoi:
        for i, (nom, donnees) in enumerate(serie, 1):
            print("%02d %-10s %s" % (i, nom, donnees))
        print("%d trames. Rien envoyé." % len(serie))
        return 0
    seq = [depart]
    if o.jumeau:
        if mcf is None:
            from simulateur.faux_mcf import FauxMCF
            mcf = FauxMCF(variante="FIS")
        envoyer, delai = envoyer_jumeau(mcf, seq, 0xC0), 0.0
    else:
        def envoyer(donnees):
            r = pousser(o.port, seq[0], donnees, cmd=0xC0)
            seq[0] = suivant(seq[0])
            return r
        delai = o.delai

    def tracer(i, nom, donnees, reponse):
        print("%s %02d %-10s %-50s  %s" % (time.strftime("%H:%M:%S"), i + 1, nom, donnees, reponse), flush=True)

    print("%s CARTE C0 : %d trames, une toutes les %.0f s." % (time.strftime("%H:%M:%S"), len(serie), delai),
          flush=True)
    vues, motif = jouer(serie, envoyer, delai, tracer)
    if motif:
        print("ARRÊT après %d trames : %s" % (len(vues), motif))
        return 1
    print("terminé : %d trames." % len(vues))
    return 0


if __name__ == "__main__":
    sys.exit(main())
