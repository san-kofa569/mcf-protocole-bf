"""Une facture entière, commande après commande : client de référence du cycle, sur le jumeau ou l'appareil.

Le cycle prouvé le 2026-10-28 (docs/REFERENCE_PROTOCOLE.md §4–5) : C3, C0 avec PSVB, une 31 par ligne, 33,
35, 38 avec le total du 33. Chaque réponse est contrôlée ; à la première qui n'a pas la forme attendue, arrêt :
la facture reste ouverte et un C1 l'annule. La réponse du 38 (NIM, IFU, signature) n'est jamais affichée :
seulement ses compteurs et son nombre de champs.

Le 35 répond `R0` quand tout est payé, `R-114.2` quand 114.2 reste dû. L'appareil accepte un montant négatif
et certifie au 38 une facture qui n'est pas soldée (2026-10-28, 14:44) : c'est donc ici qu'on le refuse. Aucun
paiement nul ou négatif ne part, et le 38 ne part qu'après un `R0`.

Scénarios :
  simple      un bien en groupe B, payé en espèces (la facture du 28 octobre) ;
  deux        un bien (B, 18 %) et un service (C, 10 %), payés en mobile money puis en espèces pour le reste :
              plusieurs lignes, PSVB sur un service, mode M, paiement partiel ;
  annulation  un bien payé, puis 38 `C` (forme d'annulation de la RDC) : sonde, la réponse arrête le scénario.

Usage :
  python3 -m appareil.cycle --scenario simple --fn ESSAI-0009 --liste
  python3 -m appareil.cycle --scenario simple --fn ESSAI-0009 --jumeau
  python3 -m appareil.cycle --scenario deux --fn ESSAI-0009 --port /dev/ttyACM0 --seq 20

Sur l'appareil : MCF_IFU exporté (9 caractères), application fiscale au premier plan, une trame toutes les
3 s, accord de l'opérateur. Un 38 accepté émet une facture certifiée : un FN jamais utilisé à chaque fois.
"""
import argparse
import os
import re
import sys
import time

from appareil.recherche_bornee import pousser, suivant
from appareil.trame import bcc_ok, paquet, remplir

DELAI = 3.0
CLIENT = "PP,CLIENT TEST,,,70123456,client@example.com,"
BIEN = "ARTICLE TEST\tLOCBIE,B18.0%100.00\t100.00*1"
SERVICE = "POSE TEST\tLOCSER,C10.0%110.00\t110.00*1"

NOMBRE = r"-?\d+(?:\.\d+)?"
FORMES = {
    0xC3: r"R",
    0xC0: r"\d+,\d+(?:,[^,]*){6}",
    0x31: r"%s(?:,%s){3}" % (NOMBRE, NOMBRE),
    0x33: r"%s(?:,%s){34}" % (NOMBRE, NOMBRE),
    0x35: r"R%s" % NOMBRE,
    0x38: r"\d+,\d+,[A-Z]{2},\d{14},[^,]+,[^,]+,[A-Z0-9]{24},[^,]+",
}


def montant(v):
    return "%.2f" % v


def etapes(scenario, fn):
    """(nom, commande, données) ; les données sont une fonction de l'état quand elles dépendent d'une réponse."""
    debut = [("client", 0xC3, CLIENT), ("ouverture", 0xC0, "1,Essai,{IFU},FV,TTC,ISF-ESSAI,%s,A" % fn)]
    if scenario == "simple":
        return debut + [("article", 0x31, BIEN), ("sous-total", 0x33, ""),
                        ("paiement", 0x35, lambda e: "E" + montant(e["total"])),
                        ("normalisation", 0x38, lambda e: montant(e["total"]))]
    if scenario == "deux":
        return debut + [("bien", 0x31, BIEN), ("service", 0x31, SERVICE), ("sous-total", 0x33, ""),
                        ("mobile", 0x35, "M100.00"),
                        ("reste", 0x35, lambda e: "E" + montant(e["du"])),
                        ("normalisation", 0x38, lambda e: montant(e["total"]))]
    if scenario == "annulation":
        return debut + [("article", 0x31, BIEN), ("sous-total", 0x33, ""),
                        ("paiement", 0x35, lambda e: "E" + montant(e["total"])),
                        ("sonde", 0x38, "C")]
    raise ValueError(scenario)


def lire(recu):
    """(données, motif) : données None si la réponse n'est pas une trame lisible."""
    if recu is None:
        return None, "déconnexion"
    if not recu:
        return None, "silence"
    debut = recu[:recu.index(1)] if 1 in recu else recu
    if b"\x15" in debut:
        p = paquet(recu)
        return None, "NAK" + (", statut " + p[1].hex(" ") if p else "")
    p = paquet(recu)
    if p is None or bcc_ok(recu) is not True:
        return None, "trame illisible"
    return p[0].decode("utf-8", "replace"), ""


