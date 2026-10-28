"""Contenu du code QR d'une facture certifiée, tiré de la réponse de son 38 — 🔍 HYPOTHÈSE à confirmer.

Le format burkinabè est « défini par l'Administration » (note 0887 §2.10.3 e) et n'est publié nulle part ; le reçu de
l'application fiscale n'en montre pas à l'écran (2026-10-28). Hypothèse : le gabarit de la famille SyGMEF qu'ECOHADA
écrit pour le Bénin comme pour le Niger (recherche/2026-10-10_carte_ecohada_cli.md) :

    F;{identifiant de machine};{signature};{IFU};{date AAAAMMJJhhmmss}

La RDC a le sien (`RDCDEF01;MID;SIG;NIF;DT`). Pour confirmer : scanner le QR d'un ticket imprimé par l'appareil, le
déposer dans appareil/brut/ et le comparer à la capture :

  python3 -m appareil.qr --comparer appareil/brut/2026-10-28_qr.txt --capture appareil/brut/2026-10-28_seance.txt --numero 1

La comparaison ne montre que la place de chaque morceau (quel champ du 38 il reprend), jamais NIM, IFU ni signature.

L'appareil n'affiche ni n'imprime de QR (reçu d'ESSAI-0008, 2026-10-28). Preuve par l'application officielle de la DGI
« FEC Burkina-Faso » (`verificationfec.apps.dgi.bf`), qui vérifie une facture en scannant son QR : --images écrit, pour
une facture de la capture, une image par variante dans appareil/brut/qr/ (hors dépôt) ; on les scanne une à une.

  python3 -m appareil.qr --images --capture appareil/brut/2026-10-28_seance.txt --numero 1
"""
import argparse
import os
import re
import sys

from appareil.signature import reponses

# Champs de la réponse du 38 (2026-10-28) : leur nom, dans l'ordre
CHAMPS_38 = ("numéro dans le type", "compteur total", "type", "date", "identifiant de machine", "IFU",
             "signature", "FN")


def contenu(reponse_38):
    """La chaîne du QR selon l'hypothèse ; ValueError si la réponse n'a pas ses 8 champs."""
    f = reponse_38.split(",")
    if len(f) != 8:
        raise ValueError("réponse du 38 à %d champs, 8 attendus" % len(f))
    return "F;%s;%s;%s;%s" % (f[4], f[6], f[5], f[3])


def reponse_38(lignes, numero, type_="FV"):
    """La réponse du 38 de la facture `numero` de ce type, lue dans une capture ; None si absente."""
    trouvee = None
    for cmd, d in reponses(lignes):
        f = d.split(",")
        if cmd == 0x38 and len(f) == 8 and f[0] == numero and f[2] == type_:
            trouvee = d
    return trouvee


VARIANTES = (
    ("A", "F;identifiant;signature;IFU;date (gabarit ECOHADA Bénin et Niger)"),
    ("B", "F;NIM sans le compteur d'activation;signature;IFU;date"),
    ("C", "identifiant;signature;IFU;date, sans le préfixe F"),
    ("D", "F;identifiant;signature en groupes de 4 à tirets;IFU;date"),
)


def variante(lettre, reponse):
    """Le texte de la variante `lettre` pour cette réponse du 38."""
    f = reponse.split(",")
    ident, sig, ifu, date = f[4], f[6], f[5], f[3]
    if lettre == "B":
        ident = ident.rsplit("-", 1)[0]
    if lettre == "D":
        sig = "-".join(sig[i:i + 4] for i in range(0, 24, 4))
    corps = "%s;%s;%s;%s" % (ident, sig, ifu, date)
    return corps if lettre == "C" else "F;" + corps


def images(reponse, dossier):
    """Une image PNG par variante dans `dossier` ; rend [(lettre, chemin, description)]."""
    import qrcode
    os.makedirs(dossier, exist_ok=True)
    faites = []
    for lettre, description in VARIANTES:
        chemin = os.path.join(dossier, "%s.png" % lettre)
        qrcode.make(variante(lettre, reponse)).save(chemin)
        faites.append((lettre, chemin, description))
    return faites


def comparer(scanne, reponse):
    """Lignes de description : séparateur, puis la place de chaque morceau, sans valeur sensible."""
    sep = next((s for s in (";", "|", ",", "\t") if s in scanne), None)
    f = reponse.split(",")
    lignes = ["séparateur : %r ; %d morceaux" % (sep, len(scanne.split(sep)) if sep else 1)]
    for i, morceau in enumerate(scanne.split(sep) if sep else [scanne], 1):
        places = [CHAMPS_38[j] for j, v in enumerate(f) if v and v == morceau]
        if places:
            lignes.append("%d : = %s du 38" % (i, " ou ".join(places)))
        elif re.fullmatch(r"[A-Za-z0-9]{1,10}", morceau) and not re.search(r"\d{5,}", morceau):
            lignes.append("%d : littéral %r" % (i, morceau))
        else:
            forme = re.sub(r"[A-Za-z]", "A", re.sub(r"\d", "9", morceau))
            lignes.append("%d : autre (%d caractères, forme %s)" % (i, len(morceau), forme))
    lignes.append("identique à l'hypothèse F;identifiant;signature;IFU;date : %s" % ("oui" if scanne == contenu(reponse) else "non"))
    return lignes


def main(argv=None):
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("--comparer", help="fichier du QR scanné (une ligne)")
    a.add_argument("--images", action="store_true", help="écrire une image par variante dans appareil/brut/qr/")
    a.add_argument("--dossier", default=os.path.join("appareil", "brut", "qr"))
    a.add_argument("--capture", required=True, help="capture où se trouve la réponse du 38")
    a.add_argument("--numero", required=True, help="numéro de la facture dans son type")
    a.add_argument("--type", default="FV")
    o = a.parse_args(argv)
    if o.images:
        with open(o.capture, encoding="utf-8", errors="replace") as f:
            r = reponse_38(f.read().splitlines(), o.numero, o.type)
        if r is None:
            print("réponse du 38 de la facture %s n°%s introuvable dans la capture" % (o.type, o.numero))
            return 1
        for lettre, chemin, description in images(r, o.dossier):
            print("%s  %s  — %s" % (lettre, chemin, description))
        print("Scanner chacune avec l'application « FEC Burkina-Faso » et noter sa réponse.")
        return 0
    if not o.comparer:
        a.error("--comparer ou --images")
    if not os.path.isfile(o.comparer):
        print("%s absent : scanner d'abord le QR d'un ticket imprimé par l'appareil, puis coller son texte dans ce "
              "fichier (par exemple : cat > %s, coller, Entrée, Ctrl-D)." % (o.comparer, o.comparer))
        return 2
    with open(o.comparer, encoding="utf-8", errors="replace") as f:
        scanne = f.read().strip()
    if not scanne:
        print("%s est vide : rien à comparer." % o.comparer)
        return 2
    with open(o.capture, encoding="utf-8", errors="replace") as f:
        r = reponse_38(f.read().splitlines(), o.numero, o.type)
    if r is None:
        print("réponse du 38 de la facture %s n°%s introuvable dans la capture" % (o.type, o.numero))
        return 1
    print("\n".join(comparer(scanne, r)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
