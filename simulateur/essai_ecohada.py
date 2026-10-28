"""Un essai d'ECOHADA MCF CLI face au faux MCF, à lancer DANS le bac à sable.

Usage : simulateur/bac_a_sable.sh python3 -m simulateur.essai_ecohada <dossier d'essai> [--variante NE|BF]
Le dossier d'essai (sous externe/wine/essais/) contient input.csv et app.xml ; l'essai y écrit
console.txt (sortie du CLI), journal.txt (trames vues par le faux MCF) et input.csv.mcf s'il y a lieu.
"""
import argparse
import os
import shutil
import subprocess
import sys
import threading
import tty

from simulateur import cale
from simulateur.faux_mcf import FauxMCF

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLI = os.path.join(RACINE, "externe", "wine", "cli")
ORIGINE = os.path.join(RACINE, "externe", "ecohada", "x_cli", "ECOHADA MCF CLI")


def wine(*args, delai=60):
    return subprocess.run(["wine", *args], capture_output=True, timeout=delai)


def main(argv=None):
    a = argparse.ArgumentParser()
    a.add_argument("dossier")
    a.add_argument("--variante", choices=("NE", "BF", "FIS"), default="NE")
    a.add_argument("--delai", type=int, default=120)
    a.add_argument("--winedebug", default="")
    a.add_argument("--latence", type=float, default=0.2)
    a.add_argument("--sans-cale", action="store_true", help="témoin : lignes modem du pty non simulées")
    a.add_argument("--garder-base", action="store_true", help="garder mcf.s3db de l'essai précédent (avoir)")
    o = a.parse_args(argv)
    d = os.path.abspath(o.dossier)
    for f in ("input.csv", "app.xml"):
        shutil.copy(os.path.join(d, f), os.path.join(CLI, f))
    if not o.garder_base:
        shutil.copy(os.path.join(ORIGINE, "mcf.s3db"), os.path.join(CLI, "mcf.s3db"))
    for f in ("input.csv.mcf", "journal.txt", "console.txt"):
        for base in (CLI, d):
            if os.path.exists(os.path.join(base, f)):
                os.remove(os.path.join(base, f))

    maitre, esclave = os.openpty()
    tty.setraw(esclave)
    port = os.ttyname(esclave)
    mcf = FauxMCF(o.variante, os.path.join(d, "journal.txt"), o.latence)
    threading.Thread(target=mcf.servir, args=(maitre,), daemon=True).start()

    wine("reg", "delete", r"HKCU\Software\Wine\Drivers", "/v", "Graphics", "/f")
    wine("reg", "add", r"HKLM\Software\Wine\Ports", "/v", "COM1", "/d", port, "/t", "REG_SZ", "/f")
    subprocess.run(["wineserver", "-k"], capture_output=True)
    try:
        env = dict(os.environ)
        if not o.sans_cale:
            env["LD_PRELOAD"] = cale.compiler()
        if o.winedebug:
            env["WINEDEBUG"] = o.winedebug
        r = subprocess.run(["wine", "MCF-CLI.exe", "input.csv", "input.csv.mcf", "COM1"],
                           cwd=CLI, capture_output=True, timeout=o.delai, env=env)
        sortie = r.stdout + r.stderr
    except subprocess.TimeoutExpired as e:
        sortie = (e.stdout or b"") + (e.stderr or b"") + b"\n[delai depasse]\n"
    with open(os.path.join(d, "console.txt"), "wb") as c:
        c.write(sortie.replace(b"\r", b""))
    if os.path.exists(os.path.join(CLI, "input.csv.mcf")):
        shutil.copy(os.path.join(CLI, "input.csv.mcf"), d)
    subprocess.run(["wineserver", "-k"], capture_output=True)
    print(sortie.decode("latin-1").replace("\r", ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
