import io
import unittest
from contextlib import redirect_stdout

from appareil.recherche_article import (
    ATTENDU, ATTENDU_TAXE, JETONS, NOMBRES, SEPARATEURS, TAUX_GROUPES, anciens, gabarits, grille, groupes,
    groupes_rdc, ht, main, nombres2, photo, psvb, psvb_rdc, quantite, rdc, taxe, taxe2,
)
from appareil.recherche_bornee import PLAFOND, classer
from simulateur.faux_mcf import E_FORMAT, reponse


def lancer(*argv, mcf=None):
    sortie = io.StringIO()
    with redirect_stdout(sortie):
        code = main(list(argv), mcf=mcf)
    return code, sortie.getvalue()


class Jumeau31:
    """Un MCF qui répond le message de format partout, sauf aux données listées."""

    def __init__(self, ailleurs=None):
        self.ailleurs = ailleurs or {}
        self.vues = []

    def repondre(self, seq, cmd, data):
        self.vues.append((cmd, data))
        return reponse(seq, cmd, self.ailleurs.get(data, E_FORMAT))


class Grille(unittest.TestCase):
    def test_taille_sous_le_plafond_et_sans_doublon(self):
        g = list(grille())
        self.assertEqual(len(g), len(NOMBRES) * len(SEPARATEURS) * len(JETONS))
        self.assertLessEqual(len(g), PLAFOND)
        self.assertEqual(len({d for _, d in g}), len(g))

    def test_un_jeton_repete_a_toutes_les_places(self):
        d = dict(grille())
        self.assertEqual(d["virgule7x1"], "1,1,1,1,1,1,1")
        self.assertEqual(d["tab7xB"], "B\tB\tB\tB\tB\tB\tB")
        self.assertEqual(d["virgule3xLOCBIE"], "LOCBIE,LOCBIE,LOCBIE")

    def test_sept_champs_d_abord_puis_par_distance(self):
        noms = [nom for nom, _ in grille()]
        self.assertTrue(all(n.startswith(("virgule7x", "tab7x")) for n in noms[:6]))
        premiers = []
        for nom in noms:
            n = int("".join(c for c in nom.split("x")[0] if c.isdigit()))
            if n not in premiers:
                premiers.append(n)
        self.assertEqual(premiers[:5], [7, 6, 8, 5, 9])

    def test_le_message_de_format_est_celui_de_l_appareil(self):
        self.assertEqual(ATTENDU.encode(), E_FORMAT)
        self.assertEqual(classer(reponse(0x70, 0x31, E_FORMAT), ATTENDU), (False, "connu"))
        self.assertEqual(classer(reponse(0x70, 0x31, E_FORMAT)), (True, "message nouveau : " + ATTENDU))


class Gabarits(unittest.TestCase):
    def test_taille_sans_doublon_et_trois_seances_au_plus(self):
        g = list(gabarits())
        self.assertGreater(len(g), 150)
        self.assertLessEqual(len(g), 3 * PLAFOND)
        self.assertEqual(len({d for _, d in g}), len(g))

    def test_formes_attendues(self):
        d = dict(gabarits())
        self.assertEqual(d["niger/T/tab@3"], "ARTICLE TEST\tB18.0%100\t100*1\tLOCBIE")
        self.assertEqual(d["niger/T/pv@3"], "ARTICLE TEST\tB18.0%100\t100*1;LOCBIE")
        self.assertEqual(d["niger/TU/virg@3"], "ARTICLE TEST\tB18.0%100\t100*1,LOCBIE,U")
        self.assertEqual(d["niger/T/tab@0"], "LOCBIE\tARTICLE TEST\tB18.0%100\t100*1")
        self.assertEqual(d["niger/T/tab@1"], "ARTICLE TEST\tLOCBIE\tB18.0%100\t100*1")
        self.assertEqual(d["benin/U/lf@2"], "ARTICLE TEST\tB100*1\nU")
        self.assertEqual(d["datecs/UT/barre@2"], "ARTICLE TEST\tB100.00*1.000|U|LOCBIE")

    def test_chaque_trame_contient_un_noyau_valide(self):
        noyaux = {"niger": "B18.0%100", "benin": "B100*1", "datecs": "B100.00*1.000"}
        for nom, donnees in gabarits():
            self.assertIn("ARTICLE TEST", donnees, nom)
            self.assertIn(noyaux[nom.split("/")[0]], donnees, nom)
            self.assertIn("LOCBIE" if "T" in nom.split("/")[1] else "U", donnees, nom)

    def test_la_fin_vient_avant_le_debut_puis_l_interieur(self):
        places = []
        for nom, _ in gabarits():
            c, _, reste = nom.partition("/")
            p = int(nom.split("@")[1])
            if c == "niger" and p not in places:
                places.append(p)
        self.assertEqual(places, [3, 0, 1, 2])


