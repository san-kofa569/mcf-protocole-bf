import io
import os
import unittest
from contextlib import redirect_stdout
from unittest import mock

from appareil.cycle import BIEN, CLIENT, SERVICE, etapes, main
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
        self.assertEqual(e[6][2]({"reste": 112.0}), "E112.00")

    def test_annulation_finit_sur_la_sonde(self):
        self.assertEqual(etapes("annulation", "X")[-1], ("sonde", 0x38, "C"))


class AuJumeau(unittest.TestCase):
    def test_simple_va_jusqu_a_la_facture_certifiee(self):
        code, sortie = lancer("--scenario", "simple", "--fn", "ESSAI-0009", "--jumeau")
        self.assertEqual(code, 0)
        self.assertIn("article 31 'ARTICLE TEST\\tLOCBIE,B18.0%100.00\\t100.00*1' -> 100.0,84.75,15.25,0.0", sortie)
        self.assertIn("paiement 35 'E102.00' -> R0", sortie)
        self.assertIn("normalisation 38 '102.00' -> accepté : 8 champs, compteurs 1/3 FV", sortie)

    def test_la_cloture_ne_montre_ni_nim_ni_ifu_ni_signature(self):
        code, sortie = lancer("--scenario", "simple", "--fn", "ESSAI-0009", "--jumeau")
        self.assertNotIn("XX99999999", sortie)
        self.assertNotIn("99999999Z", sortie)

    def test_deux_s_arrete_au_mode_jamais_vu(self):
        # le jumeau ne connaît que les espèces : le mobile money répond INCONNU, le scénario s'arrête
        code, sortie = lancer("--scenario", "deux", "--fn", "ESSAI-0009", "--jumeau")
        self.assertEqual(code, 1)
        self.assertIn("service 31 'POSE TEST\\tLOCSER,C10.0%110.00\\t110.00*1' -> 110.0,100.0,10.0,0.0", sortie)
        self.assertIn("mobile 35 'M100.00' -> E:??", sortie)
        self.assertIn("ARRÊT : réponse inattendue", sortie)

    def test_sans_psvb_l_arret_vient_de_la_31(self):
        mcf = FauxMCF(variante="FIS")
        with mock.patch("appareil.cycle.etapes", lambda s, fn: [
                ("ouverture", 0xC0, "1,Essai,{IFU},FV,TTC,ISF-ESSAI,%s" % fn), ("article", 0x31, BIEN)]):
            code, sortie = lancer("--scenario", "simple", "--fn", "X", "--jumeau", mcf=mcf)
        self.assertEqual(code, 1)
        self.assertIn("E:La taxe est incorrecte!", sortie)


class Garde(unittest.TestCase):
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
