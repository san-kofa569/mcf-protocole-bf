"""Recherche bornée du type de destinataire de C3.

Une liste de candidats, chaque candidat à chaque place d'une trame à 5 champs
(format Niger : IFU, nom, c3, c4, c5). Rien n'est envoyé par défaut.

Usage :
  python3 -m appareil.recherche_bornee --liste
  python3 -m appareil.recherche_bornee --jumeau
  python3 -m appareil.recherche_bornee --jumeau --avec-connu
  python3 -m appareil.recherche_bornee --jumeau --depuis 81
  python3 -m appareil.recherche_bornee --port /dev/ttyACM0 --seq 60

Sur l'appareil : une trame toutes les 3 s, 80 au plus par séance, arrêt au
premier message nouveau, au NAK, au silence ou à la déconnexion. EazSell au
premier plan, aucune facture ouverte, accord de l'opérateur, une séance à la fois.
La séance suivante reprend avec --depuis.
"""
import argparse
import os
import sys
import time

from appareil.trame import bcc_ok, paquet, remplir, trame

PLACES = 5
ATTENDU = "E:Erreur de type de destinataire"
NOMS = ("", "CLIENT TEST")
DELAI = 3.0
PLAFOND = 80
ATTENTE = 5.0

# Déjà refusés sur l'appareil (2026-10-09 et 2026-10-12), à ne pas rejouer.
CONNUS = (
    "CC", "PM", "PP", "PC", "0", "1", "2", "3", "4",
    "CLIENT COMPTANT", "CLIENT TEST", "ESSAI",
)


SONDES = (
    "5", "6", "7", "8", "9",
    "01", "02", "03", "04",
    "A", "B", "C", "D", "E", "F", "N", "O", "T", "P", "M",
    "FV", "FT", "FA", "EV", "ET", "EA",
    "TS", "TA", "TN", "TI", "TM", "TP",
    "IFU", "NIM", "CLIENT", "COMPTANT", "DESTINATAIRE",
)


def candidats(connus=CONNUS):
    """Valeurs encore jamais placées dans un C3. Les codes déjà refusés sont exclus."""
    deja = set(connus)
    valeurs = []
    for v in CONNUS + SONDES:
        if v not in deja:
            deja.add(v)
            valeurs.append(v)
    return tuple(valeurs)


def trames(valeurs=None, noms=NOMS):
    """(nom, données) : le candidat occupe une seule place, les autres restent neutres.

    La place 2 est le nom. Le candidat la remplace : une seule trame, pas le
    couple (nom vide, nom d'essai) qui produirait deux fois les mêmes octets.
    """
    if valeurs is None:
        valeurs = candidats()
    for valeur in valeurs:
        for place in range(PLACES):
            for nom in (("",) if place == 1 else noms):
                champs = ["", nom, "", "", ""]
                champs[place] = valeur
                yield "%s@%d:%s" % (valeur, place + 1, nom or "-"), ",".join(champs)


def borne(serie, plafond=PLAFOND):
    serie = list(serie)
    if len(serie) > plafond:
        raise ValueError("%d trames, plafond %d" % (len(serie), plafond))
    return serie


def suivant(seq):
    """Prochaine séquence imprimable. Après FF, retour à 20."""
    return 0x20 if seq >= 0xFF else seq + 1


def classer(recu, attendu=ATTENDU):
    """(arret, motif). Le message déjà connu n'arrête pas."""
    if recu is None:
        return True, "déconnexion"
    if not recu:
        return True, "silence"
    debut = recu[:recu.index(1)] if 1 in recu else recu
    if b"\x15" in debut:
        return True, "NAK"
    p = paquet(recu)
    if p is None or bcc_ok(recu) is not True:
        return True, "trame illisible"
    donnees = p[0].decode("utf-8", "replace")  # l'appareil répond en UTF-8 (é = c3 a9)
    if donnees == attendu:
        return False, "connu"
    if donnees.startswith("E:"):
        return True, "message nouveau : " + donnees
    return True, "accepté : " + (donnees or "(vide)")


def jouer(serie, envoyer, delai=0.0, horloge=time.monotonic, tracer=None, attendu=ATTENDU):
    """Envoie jusqu'à l'arrêt. Rend (nom, données, motif) de la trame qui arrête, ou None.

    tracer(i, nom, motif) voit chaque réponse, i partant de 0 dans la séance.
    """
    precedent = None
    for i, (nom, donnees) in enumerate(serie):
        if precedent is not None and delai:
            time.sleep(max(0.0, delai - (horloge() - precedent)))
        precedent = horloge()
        arret, motif = classer(envoyer(donnees), attendu)
        if tracer:
            tracer(i, nom, motif)
        if arret:
            return nom, donnees, motif
    return None


