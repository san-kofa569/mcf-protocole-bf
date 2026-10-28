import sys, time, serial
def trame(seq, cmd, data=b""):
    corps = bytes([0x20 + len(data) + 4, seq, cmd]) + data + b"\x05"
    s = sum(corps)
    bcc = bytes(((s >> sh) & 0xF) + 0x30 for sh in (12, 8, 4, 0))
    return b"\x01" + corps + bcc + b"\x03"
t = trame(0x20, 0xC1)
print("envoi :", t.hex(" "))
with serial.Serial(sys.argv[1], 115200, timeout=0.2) as p:
    p.reset_input_buffer()
    p.write(t); p.flush()
    rep, fin = b"", time.time() + 5
    while time.time() < fin:
        rep += p.read(256)
print("reçu (%d octets) :" % len(rep), rep.hex(" "))
print("ascii :", rep.decode("latin-1", "replace"))
