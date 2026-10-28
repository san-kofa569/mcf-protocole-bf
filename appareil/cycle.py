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
  annulation  un bien payé, puis 38 `C` : `E:ANNULEE`, facture non comptée (prouvé le 2026-10-28, 14:56).
              Sans 35, le 38 `C` répond « La commande 35 doit être soumise en premier. » : avant paiement, C1 annule.
  ht          un bien en mode HT (C0 `HT`) : la 31 porte le montant TTC de la ligne et le prix HT
              (`B18.0%118.00⇥100.00*1` → `118.0,100.0,18.0,0.0`, 2026-10-28 15:46) ; 33 en HT jamais vu ;
  credit      un bien vendu à crédit : 35 en mode `A` pour le total (`A102.00` → `R0`, ESSAI-0012 certifiée) ;
  modes       PSVB `D` (taux 0), un bien et un service `IMPSER` dont la désignation porte une virgule échappée
              (`^x2c;`, 📖 RDC), payés en trois modes `V`, `C`, `D` (📖) ;
  avoir       avoir de correction (FA, nature COR) d'une facture « deux » : C0 `op,nom,IFU,FA,COR,RN,TTC,ISF,FN,PSVB`
              avec RN = `{NIM-ACNT}-{TC d'origine}` (AVOIR-0001 certifié le 2026-10-28 15:13), puis les lignes, 33,
              35 et 38 comme une vente. MCF_NIM vient de `python3 -m appareil.signature … --nim` ; --origine donne
              FN, numéro et TC de la facture d'origine. Un refus de RN (`Erreur de format RN! <RN>`) est masqué.

Sur l'appareil, chaque réponse est écrite brute dans `--capture` (appareil/brut/, hors dépôt) : c'est là que se
lisent NIM, IFU et signature, jamais à l'écran.

Usage :
  python3 -m appareil.cycle --scenario simple --fn ESSAI-0009 --liste
  python3 -m appareil.cycle --scenario avoir --fn AVOIR-0001 --origine ESSAI-0009,2,4 --port /dev/ttyACM0 --seq 60
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
from appareil.trame import bcc_ok, paquet, remplir, trame

DELAI = 3.0
CLIENT = "PP,CLIENT TEST,,,70123456,client@example.com,"
BIEN = "ARTICLE TEST\tLOCBIE,B18.0%100.00\t100.00*1"
SERVICE = "POSE TEST\tLOCSER,C10.0%110.00\t110.00*1"
SERVICE_IMPORTE = "POSE^x2c; TEST\tIMPSER,C10.0%110.00\t110.00*1"  # « POSE, TEST » : virgule échappée
BIEN_HT = "ARTICLE TEST\tLOCBIE,B18.0%118.00\t100.00*1"  # en HT : montant TTC de la ligne, prix HT
FORMAT = "E:Erreur de format des données ou incompatibilité"
OUVERTE = " — une facture est sans doute restée ouverte (C3 refusé pendant une facture) : un C1 l'annule"
FORMAT_RN = "E:Erreur de format RN!"
# C0 d'avoir (📖 RDC `type,nature,référence` à la place du type ; nature 📜 COR, RAN, RAM, RRR). RN prouvée le
# 2026-10-28 : identifiant de l'appareil tel qu'il l'écrit (NIM-ACNT), tiret, TC de la facture d'origine. Refusées :
# signature brute, à tirets, FN d'origine, numéro d'origine, NIM-TC sans le compteur d'activation.
AVOIRS = (
    ("rn-nim-acnt-tc", "{NIM-ACNT}-{tc_origine}"),
)
C0_AVOIR = "1,Essai,{IFU},FA,COR,%s,TTC,ISF-ESSAI,%s,A"

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