class Photo(unittest.TestCase):
    def test_une_seance_au_plus_et_sans_doublon(self):
        g = list(photo())
        self.assertEqual(len(g), 72)
        self.assertLessEqual(len(g), PLAFOND)
        self.assertEqual(len({d for _, d in g}), len(g))

    def test_l_ordre_de_la_photo_en_tete_groupe_avant_type(self):
        d = dict(photo())
        self.assertEqual(d["NGTPQ/virg/simple"], "ARTICLE TEST,B,LOCBIE,100,1")
        self.assertEqual(d["NGTPQ/tab/decimales"], "ARTICLE TEST\tB\tLOCBIE\t100.00\t1.000")
        self.assertEqual(d["CNGTPQM/pv/simple"], "ART001;ARTICLE TEST;B;LOCBIE;100;1;100")
        self.assertEqual(d["NGTPQU/lf/simple"], "ARTICLE TEST\nB\nLOCBIE\n100\n1\nU")
        self.assertEqual(d["NTGPQ/virg/simple"], "ARTICLE TEST,LOCBIE,B,100,1")
        self.assertEqual(next(iter(dict(photo()))), "NGTPQ/virg/simple")

    def test_chaque_enregistrement_a_les_champs_de_son_ordre(self):
        for nom, donnees in photo():
            ordre = nom.split("/")[0]
            sep = {"virg": ",", "tab": "\t", "pv": ";", "lf": "\n"}[nom.split("/")[1]]
            self.assertEqual(len(donnees.split(sep)), len(ordre), nom)


class Anciens(unittest.TestCase):
    def test_les_seize_essais_d_avant_le_15_en_une_seance(self):
        g = list(anciens())
        self.assertEqual(len(g), 16)
        self.assertEqual(len({d for _, d in g}), len(g))
        self.assertTrue(all(nom.startswith("a31_") for nom, _ in g))
        self.assertTrue(all(not d.endswith("\n") for _, d in g))

    def test_les_formes_nues_les_plus_plausibles_d_abord(self):
        g = list(anciens())
        self.assertEqual(g[0], ("a31_h1_ecohada", "ARTICLE TEST\tB18.0%100\t100*1"))
        self.assertEqual(g[1], ("a31_essai3", "ARTICLE TEST\tB100*1"))
        self.assertEqual(g[2], ("a31_s2_datecs_decimales", "ARTICLE TEST\tB100.00*1.000"))
        self.assertEqual(dict(g)["a31_h2_avec_code"], "ARTICLE TEST\nART001\tB18.0%100\t100*1")

    def test_en_liste_et_au_jumeau(self):
        code, sortie = lancer("--liste", "--grille", "anciens")
        self.assertEqual(code, 0)
        self.assertIn("Séance 001–016", sortie)
        mcf = Jumeau31()
        code, sortie = lancer("--jumeau", "--grille", "anciens", mcf=mcf)
        self.assertEqual(code, 0)
        self.assertEqual(len(mcf.vues), 16)


class GroupesEtNombres2(unittest.TestCase):
    def test_seize_groupes_deux_formes(self):
        g = dict(groupes())
        self.assertEqual(len(g), 32)
        self.assertEqual(g["niger/B"], "ARTICLE TEST\tB18.0%100\t100*1")
        self.assertEqual(g["niger/A"], "ARTICLE TEST\tA0.0%100\t100*1")
        self.assertEqual(g["niger/C"], "ARTICLE TEST\tC10.0%100\t100*1")
        self.assertEqual(g["niger/F"], "ARTICLE TEST\tF18.0%100\t100*1")
        self.assertEqual(g["benin/P"], "ARTICLE TEST\tP100*1")
        self.assertEqual(len(TAUX_GROUPES), 16)

    def test_nombres2_trois_separateurs_et_une_seance(self):
        g = list(nombres2())
        self.assertEqual(len(g), len(NOMBRES) * 3 * 2)
        self.assertLessEqual(len(g), PLAFOND)
        self.assertEqual(len({d for _, d in g}), len(g))
        d = dict(g)
        self.assertEqual(d["pv7x1"], "1;1;1;1;1;1;1")
        self.assertEqual(d["lf3xB"], "B\nB\nB")
        self.assertEqual(d["barre14x1"], "|".join(["1"] * 14))

    def test_en_liste_et_au_jumeau(self):
        for nom, attendu in (("groupes", "Séance 001–032"), ("nombres2", "Séance 001–078")):
            code, sortie = lancer("--liste", "--grille", nom)
            self.assertEqual(code, 0)
            self.assertIn(attendu, sortie)
            mcf = Jumeau31()
            code, sortie = lancer("--jumeau", "--grille", nom, mcf=mcf)
            self.assertEqual(code, 0)
            self.assertEqual(len(mcf.vues), int(attendu[-3:]))


