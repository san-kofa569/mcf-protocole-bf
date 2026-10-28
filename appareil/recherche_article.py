"""Recherche bornée du nombre de champs de 31 (article) : un jeton répété à toutes les places.

Le 2026-10-15, la carte de C3 a montré que son message de format n'est pas un contrôle de valeur :
« Erreur de type de destinataire » répond à tout ce qui n'a pas sept champs ; à sept champs, les
contrôles de valeur parlent (e-mail, téléphone). 31 ne répond qu'un message de format, jamais
autre chose, après dix-sept formes en tabulations, à trois champs ou sept. Même idée : un jeton
répété à toutes les places d'une trame de n champs, séparés par une virgule ou une tabulation ;
le premier message différent désigne le bon nombre de champs.

Les jetons : « 1 » (valable en nom, code, prix, quantité), « B » (nom, code, groupe de taxe),
« LOCBIE » (nom, type d'article). Un contrôle de valeur qui échoue après la longueur répond
autre chose que le message de format.

Rien n'est envoyé par défaut. Une facture doit être ouverte (C0 accepté), sinon l'appareil
répond « C0 en premier » : message nouveau, arrêt immédiat, sans dommage.

Résultat du 2026-10-15 (grille « nombres ») : 78 trames, toutes au message de format. La grille
« gabarits » prend des noyaux d'article valides et y colle le type d'article et l'unité (séance 1,
80 trames sur le noyau Niger : toutes au message de format). La grille « photo » met des valeurs
complètes dans l'ordre de la ligne d'article de la facture de test de la DGI.

Usage :
  python3 -m appareil.recherche_article --liste [--grille gabarits]
  python3 -m appareil.recherche_article --jumeau
  python3 -m appareil.recherche_article --port /dev/ttyACM0 --seq 70 --grille gabarits [--depuis 81]

Sur l'appareil : une trame toutes les 3 s, 80 au plus, arrêt au premier message nouveau, au NAK,
au silence ou à la déconnexion. EazSell au premier plan, accord de l'opérateur, une séance à la fois.
"""
import argparse
import sys
import time
from pathlib import Path

from appareil.recherche_bornee import (
    DELAI, PLAFOND, borne, envoyer_jumeau, jouer, pousser, suivant,
)

ATTENDU = "E:Erreur de format des données ou incompatibilité"
JETONS = ("1", "B", "LOCBIE")
SEPARATEURS = ((",", "virgule"), ("\t", "tab"))
NOMBRES = tuple(range(2, 15))


def grille():
    """(nom, données) : sept champs d'abord (Burkina comme C3), puis par distance à sept."""
    for n in sorted(NOMBRES, key=lambda n: (abs(n - 7), n)):
        for sep, nom_sep in SEPARATEURS:
            for jeton in JETONS:
                yield "%s%dx%s" % (nom_sep, n, jeton), sep.join([jeton] * n)


# Noyaux d'article valides : Niger (ECOHADA), Bénin (forme simple), Datecs à décimales.
CORES = (
    ("niger", ("ARTICLE TEST", "B18.0%100", "100*1")),
    ("benin", ("ARTICLE TEST", "B100*1")),
    ("datecs", ("ARTICLE TEST", "B100.00*1.000")),
)
# Ce que le Burkina ajoute : type d'article, unité, dans les deux ordres.
EXTENSIONS = (("T", ["LOCBIE"]), ("U", ["U"]), ("TU", ["LOCBIE", "U"]), ("UT", ["U", "LOCBIE"]))
DELIMITEURS = (("tab", "\t"), ("pv", ";"), ("virg", ","), ("lf", "\n"), ("barre", "|"))


