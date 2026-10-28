import os
import tempfile
import threading
import tty
import unittest

from appareil.trame import bcc_ok, trame
from simulateur.faux_mcf import C0_EN_PREMIER, INCONNU, FauxMCF, lire_requete, reponse


class Reponse(unittest.TestCase):
    def test_longueur_comme_l_appareil(self):
        # 2B I1 du 2026-10-09 : 6 octets de données, LEN 0x31, 23 octets en tout
        r = reponse(0x21, 0x2B, b"abcdef")
        self.assertEqual((r[1], len(r)), (0x31, 23))

    def test_bcc_et_statut(self):
        r = reponse(0x20, 0xC1, b"1,2,3")
        self.assertIs(bcc_ok(r), True)
        self.assertEqual(r[r.index(4) + 1:r.index(5, r.index(4))], b"\x80" * 6)


class Commandes(unittest.TestCase):
    def setUp(self):
        self.mcf = FauxMCF()

    def test_c1_niger_29_champs(self):
        self.assertEqual(len(self.mcf.donnees(0xC1, b"").split(b",")), 29)

    def test_c1_burkina_31_champs(self):
        self.assertEqual(len(FauxMCF(variante="BF").donnees(0xC1, b"").split(b",")), 31)

    def test_c3_un_champ(self):
        self.assertEqual(len(self.mcf.donnees(0xC3, b"x,y,,,").split(b",")), 1)

    def test_c0_niger_7_champs_comme_ecohada(self):
        self.assertEqual(len(self.mcf.donnees(0xC0, b"1,a").split(b",")), 7)

    def test_c0_burkina_8_champs_comme_l_appareil(self):
        self.assertEqual(FauxMCF(variante="BF").donnees(0xC0, b"1,a"), b"1,3,,,,,,")

    def test_33_total_des_montants_de_ligne(self):
        self.mcf.donnees(0x31, b"UN\tB18.0%2360\t1180*2")
        self.mcf.donnees(0x31, b"DEUX\tA0.0%500\t500*1")
        champs = self.mcf.donnees(0x33, b"").split(b",")
        self.assertGreaterEqual(len(champs), 9)
        self.assertEqual(float(champs[0]), 2860)

    def test_33_montant_avec_taxe_specifique(self):
        self.mcf.donnees(0x31, b"TROIS\tB18.0%1190\t1180*1;T50,59")
        self.assertEqual(self.mcf.donnees(0x33, b"").split(b",")[0], b"1190")

    def test_33_mode_ht_converti_en_ttc(self):
        self.mcf.donnees(0xC0, b"1,Vendeur,{IFU},FV,HT,ISF-ESSAI,R1")
        self.mcf.donnees(0x31, b"UN\tB18.0%2000\t1000*2")
        self.assertEqual(self.mcf.donnees(0x33, b"").split(b",")[0], b"2360")

    def test_35_commence_par_r(self):
        self.assertTrue(self.mcf.donnees(0x35, b"E2860").startswith(b"R"))

    def test_38_sept_champs(self):
        self.assertEqual(len(self.mcf.donnees(0x38, b"").split(b",")), 7)