def etapes(scenario, fn, origine=("ESSAI-0009", "2", "4")):
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
    if scenario == "ht":
        return [("client", 0xC3, CLIENT), ("ouverture", 0xC0, "1,Essai,{IFU},FV,HT,ISF-ESSAI,%s,A" % fn),
                ("article", 0x31, BIEN_HT), ("sous-total", 0x33, ""),
                ("paiement", 0x35, lambda e: "E" + montant(e["total"])),
                ("normalisation", 0x38, lambda e: montant(e["total"]))]
    if scenario == "credit":
        return debut + [("article", 0x31, BIEN), ("sous-total", 0x33, ""),
                        ("credit", 0x35, lambda e: "A" + montant(e["total"])),
                        ("normalisation", 0x38, lambda e: montant(e["total"]))]
    if scenario == "modes":
        tiers = lambda e: montant(round(e["total"] / 3, 2))
        return [("client", 0xC3, CLIENT), ("ouverture", 0xC0, "1,Essai,{IFU},FV,TTC,ISF-ESSAI,%s,D" % fn),
                ("bien", 0x31, BIEN), ("service", 0x31, SERVICE_IMPORTE), ("sous-total", 0x33, ""),
                ("virement", 0x35, lambda e: "V" + tiers(e)), ("carte", 0x35, lambda e: "C" + tiers(e)),
                ("cheque", 0x35, lambda e: "D" + montant(e["du"])),
                ("normalisation", 0x38, lambda e: montant(e["total"]))]
    if scenario == "avoir":
        rn = lambda f: (f.replace("{fn_origine}", origine[0]).replace("{numero_origine}", origine[1])
                        .replace("{tc_origine}", origine[2]))
        return [("ouverture", 0xC0, [(v, C0_AVOIR % (rn(f), fn)) for v, f in AVOIRS]),
                ("bien", 0x31, BIEN), ("service", 0x31, SERVICE), ("sous-total", 0x33, ""),
                ("paiement", 0x35, lambda e: "E" + montant(e["total"])),
                ("normalisation", 0x38, lambda e: montant(e["total"]))]
    if scenario == "annulation":
        return debut + [("article", 0x31, BIEN), ("sous-total", 0x33, ""),
                        ("paiement", 0x35, lambda e: "E" + montant(e["total"])),
                        ("annulation", 0x38, "C")]
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
        return "accepté : 8 champs, compteurs %s/%s %s (NIM, IFU, signature dans --capture)" % (f[0], f[1], f[2])
    return donnees


def ouvrir(nom, cmd, formes, envoyer, delai, tracer):
    """C3 puis C0, forme après forme, tant que le C0 répond le message de format. Vrai si une facture s'ouvre."""
    for j, (variante, c0) in enumerate(formes):
        if j and delai:
            time.sleep(delai)
        r, motif = lire(envoyer(0xC3, CLIENT))
        if r != "R":
            tracer("client C3 %r : ARRÊT, %s%s" % (CLIENT, motif or r, OUVERTE if "statut a2" in motif else ""))
            return False
        if delai:
            time.sleep(delai)
        r, motif = lire(envoyer(cmd, c0))
        if r is None:
            tracer("%s %s %02X %r : ARRÊT, %s" % (nom, variante, cmd, c0, motif))
            return False
        tracer("%s %s %02X %r -> %s" % (nom, variante, cmd, c0,
                                         FORMAT_RN + " (valeur renvoyée masquée)" if r.startswith(FORMAT_RN) else r))
        if r == FORMAT or r.startswith(FORMAT_RN):
            continue
        if re.fullmatch(FORMES[cmd], r):
            return True
        tracer("ARRÊT : réponse inattendue (rien d'ouvert, ou un C1 l'annule).")
        return False
    tracer("ARRÊT : aucune forme acceptée, rien d'ouvert.")
    return False


def capturer(chemin):
    """Écrit chaque échange brut, au format de trame.py, dans `chemin` (appareil/brut/, hors dépôt)."""
    def noter(seq, cmd, d, recu):
        os.makedirs(os.path.dirname(chemin) or ".", exist_ok=True)
        with open(chemin, "a", encoding="utf-8") as f:
            f.write("%s envoi : %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"),
                                         trame(seq, cmd, remplir(d, os.environ).encode("latin-1")).hex(" ")))
            p = paquet(recu or b"")
            f.write("reçu (%d octets) : %s\n" % (len(recu or b""), (recu or b"").hex(" ")))
            if p:
                f.write("données : %s\nstatut : %s\n" % (p[0].decode("utf-8", "replace"), p[1].hex(" ")))
    return noter


