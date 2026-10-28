"""Faux MCF : répond aux trames d'un SFE sur un pty et journalise tout ce qu'il reçoit.

Usage : python3 -m simulateur.faux_mcf --lien <chemin> --journal <fichier> [--variante NE|BF|FIS]
Le lien pointe vers l'esclave du pty (pour Wine : $WINEPREFIX/dosdevices/com1).
Toutes les valeurs sont fictives. NE et BF répondent de façon plausible : l'enjeu est de lire
ce qu'envoie le SFE. FIS est le jumeau du FIS-NANO : il ne rend que ce que l'appareil a
répondu (2026-10-09 au 2026-10-28, cycle complet compris) et signale par INCONNU tout cas jamais observé.
"""
import argparse
import base64
import hashlib
import os
import re
import sys
import time
import tty

NIM, IFU = "XX99999999", "99999999Z"
TAUX = "0.0,18.0,10.0,0.0,0.0,18.0,10.0,0.0,0.0,0.0,0.0,10.0,10.0,0.0,0.0,0.0"
PSVB = "2.0,1.0,0.2,0.0"
SIGNATURE = "ABCD1234EFGH5678IJKL9012"
TAUX_GROUPES = [float(t) for t in TAUX.split(",")]
TAUX_PSVB = dict(zip("ABCD", (float(t) for t in PSVB.split(","))))
INCONNU = "E:?? cas jamais observé sur l'appareil".encode()
TYPES_FACTURE = ("FV", "FT", "FA", "EV", "ET", "EA")  # note DGI 2025-0889 §2.7
E_FORMAT = "E:Erreur de format des données ou incompatibilité".encode()
SOCIETE = {b"I0": "SOCIETE ESSAI", b"I1": "RUE ESSAI", b"I2": "VILLE ESSAI",
           b"I3": "00000000", b"I4": "essai@example.org"}


def reponse(seq, cmd, data, statut=b"\x80" * 6):
    corps = bytes([0x20 + len(data) + 11, seq, cmd]) + data + b"\x04" + statut + b"\x05"
    s = sum(corps)
    return b"\x01" + corps + bytes(((s >> k) & 0xF) + 0x30 for k in (12, 8, 4, 0)) + b"\x03"


def lire_requete(fd):
    """Une trame entière : 01, LEN, puis LEN - 0x20 + 4 octets (jusqu'à 03)."""
    b = b""
    while not b:
        c = os.read(fd, 1)
        if not c:
            return b""
        if c == b"\x01":
            b = c
    b += os.read(fd, 1)
    reste = b[1] - 0x20 + 4
    while reste > 0:
        c = os.read(fd, reste)
        if not c:
            break
        b += c; reste -= len(c)
    return b


# Réponses de C3 observées sur le FIS-NANO le 2026-10-15, charge utile exacte (pas d'état caché :
# la même trame redonne la même réponse après un rallumage). Tout autre C3 : le message connu.
C3_OBSERVE = {
    b"": b"R",
    b"99988776,CLIENT TEST,,,": b"R",
    b"PP,CLIENT TEST,,,,,": b"R",
    b"PP,CLIENT TEST,,,70123456,client@example.com,": b"R",  # rattaché au C0 (15 et 28 octobre)
    b"PP,PP,PP,PP,PP,PP,PP": "E:L'adresse e-mail du destinataire n'est pas valide".encode(),
}

# Réponses de 36 (commentaire) dans une facture ouverte, observées le 2026-10-16. Une 36 acceptée
# ne compte pas comme article (33 répond toujours « ajouter le produit en premier »).
AUCUNE_DONNEE = "E:Aucune donnée valide n'a été reçue".encode()
E_TAXE = "E:La taxe est incorrecte!".encode()
# Types d'article de la note 2025-0889 (annexe), tels que l'appareil les accepte (2026-10-28) : le service importé
# s'écrit IMPSER, comme la mention imprimée ; le code IMPSERV de l'annexe répond « Le type de produit n'existe pas »
TYPES_ARTICLE = (b"LOCBIE", b"LOCSER", b"IMPBIE", b"IMPSER")
TYPES_NON_ESSAYES = ()
C0_EN_PREMIER = "E:La commande C0 doit être soumise en premier".encode()


