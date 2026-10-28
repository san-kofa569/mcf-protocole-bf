import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

from appareil.cycle import BIEN, CLIENT, SERVICE, etapes, main
from appareil.signature import signature
from simulateur.faux_mcf import FauxMCF


def lancer(*argv, mcf=None):
    sortie = io.StringIO()
    with redirect_stdout(sortie):
        code = main(list(argv), mcf=mcf)
    return code, sortie.getvalue()


class Etapes(unittest.TestCase):
    def test_simple_est_la_facture_du_28(self):
        e = etapes("simple", "ESSAI-0009")
        self.assertEqual([c for _, c, _ in e], [0xC3, 0xC0, 0x31, 0x33, 0x35, 0x38])
        self.assertEqual(e[0][2], CLIENT)
        self.assertEqual(e[1][2], "1,Essai,{IFU},FV,TTC,ISF-ESSAI,ESSAI-0009,A")
        self.assertEqual(e[2][2], BIEN)
        self.assertEqual(e[4][2]({"total": 102.0}), "E102.00")
        self.assertEqual(e[5][2]({"total": 102.0}), "102.00")

    def test_deux_lignes_mobile_puis_reste(self):
        e = etapes("deux", "ESSAI-0009")
        self.assertEqual([n for n, _, _ in e][2:], ["bien", "service", "sous-total", "mobile", "reste", "normalisation"])
        self.assertEqual(e[3][2], SERVICE)
        self.assertEqual(e[5][2], "M100.00")
        self.assertEqual(e[6][2]({"du": 114.2}), "E114.20")

    def test_annulation_finit_par_38_c(self):
        self.assertEqual(etapes("annulation", "X")[-1], ("annulation", 0x38, "C"))


class AuJumeau(unittest.TestCase):
    def test_simple_va_jusqu_a_la_facture_certifiee(self):
        code, sortie = lancer("--scenario", "simple", "--fn", "ESSAI-0009", "--jumeau")
        self.assertEqual(code, 0)
        self.assertIn("article 31 'ARTICLE TEST\\tLOCBIE,B18.0%100.00\\t100.00*1' -> 100.0,84.75,15.25,0.0", sortie)
        self.assertIn("paiement 35 'E102.00' -> R0", sortie)
        self.assertIn("normalisation 38 '102.00' -> accepté : 8 champs, compteurs 1/3 FV", sortie)

    def test_annulation_apres_paiement_non_comptee(self):
        mcf = FauxMCF(variante="FIS")
        code, sortie = lancer("--scenario", "annulation", "--fn", "ESSAI-0010", "--jumeau", mcf=mcf)
        self.assertEqual(code, 0)
        self.assertIn("annulation 38 'C' -> E:ANNULEE", sortie)
        self.assertEqual((mcf.ventes, mcf.tc, mcf.ouverte), (0, 2, False))

    def test_la_cloture_ne_montre_ni_nim_ni_ifu_ni_signature(self):
        code, sortie = lancer("--scenario", "simple", "--fn", "ESSAI-0009", "--jumeau")
        self.assertNotIn("XX99999999", sortie)
        self.assertNotIn("99999999Z", sortie)

    def test_deux_paie_le_reste_du_et_solde(self):
        # 14:44 sur l'appareil : R-114.2 veut dire 114.2 dû ; le client paie 114.20, pas -114.20
        code, sortie = lancer("--scenario", "deux", "--fn", "ESSAI-0009", "--jumeau")
        self.assertEqual(code, 0)
        self.assertIn("sous-total 33 '' -> 214.2,", sortie)
        self.assertIn("mobile 35 'M100.00' -> R-114.2", sortie)
        self.assertIn("reste 35 'E114.20' -> R0", sortie)
        self.assertIn("normalisation 38 '214.20' -> accepté", sortie)

    def test_pas_de_38_sur_une_facture_non_soldee(self):
        e = [("client", 0xC3, CLIENT), ("ouverture", 0xC0, "1,Essai,{IFU},FV,TTC,ISF-ESSAI,X,A"),
             ("article", 0x31, BIEN), ("sous-total", 0x33, ""), ("mobile", 0x35, "M50.00"),
             ("normalisation", 0x38, "102.00")]
        mcf = FauxMCF(variante="FIS")
        with mock.patch("appareil.cycle.etapes", lambda s, fn: e):
            code, sortie = lancer("--scenario", "simple", "--fn", "X", "--jumeau", mcf=mcf)
        self.assertEqual(code, 1)
        self.assertIn("ARRÊT avant envoi, la facture n'est pas soldée (reste 52.0)", sortie)
        self.assertEqual(mcf.ventes, 0)

    def test_jamais_de_paiement_negatif(self):
        e = [("client", 0xC3, CLIENT), ("reste", 0x35, "E-114.20")]
        with mock.patch("appareil.cycle.etapes", lambda s, fn: e), mock.patch.object(FauxMCF, "repondre") as r:
            r.side_effect = lambda seq, cmd, d: __import__("simulateur.faux_mcf", fromlist=["reponse"]).reponse(seq, cmd, b"R")
            code, sortie = lancer("--scenario", "simple", "--fn", "X", "--jumeau")
        self.assertEqual(code, 1)
        self.assertIn("ARRÊT avant envoi, paiement nul ou négatif", sortie)
        self.assertEqual(r.call_count, 1)  # seul le C3 est parti

    def test_sans_psvb_l_arret_vient_de_la_31(self):
        mcf = FauxMCF(variante="FIS")
        with mock.patch("appareil.cycle.etapes", lambda s, fn: [
                ("ouverture", 0xC0, "1,Essai,{IFU},FV,TTC,ISF-ESSAI,%s" % fn), ("article", 0x31, BIEN)]):
            code, sortie = lancer("--scenario", "simple", "--fn", "X", "--jumeau", mcf=mcf)
        self.assertEqual(code, 1)
        self.assertIn("E:La taxe est incorrecte!", sortie)


