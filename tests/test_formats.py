import unittest

from appareil.formats import arrondi, article, c0, c3, commentaire, echapper, paiement


class Echapper(unittest.TestCase):
    def test_virgule_et_balises(self):
        self.assertEqual(echapper("A,B<C>&D'E"), "A^x2c;B^lt;C^gt;^amp;D E")

    def test_fins_de_ligne_croisees_comme_ecohada(self):
        self.assertEqual(echapper("a\rb\nc"), "a^xa;b^xd;c")


class Arrondi(unittest.TestCase):
    def test_demi_vers_le_haut_comme_le_c(self):
        self.assertEqual((arrondi(0.5), arrondi(2.5), arrondi(1180.4)), ("1", "3", "1180"))


class Article(unittest.TestCase):
    def test_ttc_sans_taxe_montant_de_ligne(self):
        self.assertEqual(article("ARTICLE TEST", "B", "18.0", 100, "1"), "ARTICLE TEST\tB18.0%100\t100*1")

    def test_quantite(self):
        self.assertEqual(article("UN", "B", "18.0", 1180, "2"), "UN\tB18.0%2360\t1180*2")

    def test_taxe_specifique_ajoutee_au_montant(self):
        self.assertEqual(article("UN", "B", "18.0", 1180, "1", taxe=59), "UN\tB18.0%1239\t1180*1")

    def test_code_article_apres_saut_de_ligne(self):
        self.assertEqual(article("UN", "A", "0.0", 500, "1", code="P01"), "UN\nP01\tA0.0%500\t500*1")

    def test_designation_64_et_code_24(self):
        d = article("X" * 70, "A", "0.0", 1, "1", code="C" * 30)
        self.assertEqual(d.split("\n")[0], "X" * 64)
        self.assertEqual(d.split("\n")[1].split("\t")[0], "C" * 24)

    def test_virgule_du_nom_echappee(self):
        self.assertEqual(article("SAC, RIZ", "B", "18.0", 10, "1"), "SAC^x2c; RIZ\tB18.0%10\t10*1")


class Facture(unittest.TestCase):
    def test_c0_identique_a_celui_accepte_le_2026_10_09(self):
        self.assertEqual(c0("1", "Essai", "{IFU}", "FV", "ESSAI-0001", isf="ISF-ESSAI"),
                         open("appareil/essais/c0_essai3_niger.txt", encoding="latin-1").read().strip())

    def test_c0_avoir_et_taux(self):
        self.assertEqual(c0("1", "Essai", "{IFU}", "FA", "AV-1", origine="XX99999999-5", taux="A"),
                         "1,Essai,{IFU},FA,XX99999999-5,TTC,ECOHADA,AV-1,A")

    def test_c3_client_comptant(self):
        self.assertEqual(c3("", "CLIENT COMPTANT", "CC"), ",CLIENT COMPTANT,CC,,")

    def test_paiement_mode_inconnu_devient_autre(self):
        self.assertEqual((paiement("E", "2360"), paiement("X", "5")), ("E2360", "A5"))


if __name__ == "__main__":
    unittest.main()


class TemoinsExecution(unittest.TestCase):
    """Trames émises par ECOHADA face au faux MCF le 2026-10-10 (simulateur.matrice, valeurs fictives)."""

    def test_31_taxe_colonne_7_en_ttc_et_suffixe_t(self):
        self.assertEqual(article("ARTICLE TS7", "B", "18.0", 1180, "2", taxe=10, specifique=("50", "59")),
                         "ARTICLE TS7\tB18.0%2370\t1180*2;T50,59")

    def test_31_taxe_colonne_6_en_ht(self):
        self.assertEqual(article("ARTICLE TS", "B", "18.0", 1000, "2", taxe=59, specifique=("50", "59")),
                         "ARTICLE TS\tB18.0%2059\t1000*2;T50,59")

    def test_31_decimales_arrondies_quantite_brute(self):
        self.assertEqual(article("ARTICLE DEC", "B", "18.0", 999.5, "1.5"), "ARTICLE DEC\tB18.0%1499\t1000*1.5")
        self.assertEqual(article("ARTICLE DEMI", "A", "0.0", 0.5, "3"), "ARTICLE DEMI\tA0.0%2\t1*3")

    def test_31_echappement(self):
        self.assertEqual(article("CAFÉ, l'essai & <test>", "B", "18.0", 1180, "1"),
                         "CAFÉ^x2c; l essai ^amp; ^lt;test^gt;\tB18.0%1180\t1180*1")

    def test_c0_avoir_reference_d_origine(self):
        self.assertEqual(c0("1", "Vendeur Essai", "99999999Z", "FA", "M-AV", isf="ISF-ESSAI", origine="XX99999999-3"),
                         "1,Vendeur Essai,99999999Z,FA,XX99999999-3,TTC,ISF-ESSAI,M-AV")

    def test_c0_cle_de_taux(self):
        self.assertEqual(c0("1", "Vendeur Essai", "99999999Z", "FV", "M-TXA", isf="ISF-ESSAI", taux="A"),
                         "1,Vendeur Essai,99999999Z,FV,TTC,ISF-ESSAI,M-TXA,A")

    def test_c3_client_avec_ifu(self):
        self.assertEqual(c3("9999999999999", "Societe Essai", "PM", "Adresse Essai", "Contact Essai"),
                         "9999999999999,Societe Essai,PM,Adresse Essai,Contact Essai")

    def test_36_commentaire(self):
        self.assertEqual(commentaire("A", "Commentaire essai"), "A,Commentaire essai")

    def test_35_mode_inconnu(self):
        self.assertEqual(paiement("X", "2860"), "A2860")
