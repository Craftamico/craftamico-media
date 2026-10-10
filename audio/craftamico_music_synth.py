"""Original background music for Craftamico social clips (composed procedurally, no samples)."""
import sys
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

SR = 44100


def note_freq(n):  # MIDI -> Hz
    return 440.0 * 2 ** ((n - 69) / 12)


def env(length, a=0.005, d=0.1, s=0.6, r=0.1):
    n = int(length * SR)
    t = np.arange(n) / SR
    e = np.ones(n) * s
    an, dn, rn = int(a * SR), int(d * SR), int(r * SR)
    if an:
        e[:an] = np.linspace(0, 1, an)
    if dn:
        e[an:an + dn] = np.linspace(1, s, min(dn, max(0, n - an)))[: len(e[an:an + dn])]
    if rn and rn < n:
        e[-rn:] *= np.linspace(1, 0, rn)
    return e


def lp(x, cutoff):
    return sosfilt(butter(2, cutoff, "low", fs=SR, output="sos"), x)


def hp(x, cutoff):
    return sosfilt(butter(2, cutoff, "high", fs=SR, output="sos"), x)


def kick(dur=0.35):
    t = np.arange(int(dur * SR)) / SR
    f = 110 * np.exp(-t * 18) + 45
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * np.exp(-t * 9) * 0.95


def clap(dur=0.25, rng=None):
    t = np.arange(int(dur * SR)) / SR
    n = rng.standard_normal(len(t))
    n = hp(lp(n, 6000), 900)
    e = np.exp(-t * 22)
    a = int(0.002 * SR); e[:a] *= np.linspace(0, 1, a)
    return n * e * 0.32


def hat(dur=0.06, rng=None, open_=False):
    d = 0.22 if open_ else dur
    t = np.arange(int(d * SR)) / SR
    n = hp(rng.standard_normal(len(t)), 7000)
    e = np.exp(-t * (14 if open_ else 70)); a = int(0.0015 * SR); e[:a] *= np.linspace(0, 1, a)
    return n * e * 0.11


def pluck(freq, dur):
    t = np.arange(int(dur * SR)) / SR
    x = (np.sin(2 * np.pi * freq * t) + 0.35 * np.sin(2 * np.pi * 2 * freq * t)
         + 0.12 * np.sin(2 * np.pi * 3 * freq * t))
    return lp(x * np.exp(-t * 7), 4500) * 0.22


def pad(freqs, dur):
    t = np.arange(int(dur * SR)) / SR
    x = np.zeros_like(t)
    for f in freqs:
        for det in (-0.12, 0.0, 0.12):
            ff = f * 2 ** (det / 12)
            x += 2 * ((t * ff) % 1.0) - 1  # saw
    x = lp(x / (len(freqs) * 3), 1800)
    return x * env(dur, a=0.25, d=0.3, s=0.85, r=0.3) * 0.16


def bass(freq, dur):
    t = np.arange(int(dur * SR)) / SR
    x = np.sin(2 * np.pi * freq * t) + 0.25 * np.sin(2 * np.pi * 2 * freq * t)
    return x * env(dur, a=0.004, d=0.12, s=0.7, r=0.05) * 0.32


def place(buf, sig, start):
    i = max(0, int(start * SR))
    j = min(len(buf), i + len(sig))
    if i < len(buf):
        buf[i:j] += sig[: j - i]


def render(bpm, prog, length_s, seed, mood):
    rng = np.random.default_rng(seed)
    beat = 60 / bpm
    bar = 4 * beat
    total = int(length_s * SR)
    drums = np.zeros(total)
    music = np.zeros(total)
    side = np.ones(total)
    n_bars = int(np.ceil(length_s / bar))
    for b in range(n_bars):
        t0 = b * bar
        chord = prog[b % len(prog)]
        root = chord[0]
        intro = b < 2
        # pad
        place(music, pad([note_freq(n) for n in chord], bar), t0)
        # bass: root on 1, 2.5, 3, 4.5 (energetic) or 1, 3 (calm)
        hits = [0, 1.5, 2, 3.5] if mood == "up" else [0, 2, 2.75]
        if not intro:
            for h in hits:
                place(music, bass(note_freq(root - 12), beat * 0.9), t0 + h * beat)
        # arpeggio plucks (16ths up / 8ths calm)
        step = beat / (4 if mood == "up" else 2)
        pattern = [0, 1, 2, 1, 2, 3, 2, 1] if mood == "up" else [0, 2, 1, 3]
        arp = list(chord) + [chord[0] + 12]
        k = 0
        tt = 0.0
        while tt < bar - 1e-6:
            n = arp[pattern[k % len(pattern)] % len(arp)] + 12
            place(music, pluck(note_freq(n), step * 1.8), t0 + tt)
            tt += step
            k += 1
        # drums
        if not intro:
            for q in range(4):
                place(drums, kick(), t0 + q * beat)
                i = int((t0 + q * beat) * SR)
                dl = int(0.18 * SR)
                if i < total:
                    seg = side[i:i + dl]
                    seg *= np.linspace(0.45, 1.0, len(seg))
            for q in (1, 3):
                place(drums, clap(rng=rng), t0 + q * beat)
            for e8 in range(8):
                place(drums, hat(rng=rng, open_=(e8 % 4 == 2 and mood == "up")) * (1.0 if e8 % 2 else 0.6),
                      t0 + e8 * beat / 2 + 0.004 * rng.standard_normal())
        else:
            for e8 in range(8):
                place(drums, hat(rng=rng) * 0.5, t0 + e8 * beat / 2)
    mix = music * side + drums
    mix = hp(mix, 30)
    # soft clip + fades
    mix = np.tanh(mix * 1.4) / np.tanh(1.4)
    fi, fo = int(0.3 * SR), int(1.5 * SR)
    mix[:fi] *= np.linspace(0, 1, fi)
    mix[-fo:] *= np.linspace(1, 0, fo)
    mix /= np.max(np.abs(mix)) + 1e-9
    mix *= 0.89
    # simple stereo width: delayed copy on right
    d = int(0.011 * SR)
    right = np.concatenate([np.zeros(d), mix[:-d]]) * 0.92 + mix * 0.08
    st = np.stack([mix, right], axis=1)
    return (st * 32767).astype(np.int16)


if __name__ == "__main__":
    out = sys.argv[1]
    # Track A: "Werkstatt" – zuversichtlich, mittleres Tempo (Handwerker)
    a_prog = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]]  # Am F C G
    # Track B: "Aufbruch" – hell, energisch (Hausbesitzer / Vorher-Nachher)
    b_prog = [[48, 52, 55, 59], [57, 60, 64, 67], [53, 57, 60, 64], [55, 59, 62, 65]]  # Cmaj7 Am7 Fmaj7 G7
    wavfile.write(f"{out}/track_werkstatt.wav", SR, render(100, a_prog, 40, 1, "calm"))
    wavfile.write(f"{out}/track_aufbruch.wav", SR, render(116, b_prog, 40, 2, "up"))
    print("ok")