class AvoirNimTc(FauxMCF):
    """Jumeau d'essai : C0 d'avoir lu, RN accepté à la 2e forme (hypothèse, pour éprouver le client)."""

    def fis(self, cmd, data):
        if cmd == 0xC0 and data.startswith(b"1,Essai,{IFU},FA,COR,"):
            champs = data.split(b",")
            if champs[5] != b"{NIM-ACNT}-4":
                return b"E:Erreur de format RN! " + champs[5]
            return super().fis(cmd, b"1,Essai,{IFU},FV,TTC,ISF-ESSAI," + champs[8] + b",A")
        return super().fis(cmd, data)


class Avoir(unittest.TestCase):
    def test_formes_de_rn(self):
        e = etapes("avoir", "AVOIR-0001", ("ESSAI-0009", "2", "4"))
        self.assertEqual([c0.split(",")[5] for _, c0 in e[0][2]], ["{NIM}-4", "{NIM-ACNT}-4", "2/4 FV", "{NIM}-2"])

    def test_au_jumeau_la_premiere_forme_est_inconnue(self):
        mcf = FauxMCF(variante="FIS")
        code, sortie = lancer("--scenario", "avoir", "--fn", "AVOIR-0001", "--jumeau", mcf=mcf)
        self.assertEqual(code, 1)
        self.assertIn("ouverture rn-nim-tc C0 '1,Essai,{IFU},FA,COR,{NIM}-4,TTC,ISF-ESSAI,AVOIR-0001,A' -> E:??", sortie)
        self.assertFalse(mcf.ouverte)

    def test_forme_suivante_tant_que_rn_est_refuse_et_valeur_masquee(self):
        code, sortie = lancer("--scenario", "avoir", "--fn", "AVOIR-0001", "--jumeau", mcf=AvoirNimTc(variante="FIS"))
        self.assertEqual(code, 0)
        self.assertIn("ouverture rn-nim-tc C0 '1,Essai,{IFU},FA,COR,{NIM}-4,TTC,ISF-ESSAI,AVOIR-0001,A' -> "
                      "E:Erreur de format RN! (valeur renvoyée masquée)", sortie)
        self.assertIn("ouverture rn-nim-acnt-tc C0 '1,Essai,{IFU},FA,COR,{NIM-ACNT}-4,TTC,ISF-ESSAI,AVOIR-0001,A' -> 1,3,", sortie)
        self.assertIn("paiement 35 'E214.20' -> R0", sortie)
        self.assertIn("normalisation 38 '214.20' -> accepté", sortie)

    def test_liste_montre_les_quatre_formes(self):
        code, sortie = lancer("--scenario", "avoir", "--fn", "AVOIR-0001", "--liste")
        self.assertEqual(sortie.count("(forme "), 4)


class Garde(unittest.TestCase):
    def test_avoir_sans_mcf_nim_rien_ne_part(self):
        with mock.patch.dict(os.environ, {"MCF_IFU": "99999999Z"}, clear=True), \
                mock.patch("appareil.cycle.pousser") as p:
            code, sortie = lancer("--scenario", "avoir", "--fn", "AVOIR-0001", "--port", "/dev/null")
        self.assertEqual(code, 2)
        self.assertIn("MCF_NIM (ou MCF_SIG) absent", sortie)
        p.assert_not_called()

    def test_sur_l_appareil_la_capture_est_brute_et_relisible(self):
        mcf = FauxMCF(variante="FIS")
        with tempfile.TemporaryDirectory() as dossier:
            capture = os.path.join(dossier, "brut", "cycle.txt")
            with mock.patch.dict(os.environ, {"MCF_IFU": "99999999Z"}, clear=True), \
                    mock.patch("appareil.cycle.pousser", lambda port, seq, d, cmd: mcf.repondre(seq, cmd, d.encode())), \
                    mock.patch("appareil.cycle.DELAI", 0):
                code, sortie = lancer("--scenario", "simple", "--fn", "ESSAI-0009", "--port", "/dev/null",
                                      "--capture", capture)
            self.assertEqual(code, 0)
            lignes = open(capture, encoding="utf-8").read().splitlines()
        self.assertEqual(sum(l.startswith("données : ") for l in lignes), 6)
        self.assertNotIn("99999999Z", sortie)  # l'écran reste masqué…
        self.assertTrue(any("99999999Z" in l for l in lignes))  # …la capture garde la réponse du 38
        self.assertIsNotNone(signature(lignes, "1"))

    def test_liste_n_envoie_rien(self):
        code, sortie = lancer("--scenario", "deux", "--fn", "ESSAI-0009", "--liste")
        self.assertEqual(code, 0)
        self.assertIn("(selon la réponse précédente)", sortie)
        self.assertIn("Rien envoyé.", sortie)

    def test_sans_mcf_ifu_rien_ne_part_meme_pas_le_c3(self):
        with mock.patch.dict(os.environ, {}, clear=True), mock.patch("appareil.cycle.pousser") as p:
            code, sortie = lancer("--scenario", "simple", "--fn", "ESSAI-0009", "--port", "/dev/null")
        self.assertEqual(code, 2)
        p.assert_not_called()

    def test_sequence_hors_plage(self):
        code, sortie = lancer("--scenario", "simple", "--fn", "X", "--jumeau", "--seq", "10")
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
