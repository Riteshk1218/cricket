"""Generate the app's original sound effects (FOUR, SIX, WICKET) as small WAV files.

The sounds are synthesised here from sine/square waves and noise, so they are
original works with no third-party licence. Run:  python scripts/generate_sounds.py
"""
import math
import random
import struct
import wave
from pathlib import Path

RATE = 22050
OUT = Path(__file__).resolve().parent.parent / "mobile" / "assets" / "sounds"


def envelope(i, n, attack=0.02):
    a = int(RATE * attack)
    if i < a:
        return i / a
    return max(0.0, 1 - (i - a) / max(1, n - a)) ** 1.5


def tone(freq, dur, kind="sine", vol=0.4, slide=None):
    n = int(RATE * dur)
    out = []
    phase = 0.0
    for i in range(n):
        f = freq if slide is None else freq * (slide / freq) ** (i / n)
        phase += 2 * math.pi * f / RATE
        s = math.sin(phase)
        if kind == "square":
            s = 1.0 if s >= 0 else -1.0
        elif kind == "triangle":
            s = 2 / math.pi * math.asin(math.sin(phase))
        out.append(s * vol * envelope(i, n))
    return out


def noise(dur, vol=0.3, seed=7):
    rng = random.Random(seed)
    n = int(RATE * dur)
    prev = 0.0
    out = []
    for i in range(n):
        prev = 0.6 * prev + 0.4 * (rng.random() * 2 - 1)  # soft low-pass
        out.append(prev * vol * envelope(i, n, 0.005))
    return out


def mix(*tracks):
    """tracks: (start_seconds, samples)"""
    length = max(int(start * RATE) + len(s) for start, s in tracks)
    buf = [0.0] * length
    for start, samples in tracks:
        off = int(start * RATE)
        for i, v in enumerate(samples):
            buf[off + i] += v
    peak = max(1e-9, max(abs(v) for v in buf))
    return [v / peak * 0.85 for v in buf]


def write(name, samples):
    OUT.mkdir(parents=True, exist_ok=True)
    with wave.open(str(OUT / name), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(b"".join(struct.pack("<h", int(v * 32767)) for v in samples))
    print("wrote", OUT / name)


if __name__ == "__main__":
    write("four.wav", mix((0, tone(523, 0.15, "triangle")), (0.12, tone(659, 0.15, "triangle")),
                          (0.24, tone(784, 0.4, "triangle"))))
    write("six.wav", mix(*[(i * 0.1, tone(f, 0.3, "square", 0.2)) for i, f in enumerate([523, 659, 784, 1047])],
                         (0.45, tone(1047, 0.6, "triangle")), (0.4, noise(0.8, 0.25))))
    write("wicket.wav", mix((0, noise(0.15, 0.6, 3)), (0.1, tone(440, 0.5, "triangle", 0.4, slide=110))))
