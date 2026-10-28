import io
import unittest
from contextlib import redirect_stdout

from appareil.carte_client import BASE, JETONS, PLACES, PLAFOND, jouer, lire, main, sondes
from appareil.recherche_bornee import envoyer_jumeau
from simulateur.faux_mcf import FauxMCF, reponse


def lancer(*argv, mcf=None):
    sortie = io.StringIO()
    with redirect_stdout(sortie):
        code = main(list(argv), mcf=mcf)
    return code, sortie.getvalue()


class Carte(unittest.TestCase):
    def test_dix_sept_trames_a_sept_champs(self):
        s = list(sondes())
        self.assertEqual(len(s), 2 + len(JETONS) * len(PLACES))
        self.assertLessEqual(len(s), PLAFOND)
        self.assertEqual(len({d for _, d in s}), len(s))
        for _, donnees in s:
            self.assertEqual(len(donnees.split(",")), 7)

    def test_un_seul_champ_s_ecarte_de_la_base(self):
        for nom, donnees in sondes():
            champs = donnees.split(",")
            ecarts = [i for i in range(7) if champs[i] != BASE[i]]
            self.assertEqual(len(ecarts), 1, nom)
            place = int(nom.split("@")[1])
            self.assertEqual(ecarts[0], place - 1, nom)

    def test_x_aux_places_du_type_et_du_nom_d_abord(self):
        s = list(sondes())
        self.assertEqual(s[0], ("x@1", "x,CLIENT TEST,,,,,"))
        self.assertEqual(s[1], ("x@2", "PP,x,,,,,"))

    def test_l_email_de_la_carte_est_de_syntaxe_valide_et_reserve(self):
        self.assertIn(("mail", "client@example.com"), JETONS)


class Lecture(unittest.TestCase):
    def test_texte_utf8_et_arrets(self):
        self.assertEqual(lire(reponse(0x60, 0xC3, "E:Erreur é".encode())), (False, "", "E:Erreur é"))
        self.assertEqual(lire(reponse(0x60, 0xC3, b"")), (False, "", "(vide)"))
        self.assertEqual(lire(b"\x15" + reponse(0x60, 0xC3, b"")), (True, "NAK", ""))
        self.assertEqual(lire(b""), (True, "silence", ""))
        self.assertEqual(lire(None), (True, "déconnexion", ""))
        self.assertEqual(lire(b"\x01\x2c\x60\xc3R\x04\x80\x05zzzz\x03"), (True, "trame illisible", ""))


class Jeu(unittest.TestCase):
    def test_tout_est_releve_sans_arret_sur_un_message_nouveau(self):
        mcf, seq = FauxMCF(variante="FIS"), [0xF0]
        vues, motif = jouer(list(sondes()), envoyer_jumeau(mcf, seq))
        self.assertIsNone(motif)
        self.assertEqual(len(vues), 17)

    def test_nak_de_facture_ouverte_arrete(self):
        mcf, seq = FauxMCF(variante="FIS"), [0xF0]
        mcf.donnees(0xC0, b"1,Essai,{IFU},FV,TTC,ISF-ESSAI,ESSAI-0002")
        vues, motif = jouer(list(sondes()), lambda d: mcf.repondre(seq[0], 0xC3, d.encode()))
        self.assertEqual((vues, motif), ([], "NAK"))

    def test_le_delai_deduit_le_temps_deja_ecoule(self):
        pauses, temps = [], [0.0]
        def envoyer(d):
            temps[0] += 1.0
            return reponse(0x60, 0xC3, b"R")
        jouer(list(sondes())[:3], envoyer, delai=3.0, horloge=lambda: temps[0], dormir=pauses.append)
        self.assertEqual(pauses, [2.0, 2.0])


class Commande(unittest.TestCase):
    def test_liste_n_envoie_rien(self):
        code, sortie = lancer("--liste")
        self.assertEqual(code, 0)
        self.assertIn("mail@6", sortie)
        self.assertIn("Rien envoyé", sortie)

    def test_liste_gagne_sur_le_port(self):
        code, sortie = lancer("--liste", "--port", "/dev/inexistant")
        self.assertEqual(code, 0)
        self.assertIn("Rien envoyé", sortie)

    def test_jumeau_joue_toute_la_carte(self):
        code, sortie = lancer("--jumeau")
        self.assertEqual(code, 0)
        self.assertIn("terminé : 17 trames.", sortie)
        self.assertIn("x@1", sortie)

    def test_sequence_hors_plage_n_envoie_rien(self):
        for seq in ("1F", "ZZ"):
            code, sortie = lancer("--jumeau", "--seq", seq)
            self.assertEqual(code, 2)
            self.assertIn("rien envoyé", sortie)

    def test_sans_jumeau_ni_port_n_envoie_rien(self):
        code, sortie = lancer()
        self.assertEqual(code, 0)
        self.assertIn("Rien envoyé", sortie)


if __name__ == "__main__":
    unittest.main()
