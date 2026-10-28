"""Signature d'une facture certifiée, lue dans une capture brute, pour `export MCF_SIG=$(…)`.

La signature d'une facture est dans la réponse de son 38 (7e champ ; le 1er est le numéro de la facture dans
son type) et dans celle de chaque C1 qui suit, tant qu'aucune autre n'a été certifiée (9e champ ; le 8e est le
type, le 10e le numéro). Captures lues : celles de `trame.py` et de `cycle.py` (ligne `envoi :` puis `données :`).
N'écrit que la signature, rien d'autre ; introuvable : rien sur la sortie, code 1. Avec --nim, l'identifiant
de l'appareil (`NIM-ACNT`, 1er champ du dernier C1 ou 5e du dernier 38), pour MCF_NIM.

Usage : export MCF_SIG=$(python3 -m appareil.signature appareil/brut/2026-10-28_seance.txt --numero 2)
        export MCF_NIM=$(python3 -m appareil.signature appareil/brut/2026-10-28_seance.txt --nim)
"""
import argparse
import re
import sys

SIG = re.compile(r"[A-Z0-9]{24}")


def reponses(lignes):
    """(commande, données) de chaque réponse lue, dans l'ordre de la capture."""
    cmd = None
    for l in lignes:
        if " envoi : " in l:
            octets = l.split(" envoi : ", 1)[1].split()
            cmd = int(octets[3], 16) if len(octets) > 3 else None
        elif l.startswith("données : ") and cmd is not None:
            yield cmd, l[len("données : "):]
            cmd = None


def signature(lignes, numero, type_="FV"):
    """La dernière signature connue de la facture `numero` du type donné ; None si absente."""
    trouvee = None
    for cmd, d in reponses(lignes):
        f = d.split(",")
        if cmd == 0x38 and len(f) == 8 and f[0] == numero and f[2] == type_ and SIG.fullmatch(f[6]):
            trouvee = f[6]
        elif cmd == 0xC1 and len(f) == 31 and f[9] == numero and f[7] == type_ and SIG.fullmatch(f[8]):
            trouvee = f[8]
    return trouvee


def identifiant(lignes):
    """Le dernier identifiant `NIM-ACNT` lu (C1 1er champ, 38 5e champ) ; None si absent."""
    trouve = None
    for cmd, d in reponses(lignes):
        f = d.split(",")
        v = f[0] if cmd == 0xC1 and len(f) == 31 else f[4] if cmd == 0x38 and len(f) == 8 else None
        if v and re.fullmatch(r"[A-Z]{2}\d{8}-\d+", v):
            trouve = v
    return trouve


def main(argv=None):
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("capture")
    a.add_argument("--numero", help="numéro de la facture dans son type (1er champ du 38)")
    a.add_argument("--nim", action="store_true", help="écrire l'identifiant NIM-ACNT au lieu d'une signature")
    a.add_argument("--type", default="FV")
    o = a.parse_args(argv)
    if not o.nim and not o.numero:
        a.error("--numero ou --nim")
    with open(o.capture, encoding="utf-8", errors="replace") as f:
        lignes = f.read().splitlines()
    s = identifiant(lignes) if o.nim else signature(lignes, o.numero, o.type)
    if s is None:
        quoi = "identifiant NIM-ACNT" if o.nim else "signature de la facture %s n°%s" % (o.type, o.numero)
        print("%s introuvable dans %s" % (quoi, o.capture), file=sys.stderr)
        return 1
    print(s)
    return 0


if __name__ == "__main__":
    sys.exit(main())
