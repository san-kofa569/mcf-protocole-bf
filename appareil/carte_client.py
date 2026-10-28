"""Carte des contrôles de C3 à sept champs : un jeton à chaque place, le reste neutre.

Le 2026-10-15, `PP,PP,PP,PP,PP,PP,PP` a donné « l'adresse e-mail du destinataire n'est pas valide »,
et `PP,CLIENT TEST,,,,,` a donné `R`. Chaque trame de cette carte met un seul jeton à la place p
d'une base `PP,CLIENT TEST,,,,,` ; le message obtenu est celui du contrôle qui lit cette place.
Ce n'est pas une chasse : aucun arrêt sur un message nouveau, tous sont à relever, avec la place.
Arrêt au NAK, au silence, à la déconnexion ou à une trame illisible. Rien n'est envoyé par défaut.

Usage :
  python3 -m appareil.carte_client --liste
  python3 -m appareil.carte_client --jumeau
  python3 -m appareil.carte_client --port /dev/ttyACM0 --seq F0

Sur l'appareil : une trame toutes les 3 s, 30 au plus. EazSell au premier plan, aucune facture
ouverte (sinon NAK), accord de l'opérateur, une séance à la fois.
"""
import argparse
import sys
import time

from appareil.recherche_bornee import DELAI, envoyer_jumeau, pousser, suivant
from appareil.trame import bcc_ok, paquet

BASE = ["PP", "CLIENT TEST", "", "", "", "", ""]
JETONS = (
    ("x", "x"),                       # invalide partout où une syntaxe est contrôlée
    ("mail", "client@example.com"),   # syntaxe d'e-mail valide, domaine réservé à la documentation
    ("tel", "70123456"),              # huit chiffres
)
PLACES = (3, 4, 5, 6, 7)
PLAFOND = 30


def sondes():
    """(nom, données) : `x` aux places 1 et 2 (type et nom), puis chaque jeton aux places 3 à 7."""
    for place in (1, 2):
        champs = list(BASE)
        champs[place - 1] = "x"
        yield "x@%d" % place, ",".join(champs)
    for nom, jeton in JETONS:
        for place in PLACES:
            champs = list(BASE)
            champs[place - 1] = jeton
            yield "%s@%d" % (nom, place), ",".join(champs)


def lire(recu):
    """(arret, motif, données) ; données en texte (l'appareil répond en UTF-8)."""
    if recu is None:
        return True, "déconnexion", ""
    if not recu:
        return True, "silence", ""
    debut = recu[:recu.index(1)] if 1 in recu else recu
    if b"\x15" in debut:
        return True, "NAK", ""
    p = paquet(recu)
    if p is None or bcc_ok(recu) is not True:
        return True, "trame illisible", ""
    return False, "", p[0].decode("utf-8", "replace") or "(vide)"


def jouer(serie, envoyer, delai=0.0, tracer=None, horloge=time.monotonic, dormir=time.sleep):
    """Envoie toute la série, sauf arrêt. Rend la liste (nom, données, réponse) et le motif d'arrêt."""
    vues, precedent = [], None
    for i, (nom, donnees) in enumerate(serie):
        if precedent is not None and delai:
            dormir(max(0.0, delai - (horloge() - precedent)))
        precedent = horloge()
        arret, motif, texte = lire(envoyer(donnees))
        if arret:
            if tracer:
                tracer(i, nom, donnees, "ARRÊT : " + motif)
            return vues, motif
        vues.append((nom, donnees, texte))
        if tracer:
            tracer(i, nom, donnees, texte)
    return vues, None


def main(argv=None, mcf=None):
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("--liste", action="store_true", help="afficher la carte, ne rien envoyer")
    a.add_argument("--jumeau", action="store_true", help="jouer contre le jumeau FIS, pas l'appareil")
    a.add_argument("--port", help="port série de l'appareil ; sans --jumeau ni --liste, exige ce port")
    a.add_argument("--seq", default="F0", help="séquence hexadécimale de départ (défaut F0)")
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
            print("%02d %-8s %s" % (i, nom, donnees))
        print("%d trames. Rien envoyé." % len(serie))
        return 0
    seq = [depart]
    if o.jumeau:
        if mcf is None:
            from simulateur.faux_mcf import FauxMCF
            mcf = FauxMCF(variante="FIS")
        envoyer, delai = envoyer_jumeau(mcf, seq), 0.0
    else:
        def envoyer(donnees):
            r = pousser(o.port, seq[0], donnees)
            seq[0] = suivant(seq[0])
            return r
        delai = o.delai

    def tracer(i, nom, donnees, reponse):
        print("%s %02d %-8s %-24s  %s" % (time.strftime("%H:%M:%S"), i + 1, nom, donnees, reponse), flush=True)

    print("%s CARTE : %d trames, une toutes les %.0f s." % (time.strftime("%H:%M:%S"), len(serie), delai),
          flush=True)
    vues, motif = jouer(serie, envoyer, delai, tracer)
    if motif:
        print("ARRÊT après %d trames : %s" % (len(vues), motif))
        return 1
    print("terminé : %d trames." % len(vues))
    return 0


if __name__ == "__main__":
    sys.exit(main())