class Psvb(unittest.TestCase):
    def test_vingt_huit_trames_sans_doublon(self):
        g = list(psvb())
        self.assertEqual(len(g), 28)
        self.assertLessEqual(len(g), PLAFOND)
        self.assertEqual(len({d for _, d in g}), len(g))

    def test_formes_attendues(self):
        d = dict(psvb())
        self.assertEqual(d["fin;T/x"], "ARTICLE TEST\tB18.0%100\t100*1;Tx")
        self.assertEqual(d["fin;T0,/A"], "ARTICLE TEST\tB18.0%100\t100*1;T0,A")
        self.assertEqual(d["fin-tab/A"], "ARTICLE TEST\tB18.0%100\t100*1\tA")
        self.assertEqual(d["avant-groupe/x"], "ARTICLE TEST\tx\tB18.0%100\t100*1")
        self.assertEqual(d["groupe+L/A"], "ARTICLE TEST\tBA18.0%100\t100*1")
        self.assertEqual(d["taux+L/x"], "ARTICLE TEST\tB18.0x%100\t100*1")
        self.assertEqual(d["debut/A"], "A\tARTICLE TEST\tB18.0%100\t100*1")

    def test_le_detecteur_x_vient_avant_la_lettre_valide(self):
        noms = [nom for nom, _ in psvb()]
        self.assertTrue(all(n.endswith("/x") for n in noms[:14]))
        self.assertTrue(all(n.endswith("/A") for n in noms[14:]))

    def test_en_liste_et_au_jumeau(self):
        code, sortie = lancer("--liste", "--grille", "psvb")
        self.assertEqual(code, 0)
        self.assertIn("Séance 001–028", sortie)
        mcf = Jumeau31()
        code, sortie = lancer("--jumeau", "--grille", "psvb", mcf=mcf)
        self.assertEqual(code, 0)
        self.assertEqual(len(mcf.vues), 28)

    def test_un_message_de_valeur_arrete_la_grille(self):
        mcf = Jumeau31({b"ARTICLE TEST\tB18.0%100\t100*1;Tx": "E:PSVB n'existe pas!".encode()})
        code, sortie = lancer("--jumeau", "--grille", "psvb", mcf=mcf)
        self.assertEqual(code, 1)
        self.assertIn("ARRÊT fin;T/x", sortie)
        self.assertIn("PSVB n'existe pas!", sortie)


class Rdc(unittest.TestCase):
    def test_quatorze_trames_sans_doublon(self):
        g = list(rdc())
        self.assertEqual(len(g), 14)
        self.assertEqual(len({d for _, d in g}), len(g))

    def test_formes_attendues(self):
        d = dict(rdc())
        self.assertEqual(d["rdc/LOCBIE"], "ARTICLE TEST\tLOCBIE,B18.00%100.00\t100.00")
        self.assertEqual(d["rdc/BIE"], "ARTICLE TEST\tBIE,B18.00%100.00\t100.00")
        self.assertEqual(d["rdc/LOCBIE/niger"], "ARTICLE TEST\tLOCBIE,B18.0%100\t100*1")
        self.assertEqual(d["rdc/LOCBIE/code"], "ARTICLE TEST\nART001\tLOCBIE,B18.00%100.00\t100.00")
        self.assertEqual(d["rdc/LOCBIE/x2"], "ARTICLE TEST\tLOCBIE,B18.00%200.00\t100.00*2")

    def test_la_forme_exacte_d_abord_le_detecteur_en_dernier(self):
        noms = [nom for nom, _ in rdc()]
        self.assertEqual(noms[0], "rdc/LOCBIE")
        self.assertEqual(noms[-1], "rdc/x")

    def test_aucune_trame_deja_jouee(self):
        deja = {d for f in (grille, gabarits, photo, anciens, groupes, nombres2, psvb) for _, d in f()}
        self.assertFalse(deja & {d for _, d in rdc()})

    def test_en_liste_et_au_jumeau(self):
        code, sortie = lancer("--liste", "--grille", "rdc")
        self.assertEqual(code, 0)
        self.assertIn("Séance 001–014", sortie)
        mcf = Jumeau31()
        code, sortie = lancer("--jumeau", "--grille", "rdc", mcf=mcf)
        self.assertEqual(code, 0)
        self.assertEqual(len(mcf.vues), 14)

    def test_un_article_accepte_arrete_la_grille(self):
        mcf = Jumeau31({b"ARTICLE TEST\tLOCBIE,B18.00%100.00\t100.00": b"100.00,84.75,15.25,0.00"})
        code, sortie = lancer("--jumeau", "--grille", "rdc", mcf=mcf)
        self.assertEqual(code, 1)
        self.assertIn("ARRÊT rdc/LOCBIE", sortie)
        self.assertIn("accepté : 100.00,84.75,15.25,0.00", sortie)
        self.assertEqual(len(mcf.vues), 1)


