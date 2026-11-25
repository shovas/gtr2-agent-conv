#!/usr/bin/env python3
"""Decrypt ISI ``//[[gM``-header encrypted text configs (.svm and gMb-family).

Algorithm source: Luigi Auriemma's GPLv2 ``rfactorgmdec`` (verified from the
published 0.2b source). It is a additive keystream generated from a 256-byte
permutation and a game-specific 32-bit ``keynum``. This module is an
independent Python implementation; no third-party code or binaries are stored
in this repository.

Documented keynums:

===================  ==============
Game                 Keynum
===================  ==============
rFactor              0
ARCA / ACTC          0x000b2023
Top Race 2009        0x000dfc2a
Superleague Formula  0x0001be0b
===================  ==============

Corpus verification: all 10 encrypted ``.svm`` files decrypt at 100% printable
text with keynum 0; all 18 ``gMb1.002f`` configs decrypt with their game's
keynum (Top Race / TC2000: 0x000dfc2a, Superleague: 0x0001be0b).
"""
from __future__ import annotations


def _build_key() -> list[int]:
    """Build the deterministic 256-byte substitution table."""
    key = [0] * 256
    used = [0] * 256
    d, c = 12, 5
    for b in range(256):
        a = d * b + c
        while used[a & 0xFF]:
            a += 1
            c += 1
        a = d * b + c
        key[b] = a & 0xFF
        used[a & 0xFF] = a + 1
        d = (d + 1) % 35
        c = (c + 2) % 9
    return key


GM_KEY = _build_key()

GM_KEYNUMS = {
    "rf1": 0x00000000,
    "arca": 0x000B2023,
    "tr2009": 0x000DFC2A,
    "slf": 0x0001BE0B,
}


def decrypt_gm_payload(payload: bytes, keynum: int) -> bytes:
    """Decrypt the binary payload following a ``//[[gM`` header."""
    out = bytearray()
    c = keynum & 0xFFFFFFFF
    for i, byte in enumerate(payload):
        out.append((byte - GM_KEY[c & 0xFF]) & 0xFF)
        c = ((c << 1) + (1 if c & 0x80000000 else 0)) & 0xFFFFFFFF
        c = (c & 0xFFFFFF00) | ((c ^ (i + 1)) & 0xFF)
    return bytes(out)


def split_gm_file(data: bytes) -> bytes | None:
    """Return the encrypted payload of a ``//[[gM`` file, or None."""
    if not data.startswith(b"//[[gM") or data[6:7] == b"a":
        return None
    newline = data.find(b"\n")
    if newline < 0 or newline + 1 >= len(data):
        return None
    return data[newline + 1:]


def decrypt_gm_file(data: bytes, keynum: int) -> bytes | None:
    """Split and decrypt a complete encrypted config file."""
    payload = split_gm_file(data)
    return None if payload is None else decrypt_gm_payload(payload, keynum)


def printability(data: bytes) -> float:
    """Fraction of characters typical of SimBin text configs."""
    if not data:
        return 0.0
    sample = data[:512]
    return sum(32 <= c < 127 or c in (9, 10, 13) for c in sample) / len(sample)


def detect_keynum(data: bytes) -> str | None:
    """Pick the best-scoring documented keynum for a whole file."""
    payload = split_gm_file(data)
    if payload is None:
        return None
    scores = [(printability(decrypt_gm_payload(payload, key)), name)
              for name, key in GM_KEYNUMS.items()]
    best = max(scores)
    return best[1] if best[0] > 0.9 else None
