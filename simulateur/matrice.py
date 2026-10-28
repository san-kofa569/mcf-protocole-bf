"""Matrice de variantes d'ECOHADA MCF CLI face au faux MCF, à lancer DANS le bac à sable.

Usage : simulateur/bac_a_sable.sh python3 -m simulateur.matrice [variante ...]
Chaque variante devient externe/wine/essais/m_<nom>/ (input.csv, app.xml) ; l'essai y dépose
console.txt et journal.txt. Le résumé des trames envoyées par ECOHADA va dans
externe/wine/essais/matrice.md. Valeurs fictives uniquement.
"""
import contextlib
import io
import os
import re
import sys

from simulateur import essai_ecohada

ESSAIS = os.path.join(essai_ecohada.RACINE, "externe", "wine", "essais")
ARTICLES = ["B;ARTICLE UN;2;1000;1180;;;", "A;ARTICLE DEUX;1;500;500;;;"]


def entete(ref, type_="FV", mode="E", client="Client Essai", ifu="", c7="PP", c8="Adresse Essai",
           c9="Contact Essai", taux="", origine=""):
    return ";".join([ref, type_, "Vendeur Essai", "1", mode, client, ifu, c7, c8, c9, taux, origine, ""])


# nom -> (attributs d'app.xml modifiés, lignes du CSV, garder la base de l'essai précédent)
VARIANTES = {
    "ttc_base": ({}, [entete("M-TTC")] + ARTICLES, False),
    "ht_base": ({"modePrix": "HT"}, [entete("M-HT")] + ARTICLES, False),
    "ts_ttc": ({}, [entete("M-TS-TTC"), "B;ARTICLE TS;2;1000;1180;50;59;;", "B;ARTICLE TS7;2;1000;1180;50;59;10;"],
               False),
    "ts_ht": ({"modePrix": "HT"}, [entete("M-TS-HT"), "B;ARTICLE TS;2;1000;1180;50;59;;",
                                   "B;ARTICLE TS7;2;1000;1180;50;59;10;"], False),
    "client_ifu": ({}, [entete("M-CLI", client="Societe Essai", ifu="9999999999999", c7="PM")] + ARTICLES, False),
    "client_vide": ({}, [entete("M-CLI0", client="", c7="", c8="", c9="")] + ARTICLES, False),
    "taux_a": ({}, [entete("M-TXA", taux="A")] + ARTICLES, False),
    "taux_b": ({}, [entete("M-TXB", taux="B")] + ARTICLES, False),
    "paiement_m": ({}, [entete("M-PM", mode="M")] + ARTICLES, False),
    "paiement_x": ({}, [entete("M-PX", mode="X")] + ARTICLES, False),
    "decimales": ({}, [entete("M-DEC"), "B;ARTICLE DEC;1.5;847.03;999.5;;;", "A;ARTICLE DEMI;3;0.5;0.5;;;"], False),
    "regime_vide": ({}, [entete("M-REG"), ";ARTICLE TVA;1;1000;1180;;;", ";ARTICLE SANS TVA;1;500;500;;;"], False),
    "echappement": ({}, [entete("M-ESC", client="Client, & <Essai>"),
                         "B;CAFÉ, l'essai & <test>;1;1000;1180;;;"], False),
    "commentaire": ({}, [entete("M-COM"), "#;A;Commentaire essai"] + ARTICLES, False),
    "commentaire_cle_i": ({}, [entete("M-COMI"), "#;I;Commentaire hors cle"] + ARTICLES, False),
    "avoir_origine": ({}, [entete("M-ORIG")] + ARTICLES, False),
    "avoir": ({}, [entete("M-AV", type_="FA", origine="M-ORIG")] + ARTICLES, True),
    "avoir_saisi": ({}, [entete("M-AV2", type_="FA", origine="XX99999999-7")] + ARTICLES, False),
}
APP = {"portMCF": "COM1", "modePrix": "TTC", "isf": "ISF-ESSAI", "pays": "Niger", "modeMCF": "Développement"}


def preparer(nom):
    app, lignes, garder = VARIANTES[nom]
    d = os.path.join(ESSAIS, "m_" + nom)
    os.makedirs(d, exist_ok=True)
    attributs = " ".join('%s="%s"' % kv for kv in dict(APP, **app).items())
    with open(os.path.join(d, "app.xml"), "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<config %s/>\n' % attributs)
    with open(os.path.join(d, "input.csv"), "w", encoding="utf-8") as f:
        f.write("\n".join(lignes) + "\n")
    return d, garder


def resumer(nom, d):
    """Trames reçues par le faux MCF (hors C1) et issue lue dans la console."""
    trames = []
    with open(os.path.join(d, "journal.txt"), encoding="utf-8") as j:
        for ligne in j:
            m = re.match(r"\S+ recu  (\w\w) seq=\w\w donnees=(.*) hex=", ligne)
            if m and m.group(1) != "C1":
                trames.append("`%s %s`" % (m.group(1), m.group(2).replace("|", "\\|")))
    with open(os.path.join(d, "console.txt"), encoding="latin-1") as c:
        console = c.read()
    issues = re.findall(r"^(Erreur:.*|Total facture (?:in)?acceptable.*|La facture a ete \w+\.|Facture non retrouvee.*"
                        r"|.*manquant\.|Cette facture est deja validee\.)$", console, re.M)
    return "| %s | %s | %s |" % (nom, "<br>".join(trames), "<br>".join(issues))


def main(argv=None):
    noms = (argv if argv is not None else sys.argv[1:]) or list(VARIANTES)
    lignes = ["| variante | trames envoyées par ECOHADA (hors C1) | issue |", "|---|---|---|"]
    for nom in noms:
        d, garder = preparer(nom)
        with contextlib.redirect_stdout(io.StringIO()):
            essai_ecohada.main([d] + (["--garder-base"] if garder else []))
        lignes.append(resumer(nom, d))
        print(lignes[-1], flush=True)
    with open(os.path.join(ESSAIS, "matrice.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lignes) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