class Taxe(unittest.TestCase):
    def test_vingt_deux_trames_sans_doublon_toutes_en_structure_rdc(self):
        g = list(taxe())
        self.assertEqual(len(g), 22)
        self.assertEqual(len({d for _, d in g}), len(g))
        for _, d in g:
            parties = d.split("\t")
            self.assertEqual(len(parties), 3)
            self.assertIn(",", parties[1])

    def test_formes_attendues(self):
        d = dict(taxe())
        self.assertEqual(d["taxe/B18.0"], "ARTICLE TEST\tLOCBIE,B18.0%100.00\t100.00")
        self.assertEqual(d["taxe/montant-taxe"], "ARTICLE TEST\tLOCBIE,B18.00%15.25\t100.00")
        self.assertEqual(d["taxe/specifique"], "ARTICLE TEST\tLOCBIE,B18.00%100.00\t100.00;0.00")
        self.assertEqual(d["type/x"], "ARTICLE TEST\tx,B18.00%100.00\t100.00")

    def test_la_trame_du_28_n_est_pas_rejouee(self):
        self.assertNotIn("ARTICLE TEST\tLOCBIE,B18.00%100.00\t100.00", {d for _, d in taxe()})

    def test_au_jumeau_comme_sur_l_appareil(self):
        # 2026-10-28 : arrêts au format sans `%` (11e), au `;` (16e), aux types BIE (17e) et IMPSERV (20e)
        for depuis, arret in ((1, "ARRÊT taxe/lettre-montant"), (13, "ARRÊT taxe/specifique"),
                              (17, "ARRÊT type/BIE"), (18, "ARRÊT type/IMPSERV")):
            code, sortie = lancer("--jumeau", "--grille", "taxe", "--depuis", str(depuis))
            self.assertEqual(code, 1)
            self.assertIn(arret, sortie)
        code, sortie = lancer("--jumeau", "--grille", "taxe", "--depuis", "18", "--plafond", "2")
        self.assertEqual(code, 0)
        self.assertIn("terminé : 2 trames, « E:La taxe est incorrecte! » partout.", sortie)


class Taxe2(unittest.TestCase):
    def test_dix_sept_trames_nouvelles_toutes_en_locbie_avec_pourcent(self):
        g = list(taxe2())
        self.assertEqual(len(g), 17)
        self.assertEqual(len({d for _, d in g}), len(g))
        self.assertFalse({d for _, d in g} & {d for _, d in taxe()})
        for _, d in g:
            nom, milieu, prix = d.split("\t")
            self.assertTrue(milieu.startswith("LOCBIE,") and "%" in milieu)
            self.assertEqual(prix, "100.00")

    def test_groupe_puis_taux_d_abord(self):
        g = list(taxe2())
        self.assertEqual(g[0], ("taxe2/B%18.0", "ARTICLE TEST\tLOCBIE,B%18.0\t100.00"))

    def test_au_jumeau_va_au_bout(self):
        code, sortie = lancer("--jumeau", "--grille", "taxe2")
        self.assertEqual(code, 0)
        self.assertIn("terminé : 17 trames, « E:La taxe est incorrecte! » partout.", sortie)

    def test_le_message_de_format_l_arrete(self):
        mcf = Jumeau31({b"ARTICLE TEST\tLOCBIE,B18.0%100.00\t100.00": ATTENDU_TAXE.encode()})
        code, sortie = lancer("--jumeau", "--grille", "taxe", mcf=mcf)
        self.assertEqual(code, 1)
        self.assertIn("ARRÊT taxe/B18", sortie)
        self.assertIn("message nouveau : " + ATTENDU, sortie)


