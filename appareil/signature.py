"""Signature d'une facture certifiée, lue dans une capture brute, pour `export MCF_SIG=$(…)`.

La signature d'une facture est dans la réponse de son 38 (7e champ ; le 1er est le numéro de la facture dans
son type) et dans celle de chaque C1 qui suit, tant qu'aucune autre n'a été certifiée (9e champ ; le 8e est le
type, le 10e le numéro). Captures lues : celles de `trame.py` et de `cycle.py` (ligne `envoi :` puis `données :`).
N'écrit que la signature, rien d'autre ; introuvable : rien sur la sortie, code 1.

Usage : export MCF_SIG=$(python3 -m appareil.signature appareil/brut/2026-10-28_seance.txt --numero 2)
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


def main(argv=None):
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("capture")
    a.add_argument("--numero", required=True, help="numéro de la facture dans son type (1er champ du 38)")
    a.add_argument("--type", default="FV")
    o = a.parse_args(argv)
    with open(o.capture, encoding="utf-8", errors="replace") as f:
        s = signature(f.read().splitlines(), o.numero, o.type)
    if s is None:
        print("signature de la facture %s n°%s introuvable dans %s" % (o.type, o.numero, o.capture), file=sys.stderr)
        return 1
    print(s)
    return 0


if __name__ == "__main__":
    sys.exit(main())
