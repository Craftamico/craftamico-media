"""Craftamico 'Feierabend' – ruhige Hintergrundmusik, komplett synthetisch erzeugt (keine Samples, keine fremden Melodien)."""
import sys
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt, fftconvolve

SR = 44100
rng = np.random.default_rng(7)

def hz(n): return 440.0 * 2 ** ((n - 69) / 12)
def lp(x, c): return sosfilt(butter(2, c, "low", fs=SR, output="sos"), x)
def hp(x, c): return sosfilt(butter(2, c, "high", fs=SR, output="sos"), x)

def place(buf, sig, t):
    i = int(t * SR); j = min(len(buf), i + len(sig))
    if 0 <= i < len(buf): buf[i:j] += sig[: j - i]

def epiano(f, dur, vel=1.0):
    t = np.arange(int(dur * SR)) / SR
    mod = np.sin(2 * np.pi * f * t) * 1.2 * np.exp(-t * 3.0)          # FM -> soft bell attack
    x = np.sin(2 * np.pi * f * t + mod) + 0.18 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t * 2)
    e = np.exp(-t * 1.1); a = int(0.006 * SR); e[:a] *= np.linspace(0, 1, a)
    r = int(0.25 * SR); e[-r:] *= np.linspace(1, 0, r)
    trem = 1 + 0.06 * np.sin(2 * np.pi * 4.5 * t)
    return lp(x * e * trem, 3200) * 0.11 * vel

def pad(freqs, dur):
    t = np.arange(int(dur * SR)) / SR; x = np.zeros_like(t)
    for f in freqs:
        for d in (-0.07, 0.07):
            x += np.sin(2 * np.pi * f * 2 ** (d / 12) * t) + 0.3 * np.sin(2 * np.pi * 2 * f * t)
    e = np.ones_like(t); a = int(1.2 * SR); r = int(1.2 * SR)
    e[:a] = np.linspace(0, 1, a); e[-r:] = np.linspace(1, 0, r)
    return lp(x / (len(freqs) * 2), 1200) * e * 0.07

def bass(f, dur):
    t = np.arange(int(dur * SR)) / SR
    x = np.sin(2 * np.pi * f * t) + 0.15 * np.sin(2 * np.pi * 2 * f * t)
    e = np.exp(-t * 0.9); a = int(0.02 * SR); e[:a] *= np.linspace(0, 1, a)
    r = int(0.15 * SR); e[-r:] *= np.linspace(1, 0, r)
    return x * e * 0.2

def shaker(dur=0.09):
    t = np.arange(int(dur * SR)) / SR
    n = hp(lp(rng.standard_normal(len(t)), 9000), 4000)
    e = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 2
    return n * e * 0.025

def reverb(x, secs=2.2, wet=0.28):
    n = int(secs * SR); t = np.arange(n) / SR
    ir = rng.standard_normal(n) * np.exp(-t * 3.2); ir = lp(ir, 5000); ir /= np.sqrt(np.sum(ir ** 2))
    y = fftconvolve(x, ir)[: len(x)]
    return x * (1 - wet) + y * wet * 0.9

def render(length_s=40, bpm=72):
    beat = 60 / bpm; bar = 4 * beat; total = int(length_s * SR)
    keys = np.zeros(total); low = np.zeros(total); perc = np.zeros(total)
    # Fmaj9 – Em7 – Dm9 – Cmaj9  (absteigend, warm, entspannt)
    prog = [[53, 57, 60, 64, 67], [52, 55, 59, 62], [50, 53, 57, 60, 64], [48, 52, 55, 59, 62]]
    melody = {1: [(0, 76), (2.5, 74)], 3: [(0, 72), (1.5, 71), (3, 67)], 5: [(0, 76), (2, 79)], 7: [(0.5, 74), (2, 72)]}
    nbars = int(np.ceil(length_s / bar))
    for b in range(nbars):
        t0 = b * bar; ch = prog[b % 4]
        place(low, pad([hz(n) for n in ch[:4]], bar + 1.2), t0 - 0.3)
        # piano: chord on 1, soft re-strike on the "and" of 2
        for k, n in enumerate(ch):
            place(keys, epiano(hz(n), bar, 0.9), t0 + k * 0.012)
        for n in ch[1:]:
            place(keys, epiano(hz(n), beat * 2.2, 0.45), t0 + 1.5 * beat)
        if b >= 1:
            place(low, bass(hz(ch[0] - 24), beat * 2.6), t0)
            place(low, bass(hz(ch[0] - 24 + 7), beat * 1.4), t0 + 2.5 * beat)
        if (b % 8) in melody and b < nbars - 1:
            for pos, n in melody[b % 8]:
                place(keys, epiano(hz(n), beat * 3, 0.7), t0 + pos * beat)
        if b >= 2:
            for e8 in range(8):
                place(perc, shaker() * (1.0 if e8 % 2 else 0.55), t0 + e8 * beat / 2 + 0.006 * rng.standard_normal())
    mix = reverb(keys) + low + reverb(perc, 1.0, 0.2)
    mix = hp(mix, 35)
    mix = np.tanh(mix * 1.2) / np.tanh(1.2)
    fi, fo = int(1.0 * SR), int(2.0 * SR)
    mix[:fi] *= np.linspace(0, 1, fi); mix[-fo:] *= np.linspace(1, 0, fo)
    mix /= np.max(np.abs(mix)) + 1e-9; mix *= 0.85
    d = int(0.013 * SR)
    right = np.concatenate([np.zeros(d), mix[:-d]]) * 0.85 + mix * 0.15
    return (np.stack([mix, right], 1) * 32767).astype(np.int16)

if __name__ == "__main__":
    wavfile.write(sys.argv[1], SR, render())
    print("ok")
