"""Envoi d'UNE trame au MCF par le port série, et lecture de sa réponse.

Usage : python3 trame.py <port> <seq hex> <cmd hex> [données] [--simulation]
Un {IFU} dans les données est remplacé par la variable d'environnement MCF_IFU ;
sans elle, ou si elle ne fait pas 9 caractères alphanumériques, rien n'est envoyé (la simulation, elle, affiche la trame telle quelle).
"""
import os
import sys
import time


def trame(seq, cmd, data=b""):
    corps = bytes([0x20 + len(data) + 4, seq, cmd]) + data + b"\x05"
    s = sum(corps)
    return b"\x01" + corps + bytes(((s >> k) & 0xF) + 0x30 for k in (12, 8, 4, 0)) + b"\x03"


def bcc_ok(b):
    try:
        d = b.index(1); i5 = b.index(5, b.index(4, d)); s = sum(b[d+1:i5+1])
        return bytes(((s >> k) & 0xF) + 0x30 for k in (12, 8, 4, 0)) == b[i5+1:i5+5]
    except ValueError:
        return None


def paquet(b):
    """(données, statut) de la trame de réponse, même précédée d'un NAK (15) ou de SYN (16) ; None sans trame."""
    try:
        d = b.index(1); i4 = b.index(4, d); i5 = b.index(5, i4)
    except ValueError:
        return None
    return b[d+4:i4], b[i4+1:i5]


def remplir(texte, env=os.environ):
    if "{IFU}" in texte:
        # 9 caractères (C1, 2e champ). Un « … » collé tel quel a failli partir le 2026-10-12.
        ifu = env.get("MCF_IFU", "")
        if len(ifu) != 9 or not (ifu.isascii() and ifu.isalnum()):
            return None
        texte = texte.replace("{IFU}", env["MCF_IFU"])
    return texte


def main(argv):
    port, seq, cmd = argv[1], int(argv[2], 16), int(argv[3], 16)
    args = [a for a in argv[4:] if a != "--simulation"]
    simulation = "--simulation" in argv
    texte = args[0] if args else ""
    rempli = remplir(texte)
    if rempli is None and not simulation:
        print("{IFU} présent mais MCF_IFU absent ou invalide (9 caractères) : rien envoyé."); return 2
    data = (texte if rempli is None else rempli).encode("latin-1")
    t = trame(seq, cmd, data)
    print(time.strftime("%Y-%m-%d %H:%M:%S"), "envoi :", t.hex(" "))
    if simulation:
        print("SIMULATION : rien envoyé. Données :", data.decode("latin-1")); return 0
    import serial
    with serial.Serial(port, 115200, timeout=0.2) as p:
        p.reset_input_buffer(); p.write(t); p.flush()
        rep, fin = b"", time.time() + 5
        while time.time() < fin:
            rep += p.read(256)
    print("reçu (%d octets) :" % len(rep), rep.hex(" "))
    print("BCC :", bcc_ok(rep))
    p = paquet(rep)
    if p:
        if rep.index(1):
            print("avant la trame :", rep[:rep.index(1)].hex(" "), "(15 = NAK, 16 = SYN)")
        print("données :", p[0].decode("utf-8", "replace"))
        print("statut :", p[1].hex(" "))
    else:
        print("ascii :", rep.decode("latin-1", "replace"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
