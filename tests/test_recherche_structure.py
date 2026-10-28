import io
import unittest
from contextlib import redirect_stdout

from appareil.recherche_bornee import ATTENDU, PLAFOND
from appareil.recherche_structure import (
    CONNUS, NATURELLES, NOMBRES, TYPES, grille, main,
)
from simulateur.faux_mcf import FauxMCF, reponse


def trame(donnees):
    return reponse(0x60, 0xC3, donnees)


def lancer(*argv, mcf=None):
    sortie = io.StringIO()
    with redirect_stdout(sortie):
        code = main(list(argv), mcf=mcf)
    return code, sortie.getvalue()


class Grille(unittest.TestCase):
    def test_taille_et_pas_de_doublon(self):
        g = list(grille())
        self.assertEqual(len(g), len(NATURELLES) + len(NOMBRES) * len(TYPES) - len(CONNUS))
        self.assertLessEqual(len(g), PLAFOND)
        donnees = [d for _, d in g]
        self.assertEqual(len(donnees), len(set(donnees)))

    def test_les_formes_naturelles_d_abord(self):
        g = list(grille())
        self.assertEqual(g[:2], list(NATURELLES))
        self.assertEqual(g[0][1].count(","), 5)  # six champs, comme le bloc client

    def test_chaque_type_a_chaque_place_pour_un_nombre_de_champs(self):
        d = dict(grille())
        self.assertEqual(d["PPx6"], "PP,PP,PP,PP,PP,PP")
        self.assertEqual(d["CCx2"], "CC,CC")
        for nom, donnees in grille():
            if "x" in nom and nom != "type-en-1re-place":
                t, n = nom.split("x")
                self.assertEqual(donnees.split(","), [t] * int(n))

    def test_les_essais_deja_joues_sont_exclus(self):
        d = dict(grille())
        for n, t in CONNUS:
            self.assertNotIn("%sx%d" % (t, n), d)
        self.assertNotIn("PPx5", d)
        self.assertIn("CCx12", d)
        self.assertIn("PPx8", d)

    def test_les_nombres_viennent_par_distance_a_six(self):
        nombres = []
        for nom, _ in grille():
            if "x" in nom and nom != "type-en-1re-place":
                n = int(nom.split("x")[1])
                if n not in nombres:
                    nombres.append(n)
        self.assertEqual(nombres[:4], [6, 7, 4, 8])


class Commande(unittest.TestCase):
    def test_liste_n_envoie_rien(self):
        code, sortie = lancer("--liste")
        self.assertEqual(code, 0)
        self.assertIn("PP,CLIENT TEST,,,,", sortie)
        self.assertIn("Rien envoyé", sortie)

    def test_liste_gagne_sur_le_port(self):
        code, sortie = lancer("--liste", "--port", "/dev/inexistant")
        self.assertEqual(code, 0)
        self.assertIn("Rien envoyé", sortie)

    def test_jumeau_s_arrete_a_la_trame_7_comme_l_appareil(self):
        code, sortie = lancer("--jumeau")
        self.assertEqual(code, 1)
        self.assertIn("ARRÊT PPx7", sortie)
        self.assertIn("e-mail du destinataire n'est pas valide", sortie)

    def test_jumeau_connu_partout_apres_la_trame_7_va_au_bout(self):
        code, sortie = lancer("--jumeau", "--depuis", "8")
        self.assertEqual(code, 0)
        self.assertIn("terminé : %d trames, message connu partout." % (len(list(grille())) - 7), sortie)

    def test_jumeau_s_arrete_sur_le_crochet(self):
        mcf = FauxMCF(variante="FIS", nouveau=(b"PP,PP,PP,PP,PP,PP", b"E:autre message"))
        code, sortie = lancer("--jumeau", mcf=mcf)
        self.assertEqual(code, 1)
        self.assertIn("ARRÊT PPx6", sortie)
        self.assertIn("message nouveau : E:autre message", sortie)
        self.assertNotIn("PPx7", sortie)

    def test_r_au_milieu_de_la_grille_est_un_ecart(self):
        # « R » au milieu de la grille est un écart à signaler.
        mcf = FauxMCF(variante="FIS", nouveau=(b"PM,PM,PM,PM,PM,PM", b"R"))
        code, sortie = lancer("--jumeau", mcf=mcf)
        self.assertEqual(code, 1)
        self.assertIn("accepté : R", sortie)

    def test_depuis_reprend_au_numero_affiche(self):
        code, sortie = lancer("--jumeau", "--depuis", "10", "--plafond", "3")
        self.assertEqual(code, 0)
        lignes = [l for l in sortie.splitlines() if " 010 " in l or " 011 " in l or " 012 " in l]
        self.assertEqual(len(lignes), 3)
        self.assertIn("suite : --depuis 13", sortie)

    def test_plafond_au_dessus_de_la_limite_n_envoie_rien(self):
        code, sortie = lancer("--jumeau", "--plafond", str(PLAFOND + 1))
        self.assertEqual(code, 2)
        self.assertIn("rien envoyé", sortie)

    def test_depart_hors_grille_n_envoie_rien(self):
        for depuis in ("0", "999"):
            code, sortie = lancer("--jumeau", "--depuis", depuis)
            self.assertEqual(code, 2)
            self.assertIn("rien envoyé", sortie)

    def test_sequence_hors_plage_n_envoie_rien(self):
        for seq in ("1F", "ZZ"):
            code, sortie = lancer("--jumeau", "--seq", seq)
            self.assertEqual(code, 2)
            self.assertIn("rien envoyé", sortie)


if __name__ == "__main__":
    unittest.main()