def gabarits():
    """(nom, données) : un noyau valide et une extension collée à une place, avec un délimiteur.

    Les places viennent dans l'ordre : fin, début, puis entre les parties du noyau. Les parties du
    noyau restent séparées par une tabulation ; le délimiteur ne joint que l'extension.
    """
    vus = set()
    for nom_c, parties in CORES:
        for place in [len(parties), 0] + list(range(1, len(parties))):
            for nom_e, ext in EXTENSIONS:
                for nom_d, d in DELIMITEURS:
                    e = d.join(ext)
                    gauche, droite = "\t".join(parties[:place]), "\t".join(parties[place:])
                    if place == len(parties):
                        donnees = gauche + d + e
                    elif place == 0:
                        donnees = e + d + droite
                    else:
                        donnees = gauche + d + e + d + droite
                    if donnees not in vus:
                        vus.add(donnees)
                        yield "%s/%s/%s@%d" % (nom_c, nom_e, nom_d, place), donnees


# La ligne d'article de la facture de test de la DGI : désignation, [groupe] [type], prix, quantité,
# montant. Des valeurs complètes dans l'ordre de la photo (et quelques voisins), pas un jeton répété.
CHAMPS_PHOTO = {"N": "ARTICLE TEST", "C": "ART001", "G": "B", "T": "LOCBIE", "U": "U"}
ORDRES_PHOTO = ("NGTPQ", "NGTPQM", "CNGTPQ", "CNGTPQM", "NCGTPQ", "NGTPQU", "NTGPQ", "NGTQP", "GTNPQ")
NOMBRES_PHOTO = (
    ("simple", {"P": "100", "Q": "1", "M": "100"}),
    ("decimales", {"P": "100.00", "Q": "1.000", "M": "100.00"}),
)
SEPARATEURS_PHOTO = (("virg", ","), ("tab", "\t"), ("pv", ";"), ("lf", "\n"))


def photo():
    """(nom, données) : un enregistrement complet dans l'ordre de la photo, par séparateur et format."""
    for ordre in ORDRES_PHOTO:
        for nom_n, nombres in NOMBRES_PHOTO:
            for nom_s, sep in SEPARATEURS_PHOTO:
                champs = dict(CHAMPS_PHOTO, **nombres)
                yield "%s/%s/%s" % (ordre, nom_s, nom_n), sep.join(champs[c] for c in ordre)


ESSAIS = Path(__file__).resolve().parent / "essais"
# Les formes nues les plus plausibles d'abord : Niger (ECOHADA), Bénin simple, Datecs à décimales.
PRIORITE = ("a31_h1_ecohada", "a31_essai3", "a31_s2_datecs_decimales", "a31_h2_avec_code",
            "a31_h3_groupe_a", "a31_essai4", "a31_essai5", "a31_h4_type_article")


def anciens():
    """(nom, données) : tous les essais de 31 d'avant le 15 octobre, jamais joués avec un client rattaché."""
    fichiers = sorted(ESSAIS.glob("**/a31_*.txt"), key=lambda p: (
        PRIORITE.index(p.stem) if p.stem in PRIORITE else len(PRIORITE), str(p)))
    for p in fichiers:
        yield p.stem, p.read_text(encoding="utf-8").rstrip("\n")


# Les 16 groupes de taxe A à P et leurs taux, dans l'ordre de C1 (champs 11 à 26). Seuls A et B ont
# été joués (2026-10-09 et 12) ; un décalage d'un rang dans cet ordre expliquerait « incompatibilité ».
TAUX_GROUPES = (0.0, 18.0, 10.0, 0.0, 0.0, 18.0, 10.0, 0.0, 0.0, 0.0, 0.0, 10.0, 10.0, 0.0, 0.0, 0.0)


def groupes():
    """(nom, données) : chaque groupe A à P, en forme Niger (taux lu par C1) et en forme Bénin simple."""
    for lettre, taux in zip("ABCDEFGHIJKLMNOP", TAUX_GROUPES):
        yield "niger/%s" % lettre, "ARTICLE TEST\t%s%.1f%%100\t100*1" % (lettre, taux)
        yield "benin/%s" % lettre, "ARTICLE TEST\t%s100*1" % lettre


SEPARATEURS_2 = ((";", "pv"), ("\n", "lf"), ("|", "barre"))
JETONS_2 = ("1", "B")