def envoyer_jumeau(mcf, seq, cmd=0xC3):
    def envoyer(donnees):
        r = mcf.repondre(seq[0], cmd, donnees.encode("latin-1"))
        seq[0] = suivant(seq[0])
        return r
    return envoyer


def ligne(depuis, avec_connu=False, seq="60", plafond=PLAFOND, port=None):
    """Commande de la séance suivante : sur l'appareil si port, sinon sur le jumeau.

    Le numéro est celui affiché (1 = début).
    """
    morceaux = ["python3 -m appareil.recherche_bornee", "--port %s" % port if port else "--jumeau"]
    if avec_connu:
        morceaux.append("--avec-connu")
    if depuis != 1:
        morceaux.append("--depuis %d" % depuis)
    if seq != "60":
        morceaux.append("--seq %s" % seq)
    if plafond != PLAFOND:
        morceaux.append("--plafond %d" % plafond)
    return " ".join(morceaux)


def pousser(port, seq, donnees, attente=ATTENTE, env=None, cmd=0xC3):
    """Écrit une trame (C3 par défaut) et lit la réponse. None si le port disparaît.

    {IFU} sans MCF_IFU : arrêt avant d'ouvrir le port.
    """
    rempli = remplir(donnees, os.environ if env is None else env)
    if rempli is None:
        raise SystemExit("{IFU} présent mais MCF_IFU absent ou invalide (9 caractères) : rien envoyé.")
    import serial
    t = trame(seq, cmd, rempli.encode("latin-1"))
    try:
        with serial.Serial(port, 115200, timeout=0.2) as p:
            p.reset_input_buffer()
            p.write(t)
            p.flush()
            recu, fin = b"", time.time() + attente
            while time.time() < fin:
                recu += p.read(256)
                if paquet(recu):
                    break
            return recu
    except (OSError, serial.SerialException):
        return None


def main(argv=None, mcf=None):
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("--liste", action="store_true", help="afficher les trames, ne rien envoyer")
    a.add_argument("--jumeau", action="store_true", help="jouer contre le jumeau FIS, pas l'appareil")
    a.add_argument("--avec-connu", action="store_true", help="réinclure les valeurs déjà refusées, en tête")
    a.add_argument("--port", help="port série de l'appareil ; sans --jumeau ni --liste, exige ce port")
    a.add_argument("--seq", default="60", help="séquence hexadécimale de départ (défaut 60)")
    a.add_argument("--depuis", type=int, default=1,
                   help="numéro affiché de la première trame (1 = début)")
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
    valeurs = candidats(() if o.avec_connu else CONNUS)
    complet = list(trames(valeurs))
    if o.depuis < 1 or o.depuis > len(complet) + 1:
        print("départ %d hors liste (trames 1–%d) : rien envoyé." % (o.depuis, len(complet)))
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
            print("%03d %s  %s" % (i, nom, donnees))
        if serie:
            print("%d trames au catalogue. Séance %03d–%03d. Rien envoyé."
                  % (len(complet), o.depuis, o.depuis + len(serie) - 1))
        else:
            print("%d trames au catalogue. Séance vide. Rien envoyé." % len(complet))
        print(ligne(o.depuis, o.avec_connu, o.seq, plafond))
        return 0
    seq = [depart]

    def tracer(i, nom, motif):
        print("%03d %s  %s" % (o.depuis + i, nom, motif), flush=True)

    if o.jumeau:
        if mcf is None:
            from simulateur.faux_mcf import FauxMCF
            mcf = FauxMCF(variante="FIS")
        resultat = jouer(serie, envoyer_jumeau(mcf, seq), tracer=tracer)
    else:
        def envoyer(donnees):
            r = pousser(o.port, seq[0], donnees)
            seq[0] = suivant(seq[0])
            return r
        print("ENVOI vers %s : %d trames, une toutes les %.0f s. Arrêt au premier écart."
              % (o.port, len(serie), o.delai), flush=True)
        resultat = jouer(serie, envoyer, o.delai, tracer=tracer)
    if resultat is None:
        print("terminé : %d trames, message connu partout." % len(serie))
        prochain = o.depuis + len(serie)
        if prochain <= len(complet):
            print(ligne(prochain, o.avec_connu, o.seq, o.plafond, None if o.jumeau else o.port))
        return 0
    print("ARRÊT %s  données=%r  %s" % resultat)
    return 1


if __name__ == "__main__":
    sys.exit(main())
