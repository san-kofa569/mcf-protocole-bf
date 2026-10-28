import os
import shutil
import subprocess
import unittest

PROJET = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(PROJET, "simulateur", "bac_a_sable.sh")


# Le bac à sable monte externe/wine (logiciels tiers) et masque appareil/brut : deux dossiers jamais publiés.
LOCAUX = all(os.path.isdir(os.path.join(PROJET, d)) for d in ("externe/wine", "appareil/brut"))


def dedans(*commande, delai=60):
    return subprocess.run([SCRIPT, *commande], capture_output=True, text=True, timeout=delai)


@unittest.skipUnless(shutil.which("bwrap") and LOCAUX, "bwrap, externe/wine ou appareil/brut absent")
class BacASable(unittest.TestCase):
    def test_aucun_reseau(self):
        r = dedans("ip", "-o", "link")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual([l.split(":")[1].strip() for l in r.stdout.splitlines()], ["lo"])

    def test_dossier_personnel_masque(self):
        cible = os.path.expanduser("~/.zshrc")
        self.assertTrue(os.path.exists(cible))
        self.assertNotEqual(dedans("test", "-e", cible).returncode, 0)

    def test_projet_en_lecture_seule_et_captures_masquees(self):
        self.assertNotEqual(dedans("touch", os.path.join(PROJET, "README.md")).returncode, 0)
        r = dedans("ls", "-A", os.path.join(PROJET, "appareil", "brut"))
        self.assertEqual(r.stdout.strip(), "")

    def test_externe_wine_en_ecriture(self):
        temoin = os.path.join(PROJET, "externe", "wine", ".essai_ecriture")
        self.assertEqual(dedans("touch", temoin).returncode, 0)
        os.remove(temoin)

    def test_wine_demarre(self):
        r = dedans("wine", "cmd", "/c", "echo", "bac-a-sable-ok", delai=120)
        self.assertIn("bac-a-sable-ok", r.stdout)


if __name__ == "__main__":
    unittest.main()