def nombres2():
    """Comme « nombres » pour les séparateurs que cette grille n'avait pas : point-virgule, saut de ligne, barre."""
    for n in sorted(NOMBRES, key=lambda n: (abs(n - 7), n)):
        for sep, nom_sep in SEPARATEURS_2:
            for jeton in JETONS_2:
                yield "%s%dx%s" % (nom_sep, n, jeton), sep.join([jeton] * n)


def psvb():
    """(nom, données) : le noyau Niger et une catégorie PSVB (A à D dans C1) à quatorze endroits.

    Le Burkina a un PSVB que le Niger ignore (C0 a un 8e champ « PSVB », « PSVB n'existe pas! » pour x).
    La lettre `x` est un détecteur : si la structure est la bonne, l'appareil répond un message de valeur
    (« PSVB n'existe pas! »), pas le message de format. `A` est une catégorie valide.
    """
    n, g, q = "ARTICLE TEST", "B18.0%100", "100*1"
    for lettre in ("x", "A"):
        formes = (
            ("fin;T", "\t".join((n, g, q)) + ";T" + lettre),
            ("fin;T,0", "\t".join((n, g, q)) + ";T" + lettre + ",0"),
            ("fin;T0,", "\t".join((n, g, q)) + ";T0," + lettre),
            ("fin;P", "\t".join((n, g, q)) + ";P" + lettre),
            ("fin;", "\t".join((n, g, q)) + ";" + lettre),
            ("fin,", "\t".join((n, g, q)) + "," + lettre),
            ("fin-tab", "\t".join((n, g, q, lettre))),
            ("avant-groupe", "\t".join((n, lettre, g, q))),
            ("avant-prix", "\t".join((n, g, lettre, q))),
            ("groupe+L", "\t".join((n, "B" + lettre + "18.0%100", q))),
            ("taux+L", "\t".join((n, "B18.0" + lettre + "%100", q))),
            ("montant+L", "\t".join((n, "B18.0%100" + lettre, q))),
            ("prix+L", "\t".join((n, g, q + lettre))),
            ("debut", "\t".join((lettre, n, g, q))),
        )
        for nom, donnees in formes:
            yield "%s/%s" % (nom, lettre), donnees


def rdc():
    """(nom, données) : la ligne d'article du protocole MCF-SFE v1.0 de la RDC, avec les types burkinabè.

    `nom⇥TYPE,G{taux}%{montant}⇥{prix}[*qté]` (code tiers, recherche/2026-10-28_balayage_sources.md §4) : le type
    vient après une tabulation et devant une virgule, forme qu'aucune grille n'a produite. La forme RDC exacte avec
    `LOCBIE` d'abord, puis ses variantes une à une (type RDC, quantité, nombres Niger, groupe A, les autres types,
    code, deux unités). `x` en dernier : si la structure est la bonne, il donne un message de valeur.
    """
    n, g, p = "ARTICLE TEST", "B18.00%100.00", "100.00"
    formes = (
        ("LOCBIE", "\t".join((n, "LOCBIE," + g, p))),
        ("BIE", "\t".join((n, "BIE," + g, p))),
        ("LOCBIE*1", "\t".join((n, "LOCBIE," + g, p + "*1"))),
        ("LOCBIE/niger", "\t".join((n, "LOCBIE,B18.0%100", "100*1"))),
        ("LOCBIE/entiers", "\t".join((n, "LOCBIE,B18%100", "100"))),
        ("LOCBIE/A", "\t".join((n, "LOCBIE,A0.00%100.00", p))),
        ("LOCSER", "\t".join((n, "LOCSER," + g, p))),
        ("IMPBIE", "\t".join((n, "IMPBIE," + g, p))),
        ("IMPSERV", "\t".join((n, "IMPSERV," + g, p))),
        ("SER", "\t".join((n, "SER," + g, p))),
        ("1", "\t".join((n, "1," + g, p))),
        ("LOCBIE/code", "\t".join((n + "\nART001", "LOCBIE," + g, p))),
        ("LOCBIE/x2", "\t".join((n, "LOCBIE,B18.00%200.00", p + "*2"))),
        ("x", "\t".join((n, "x," + g, p))),
    )
    for nom, donnees in formes:
        yield "rdc/" + nom, donnees