class JumeauFisNano(unittest.TestCase):
    """Variante FIS : uniquement ce que l'appareil a répondu (2026-10-09 et 2026-10-12)."""

    def setUp(self):
        self.mcf = FauxMCF(variante="FIS")

    def ouvrir(self):
        self.assertEqual(self.mcf.donnees(0xC0, b"1,Essai,{IFU},FV,TTC,ISF-ESSAI,ESSAI-0002"), b"1,3,,,,,,")

    def test_c1_31_champs(self):
        self.assertEqual(len(self.mcf.donnees(0xC1, b"").split(b",")), 31)

    def test_31_sans_facture(self):
        self.assertEqual(self.mcf.donnees(0x31, b"ARTICLE TEST\tB18.0%100\t100*1"),
                         "E:La commande C0 doit être soumise en premier".encode())

    def test_c3_types_refuses(self):
        for d in (b",ESSAI,,,", b",CLIENT COMPTANT,CC,,", b",CLIENT COMPTANT,,CC,", b",CLIENT COMPTANT,1,,"):
            self.assertEqual(self.mcf.donnees(0xC3, d), b"E:Erreur de type de destinataire")

    def test_c0_beninois_refuse(self):
        self.assertEqual(self.mcf.donnees(0xC0, b"1,Essai,{IFU},0.0,18.0,10.0,0.0,FV"),
                         "E:Erreur de format des données ou incompatibilité".encode())

    def test_31_formes_essayees_refusees(self):
        self.ouvrir()
        for d in (b"ARTICLE TEST\tB100*1", b"ARTICLE TEST\tB18.0%\t100*1", b"ARTICLE TEST\tB18.0%0\t100*1",
                  b"ARTICLE TEST\tB18.0%100\t100*1", b"ARTICLE TEST\nART001\tB18.0%100\t100*1",
                  b"ARTICLE TEST\tA0.0%100\t100*1", b"ARTICLE TEST\nLOCBIE\tB18.0%100\t100*1"):
            self.assertEqual(self.mcf.donnees(0x31, d), "E:Erreur de format des données ou incompatibilité".encode())

    def test_facture_sans_article(self):
        self.ouvrir()
        self.assertEqual(self.mcf.donnees(0x33, b""), b"E:Veuillez ajouter le produit en premier")
        self.assertEqual(self.mcf.donnees(0x35, b"E100"), "E:Le montant payé est suffisant".encode())
        self.assertEqual(self.mcf.donnees(0x38, b""), "E:Aucune donnée valide n'a été reçue".encode())

    def test_31_forme_rdc_bute_sur_la_taxe(self):
        # 2026-10-28, ESSAI-0007 : premier message autre que celui de format
        self.ouvrir()
        self.assertEqual(self.mcf.donnees(0x31, b"ARTICLE TEST\tLOCBIE,B18.00%100.00\t100.00"),
                         "E:La taxe est incorrecte!".encode())

    def test_31_forme_rdc_format_puis_type_puis_taxe(self):
        # 2026-10-28 : grille `taxe` jusqu'à la 17e trame
        self.ouvrir()
        f = "E:Erreur de format des données ou incompatibilité".encode()
        self.assertEqual(self.mcf.donnees(0x31, b"ARTICLE TEST\tLOCBIE,B100.00\t100.00"), f)
        self.assertEqual(self.mcf.donnees(0x31, b"ARTICLE TEST\tLOCBIE,B18.00%100.00\t100.00;0.00"), f)
        for ty in (b"BIE", b"IMPSERV"):
            self.assertEqual(self.mcf.donnees(0x31, b"ARTICLE TEST\t" + ty + b",B18.00%100.00\t100.00"),
                             "E:Le type de produit n'existe pas".encode())
        for ty in (b"LOCSER", b"IMPBIE"):
            self.assertEqual(self.mcf.donnees(0x31, b"ARTICLE TEST\t" + ty + b",B18.00%100.00\t100.00"),
                             "E:La taxe est incorrecte!".encode())
        for tx in (b"B18.0%100.00", b"A0%100.00", b"B%100.00", b"18.00%100.00", b"B0.18%100.00"):
            self.assertEqual(self.mcf.donnees(0x31, b"ARTICLE TEST\tLOCBIE," + tx + b"\t100.00"),
                             "E:La taxe est incorrecte!".encode())

    def test_38_avec_donnees_demande_35(self):
        # 2026-10-28 : 38 `C` (annulation de la RDC) sur une facture sans article
        self.ouvrir()
        self.assertEqual(self.mcf.donnees(0x38, b"C"), "E:La commande 35 doit être soumise en premier.".encode())

    def test_c3_facture_ouverte_nak_et_statut_a2(self):
        self.ouvrir()
        r = self.mcf.repondre(0x3F, 0xC3, b",CLIENT COMPTANT,1,,")
        self.assertEqual(r.hex(" "), "15 01 2b 3f c3 04 a2 80 80 80 80 80 05 30 34 35 38 03")

    def test_redemarrage_perd_la_facture_sans_la_compter(self):
        self.ouvrir()
        avant = self.mcf.donnees(0xC1, b"").split(b",")[3:6]
        self.mcf.redemarrer()
        self.assertEqual(self.mcf.donnees(0xC1, b"").split(b",")[3:6], avant)
        self.assertEqual(self.mcf.donnees(0x31, b"X\tB100*1"), "E:La commande C0 doit être soumise en premier".encode())

    def test_cas_jamais_observe_signale(self):
        self.assertEqual(self.mcf.donnees(0x33, b""), INCONNU)

    def test_crochet_un_seul_c3_nouveau(self):
        mcf = FauxMCF(variante="FIS", nouveau=(b",,5,,", b"E:message nouveau"))
        self.assertEqual(mcf.donnees(0xC3, b",,5,,"), b"E:message nouveau")
        self.assertEqual(mcf.donnees(0xC3, b",ESSAI,,,"), b"E:Erreur de type de destinataire")

    def test_c3_observes_le_15_octobre(self):
        mcf = FauxMCF(variante="FIS")
        self.assertEqual(mcf.donnees(0xC3, b""), b"R")
        self.assertEqual(mcf.donnees(0xC3, b"99988776,CLIENT TEST,,,"), b"R")
        self.assertEqual(mcf.donnees(0xC3, b"PP,CLIENT TEST,,,,,"), b"R")
        self.assertEqual(mcf.donnees(0xC3, b"PP,PP,PP,PP,PP,PP,PP"),
                         "E:L'adresse e-mail du destinataire n'est pas valide".encode())
        self.assertEqual(mcf.donnees(0xC3, b"PP,PP,PP,PP,PP,PP"), b"E:Erreur de type de destinataire")

    def test_c3_non_observe_garde_le_message_connu(self):
        self.assertEqual(FauxMCF(variante="FIS").donnees(0xC3, b",CLIENT COMPTANT,CC,,"),
                         b"E:Erreur de type de destinataire")

    def test_crochet_ignore_si_facture_ouverte(self):
        mcf = FauxMCF(variante="FIS", nouveau=(b",,5,,", b"E:message nouveau"))
        self.assertEqual(mcf.donnees(0xC0, b"1,Essai,{IFU},FV,TTC,ISF-ESSAI,ESSAI-0002"), b"1,3,,,,,,")
        r = mcf.repondre(0x40, 0xC3, b",,5,,")
        self.assertEqual(r[0], 0x15)

    def test_36_sans_facture(self):
        self.assertEqual(self.mcf.donnees(0x36, b"A,ESSAI"),
                         "E:La commande C0 doit être soumise en premier".encode())

    def test_36_observee_le_16_octobre(self):
        self.ouvrir()
        self.assertEqual(self.mcf.donnees(0x36, b"A,ESSAI"), b"R")
        for data in (b"ESSAI", b"Z,ESSAI", b"A,ESSAI,X"):
            self.assertEqual(self.mcf.donnees(0x36, data), "E:Aucune donnée valide n'a été reçue".encode())

    def test_36_acceptee_ne_compte_pas_comme_article(self):
        self.ouvrir()
        self.assertEqual(self.mcf.donnees(0x33, b""), b"E:Veuillez ajouter le produit en premier")
        self.mcf.donnees(0x36, b"A,ESSAI")
        # message avec point final : observé le 16 octobre après une 36 acceptée
        self.assertEqual(self.mcf.donnees(0x33, b""), b"E:Veuillez ajouter le produit en premier.")

    def test_36_jamais_observee_est_inconnue(self):
        self.ouvrir()
        self.assertEqual(self.mcf.donnees(0x36, b"B,AUTRE"), INCONNU)

    def test_2b_i5_nak_a1(self):
        r = self.mcf.repondre(0x70, 0x2B, b"I5")
        self.assertEqual(r[0], 0x15)
        self.assertEqual(r[r.index(4) + 1:r.index(5, r.index(4))], b"\xa1" + b"\x80" * 5)
        self.assertIs(bcc_ok(r[1:]), True)

    def test_2b_i0_inchange(self):
        r = self.mcf.repondre(0x70, 0x2B, b"I0")
        self.assertEqual(r[0], 0x01)


