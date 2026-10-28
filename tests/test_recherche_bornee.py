import io
import unittest
from contextlib import redirect_stdout

from appareil.recherche_bornee import (
    ATTENDU, CONNUS, NOMS, PLACES, PLAFOND, SONDES, borne, candidats, classer,
    envoyer_jumeau, jouer, ligne, main, pousser, suivant, trames,
)
from simulateur.faux_mcf import FauxMCF, reponse


def connu():
    return reponse(0x60, 0xC3, ATTENDU.encode("latin-1"))


class Catalogue(unittest.TestCase):
    def test_les_refus_deja_vus_sont_exclus(self):
        self.assertFalse(set(CONNUS) & set(SONDES))
        self.assertEqual(candidats()[0], "5")
        for v in CONNUS:
            self.assertNotIn(v, candidats())

    def test_avec_connu_les_remet_en_tete(self):
        self.assertEqual(candidats(()), CONNUS + SONDES)

    def test_une_place_une_trame_et_pas_de_doublon(self):
        self.assertEqual(len(list(trames())), len(SONDES) * (4 * len(NOMS) + 1))
        donnees = [d for _, d in trames()]
        self.assertEqual(len(donnees), len(set(donnees)))
        for valeur in SONDES:
            for _, d in trames((valeur,)):
                champs = d.split(",")
                self.assertEqual(len(champs), PLACES)
                self.assertEqual(champs.count(valeur), 1)

    def test_la_place_du_nom_ne_double_pas_la_trame(self):
        donnees = [d for _, d in trames(("5",))]
        self.assertEqual(donnees.count(",5,,,"), 1)
        self.assertEqual(donnees, [
            "5,,,,", "5,CLIENT TEST,,,", ",5,,,", ",,5,,", ",CLIENT TEST,5,,",
            ",,,5,", ",CLIENT TEST,,5,", ",,,,5", ",CLIENT TEST,,,5",
        ])

    def test_borne_refuse_au_dela_du_plafond(self):
        self.assertEqual(len(borne(trames(("5",)))), 9)
        with self.assertRaises(ValueError):
            borne(trames(("5", "6")), 10)


class Classement(unittest.TestCase):
    def test_connu_nak_silence_et_nouveau(self):
        self.assertEqual(classer(connu()), (False, "connu"))
        self.assertEqual(classer(b"\x16" + connu()), (False, "connu"))
        self.assertEqual(classer(b"\x15" + connu()), (True, "NAK"))
        self.assertEqual(classer(b"\x15"), (True, "NAK"))
        self.assertEqual(classer(b""), (True, "silence"))
        self.assertEqual(classer(None), (True, "déconnexion"))
        self.assertEqual(classer(reponse(0x60, 0xC3, b"E:autre")),
                         (True, "message nouveau : E:autre"))
        self.assertEqual(classer(reponse(0x60, 0xC3, b"1")), (True, "accepté : 1"))
        self.assertEqual(classer(reponse(0x60, 0xC3, b"")), (True, "accepté : (vide)"))
        mauvais = bytearray(connu())
        mauvais[-3] ^= 1
        self.assertEqual(classer(bytes(mauvais)), (True, "trame illisible"))
        self.assertEqual(classer(b"\x01"), (True, "trame illisible"))


class Jeu(unittest.TestCase):
    def test_message_connu_va_au_bout(self):
        serie = list(trames(("5",)))
        self.assertIsNone(jouer(serie, envoyer_jumeau(FauxMCF(variante="FIS"), [0x60])))

    def test_arret_au_premier_message_nouveau(self):
        serie = list(trames(("5",)))
        cible = serie[3][1]
        self.assertEqual(cible, ",,5,,")
        mcf = FauxMCF(variante="FIS", nouveau=(cible.encode("latin-1"), b"E:message nouveau"))
        vus = []
        seq = [0x60]
        envoyer = envoyer_jumeau(mcf, seq)

        def suivre(donnees):
            vus.append(donnees)
            return envoyer(donnees)

        nom, donnees, motif = jouer(serie, suivre)
        self.assertEqual((nom, donnees), serie[3])
        self.assertEqual(motif, "message nouveau : E:message nouveau")
        self.assertEqual(vus, [d for _, d in serie[:4]])
        self.assertEqual(seq[0], 0x64)

    def test_nak_de_facture_ouverte_arrete(self):
        mcf = FauxMCF(variante="FIS")
        mcf.donnees(0xC0, b"1,Essai,{IFU},FV,TTC,ISF-ESSAI,R")
        vus = []
        envoyer = envoyer_jumeau(mcf, [0x60])

        def suivre(donnees):
            vus.append(donnees)
            return envoyer(donnees)

        self.assertEqual(jouer(list(trames(("5",))), suivre)[2], "NAK")
        self.assertEqual(len(vus), 1)

    def test_le_delai_deduit_le_temps_deja_ecoule(self):
        import appareil.recherche_bornee as r
        t = [0.0]
        dors = []

        def horloge():
            return t[0]

        def dormir(s):
            dors.append(s)
            t[0] += s

        def envoyer(donnees):
            t[0] += 1.0
            return connu()

        origine = r.time.sleep
        r.time.sleep = dormir
        try:
            self.assertIsNone(jouer([("a", "1"), ("b", "2"), ("c", "3")],
                                    envoyer, delai=3.0, horloge=horloge))
        finally:
            r.time.sleep = origine
        self.assertEqual(dors, [2.0, 2.0])

    def test_sequence_apres_ff(self):
        self.assertEqual(suivant(0x60), 0x61)
        self.assertEqual(suivant(0xFF), 0x20)


