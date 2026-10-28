import unittest

from appareil.trame import bcc_ok, paquet, remplir, trame


def reponse(seq, cmd, data, statut=b"\x80" * 6):
    corps = bytes([0x20 + len(data) + 4 + len(statut) + 1, seq, cmd]) + data + b"\x04" + statut + b"\x05"
    s = sum(corps)
    return b"\x01" + corps + bytes(((s >> k) & 0xF) + 0x30 for k in (12, 8, 4, 0)) + b"\x03"


class Trame(unittest.TestCase):
    def test_c1_envoyee_le_2026_10_09(self):
        self.assertEqual(trame(0x20, 0xC1).hex(" "), "01 24 20 c1 05 30 31 30 3a 03")

    def test_longueur_compte_les_donnees(self):
        t = trame(0x21, 0x2B, b"I0")
        self.assertEqual(t[1], 0x20 + 2 + 4)
        self.assertEqual(t[4:6], b"I0")

    def test_bcc_reponse_juste(self):
        self.assertIs(bcc_ok(reponse(0x20, 0xC1, b"1,2,3")), True)

    def test_bcc_reponse_alteree(self):
        r = bytearray(reponse(0x20, 0xC1, b"1,2,3")); r[5] ^= 1
        self.assertIs(bcc_ok(bytes(r)), False)

    def test_bcc_apres_nak(self):
        # 2026-10-12, C3 facture ouverte : NAK (15) puis une trame complète, BCC juste
        r = bytes.fromhex("15 01 2b 3f c3 04 a2 80 80 80 80 80 05 30 34 35 38 03")
        self.assertIs(bcc_ok(r), True)

    def test_paquet_apres_nak(self):
        r = b"\x15" + reponse(0x3F, 0xC3, b"", b"\xa2" + b"\x80" * 5)
        self.assertEqual(paquet(r), (b"", b"\xa2" + b"\x80" * 5))

    def test_paquet_sans_trame(self):
        self.assertIsNone(paquet(b"\x15"))

    def test_bcc_sans_fin_de_donnees(self):
        self.assertIsNone(bcc_ok(b"\x15"))


class Remplir(unittest.TestCase):
    def test_sans_ifu_inchange(self):
        self.assertEqual(remplir("ARTICLE\tB100*1", {}), "ARTICLE\tB100*1")

    def test_ifu_remplace(self):
        self.assertEqual(remplir("1,Essai,{IFU},FV", {"MCF_IFU": "IFU00000X"}), "1,Essai,IFU00000X,FV")

    def test_signature_remplacee(self):
        env = {"MCF_IFU": "IFU00000X", "MCF_SIG": "ABCDEFGHIJKLMNOPQRSTUV23"}
        self.assertEqual(remplir("{IFU},FA,COR,{SIG}", env), "IFU00000X,FA,COR,ABCDEFGHIJKLMNOPQRSTUV23")

    def test_signature_absente_ou_invalide_refusee(self):
        for sig in (None, "", "ABCDEFGHIJKLMNOPQRSTUV2", "abcdefghijklmnopqrstuv23", "ABCDEFGHIJKLMNOPQRSTUV2…"):
            env = {} if sig is None else {"MCF_SIG": sig}
            self.assertIsNone(remplir("FA,COR,{SIG}", env), sig)

    def test_ifu_absent_refuse(self):
        self.assertIsNone(remplir("1,Essai,{IFU},FV", {}))

    def test_ifu_invalide_refuse(self):
        for faux in ("\u2026", "X", "IFU00000XX", "IFU 0000X", "IFU0000\u00e9X"):
            self.assertIsNone(remplir("1,Essai,{IFU},FV", {"MCF_IFU": faux}), faux)


if __name__ == "__main__":
    unittest.main()
