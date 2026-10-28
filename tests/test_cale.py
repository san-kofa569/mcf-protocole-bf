import os
import subprocess
import sys
import tempfile
import unittest

from simulateur.cale import compiler

# Exécuté dans un processus à part, cale chargée ou non : imprime le résultat de chaque ioctl.
SONDE = r"""
import fcntl, os, select, struct, sys, termios, tty
def essai(fd, req, val=0):
    try:
        return struct.unpack("i", fcntl.ioctl(fd, req, struct.pack("i", val)))[0]
    except OSError as e:
        return "errno%d" % e.errno
m, s = os.openpty(); tty.setraw(s)
print(essai(s, termios.TIOCMGET))
bic = essai(s, termios.TIOCMBIC, termios.TIOCM_DTR)
print("ok" if isinstance(bic, int) else bic, essai(s, termios.TIOCMGET))
os.write(m, b"abc")
select.select([s], [], [], 2)
print(essai(s, termios.FIONREAD))
with open(sys.argv[1], "wb") as f:
    print(essai(f.fileno(), termios.TIOCMGET))
"""
CTS, CAR, DSR, DTR = 0x020, 0x040, 0x100, 0x002


class Cale(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dossier = tempfile.mkdtemp()
        cls.preload = compiler(cls.dossier)

    def sonde(self, avec_cale):
        env = dict(os.environ)
        env.pop("LD_PRELOAD", None)
        if avec_cale:
            env["LD_PRELOAD"] = self.preload
        r = subprocess.run([sys.executable, "-I", "-c", SONDE, os.path.join(self.dossier, "fichier")],
                           env=env, capture_output=True, text=True, check=True)
        self.assertEqual(r.stderr, "")
        return r.stdout.split("\n")

    def test_deux_classes_elf(self):
        classes = {}
        for triplet in ("i386-linux-gnu", "x86_64-linux-gnu"):
            with open(os.path.join(self.dossier, "lib", triplet, "modem_pty.so"), "rb") as f:
                classes[triplet] = f.read(5)[4]
        self.assertEqual(classes, {"i386-linux-gnu": 1, "x86_64-linux-gnu": 2})

    def test_temoin_sans_cale_un_pty_refuse_tiocmget(self):
        self.assertEqual(self.sonde(False)[0], "errno25")

    def test_cale_leve_cts_dsr_cd(self):
        lignes = int(self.sonde(True)[0])
        self.assertEqual(lignes & (CTS | CAR | DSR), CTS | CAR | DSR)

    def test_dtr_reglable_cts_reste_leve(self):
        bic, lignes = self.sonde(True)[1].split()
        self.assertEqual(bic, "ok")
        self.assertEqual((int(lignes) & DTR, int(lignes) & CTS), (0, CTS))

    def test_autres_ioctl_intacts(self):
        self.assertEqual(self.sonde(True)[2], "3")

    def test_pas_un_terminal_echec_conserve(self):
        self.assertEqual(self.sonde(True)[3], "errno25")


if __name__ == "__main__":
    unittest.main()