class Commande(unittest.TestCase):
    def test_liste_n_envoie_rien(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(["--liste"])
        texte = buf.getvalue()
        n = len(list(trames()))
        self.assertEqual(code, 0)
        self.assertIn("Rien envoyé", texte)
        self.assertNotIn("ENVOI", texte)
        self.assertNotIn("--port", texte)
        self.assertIn("%d trames au catalogue. Séance 001–%03d." % (n, PLAFOND), texte)
        self.assertIn("python3 -m appareil.recherche_bornee --jumeau\n", texte)

    def test_jumeau_connu_partout_s_arrete_au_plafond(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(["--jumeau"])
        self.assertEqual(code, 0)
        texte = buf.getvalue()
        self.assertIn("terminé : %d trames, message connu partout." % PLAFOND, texte)
        self.assertIn("python3 -m appareil.recherche_bornee --jumeau --depuis %d" % (PLAFOND + 1), texte)
        self.assertIn("001 ", texte)
        self.assertIn("080 ", texte)
        self.assertNotIn("081 ", texte)

    def test_jumeau_s_arrete_sur_le_crochet(self):
        cible = ",,5,,"
        mcf = FauxMCF(variante="FIS", nouveau=(cible.encode("latin-1"), "E:message nouveau"))
        vus = []
        origine = mcf.repondre

        def repondre(seq, cmd, data):
            vus.append(data)
            return origine(seq, cmd, data)

        mcf.repondre = repondre
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(["--jumeau"], mcf=mcf)
        self.assertEqual(code, 1)
        self.assertEqual(len(vus), 4)
        self.assertEqual(vus[-1], cible.encode("latin-1"))
        texte = buf.getvalue()
        self.assertIn("004 5@3:-  message nouveau : E:message nouveau", texte)
        self.assertIn("ARRÊT 5@3:-", texte)
        self.assertNotIn("--depuis", texte)

    def test_port_au_dessus_du_plafond_n_envoie_rien(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(["--port", "/dev/inexistant-mcf-test", "--plafond", str(PLAFOND + 1)])
        self.assertEqual(code, 2)
        self.assertIn("rien envoyé", buf.getvalue())
        self.assertNotIn("ENVOI", buf.getvalue())

    def test_liste_gagne_sur_le_port(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(["--liste", "--port", "/dev/inexistant-mcf-test"])
        self.assertEqual(code, 0)
        self.assertIn("Rien envoyé", buf.getvalue())
        self.assertNotIn("ENVOI", buf.getvalue())

    def test_depuis_reprend_au_numero_affiche(self):
        complet = list(trames())
        mcf = FauxMCF(variante="FIS", nouveau=(complet[80][1].encode("latin-1"), b"E:reprise"))
        vus = []
        origine = mcf.repondre

        def repondre(seq, cmd, data):
            vus.append(data)
            return origine(seq, cmd, data)

        mcf.repondre = repondre
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(["--jumeau", "--depuis", "81"], mcf=mcf)
        self.assertEqual(code, 1)
        self.assertEqual(vus, [complet[80][1].encode("latin-1")])
        self.assertIn("081 ", buf.getvalue())
        self.assertNotIn("001 ", buf.getvalue())
        self.assertNotIn("--depuis", buf.getvalue())

    def test_depuis_zero_n_envoie_rien(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(["--jumeau", "--depuis", "0"])
        self.assertEqual(code, 2)
        self.assertIn("rien envoyé", buf.getvalue())
        self.assertNotIn("terminé", buf.getvalue())

    def test_ifu_absent_n_ouvre_pas_le_port(self):
        with self.assertRaises(SystemExit) as ctx:
            pousser("/dev/inexistant-mcf-test", 0x60, "x,{IFU}", env={})
        self.assertIn("rien envoyé", str(ctx.exception))

    def test_seance_suivante_reste_sur_l_appareil(self):
        # 2026-10-12 : après une séance sur l'appareil, la ligne imprimée disait --jumeau
        self.assertEqual(ligne(81, port="/dev/ttyACM0"),
                         "python3 -m appareil.recherche_bornee --port /dev/ttyACM0 --depuis 81")
        self.assertEqual(ligne(81), "python3 -m appareil.recherche_bornee --jumeau --depuis 81")


if __name__ == "__main__":
    unittest.main()