def montrer(cmd, donnees):
    """Ce qui s'affiche d'une réponse : la clôture réduite à ses compteurs."""
    if cmd == 0x38 and re.fullmatch(FORMES[0x38], donnees):
        f = donnees.split(",")
        return "accepté : 8 champs, compteurs %s/%s %s (NIM, IFU, signature dans la capture)" % (f[0], f[1], f[2])
    return donnees


def jouer(scenario, fn, envoyer, delai=0.0, tracer=print):
    """Déroule le scénario. Rend 0 si tout a la forme attendue, 1 à l'arrêt (sonde comprise)."""
    etat = {}
    for i, (nom, cmd, donnees) in enumerate(etapes(scenario, fn)):
        if i and delai:
            time.sleep(delai)
        d = donnees(etat) if callable(donnees) else donnees
        if cmd == 0x35 and not (re.fullmatch(r"[A-Z]\d+\.\d{2}", d) and float(d[1:]) > 0):
            tracer("%s %02X %r : ARRÊT avant envoi, paiement nul ou négatif." % (nom, cmd, d))
            return 1
        if cmd == 0x38 and nom != "sonde" and etat.get("du") != 0:
            tracer("%s %02X %r : ARRÊT avant envoi, la facture n'est pas soldée (reste %s)." % (nom, cmd, d, etat.get("du")))
            return 1
        r, motif = lire(envoyer(cmd, d))
        if r is None:
            tracer("%s %02X %r : ARRÊT, %s" % (nom, cmd, d, motif))
            return 1
        tracer("%s %02X %r -> %s" % (nom, cmd, d, montrer(cmd, r)))
        if nom == "sonde":
            return 1
        if not re.fullmatch(FORMES[cmd], r):
            tracer("ARRÊT : réponse inattendue ; la facture reste ouverte (C1 l'annule).")
            return 1
        if cmd == 0x33:
            etat["total"] = float(r.split(",")[0])
        if cmd == 0x35:
            reste = float(r[1:])
            if reste > 0:
                tracer("ARRÊT : reste positif %s, jamais vu (rendu de monnaie ?)." % r)
                return 1
            etat["du"] = round(-reste, 2) if reste else 0
    return 0


def main(argv=None, mcf=None):
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("--scenario", choices=("simple", "deux", "annulation"), required=True)
    a.add_argument("--fn", required=True, help="référence de la facture, jamais réutilisée (ESSAI-0009…)")
    a.add_argument("--liste", action="store_true", help="afficher les trames, ne rien envoyer")
    a.add_argument("--jumeau", action="store_true", help="jouer contre le jumeau FIS")
    a.add_argument("--port", help="port série de l'appareil")
    a.add_argument("--seq", default="20", help="séquence hexadécimale de départ (défaut 20)")
    o = a.parse_args(argv)
    try:
        depart = int(o.seq, 16)
    except ValueError:
        print("séquence illisible : rien envoyé.")
        return 2
    if not (0x20 <= depart <= 0xFF):
        print("séquence hors 20–FF : rien envoyé.")
        return 2
    if o.liste or not (o.jumeau or o.port):
        for nom, cmd, d in etapes(o.scenario, o.fn):
            print("%-13s %02X %s" % (nom, cmd, "(selon la réponse précédente)" if callable(d) else repr(d)))
        print("Rien envoyé.")
        return 0
    seq = [depart]
    if o.jumeau:
        if mcf is None:
            from simulateur.faux_mcf import FauxMCF
            mcf = FauxMCF(variante="FIS")

        def envoyer(cmd, d):
            r = mcf.repondre(seq[0], cmd, d.encode("utf-8"))
            seq[0] = suivant(seq[0])
            return r
        delai = 0.0
    else:
        if remplir("{IFU}", os.environ) is None:  # avant le C3 : sinon il partirait seul
            print("MCF_IFU absent ou invalide (9 caractères) : rien envoyé.")
            return 2

        def envoyer(cmd, d):
            r = pousser(o.port, seq[0], d, cmd=cmd)
            seq[0] = suivant(seq[0])
            return r
        delai = DELAI
    print("%s cycle %s, FN %s, %s" % (time.strftime("%H:%M:%S"), o.scenario, o.fn,
                                      "jumeau" if o.jumeau else o.port), flush=True)
    return jouer(o.scenario, o.fn, envoyer, delai, tracer=lambda t: print(time.strftime("%H:%M:%S ") + t, flush=True))


if __name__ == "__main__":
    sys.exit(main())
