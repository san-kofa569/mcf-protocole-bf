import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout

from appareil.qr import comparer, contenu, main, reponse_38

# valeurs fictives, à la forme de l'appareil
R38 = "1,3,FV,20261028113101,XX99999999-1,99999999Z,ABCDEFGHIJKLMNOPQRSTUV23,ESSAI-0008"


class Contenu(unittest.TestCase):
    def test_gabarit_bénin_niger(self):
        self.assertEqual(contenu(R38), "F;XX99999999-1;ABCDEFGHIJKLMNOPQRSTUV23;99999999Z;20261028113101")

    def test_reponse_incomplete(self):
        with self.assertRaises(ValueError):
            contenu("1,3,FV")

    def test_lue_dans_une_capture(self):
        capture = ["2026-10-28 12:31:01 envoi : 01 2a ef 38 31 30 32 05 30 33 30 3e 03", "données : " + R38]
        self.assertEqual(reponse_38(capture, "1"), R38)
        self.assertIsNone(reponse_38(capture, "2"))


class Comparer(unittest.TestCase):
    def test_hypothese_confirmee_sans_valeur_affichee(self):
        lignes = comparer(contenu(R38), R38)
        texte = "\n".join(lignes)
        self.assertIn("1 : littéral 'F'", texte)
        self.assertIn("2 : = identifiant de machine du 38", texte)
        self.assertIn("3 : = signature du 38", texte)
        self.assertIn("identique à l'hypothèse F;identifiant;signature;IFU;date : oui", texte)
        for valeur in ("XX99999999", "99999999Z", "ABCDEFGHIJ"):
            self.assertNotIn(valeur, texte)

    def test_autre_format_decrit_par_places(self):
        lignes = comparer("BF01|ABCDEFGHIJKLMNOPQRSTUV23|99999999Z|20261028113101|https://x.example/v?q=1", R38)
        texte = "\n".join(lignes)
        self.assertIn("séparateur : '|'", texte)
        self.assertIn("1 : littéral 'BF01'", texte)
        self.assertIn("4 : = date du 38", texte)
        self.assertIn("5 : autre (", texte)
        self.assertIn(": non", texte)
        self.assertNotIn("ABCDEFGHIJ", texte)


class Commande(unittest.TestCase):
    def test_fichier_absent_ou_vide_sans_trace(self):
        with tempfile.TemporaryDirectory() as d:
            sortie = io.StringIO()
            with redirect_stdout(sortie):
                code = main(["--comparer", os.path.join(d, "qr.txt"), "--capture", "x", "--numero", "1"])
            self.assertEqual(code, 2)
            self.assertIn("absent : scanner d'abord le QR", sortie.getvalue())
            open(os.path.join(d, "qr.txt"), "w").close()
            with redirect_stdout(io.StringIO()):
                self.assertEqual(main(["--comparer", os.path.join(d, "qr.txt"), "--capture", "x", "--numero", "1"]), 2)


if __name__ == "__main__":
    unittest.main()