ATTENDU_TAXE = "E:La taxe est incorrecte!"


def taxe():
    """(nom, données) : la structure RDC, passée le 2026-10-28, et seule la partie taxe qui varie.

    `ARTICLE TEST⇥LOCBIE,B18.00%100.00⇥100.00` a répondu « La taxe est incorrecte! » : la structure est lue,
    une valeur de taxe est jugée. D'abord l'écriture du taux de B (18.0 comme dans C1), le groupe A à taux nul,
    d'autres groupes, puis le sens des champs (montant de taxe, sans taux, sans lettre), une taxe spécifique,
    enfin le type à taxe égale : si un type change le message, la taxe dépend du type.
    """
    n, t, p = "ARTICLE TEST", "LOCBIE", "100.00"
    taxes = (
        ("B18.0", "B18.0%100.00"), ("B18", "B18%100.00"), ("B18.000", "B18.000%100.00"),
        ("A0.00", "A0.00%100.00"), ("A0.0", "A0.0%100.00"), ("A0", "A0%100.00"),
        ("C10.00", "C10.00%100.00"), ("F18.00", "F18.00%100.00"),
        ("montant-taxe", "B18.00%15.25"), ("sans-taux", "B%100.00"), ("lettre-montant", "B100.00"),
        ("lettre", "B"), ("sans-lettre", "18.00%100.00"), ("minuscule", "b18.00%100.00"),
        ("fraction", "B0.18%100.00"),
    )
    for nom, tx in taxes:
        yield "taxe/" + nom, "\t".join((n, t + "," + tx, p))
    yield "taxe/specifique", "\t".join((n, t + ",B18.00%100.00", p + ";0.00"))
    for ty in ("BIE", "LOCSER", "IMPBIE", "IMPSERV", "1", "x"):
        yield "type/" + ty, "\t".join((n, ty + ",B18.00%100.00", p))


def taxe2():
    """(nom, données) : `LOCBIE` (type valide, 2026-10-28) et la sous-partie `X%Y` lue autrement.

    Grille `taxe` : sans `%`, format ; X en lettre + taux, lettre seule ou taux seul, Y = 100.00 : taxe incorrecte.
    Deux lectures restent : le groupe avant `%` et le taux après (`B%18.0`) ; ou Y montant de taxe ou taxe
    spécifique, nul au groupe A. Puis les groupes nommés comme dans la spécification (PARAM_TA…TP), l'ordre inverse.
    """
    n, t, p = "ARTICLE TEST", "LOCBIE", "100.00"
    taxes = (
        ("B%18.0", "B%18.0"), ("B%18.00", "B%18.00"), ("A%0.0", "A%0.0"), ("A%0.00", "A%0.00"),
        ("B%18", "B%18"), ("A%0", "A%0"),
        ("A0.00%0.00", "A0.00%0.00"), ("B18.0%0", "B18.0%0"), ("B18.00%0.00", "B18.00%0.00"),
        ("B18.0%15.25", "B18.0%15.25"), ("B18.00%18.00", "B18.00%18.00"), ("B18.0%84.75", "B18.0%84.75"),
        ("TB18.00%100.00", "TB18.00%100.00"), ("TB%18.0", "TB%18.0"), ("TA%0.0", "TA%0.0"),
        ("18.0%B", "18.0%B"), ("0.0%A", "0.0%A"),
    )
    for nom, tx in taxes:
        yield "taxe2/" + nom, "\t".join((n, t + "," + tx, p))


