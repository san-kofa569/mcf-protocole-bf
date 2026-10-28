import io
import unittest
from contextlib import redirect_stdout

from appareil.carte_c0 import BASE, PLAFOND, TYPES, main, sondes
from simulateur.faux_mcf import FauxMCF, reponse


def lancer(*argv, mcf=None):
    sortie = io.StringIO()
    with redirect_stdout(sortie):
        code = main(list(argv), mcf=mcf)
    return code, sortie.getvalue()


class Carte(unittest.TestCase):
    def test_vingt_deux_trames_sous_le_plafond_et_sans_doublon(self):
        s = list(sondes())
        self.assertEqual(len(s), 22)
        self.assertLessEqual(len(s), PLAFOND)
        self.assertEqual(len({d for _, d in s}), len(s))

    def test_chaque_trame_s_ecarte_de_la_base_a_un_seul_endroit(self):
        base = ",".join(BASE)
        for nom, donnees in sondes():
            self.assertNotEqual(donnees, base, nom)
            if nom.startswith("x@") or nom.startswith(("type=", "mode=", "isf=", "ref=")):
                champs, ref = donnees.split(","), list(BASE)
                self.assertEqual(len(champs), 7, nom)
                self.assertEqual(sum(1 for i in range(7) if champs[i] != ref[i]), 1, nom)

    def test_formes_attendues(self):
        d = dict(sondes())
        self.assertEqual(d["x@3"], "1,Essai,x,FV,TTC,ISF-ESSAI,ESSAI-0015")
        self.assertEqual(d["type=FA"], "1,Essai,{IFU},FA,TTC,ISF-ESSAI,ESSAI-0015")
        self.assertEqual(d["mode=HT"], "1,Essai,{IFU},FV,HT,ISF-ESSAI,ESSAI-0015")
        self.assertEqual(d["isf=vide"], "1,Essai,{IFU},FV,TTC,,ESSAI-0015")
        self.assertEqual(d["champs=5"], "1,Essai,{IFU},FV,TTC")
        self.assertEqual(d["champs=8"], ",".join(BASE) + ",x")
        self.assertEqual(d["champs=12"], ",".join(BASE) + ",x,x,x,x,x")
        self.assertEqual(set(TYPES), {"FT", "FA", "EV", "ET", "EA"})


class Commande(unittest.TestCase):
    def test_liste_n_envoie_rien(self):
        code, sortie = lancer("--liste")
        self.assertEqual(code, 0)
        self.assertIn("x@6", sortie)
        self.assertIn("Rien envoyé", sortie)

    def test_liste_gagne_sur_le_port_et_sans_cible_rien_ne_part(self):
        for argv in (("--liste", "--port", "/dev/inexistant"), ()):
            code, sortie = lancer(*argv)
            self.assertEqual(code, 0)
            self.assertIn("Rien envoyé", sortie)

    def test_jumeau_releve_toutes_les_reponses(self):
        code, sortie = lancer("--jumeau")
        self.assertEqual(code, 0)
        self.assertIn("terminé : 22 trames.", sortie)
        self.assertIn("type=FA", sortie)

    def test_arret_sur_deconnexion(self):
        class Muet:
            def repondre(self, seq, cmd, data):
                return None
        code, sortie = lancer("--jumeau", mcf=Muet())
        self.assertEqual(code, 1)
        self.assertIn("déconnexion", sortie)

    def test_sequence_hors_plage_n_envoie_rien(self):
        for seq in ("1F", "ZZ"):
            code, sortie = lancer("--jumeau", "--seq", seq)
            self.assertEqual(code, 2)
            self.assertIn("rien envoyé", sortie)


if __name__ == "__main__":
    unittest.main()