class GroupesRdc(unittest.TestCase):
    def test_douze_groupes_deux_ecritures(self):
        g = dict(groupes_rdc())
        self.assertEqual(len(g), 24)
        self.assertFalse(any(nom[4] in "ABCF" for nom in g))
        self.assertEqual(g["rdc/D0.0"], "ARTICLE TEST\tLOCBIE,D0.0%100.00\t100.00")
        self.assertEqual(g["rdc/L%10.0"], "ARTICLE TEST\tLOCBIE,L%10.0\t100.00")
        self.assertFalse(set(g.values()) & {d for f in (rdc, taxe, taxe2) for _, d in f()})

    def test_au_jumeau_va_au_bout(self):
        code, sortie = lancer("--jumeau", "--grille", "groupes_rdc")
        self.assertEqual(code, 0)
        self.assertIn("terminé : 24 trames", sortie)


class Quantite(unittest.TestCase):
    def test_treize_trames_toutes_avec_une_quantite(self):
        g = list(quantite())
        self.assertEqual(len(g), 13)
        self.assertEqual(len({d for _, d in g}), len(g))
        for _, d in g:
            self.assertIn("*", d.split("\t")[2])

    def test_aucune_trame_deja_envoyee_le_28(self):
        envoyees = {d for f in (taxe, taxe2, groupes_rdc) for _, d in f()}
        envoyees.add("ARTICLE TEST\tLOCBIE,B18.00%100.00\t100.00")
        self.assertFalse(envoyees & {d for _, d in quantite()})

    def test_au_jumeau_va_au_bout(self):
        code, sortie = lancer("--jumeau", "--grille", "quantite")
        self.assertEqual(code, 0)
        self.assertIn("terminé : 13 trames", sortie)


class PsvbRdc(unittest.TestCase):
    def test_douze_trames_nouvelles(self):
        g = dict(psvb_rdc())
        self.assertEqual(len(g), 12)
        self.assertEqual(g["psvb/%A"], "ARTICLE TEST\tLOCBIE,B18.0%A\t100.00*1")
        self.assertEqual(g["psvb/%0.2"], "ARTICLE TEST\tLOCBIE,B18.0%0.2\t100.00*1")
        self.assertEqual(g["psvb/specifique;T0,0"], "ARTICLE TEST\tLOCBIE,B18.0%100.00\t100.00*1;T0,0")
        envoyees = {d for f in (taxe, taxe2, groupes_rdc, quantite) for _, d in f()}
        self.assertFalse(envoyees & set(g.values()))

    def test_au_jumeau_comme_sur_l_appareil(self):
        # 2026-10-28 : les 12 trames, `;T0,0` et le 3e sous-champ compris, ont buté sur la taxe (C0 sans PSVB)
        code, sortie = lancer("--jumeau", "--grille", "psvb_rdc")
        self.assertEqual(code, 0)
        self.assertIn("terminé : 12 trames, « E:La taxe est incorrecte! » partout.", sortie)


class Ht(unittest.TestCase):
    def test_six_formes_le_groupe_a_en_dernier(self):
        g = list(ht())
        self.assertEqual(len(g), 6)
        self.assertEqual(g[0], ("ht/montant-ttc", "ARTICLE TEST\tLOCBIE,B18.0%118.00\t100.00*1"))
        self.assertEqual(g[-1][0], "ht/groupe-A")
        self.assertNotIn("ARTICLE TEST\tLOCBIE,B18.0%100.00\t100.00*1", {d for _, d in g})

    def test_le_mismatch_ne_l_arrete_pas(self):
        mcf = Jumeau31({d.encode(): b"E:Mismatch de montant" for _, d in ht()})
        code, sortie = lancer("--jumeau", "--grille", "ht", mcf=mcf)
        self.assertEqual(code, 0)
        self.assertIn("terminé : 6 trames, « E:Mismatch de montant » partout.", sortie)