def jouer(scenario, fn, envoyer, delai=0.0, tracer=print, origine=("ESSAI-0009", "2", "4")):
    """Déroule le scénario. Rend 0 si tout a la forme attendue, 1 à l'arrêt."""
    etat = {}
    for i, (nom, cmd, donnees) in enumerate(etapes(scenario, fn, origine) if scenario == "avoir" else etapes(scenario, fn)):
        if i and delai:
            time.sleep(delai)
        if isinstance(donnees, list):
            if not ouvrir(nom, cmd, donnees, envoyer, delai, tracer):
                return 1
            continue
        d = donnees(etat) if callable(donnees) else donnees
        if cmd == 0x35 and not (re.fullmatch(r"[A-Z]\d+\.\d{2}", d) and float(d[1:]) > 0):
            tracer("%s %02X %r : ARRÊT avant envoi, paiement nul ou négatif." % (nom, cmd, d))
            return 1
        if cmd == 0x38 and d != "C" and etat.get("du") != 0:
            tracer("%s %02X %r : ARRÊT avant envoi, la facture n'est pas soldée (reste %s)." % (nom, cmd, d, etat.get("du")))
            return 1
        r, motif = lire(envoyer(cmd, d))
        if r is None:
            tracer("%s %02X %r : ARRÊT, %s%s" % (nom, cmd, d, motif,
                                                 OUVERTE if cmd == 0xC3 and "statut a2" in motif else ""))
            return 1
        tracer("%s %02X %r -> %s" % (nom, cmd, d, montrer(cmd, r)))
        if not re.fullmatch("E:ANNULEE" if (cmd, d) == (0x38, "C") else FORMES[cmd], r):
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
    a.add_argument("--scenario", choices=("simple", "deux", "annulation", "ht", "credit", "modes", "avoir"),
                   required=True)
    a.add_argument("--fn", required=True, help="référence de la facture, jamais réutilisée (ESSAI-0009…)")
    a.add_argument("--origine", default="ESSAI-0009,2,4", help="avoir : FN, numéro et TC de la facture d'origine")
    a.add_argument("--liste", action="store_true", help="afficher les trames, ne rien envoyer")
    a.add_argument("--jumeau", action="store_true", help="jouer contre le jumeau FIS")
    a.add_argument("--port", help="port série de l'appareil")
    a.add_argument("--seq", default="20", help="séquence hexadécimale de départ (défaut 20)")
    a.add_argument("--capture", default=os.path.join("appareil", "brut", time.strftime("%Y-%m-%d") + "_cycle.txt"),
                   help="fichier des réponses brutes, sur l'appareil (défaut appareil/brut/AAAA-MM-JJ_cycle.txt)")
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
        for nom, cmd, d in etapes(o.scenario, o.fn, tuple(o.origine.split(","))):
            if isinstance(d, list):
                for variante, c0 in d:
                    print("%-13s %02X %r  (forme %s, après un C3)" % (nom, cmd, c0, variante))
                continue
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
        if o.scenario == "avoir":
            formes = [c0 for _, c0 in etapes("avoir", o.fn, tuple(o.origine.split(",")))[0][2]]
            if any(remplir(c0, os.environ) is None for c0 in formes):
                print("MCF_NIM (ou MCF_SIG) absent ou invalide pour une forme d'avoir : rien envoyé.")
                return 2
        noter = capturer(o.capture)

        def envoyer(cmd, d):
            r = pousser(o.port, seq[0], d, cmd=cmd)
            noter(seq[0], cmd, d, r)
            seq[0] = suivant(seq[0])
            return r
        delai = DELAI
    print("%s cycle %s, FN %s, %s" % (time.strftime("%H:%M:%S"), o.scenario, o.fn,
                                      "jumeau" if o.jumeau else o.port), flush=True)
    return jouer(o.scenario, o.fn, envoyer, delai, tracer=lambda t: print(time.strftime("%H:%M:%S ") + t, flush=True),
                 origine=tuple(o.origine.split(",")))


if __name__ == "__main__":
    sys.exit(main())