def nombre(v):
    """Écriture des montants par l'appareil : 102.0, 15.25, 0.0 (2026-10-28)."""
    return str(round(v, 2))
C36_OBSERVE = {
    b"A,ESSAI": b"R",
    b"ESSAI": AUCUNE_DONNEE,
    b"Z,ESSAI": AUCUNE_DONNEE,
    b"A,ESSAI,X": AUCUNE_DONNEE,
}


class FauxMCF:
    def __init__(self, variante="NE", journal=None, latence=0.0, nouveau=None):
        self.variante, self.journal, self.latence = variante, journal, latence
        self.ventes, self.tc, self.total, self.type, self.ttc = 0, 2, 0.0, "FV", True
        self.avoirs, self.certifiees = 0, set()  # TC des factures de vente certifiées, que RN peut désigner
        self.ouverte, self.articles, self.commentaires = False, 0, 0
        self.lignes, self.paye, self.paiements, self.psvb, self.fn, self.client = [], 0.0, 0, None, "", None
        # (données, réponse) en octets : un seul C3 qui s'écarte du message connu.
        # Sert à vérifier qu'une recherche s'arrête. Absent : aucun écart.
        self.nouveau = nouveau

    def redemarrer(self):
        """Arrêt et rallumage : la facture ouverte disparaît, sans être comptée (2026-10-12)."""
        self.ouverte, self.articles, self.total, self.commentaires = False, 0, 0.0, 0
        self.lignes, self.paye, self.paiements, self.psvb = [], 0.0, 0, None

    def montants(self):
        """(total à payer, 16 montants TTC, 16 TVA, PSVB) de la facture ouverte, en mode TTC.

        Vu le 2026-10-28 (un bien B ; puis un bien B et un service C) : TVA du groupe = TTC × taux / (100 + taux)
        arrondie au centime ; PSVB = taux de la catégorie du C0 × TTC de **toutes** les lignes, services compris
        (4.2 sur 210) ; total = TTC + PSVB. 🔍 TVA calculée par groupe et non par ligne (un article par groupe vu).
        """
        ttc = [0.0] * 16
        for groupe, montant, _ in self.lignes:
            ttc[ord(groupe) - 65] += montant
        tva = [round(m * t / (100 + t), 2) for m, t in zip(ttc, TAUX_GROUPES)]
        psvb = round(sum(ttc) * TAUX_PSVB[self.psvb] / 100, 2)
        return round(sum(ttc) + psvb, 2), ttc, tva, psvb

    def article(self, ty, tx, prix):
        """31 dans une facture à PSVB : accepté (une forme vue le 2026-10-28, `B18.0%100.00⇥100.00*1`).

        🔍 Généralisé : groupe A à P au taux lu par C1, montant = prix × quantité, quantité facultative, mode TTC.
        Tout le reste (autre taux, montant faux, mode HT) n'a jamais été envoyé avec un PSVB : INCONNU.
        """
        m = re.fullmatch(rb"([A-P])([0-9.]+)%([0-9.]+)", tx)
        p = re.fullmatch(rb"([0-9.]+)(?:\*([0-9.]+))?", prix)
        if not (m and p):
            return INCONNU
        if not self.ttc:
            # 2026-10-28 15:46 : en HT, le montant est le TTC de la ligne, le prix est HT : `B18.0%118.00⇥100.00*1` →
            # `118.0,100.0,18.0,0.0` ; montant = prix × qté (HT) : « Mismatch de montant » ; le reste : jamais vu
            groupe = m.group(1).decode()
            taux = TAUX_GROUPES[ord(groupe) - 65]
            montant, ht = float(m.group(3)), float(p.group(1)) * float(p.group(2) or 1)
            if abs(float(m.group(2)) - taux) > 1e-9:
                return INCONNU
            tva = round(ht * taux / 100, 2)
            if abs(montant - round(ht + tva, 2)) <= 0.005:
                self.lignes.append((groupe, montant, ty)); self.articles += 1
                return ",".join(nombre(v) for v in (montant, ht, tva, 0.0)).encode()
            return b"E:Mismatch de montant" if abs(montant - ht) <= 0.005 else INCONNU
        groupe = m.group(1).decode()
        taux = TAUX_GROUPES[ord(groupe) - 65]
        montant, pu, qte = float(m.group(3)), float(p.group(1)), float(p.group(2) or 1)
        if abs(float(m.group(2)) - taux) > 1e-9 or abs(montant - pu * qte) > 0.005:
            return INCONNU
        self.lignes.append((groupe, montant, ty))
        self.articles += 1
        tva = round(montant * taux / (100 + taux), 2)
        return ",".join(nombre(v) for v in (montant, montant - tva, tva, 0.0)).encode()

    def normaliser(self, data):
        """38 d'une facture à articles : `MV` seul, le total du 33 (2026-10-28)."""
        total = self.montants()[0]
        if not self.paiements:
            return "E:La commande 35 doit être soumise en premier.".encode()  # 🔍 vu sur une facture sans article
        if data == b"C":
            self.redemarrer()  # 2026-10-28 14:56 : annulée après le 35, non comptée (C1 : compteurs inchangés)
            return b"E:ANNULEE"
        # 2026-10-28 14:45 : une facture non soldée (reste -228.4) a été certifiée : aucun contrôle du paiement
        if b"," in data:
            return "E:MV n'est pas un nombre valide.".encode()  # 5 formes à virgule, 2026-10-28
        try:
            mv = float(data)
        except ValueError:
            return INCONNU
        if abs(mv - total) > 0.005:
            return INCONNU
        avoir = self.type in ("FA", "EA")
        if avoir:
            self.avoirs += 1
        else:
            self.ventes += 1
        self.tc += 1
        if not avoir:
            self.certifiees.add(self.tc)
        sig = base64.b32encode(hashlib.sha256(("%s|%d" % (self.fn, self.tc)).encode()).digest()).decode()[:24]
        r = "%d,%d,%s,%s,%s-1,%s,%s,%s" % (self.avoirs if avoir else self.ventes, self.tc, self.type,
                                          time.strftime("%Y%m%d%H%M%S"), NIM, IFU, sig, self.fn)
        self.redemarrer()
        return r.encode()

    def repondre(self, seq, cmd, data):
        """Trame complète. FIS : C3 pendant une facture ouverte = NAK puis trame vide, statut A2 (2026-10-12)."""
        if self.variante == "FIS" and cmd == 0xC3 and self.ouverte:
            return b"\x15" + reponse(seq, cmd, b"", b"\xa2" + b"\x80" * 5)
        if self.variante == "FIS" and cmd == 0x2B and data not in SOCIETE:
            # 2B I5 : NAK, statut A1 (2026-10-16), et non A2 comme le C3 refusé dans l'état
            return b"\x15" + reponse(seq, cmd, b"", b"\xa1" + b"\x80" * 5)
        return reponse(seq, cmd, self.donnees(cmd, data))

    def fis(self, cmd, data):
        """Réponse du FIS-NANO quand elle a été observée ; None : réponse commune."""
        champs = data.decode("latin-1").split(",")
        if cmd == 0xC3:
            # vide, CC (3e, 4e), 1 (3e) : aucun type accepté connu. Le crochet
            # `nouveau` substitue une réponse, pour prouver un arrêt de recherche.
            if self.nouveau is not None and data == self.nouveau[0]:
                r = self.nouveau[1]
                return r if isinstance(r, bytes) else r.encode("latin-1")
            if data in C3_OBSERVE:
                if C3_OBSERVE[data] == b"R" and len(champs) == 7:
                    self.client = ",".join(champs[1:])  # recopié par le C0 suivant (champs 2 à 7)
                return C3_OBSERVE[data]
            return b"E:Erreur de type de destinataire"
        if cmd == 0xC0:
            if len(champs) < 4 or champs[3] not in TYPES_FACTURE:
                return E_FORMAT  # formats béninois du 09 (taux en 4e champ)
            if champs[3] in ("FA", "EA"):
                # avoir : à 7 champs, message de format (15 octobre). `FA,COR,RN,TTC,ISF,FN,PSVB` est lu (28 octobre) :
                # RN = identifiant `NIM-ACNT` + `-` + TC de la facture d'origine (AVOIR-0001, 15:13) ; toute autre RN
                # essayée (signature brute ou à tirets, FN, numéro, `NIM-TC` sans ACNT) : « Erreur de format RN! » + RN
                if len(champs) == 7:
                    return E_FORMAT
                if len(champs) != 10 or champs[4] != "COR":
                    return INCONNU  # autres natures et autres formes : jamais essayées
                rn = re.fullmatch(r"(?:%s-1|\{NIM-ACNT\})-(\d+)" % NIM, champs[5])
                if not (rn and int(rn.group(1)) in self.certifiees):
                    return ("E:Erreur de format RN! " + champs[5]).encode()
                self.redemarrer()
                self.ouverte, self.psvb, self.type, self.ttc, self.fn = True, champs[9], champs[3], champs[6] != "HT", champs[8]
                client, self.client = self.client, None
                return ("%d,%d,%s" % (self.avoirs + 1, self.tc + 1, client if client is not None else ",,,,,")).encode()
            # PSVB : 8e champ à 8 champs, dernier à 10 ; `x` refusé, `A` accepté (15 octobre)
            psvb = champs[7] if len(champs) == 8 else champs[9] if len(champs) == 10 else None
            if psvb is not None and psvb not in TAUX_PSVB:
                return "E:PSVB n'existe pas!".encode()
            self.redemarrer()
            self.ouverte, self.psvb = True, psvb
            self.type, self.ttc = champs[3], (champs[4] if len(champs) > 4 else "") != "HT"
            self.fn = champs[6] if len(champs) > 6 else ""
            client, self.client = self.client, None
            if client is not None:
                return ("%d,%d,%s" % (self.ventes + 1, self.tc + 1, client)).encode()
            return None
        if cmd == 0x36:
            if not self.ouverte:
                return "E:La commande C0 doit être soumise en premier".encode()
            r = C36_OBSERVE.get(data, INCONNU)
            if r == b"R":
                self.commentaires += 1
            return r
        if cmd == 0x31:
            if not self.ouverte:
                return C0_EN_PREMIER
            # 2026-10-28 : la forme RDC `nom⇥TYPE,X%Y⇥prix` est lue. Format sans `%`, ou `;` sans `T` au prix ;
            # puis le type (BIE, IMPSERV : n'existe pas) ; puis la taxe : sans PSVB au C0, toujours incorrecte
            parties = data.split(b"\t")
            if len(parties) == 3 and b"," in parties[1]:
                ty, _, tx = parties[1].partition(b",")
                if b"%" not in tx or re.search(rb";(?!T)", parties[2]):
                    return E_FORMAT
                if ty in TYPES_NON_ESSAYES:
                    return INCONNU
                if ty not in TYPES_ARTICLE:
                    return "E:Le type de produit n'existe pas".encode()
                if self.psvb is None:
                    return E_TAXE
                return self.article(ty, tx, parties[2])
            # forme sans type : plus de 500 refusées (09 au 15)
            return E_FORMAT
        if cmd == 0x33 and self.ouverte and self.articles and not self.ttc:
            return INCONNU  # sous-total d'une facture HT : jamais vu
        if cmd == 0x33 and self.ouverte and self.articles:
            total, ttc, tva, psvb = self.montants()
            return ",".join(nombre(v) for v in [total] + ttc + tva + [psvb, 0.0]).encode()
        if cmd == 0x35 and self.ouverte and self.articles:
            m = re.fullmatch(rb"[EMAVCD](-?[0-9.]+)", data)  # E, M, A (crédit), V, C, D essayés ; un négatif passe
            if not m:
                return INCONNU
            self.paye += float(m.group(1)); self.paiements += 1
            ecart = round(self.paye - self.montants()[0], 2)
            if abs(ecart) < 0.005:
                return b"R0"
            # reste dû écrit en négatif (R-114.2, R-228.4) ; un excédent n'a jamais été vu
            return b"R" + nombre(ecart).encode() if ecart < 0 else INCONNU
        if cmd == 0x38 and self.ouverte and self.articles:
            return self.normaliser(data)
        if cmd == 0x38 and self.ouverte and not self.articles and data:
            return "E:La commande 35 doit être soumise en premier.".encode()  # 38 `C`, 2026-10-28
        if cmd in (0x33, 0x35, 0x38) and self.ouverte and not self.articles:
            # 2026-10-16 : après une 36 acceptée, le 33 ajoute un point final (jamais vu avant, sans 36 : 12 octobre)
            point = b"." if self.commentaires and cmd == 0x33 else b""
            return {0x33: b"E:Veuillez ajouter le produit en premier" + point,
                    0x35: "E:Le montant payé est suffisant".encode(),
                    0x38: "E:Aucune donnée valide n'a été reçue".encode()}[cmd]
        if cmd in (0xC1, 0xC2):
            self.redemarrer()  # C1 et C2 annulent la facture ouverte, sans la compter (2026-10-12)
            return None
        if cmd == 0x2B:
            return None
        return INCONNU

    def noter(self, texte):
        if self.journal:
            with open(self.journal, "a", encoding="utf-8") as j:
                j.write(time.strftime("%H:%M:%S ") + texte + "\n")

    def donnees(self, cmd, data):
        maintenant = time.strftime("%Y%m%d%H%M%S")
        if self.variante == "FIS":
            r = self.fis(cmd, data)
            if r is not None:
                return r
        if cmd == 0xC1:
            vides = ",,,," if self.variante == "NE" else ",,,,,,"  # BF et FIS : 31 champs
            r = "%s-1,%s,%s,%d,%d,%d%s%s,%s" % (NIM, IFU, maintenant, self.tc, self.ventes, self.avoirs, vides, TAUX, PSVB)
        elif cmd == 0xC2:
            r = "%d,%d,%s" % (self.tc, self.tc, maintenant)
        elif cmd == 0x2B:
            r = SOCIETE.get(data[:2], "")
        elif cmd == 0xC3:
            r = "1"
        elif cmd == 0xC0:
            # ECOHADA (NE) exige exactement 7 champs (0x40a503) ; l'appareil BF en a renvoyé 8 le 2026-10-09
            self.total = 0.0
            champs = data.decode("latin-1").split(",")
            self.type = champs[3] if len(champs) > 3 else "FV"
            self.ttc = "HT" not in champs[4:6]
            r = "%d,%d" % (self.ventes + 1, self.tc + 1) + "," * (5 if self.variante == "NE" else 6)
        elif cmd == 0x31:
            # nom<TAB><groupe><taux>%<montant de la ligne><TAB><prix>*<qté>[;T<col 5>,<col 6>] (vu le 2026-10-10)
            m = re.search(rb"\t[A-Z]([0-9.]+)%(-?[0-9.]+)\t", data)
            if m:
                montant = float(m.group(2))
                self.total += montant if self.ttc else montant * (1 + float(m.group(1)) / 100)
            r = "%.0f,0,0,0,0" % self.total
        elif cmd == 0x33:
            r = "%.0f" % self.total + ",0" * 14
        elif cmd == 0x35:
            r = "R"
        elif cmd == 0x38:
            self.ventes += 1; self.tc += 1
            r = "%d,%d,%s,%s,%s,%s,%s" % (self.ventes, self.tc, self.type, maintenant, NIM, IFU, SIGNATURE)
        else:
            r = ""
        return r.encode("latin-1")

    def servir(self, fd, nombre=None):
        vues = 0
        while nombre is None or vues < nombre:
            req = lire_requete(fd)
            if not req:
                return
            seq, cmd, data = req[2], req[3], req[4:-6]
            self.noter("recu  %02X seq=%02X donnees=%r hex=%s" % (cmd, seq, data.decode("latin-1"), req.hex(" ")))
            rep = self.repondre(seq, cmd, data)
            d = rep.index(1)
            self.noter("envoi %02X %sdonnees=%r" % (cmd, "NAK " if d else "", rep[d+4:rep.index(4, d)].decode("latin-1")))
            time.sleep(self.latence)
            os.write(fd, rep)
            vues += 1


def main(argv=None):
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("--lien", required=True)
    a.add_argument("--journal", required=True)
    a.add_argument("--variante", choices=("NE", "BF", "FIS"), default="NE")
    o = a.parse_args(argv)
    maitre, esclave = os.openpty()
    tty.setraw(esclave)
    if os.path.lexists(o.lien):
        os.remove(o.lien)
    os.symlink(os.ttyname(esclave), o.lien)
    print("faux MCF %s sur %s" % (o.variante, os.ttyname(esclave)), flush=True)
    FauxMCF(o.variante, o.journal).servir(maitre)


if __name__ == "__main__":
    sys.exit(main())