class Commande(unittest.TestCase):
    def test_grille_photo_en_liste_et_au_jumeau(self):
        code, sortie = lancer("--liste", "--grille", "photo")
        self.assertEqual(code, 0)
        self.assertIn("Séance 001–072", sortie)
        mcf = Jumeau31()
        code, sortie = lancer("--jumeau", "--grille", "photo", mcf=mcf)
        self.assertEqual(code, 0)
        self.assertEqual(len(mcf.vues), 72)

    def test_grille_gabarits_en_liste_et_au_jumeau(self):
        code, sortie = lancer("--liste", "--grille", "gabarits")
        self.assertEqual(code, 0)
        self.assertIn("niger/T/tab@3", sortie)
        self.assertIn("Séance 001–080", sortie)
        mcf = Jumeau31()
        code, sortie = lancer("--jumeau", "--grille", "gabarits", "--depuis", "81", mcf=mcf)
        self.assertEqual(code, 0)
        self.assertEqual(len(mcf.vues), 80)
        self.assertIn("suite : --depuis 161", sortie)

    def test_arret_sur_un_gabarit_nouveau(self):
        mcf = Jumeau31({b"ARTICLE TEST\tB18.0%100\t100*1;LOCBIE": b"R"})
        code, sortie = lancer("--jumeau", "--grille", "gabarits", mcf=mcf)
        self.assertEqual(code, 1)
        self.assertIn("ARRÊT niger/T/pv@3", sortie)

    def test_liste_n_envoie_rien(self):
        code, sortie = lancer("--liste")
        self.assertEqual(code, 0)
        self.assertIn("virgule7x1", sortie)
        self.assertIn("Rien envoyé", sortie)

    def test_liste_gagne_sur_le_port(self):
        code, sortie = lancer("--liste", "--port", "/dev/inexistant")
        self.assertEqual(code, 0)
        self.assertIn("Rien envoyé", sortie)

    def test_jumeau_format_partout_va_au_bout(self):
        mcf = Jumeau31()
        code, sortie = lancer("--jumeau", mcf=mcf)
        self.assertEqual(code, 0)
        self.assertIn("terminé : %d trames, message de format partout." % len(list(grille())), sortie)
        self.assertEqual({cmd for cmd, _ in mcf.vues}, {0x31})

    def test_arret_au_premier_message_nouveau_et_la_suite_reprend(self):
        mcf = Jumeau31({b"B,B,B,B,B,B,B": b"E:Le groupe de taxe est invalide"})
        code, sortie = lancer("--jumeau", mcf=mcf)
        self.assertEqual(code, 1)
        self.assertIn("ARRÊT virgule7xB", sortie)
        self.assertIn("message nouveau : E:Le groupe de taxe est invalide", sortie)
        self.assertEqual(len(mcf.vues), 2)  # 1,1,1,1,1,1,1 puis B,B,B,B,B,B,B

    def test_sans_facture_ouverte_arret_immediat_sur_le_jumeau_de_base(self):
        from simulateur.faux_mcf import FauxMCF
        code, sortie = lancer("--jumeau", mcf=FauxMCF(variante="FIS"))
        self.assertEqual(code, 1)
        self.assertIn("C0 doit être soumise en premier", sortie)

    def test_jumeau_par_defaut_a_une_facture_ouverte(self):
        code, sortie = lancer("--jumeau")
        self.assertEqual(code, 0)
        self.assertIn("message de format partout", sortie)

    def test_depuis_reprend_au_numero_affiche(self):
        code, sortie = lancer("--jumeau", "--depuis", "7", "--plafond", "2")
        self.assertEqual(code, 0)
        lignes = [l for l in sortie.splitlines() if " 007 " in l or " 008 " in l]
        self.assertEqual(len(lignes), 2)
        self.assertIn("suite : --depuis 9", sortie)

    def test_plafond_au_dessus_de_la_limite_n_envoie_rien(self):
        mcf = Jumeau31()
        code, sortie = lancer("--jumeau", "--plafond", str(PLAFOND + 1), mcf=mcf)
        self.assertEqual(code, 2)
        self.assertEqual(mcf.vues, [])

    def test_depart_hors_grille_et_sequence_hors_plage_n_envoient_rien(self):
        mcf = Jumeau31()
        for argv in (("--depuis", "0"), ("--depuis", "999"), ("--seq", "1F"), ("--seq", "ZZ")):
            code, sortie = lancer("--jumeau", *argv, mcf=mcf)
            self.assertEqual(code, 2)
            self.assertIn("rien envoyé", sortie)
        self.assertEqual(mcf.vues, [])


if __name__ == "__main__":
    unittest.main()