def groupes_rdc():
    """(nom, données) : les douze groupes jamais essayés en structure RDC, au taux lu par C1, sous deux écritures.

    A, B, C et F ont buté sur la taxe sous toutes les écritures (grilles `taxe`, `taxe2`), LOCSER et IMPBIE aussi :
    la taxe ne dépend ni de l'écriture ni du type. Reste qu'un groupe seulement soit ouvert à ce contribuable.
    """
    n, t, p = "ARTICLE TEST", "LOCBIE", "100.00"
    for lettre, taux in zip("ABCDEFGHIJKLMNOP", TAUX_GROUPES):
        if lettre in "ABCF":
            continue
        yield "rdc/%s%.1f" % (lettre, taux), "\t".join((n, "%s,%s%.1f%%100.00" % (t, lettre, taux), p))
        yield "rdc/%s%%%.1f" % (lettre, taux), "\t".join((n, "%s,%s%%%.1f" % (t, lettre, taux), p))


def quantite():
    """(nom, données) : la structure RDC avec une quantité explicite, jamais envoyée.

    Les 62 trames de `taxe`, `taxe2` et `groupes_rdc` finissaient par `⇥100.00`, sans `*qté` (le code RDC l'omet
    pour 1) ; les formes à quantité de la grille `rdc` n'ont pas été jouées (arrêt à la 1re). Une quantité absente
    lue comme 0 rendrait toute taxe incorrecte. Puis les montants de taxe arrondis au supérieur (§6.7 : 15.26).
    """
    n = "ARTICLE TEST"
    formes = (
        ("B18.0", "LOCBIE,B18.0%100.00", "100.00*1"),
        ("B18.00", "LOCBIE,B18.00%100.00", "100.00*1"),
        ("niger", "LOCBIE,B18.0%100", "100*1"),
        ("qte3", "LOCBIE,B18.0%100.00", "100.00*1.000"),
        ("A0.0", "LOCBIE,A0.0%100.00", "100.00*1"),
        ("x2", "LOCBIE,B18.0%200.00", "100.00*2"),
        ("LOCSER", "LOCSER,B18.0%100.00", "100.00*1"),
        ("B%18.0", "LOCBIE,B%18.0", "100.00*1"),
        ("taxe15.26", "LOCBIE,B18.0%15.26", "100.00*1"),
        ("taxe15.25", "LOCBIE,B18.0%15.25", "100.00*1"),
        ("ht84.74", "LOCBIE,B18.0%84.74", "100.00*1"),
        ("specifique0", "LOCBIE,B18.0%0", "100*1"),
        ("qte*prix", "LOCBIE,B18.0%100.00", "1*100.00"),
    )
    for nom, milieu, prix in formes:
        yield "qte/" + nom, "\t".join((n, milieu, prix))


def psvb_rdc():
    """(nom, données) : la structure RDC et le PSVB, taxe que le Burkina ajoute (spécification SFE §6.10).

    Environ 90 écritures de la taxe, 16 groupes, 3 types, avec ou sans quantité : toujours « taxe incorrecte ».
    Il manque peut-être une taxe : la catégorie PSVB (A à D) ou son taux (C1 : 2.0, 1.0, 0.2, 0.0) après `%`,
    la taxe spécifique à la manière du Niger (`;T…,…` après la quantité), le PSVB en 3e sous-champ.
    """
    n, q = "ARTICLE TEST", "100.00*1"
    formes = [("%" + c, "LOCBIE,B18.0%" + c, q) for c in "ABCD"]
    formes += [("%" + t, "LOCBIE,B18.0%" + t, q) for t in ("2.0", "1.0", "0.2", "0.0")]
    formes += [
        ("specifique;T0,0", "LOCBIE,B18.0%100.00", q + ";T0,0"),
        ("specifique;T0.00,0.00", "LOCBIE,B18.0%100.00", q + ";T0.00,0.00"),
        ("sous-champ,A", "LOCBIE,B18.0%100.00,A", q),
        ("sous-champ,A,", "LOCBIE,A,B18.0%100.00", q),
    ]
    for nom, milieu, prix in formes:
        yield "psvb/" + nom, "\t".join((n, milieu, prix))


GRILLES = {"nombres": grille, "gabarits": gabarits, "photo": photo, "anciens": anciens,
           "groupes": groupes, "nombres2": nombres2, "psvb": psvb, "rdc": rdc, "taxe": taxe, "taxe2": taxe2,
           "groupes_rdc": groupes_rdc, "quantite": quantite, "psvb_rdc": psvb_rdc}
