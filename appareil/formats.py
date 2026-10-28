"""Données des commandes de facture au format « Niger », celui qu'accepte le MCF pour C0.

Reproduit la construction d'ECOHADA MCF CLI 23.04081, lue dans le binaire
(recherche/2026-10-10_carte_ecohada_cli.md) : C3 fcn.0040f5f0, C0 fcn.00409fb0,
31 fcn.004096b0 et ses montants fcn.00411ea0 (0x4127cb-0x4128d1), 35 fcn.0040aa70,
échappement fcn.004155a0.
"""
import math

MODES_PAIEMENT = "VCMDEA"


def echapper(texte):
    # Ordre et correspondances du binaire, fins de ligne croisées comprises.
    for avant, apres in (("\r", "^xa;"), ("\n", "^xd;"), (",", "^x2c;"),
                         ("<", "^lt;"), (">", "^gt;"), ("&", "^amp;"), ("'", " ")):
        texte = texte.replace(avant, apres)
    return texte


def arrondi(x):
    """round() du C (demi vers le haut, loin de zéro) puis « %.0f »."""
    return "%.0f" % math.copysign(math.floor(abs(x) + 0.5), x)


def article(nom, groupe, taux, prix, quantite, taxe=0.0, code="", specifique=None):
    """31 : nom[\\ncode]<TAB><groupe><taux lu par C1>%<montant><TAB><prix>*<quantité>[;T<a>,<b>].

    Le montant est round(prix × quantité + taxe) : le total de la ligne, pas la taxe seule.
    Le prix est TTC ou HT selon le mode de prix de C0 ; la taxe ajoutée est la colonne 7 du CSV
    d'ECOHADA en TTC, la colonne 6 en HT. `specifique` = (col 5, col 6), recopiées après ";T".
    Vérifié en exécution le 2026-10-10 (recherche/2026-10-10_execution_ecohada.md).
    """
    d = echapper(nom[:64])
    if code:
        d += "\n" + echapper(code[:24])
    montant = arrondi(float(prix) * float(quantite) + float(taxe))
    d = "%s\t%s%s%%%s\t%s*%s" % (d, groupe, taux, montant, arrondi(float(prix)), quantite)
    if specifique:
        d += ";T%s,%s" % specifique
    return d


def commentaire(cle, texte):
    """36 : clé (A à H) et texte ; ECOHADA ignore sans message une autre clé."""
    return echapper(cle) + "," + echapper(texte)


def c0(id_vendeur, nom_vendeur, ifu, type_facture, reference, mode_prix="TTC",
       isf="ECOHADA", origine="", taux=""):
    d = "%s,%s,%s,%s" % (echapper(id_vendeur), echapper(nom_vendeur), echapper(ifu), type_facture)
    if origine:
        d += "," + echapper(origine)
    d += ",%s,%s,%s" % (mode_prix, isf, reference)
    if taux:
        d += "," + echapper(taux)
    return d


def c3(ifu_client, nom_client, type_client, champ4="", champ5=""):
    return ",".join(echapper(x) for x in (ifu_client, nom_client, type_client, champ4, champ5))


def paiement(mode, montant):
    """35 : mode collé au montant (premier champ de la réponse de 33)."""
    return echapper(mode if mode in MODES_PAIEMENT and len(mode) == 1 else "A") + echapper(montant)
