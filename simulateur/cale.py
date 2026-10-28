"""Compile la cale modem_pty.c en 32 et 64 bits et donne la valeur de LD_PRELOAD.

Wine 32 bits charge la version i386, ses processus 64 bits la version x86_64 :
le chargeur remplace $LIB par lib/<triplet> selon la classe du processus.
"""
import os
import subprocess

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = os.path.join(RACINE, "simulateur", "modem_pty.c")
SORTIE = os.path.join(RACINE, "externe", "wine", "cale")
TRIPLETS = {"i386-linux-gnu": ["-m32"], "x86_64-linux-gnu": []}
OPTIONS = ["-shared", "-fPIC", "-nostdlib", "-ffreestanding", "-fno-stack-protector", "-O2", "-Wall"]


def compiler(sortie=SORTIE):
    """Recompile si la source est plus récente ; renvoie la valeur de LD_PRELOAD."""
    for triplet, arch in TRIPLETS.items():
        so = os.path.join(sortie, "lib", triplet, "modem_pty.so")
        if os.path.exists(so) and os.path.getmtime(so) >= os.path.getmtime(SOURCE):
            continue
        os.makedirs(os.path.dirname(so), exist_ok=True)
        subprocess.run(["gcc", *arch, *OPTIONS, "-o", so, SOURCE, "/lib/%s/libc.so.6" % triplet],
                       check=True, capture_output=True)
    return os.path.join(sortie, "$LIB", "modem_pty.so")