E_FORMAT_ATTENDU = "E:Erreur de format des données ou incompatibilité".encode()


class CycleFisNano(unittest.TestCase):
    """Le cycle accepté le 2026-10-28 (ESSAI-0008), réponse par réponse, puis ce qui n'a jamais été vu."""

    C3 = b"PP,CLIENT TEST,,,70123456,client@example.com,"
    C0 = b"1,Essai,{IFU},FV,TTC,ISF-ESSAI,ESSAI-0008,A"
    ARTICLE = b"ARTICLE TEST\tLOCBIE,B18.0%100.00\t100.00*1"
    SOUS_TOTAL = ("102.0,0.0,100.0" + ",0.0" * 15 + ",15.25" + ",0.0" * 14 + ",2.0,0.0").encode()

    def setUp(self):
        self.mcf = FauxMCF(variante="FIS")

    def ouvrir(self, c0=C0):
        self.assertEqual(self.mcf.donnees(0xC3, self.C3), b"R")
        self.assertEqual(self.mcf.donnees(0xC0, c0), b"1,3,CLIENT TEST,,,70123456,client@example.com,")

    def test_cycle_du_28_octobre(self):
        self.ouvrir()
        self.assertEqual(self.mcf.donnees(0x31, self.ARTICLE), b"100.0,84.75,15.25,0.0")
        self.assertEqual(self.mcf.donnees(0x33, b""), self.SOUS_TOTAL)
        self.assertEqual(len(self.SOUS_TOTAL.split(b",")), 35)
        self.assertEqual(self.mcf.donnees(0x35, b"E102.00"), b"R0")
        for d in (b"102.00,15.25", b"102.0,15.25", b"102,15.25", b"102.00,15.25,2.00", b"102,15,2"):
            self.assertEqual(self.mcf.donnees(0x38, d), "E:MV n'est pas un nombre valide.".encode())
        f = self.mcf.donnees(0x38, b"102.00").decode().split(",")
        self.assertEqual(len(f), 8)
        self.assertEqual(f[:3], ["1", "3", "FV"])
        self.assertRegex(f[3], r"^\d{14}$")
        self.assertEqual((f[4], f[5], f[7]), ("XX99999999-1", "99999999Z", "ESSAI-0008"))
        self.assertRegex(f[6], r"^[A-Z2-7]{24}$")
        self.assertEqual(self.mcf.donnees(0xC2, b"").split(b",")[:2], [b"3", b"3"])  # 12:53 : 3,3
        self.assertEqual(self.mcf.donnees(0x31, self.ARTICLE), C0_EN_PREMIER)  # facture close

    def test_sans_psvb_toute_taxe_est_incorrecte(self):
        self.ouvrir(b"1,Essai,{IFU},FV,TTC,ISF-ESSAI,ESSAI-0007")
        self.assertEqual(self.mcf.donnees(0x31, self.ARTICLE), "E:La taxe est incorrecte!".encode())

    def test_psvb_inconnu_refuse(self):
        self.assertEqual(self.mcf.donnees(0xC0, b"1,Essai,{IFU},FV,TTC,ISF-ESSAI,R,x"), "E:PSVB n'existe pas!".encode())

    def test_c1_annule_la_facture(self):
        self.ouvrir()
        self.mcf.donnees(0x31, self.ARTICLE)
        self.mcf.donnees(0xC1, b"")
        self.assertEqual(self.mcf.donnees(0x33, b""), INCONNU)  # plus de facture ouverte : jamais vu

    def test_38_avant_le_paiement(self):
        self.ouvrir()
        self.mcf.donnees(0x31, self.ARTICLE)
        self.assertEqual(self.mcf.donnees(0x38, b"102.00"), "E:La commande 35 doit être soumise en premier.".encode())

    def test_jamais_vu_reste_inconnu(self):
        self.ouvrir()
        self.assertEqual(self.mcf.donnees(0x31, b"ARTICLE TEST\tLOCBIE,B10.0%100.00\t100.00*1"), INCONNU)  # taux faux
        self.assertEqual(self.mcf.donnees(0x31, b"ARTICLE TEST\tLOCBIE,B18.0%90.00\t100.00*1"), INCONNU)  # montant faux
        self.mcf.donnees(0x31, self.ARTICLE)
        self.assertEqual(self.mcf.donnees(0x35, b"V102.00"), INCONNU)  # virement : jamais essayé
        self.assertEqual(self.mcf.donnees(0x35, b"E150.00"), INCONNU)  # excédent : jamais vu
        self.assertEqual(self.mcf.donnees(0x38, b"99.00"), INCONNU)  # MV faux

    def test_facture_du_28_a_14h44(self):
        # ESSAI-0009 : un bien B, un service C ; PSVB sur les deux ; reste dû en négatif ; montant négatif accepté ;
        # certifiée alors qu'elle n'était pas soldée
        self.mcf = FauxMCF(variante="FIS")
        self.mcf.ventes, self.mcf.tc = 1, 3
        self.mcf.donnees(0xC3, self.C3)
        self.assertEqual(self.mcf.donnees(0xC0, b"1,Essai,{IFU},FV,TTC,ISF-ESSAI,ESSAI-0009,A"),
                         b"2,4,CLIENT TEST,,,70123456,client@example.com,")
        self.assertEqual(self.mcf.donnees(0x31, self.ARTICLE), b"100.0,84.75,15.25,0.0")
        self.assertEqual(self.mcf.donnees(0x31, b"POSE TEST\tLOCSER,C10.0%110.00\t110.00*1"), b"110.0,100.0,10.0,0.0")
        self.assertEqual(self.mcf.donnees(0x33, b""), b"214.2,0.0,100.0,110.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,"
                         b"0.0,0.0,0.0,0.0,0.0,15.25,10.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,4.2,0.0")
        self.assertEqual(self.mcf.donnees(0x35, b"M100.00"), b"R-114.2")
        self.assertEqual(self.mcf.donnees(0x35, b"E-114.20"), b"R-228.4")
        self.assertEqual(self.mcf.donnees(0x38, b"214.20").split(b",")[:3], [b"2", b"4", b"FV"])

    def test_avoir_a_sept_champs_format(self):
        self.assertEqual(self.mcf.donnees(0xC0, b"1,Essai,{IFU},FA,TTC,ISF-ESSAI,AV-1"), E_FORMAT_ATTENDU)

    def test_avoir_rn_refusees_le_28(self):
        for rn in (b"ABCDEFGHIJKLMNOPQRSTUV23", b"ABCD-EFGH-IJKL-MNOP-QRST-UV23", b"ESSAI-0009", b"2", b"XX99999999-4"):
            self.assertEqual(self.mcf.donnees(0xC0, b"1,Essai,{IFU},FA,COR," + rn + b",TTC,ISF-ESSAI,AV-1,A"),
                             b"E:Erreur de format RN! " + rn)

    def test_avoir_d_une_facture_certifiee(self):
        # AVOIR-0001, 15:13 : RN = NIM-ACNT-TC d'origine ; avoir n°1 ; compteur des avoirs à part ; type FA au 38
        self.ouvrir()
        self.mcf.donnees(0x31, self.ARTICLE); self.mcf.donnees(0x35, b"E102.00")
        self.assertEqual(self.mcf.donnees(0x38, b"102.00").split(b",")[:3], [b"1", b"3", b"FV"])
        self.mcf.donnees(0xC3, self.C3)
        self.assertEqual(self.mcf.donnees(0xC0, b"1,Essai,{IFU},FA,COR,XX99999999-1-3,TTC,ISF-ESSAI,AV-1,A"),
                         b"1,4,CLIENT TEST,,,70123456,client@example.com,")
        self.mcf.donnees(0x31, self.ARTICLE)
        self.assertEqual(self.mcf.donnees(0x35, b"E102.00"), b"R0")
        f = self.mcf.donnees(0x38, b"102.00").split(b",")
        self.assertEqual((f[0], f[1], f[2], f[7]), (b"1", b"4", b"FA", b"AV-1"))
        self.assertEqual(self.mcf.donnees(0xC1, b"").split(b",")[3:6], [b"4", b"1", b"1"])

    def test_38_c_apres_le_35_annule_sans_compter(self):
        # 2026-10-28 14:56 : ESSAI-0010 payée puis annulée ; C1 suivant : compteurs inchangés, statut normal
        self.ouvrir()
        self.mcf.donnees(0x31, self.ARTICLE)
        self.assertEqual(self.mcf.donnees(0x38, b"C"), "E:La commande 35 doit être soumise en premier.".encode())
        self.mcf.donnees(0x35, b"E102.00")
        self.assertEqual(self.mcf.donnees(0x38, b"C"), b"E:ANNULEE")
        self.assertEqual((self.mcf.ventes, self.mcf.tc, self.mcf.ouverte), (0, 2, False))

    def test_ht_montant_ttc_prix_ht(self):
        # ESSAI-0011, 15:42 et 15:46 : C0 HT accepté ; montant = prix × qté refusé ; montant TTC, prix HT accepté
        self.mcf.donnees(0xC3, self.C3)
        self.assertEqual(self.mcf.donnees(0xC0, b"1,Essai,{IFU},FV,HT,ISF-ESSAI,ESSAI-0011,A")[:4], b"1,3,")
        self.assertEqual(self.mcf.donnees(0x31, self.ARTICLE), b"E:Mismatch de montant")
        self.assertEqual(self.mcf.donnees(0x31, b"ARTICLE TEST\tLOCBIE,B18.0%118.00\t100.00*1"), b"118.0,100.0,18.0,0.0")
        self.assertEqual(self.mcf.donnees(0x33, b""), INCONNU)

    def test_credit_en_mode_a(self):
        self.ouvrir()
        self.mcf.donnees(0x31, self.ARTICLE)
        self.assertEqual(self.mcf.donnees(0x35, b"A102.00"), b"R0")

    def test_paiement_en_deux_fois_solde(self):
        self.ouvrir()
        self.mcf.donnees(0x31, self.ARTICLE)
        self.assertEqual(self.mcf.donnees(0x35, b"M50.00"), b"R-52.0")
        self.assertEqual(self.mcf.donnees(0x35, b"E52.00"), b"R0")