# Le message qui n'arrête pas la grille : celui de format, sauf pour les grilles qui partent d'une structure lue.
CONNU = {"taxe": ATTENDU_TAXE, "taxe2": ATTENDU_TAXE, "groupes_rdc": ATTENDU_TAXE, "quantite": ATTENDU_TAXE,
         "psvb_rdc": ATTENDU_TAXE}


def main(argv=None, mcf=None):
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("--liste", action="store_true", help="afficher la grille, ne rien envoyer")
    a.add_argument("--jumeau", action="store_true", help="jouer contre le jumeau FIS, pas l'appareil")
    a.add_argument("--port", help="port série de l'appareil ; sans --jumeau ni --liste, exige ce port")
    a.add_argument("--seq", default="70", help="séquence hexadécimale de départ (défaut 70)")
    a.add_argument("--grille", choices=sorted(GRILLES), default="nombres",
                   help="nombres : un jeton répété, 2 à 14 champs ; gabarits : noyaux valides + type et unité ; "
                        "photo : enregistrement complet dans l'ordre de la ligne d'article de la facture DGI ; "
                        "anciens : les 16 essais d'avant le 15 octobre, rejoués avec un client rattaché ; "
                        "groupes : les 16 groupes de taxe A à P ; "
                        "nombres2 : comme nombres, avec point-virgule, saut de ligne et barre ; "
                        "psvb : le noyau Niger et une catégorie PSVB à quatorze endroits (x en détecteur, A valide) ; "
                        "rdc : la ligne d'article du protocole de la RDC, type burkinabè devant le groupe ; "
                        "taxe : la structure RDC, seule la taxe varie (arrêt à tout autre message que « taxe incorrecte ») ; "
                        "taxe2 : LOCBIE et la sous-partie X%%Y lue autrement (groupe%%taux, taxe nulle, TA…TP) ; "
                        "groupes_rdc : les groupes D, E, G à P en structure RDC, au taux de C1 ; "
                        "quantite : la structure RDC avec *qté explicite, puis les taxes arrondies (§6.7) ; "
                        "psvb_rdc : la structure RDC et le PSVB ou la taxe spécifique")
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
    complet = list(GRILLES[o.grille]())
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
            print("%03d %-14s %r" % (i, nom, donnees))
        print("%d trames à la grille. Séance %03d–%03d. Rien envoyé."
              % (len(complet), o.depuis, o.depuis + len(serie) - 1))
        return 0
    seq = [depart]
    if o.jumeau:
        if mcf is None:
            from simulateur.faux_mcf import FauxMCF
            mcf = FauxMCF(variante="FIS")
            mcf.donnees(0xC0, b"1,Essai,{IFU},FV,TTC,ISF-ESSAI,ESSAI-0002")  # facture ouverte
        envoyer, delai = envoyer_jumeau(mcf, seq, 0x31), 0.0
    else:
        def envoyer(donnees):
            r = pousser(o.port, seq[0], donnees, cmd=0x31)
            seq[0] = suivant(seq[0])
            return r
        delai = o.delai

    print("%s GRILLE : %d trames, une toutes les %.0f s. Arrêt au premier écart."
          % (time.strftime("%H:%M:%S"), len(serie), delai), flush=True)

    def tracer(i, nom, motif):
        print("%s %03d %s  %s" % (time.strftime("%H:%M:%S"), o.depuis + i, nom, motif), flush=True)

    connu = CONNU.get(o.grille, ATTENDU)
    resultat = jouer(serie, envoyer, delai, tracer=tracer, attendu=connu)
    if resultat is None:
        print("terminé : %d trames, %s partout." % (
            len(serie), "message de format" if connu == ATTENDU else "« %s »" % connu))
        prochain = o.depuis + len(serie)
        if prochain <= len(complet):
            print("suite : --depuis %d" % prochain)
        return 0
    print("ARRÊT %s  données=%r  %s" % resultat)
    return 1


if __name__ == "__main__":
    sys.exit(main())
