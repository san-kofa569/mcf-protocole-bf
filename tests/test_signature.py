import io
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

from appareil.signature import identifiant, main, signature

# valeurs fictives, à la forme de l'appareil
SIG1, SIG2 = "ABCDEFGHIJKLMNOPQRSTUV23", "ZYXWVUTSRQPONMLKJIHGFE45"
C1_APRES_2 = ("XX99999999-1,99999999Z,20261028134515,4,2,0,20261028134501,FV,%s,2,214.2,"
              "0.0,18.0,10.0,0.0,0.0,18.0,10.0,0.0,0.0,0.0,0.0,10.0,10.0,0.0,0.0,0.0,2.0,1.0,0.2,0.0" % SIG2)
CAPTURE = [
    "2026-10-28 12:31:01 envoi : 01 2a ef 38 31 30 32 2e 30 30 05 30 33 30 3e 03",
    "reçu (90 octets) : …",
    "BCC : True",
    "données : 1,3,FV,20261028113101,XX99999999-1,99999999Z,%s,ESSAI-0008" % SIG1,
    "statut : 80 80 80 80 80 80",
    "2026-10-28 14:45:15 envoi : 01 24 50 c1 05 30 31 3c 30 03",
    "données : " + C1_APRES_2,
    "statut : 80 80 80 80 80 80",
]


class Signature(unittest.TestCase):
    def test_lue_dans_la_reponse_du_38(self):
        self.assertEqual(signature(CAPTURE, "1"), SIG1)

    def test_lue_dans_le_c1_qui_suit(self):
        self.assertEqual(signature(CAPTURE, "2"), SIG2)

    def test_c1_apres_un_avoir_le_10e_champ_compte_toutes_les_factures(self):
        # 16:01 : vente n°3 après l'avoir n°1 : compteurs 6,3,1 ; 10e champ = 4 (toutes factures)
        c1 = ("XX99999999-1,99999999Z,20261028140138,6,3,1,20261028134659,FV,%s,4,102.0,"
              "0.0,18.0,10.0,0.0,0.0,18.0,10.0,0.0,0.0,0.0,0.0,10.0,10.0,0.0,0.0,0.0,2.0,1.0,0.2,0.0" % SIG1)
        capture = ["2026-10-28 16:01:38 envoi : 01 24 70 c1 05 30 31 3c 30 03", "données : " + c1]
        self.assertEqual(signature(capture, "3"), SIG1)
        self.assertIsNone(signature(capture, "4"))

    def test_numero_ou_type_inconnu(self):
        self.assertIsNone(signature(CAPTURE, "3"))
        self.assertIsNone(signature(CAPTURE, "1", "FA"))

    def test_identifiant_nim_acnt(self):
        self.assertEqual(identifiant(CAPTURE), "XX99999999-1")
        self.assertIsNone(identifiant(CAPTURE[:2]))

    def test_n_ecrit_que_la_signature(self):
        with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as f:
            f.write("\n".join(CAPTURE))
        try:
            sortie, erreur = io.StringIO(), io.StringIO()
            with redirect_stdout(sortie), redirect_stderr(erreur):
                self.assertEqual(main([f.name, "--numero", "2"]), 0)
            self.assertEqual(sortie.getvalue(), SIG2 + "\n")
            sortie = io.StringIO()
            with redirect_stdout(sortie), redirect_stderr(erreur):
                self.assertEqual(main([f.name, "--numero", "9"]), 1)
            self.assertEqual(sortie.getvalue(), "")
        finally:
            os.remove(f.name)


if __name__ == "__main__":
    unittest.main()