class Liaison(unittest.TestCase):
    def test_aller_retour_sur_pty_et_journal(self):
        maitre, esclave = os.openpty()
        tty.setraw(esclave)
        with tempfile.TemporaryDirectory() as d:
            journal = os.path.join(d, "j.log")
            mcf = FauxMCF(journal=journal)
            t = threading.Thread(target=mcf.servir, args=(maitre, 1), daemon=True)
            t.start()
            os.write(esclave, trame(0x20, 0xC1))
            r = lire_requete(esclave)
            t.join(2)
            self.assertIs(bcc_ok(r), True)
            self.assertEqual(r[3], 0xC1)
            self.assertIn("C1", open(journal, encoding="utf-8").read())
        os.close(maitre); os.close(esclave)

    def test_nak_du_jumeau_passe_par_le_pty(self):
        maitre, esclave = os.openpty()
        tty.setraw(esclave)
        mcf = FauxMCF(variante="FIS")
        mcf.donnees(0xC0, b"1,Essai,X,FV,TTC,S,R")
        t = threading.Thread(target=mcf.servir, args=(maitre, 1), daemon=True)
        t.start()
        os.write(esclave, trame(0x3F, 0xC3, b",C,1,,"))
        self.assertEqual(os.read(esclave, 1), b"\x15")
        r = lire_requete(esclave)
        t.join(2)
        self.assertIs(bcc_ok(r), True)
        os.close(maitre); os.close(esclave)


if __name__ == "__main__":
    unittest.main()
