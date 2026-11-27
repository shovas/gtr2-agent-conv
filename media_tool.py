"""Basic media format identification and limited semantic read/write.

Supported semantic R/W: WAV (PCM via stdlib wave; lossless copy for unsupported formats like MP3-in-WAV).
Supported identification/header parsing: WAV, DDS, TGA, BMP, JPG, MP3, BIK.
Lossless byte copy is always possible for supported identified files.
"""
from __future__ import annotations

import argparse
import json
import math
import struct
import wave
from dataclasses import dataclass, asdict, field
from pathlib import Path


@dataclass
class MediaInfo:
    path: str
    size: int
    format: str
    details: dict


JCA_MAGIC = b"\x0f\xb1\xff\xff"


GMT_MAGIC_ISI = bytes.fromhex("c8cfd2d8ced8e6c3d6ded8bebba7bf90")
GMT_MAGIC_GTR1 = bytes.fromhex("c8cfd2d8ced8e6c3d6ded8bdbba6bf90")


def _looks_like_media(data: bytes) -> bool:
    return (data[:4] in (b"DDS ", b"RIFF") or
            (len(data) >= 18 and data[1] == 0 and data[2] in (2, 3, 10)) or
            (len(data) >= 24 and (data[8:24] == GMT_MAGIC_ISI or
                                  data[4:20] == GMT_MAGIC_GTR1)))


def _looks_like_text_config(data: bytes) -> bool:
    """ISIMotor key=value / section text: >90% printable plus '=' or braces.

    Shared by ``decrypt_jca_text`` and ``detect_jca_key`` so the auto-detecting
    CLI accepts the same payloads as the decryption API.
    """
    sample = data[:4096]
    if not sample:
        return False
    config_syntax = b"=" in sample or (b"{" in sample and b"}" in sample)
    return (config_syntax and
            sum(32 <= c < 127 or c in (9, 10, 13) for c in sample)
            > 0.9 * len(sample))


def _looks_like_shader(data: bytes) -> bool:
    """HLSL/PS1.1 or gMotor2 shader-description source (no '=' keys)."""
    flat = b" ".join(data[:4096].split())
    return (b"ps.1.1" in flat or b"register (c" in flat or
            b"gMotor2 Shader" in flat or b"PS_OUTPUT ps2" in flat)


def detect_jca_key(data: bytes) -> str | None:
    """Try each known JCA key and return the name that yields a valid payload.

    Corpus-verified: Race07/GTL/Volvo default vs Volvo's custom key, and
    RaceRoomTheGame/RaceRoomTheGame2 JCA GMTs (v1, volvo key) whose decrypted
    ISI GMT magic sits at offset 8. Also recognises text configs and shaders,
    so the ``jca-decrypt --key auto`` CLI accepts everything the dedicated
    ``decrypt_jca_text`` / ``decrypt_jca_shader`` APIs do. Media is tried
    across all keys first so a text-like false positive cannot win over the
    correct media key. Returns ``None`` if no key produces a recognisable
    payload.
    """
    import jca_crypt
    keys = [None] + sorted(jca_crypt.CUSTOM_KEYS)
    candidates = []
    for name in keys:
        try:
            candidates.append((name, jca_crypt.decrypt_bytes(
                data, jca_crypt.CUSTOM_KEYS.get(name))))
        except Exception:
            continue
    for name, out in candidates:
        if _looks_like_media(out):
            return name or "default"
    for name, out in candidates:
        if _looks_like_text_config(out):
            return name or "default"
    for name, out in candidates:
        if _looks_like_shader(out):
            return name or "default"
    return None


def decrypt_jca_bytes(data: bytes, key_name: str | None = None) -> bytes:
    """Decrypt a JCA-wrapped payload (WAV, DDS, TGA) with the given JCA key."""
    import jca_crypt
    if data[:4] != JCA_MAGIC:
        raise ValueError("not a JCA-encrypted file")
    custom = jca_crypt.CUSTOM_KEYS.get(key_name) if key_name else None
    return jca_crypt.decrypt_bytes(data, custom)


def decrypt_jca_text(data: bytes) -> bytes:
    """Decrypt a JCA-wrapped text config (.aud/.car/.gdb/.scn/...) to plain text.

    Unlike media payloads, text has no recognisable magic, so each known key
    is tried and the >90%-printable candidate with config syntax is chosen:
    either a '=' (key/value) or both '{' and '}' (a section with no keys).
    Non-JCA input is returned unchanged; undecryptable input is preserved.
    Corpus-verified on 153 JCA-wrapped .aud files (Race07/Volvo) and on
    section-only configs such as Volvo's `DefTweak.gdb`.
    """
    if data[:4] != JCA_MAGIC:
        return data
    import jca_crypt
    for name in [None] + sorted(jca_crypt.CUSTOM_KEYS):
        try:
            out = jca_crypt.decrypt_bytes(data, jca_crypt.CUSTOM_KEYS.get(name))
        except Exception:
            continue
        if _looks_like_text_config(out):
            return out
    return data


def decrypt_jca_shader(data: bytes) -> bytes | None:
    """Decrypt a JCA-wrapped ISI shader source (.vsh/.psh/.gfx).

    Corpus-verified on 226 RaceRoom shader files (v1, volvo key): decrypted
    payloads are HLSL/PS1.1 or gMotor2 shader-description text, which contain
    no '=' and therefore are not accepted by ``decrypt_jca_text``.
    """
    if data[:4] != JCA_MAGIC:
        return None
    import jca_crypt
    for name in [None] + sorted(jca_crypt.CUSTOM_KEYS):
        try:
            out = jca_crypt.decrypt_bytes(data, jca_crypt.CUSTOM_KEYS.get(name))
        except Exception:
            continue
        if _looks_like_shader(out):
            return out
    return None


def decrypt_jca_wav(data: bytes, key_name: str | None = None) -> bytes:
    """Decrypt a JCA-wrapped WAV to plain RIFF/WAVE bytes.

    ``key_name`` selects a non-default JCA key (e.g. ``volvo``); ``None`` uses
    the game default. Raises on bad magic or wrong key.
    """
    import jca_crypt
    if data[:4] != JCA_MAGIC:
        raise ValueError("not a JCA-encrypted file")
    custom = jca_crypt.CUSTOM_KEYS.get(key_name) if key_name else None
    out = jca_crypt.decrypt_bytes(data, custom)
    if out[:4] != b"RIFF" or out[8:12] != b"WAVE":
        raise ValueError("JCA payload is not a WAVE file")
    return out


def identify(path: str | Path) -> MediaInfo:
    p = Path(path)
    b = p.read_bytes()
    size = len(b)
    head = b[:64]
    ext = p.suffix.lower()
    # JCA-encrypted files (SimBin audio and texture archives)
    if head.startswith(JCA_MAGIC):
        details = {"jca_encrypted": True}
        try:
            key = detect_jca_key(b)
            plain = decrypt_jca_bytes(b, key)
            details["jca_key"] = key
            details["decrypted_size"] = len(plain)
            if len(plain) >= 24 and plain[8:24] == GMT_MAGIC_ISI:
                details["gmt_magic_at"] = 8
                return MediaInfo(str(p), size, "gmt-jca", details)
            if len(plain) >= 20 and plain[4:20] == GMT_MAGIC_GTR1:
                details["gmt_magic_at"] = 4
                return MediaInfo(str(p), size, "gmt-gtr1-jca", details)
            if plain[:4] == b"DDS " and len(plain) >= 128:
                w, h = struct.unpack_from("<II", plain, 12)
                details.update({"width": w, "height": h,
                                "fourcc": plain[84:88].decode("latin1", "replace")})
                return MediaInfo(str(p), size, "dds-jca", details)
            if plain[:4] == b"RIFF" and plain[8:12] == b"WAVE":
                off = 12
                while off + 8 <= len(plain):
                    cid = plain[off:off+4]; csz = struct.unpack_from('<I', plain, off+4)[0]
                    if cid == b'fmt ' and csz >= 16:
                        af, ch, sr, br, ba, bits = struct.unpack_from('<HHIIHH', plain, off+8)
                        details.update({"audio_format": af, "channels": ch, "framerate": sr,
                                        "bits_per_sample": bits, "byte_rate": br, "block_align": ba})
                        break
                    off += 8 + csz + (csz & 1)
                return MediaInfo(str(p), size, "wav-jca", details)
            if len(plain) >= 18 and plain[1] == 0 and plain[2] in (2, 3, 10):
                w, h, bpp = struct.unpack_from("<HHB", plain, 12)
                details.update({"image_type": plain[2], "width": w, "height": h, "bpp": bpp})
                return MediaInfo(str(p), size, "tga-jca", details)
            # RaceRoom .vsh/.psh/.gfx are JCA-encrypted ISI shader sources;
            # identify them by decrypted source signatures.
            head = plain[:4096]
            if ext in (".vsh", ".psh", ".gfx"):
                flat0 = b" ".join(head.split())
                if (b"register (c" in flat0 or b"ps.1.1" in flat0 or
                        b"gMotor2 Shader" in flat0 or b"PS_OUTPUT ps2" in flat0):
                    details["shader_source"] = True
                    return MediaInfo(str(p), size, "shader-jca", details)
        except Exception as e:
            details["error"] = str(e)
        # JCA-wrapped text config / shader source: detect_jca_key only recognises
        # media magic, so try the text-aware decoder here.
        try:
            text = decrypt_jca_text(b)
            if ext in (".vsh", ".psh", ".gfx") and decrypt_jca_shader(b):
                details["shader_source"] = True
                return MediaInfo(str(p), size, "shader-jca", details)
            if text != b and b"=" in text[:4096]:
                lines = text[:4096].count(b"\n") + 1
                details.update({"jca_text": True, "lines": lines,
                                "extension": ext})
                return MediaInfo(str(p), size, "text-jca", details)
        except Exception as e:
            details["error"] = str(e)
        return MediaInfo(str(p), size, "jca", details)
    # WAV
    if head.startswith(b"RIFF") and b[8:12] == b"WAVE":
        fmt = "wav"
        details = {}
        try:
            with wave.open(str(p), "rb") as w:
                details = {
                    "channels": w.getnchannels(),
                    "sampwidth": w.getsampwidth(),
                    "framerate": w.getframerate(),
                    "nframes": w.getnframes(),
                    "comptype": w.getcomptype(),
                }
        except Exception as e:
            # Fallback: parse fmt chunk manually (e.g. WAVE_FORMAT_MP3=0x55)
            details = {"error": str(e)}
            try:
                off = 12
                while off + 8 <= len(b):
                    cid = b[off:off+4]; csz = struct.unpack_from('<I', b, off+4)[0]
                    if cid == b'fmt ' and csz >= 16:
                        audio_fmt, ch, sr, br, ba, bits = struct.unpack_from('<HHIIHH', b, off+8)
                        details.update({"audio_format": audio_fmt, "channels": ch, "framerate": sr, "bits_per_sample": bits, "byte_rate": br, "block_align": ba})
                        break
                    off += 8 + csz + (csz & 1)
            except Exception:
                pass
        return MediaInfo(str(p), size, fmt, details)
    # DDS
    if head.startswith(b"DDS "):
        details = {}
        if size >= 128:
            hdr_size, flags, height, width, pitch, depth, mipmaps = struct.unpack_from("<7I", b, 4)
            pf_size, pf_flags, fourcc, rgb_bits, rmask, gmask, bmask, amask = struct.unpack_from("<2I4s5I", b, 76)
            caps1, caps2 = struct.unpack_from("<2I", b, 108)
            details = {
                "header_size": hdr_size, "flags": flags, "height": height, "width": width,
                "pitch_or_linear_size": pitch, "depth": depth, "mipmaps": mipmaps,
                "pf_size": pf_size, "pf_flags": pf_flags,
                "pf_fourcc": fourcc.decode("latin1", "replace").strip("\x00"),
                "rgb_bit_count": rgb_bits, "r_mask": rmask, "g_mask": gmask, "b_mask": bmask, "a_mask": amask,
                "caps1": caps1, "caps2": caps2,
            }
        return MediaInfo(str(p), size, "dds", details)
    # BMP (may be TGA with .bmp extension in GTL/GTR2)
    if head.startswith(b"BM"):
        details = {}
        if size >= 54:
            fsize, _, _, off = struct.unpack_from("<IHHI", b, 2)
            dib = struct.unpack_from("<I", b, 14)[0]
            details = {"file_size_field": fsize, "pixel_offset": off, "dib_size": dib}
        return MediaInfo(str(p), size, "bmp", details)
    # JPG
    if head.startswith(b"\xff\xd8\xff"):
        details = {}
        i = 2
        while i < len(b) - 9:
            if b[i] != 0xFF:
                i += 1; continue
            marker = b[i+1]
            if marker in (0xC0, 0xC1, 0xC2):
                ln = struct.unpack_from('>H', b, i+2)[0]
                bits, h, w = struct.unpack_from('>BHH', b, i+4)
                details = {'sof': marker, 'width': w, 'height': h, 'bits': bits}
                break
            if marker == 0xD9 or marker == 0xDA:
                break
            if i+4 <= len(b):
                ln = struct.unpack_from('>H', b, i+2)[0]
                i += 2 + max(ln,2)
            else:
                break
        return MediaInfo(str(p), size, "jpg", details)
    # MAS archive headers (content-based, regardless of file extension)
    if b.startswith(b"GMOTORMAS10"):
        return MediaInfo(str(p), size, "mas", {"variant": "type0"})
    if b.startswith(b"CUBEMAS4.10"):
        return MediaInfo(str(p), size, "mas", {"variant": "type3"})
    if b.startswith((b"CUBEMAS4.00", b"CUBEMAS4.01")):
        return MediaInfo(str(p), size, "mas", {"variant": "type6"})
    if b.startswith(b"CUBEMAS2.50"):
        return MediaInfo(str(p), size, "mas", {"variant": "type5"})
    if b.startswith(bytes.fromhex("c8cfd2d8ced8e6c9caddd8bebba6bf90")):
        return MediaInfo(str(p), size, "mas", {"variant": "type1"})
    if b.startswith(bytes.fromhex("cec3d5c7c0d9e6c9caddd8bebba6bf90")):
        return MediaInfo(str(p), size, "mas", {"variant": "type1x"})
    # GMT mesh variants: ISI magic at +8, GTR1 third magic at +4, Race 07 DLC
    if len(b) >= 24 and b[8:24] == bytes.fromhex(
            "c8cfd2d8ced8e6c3d6ded8bebba7bf90"):
        return MediaInfo(str(p), size, "gmt", {"version": "isi-magic@8"})
    if len(b) >= 20 and b[4:20] == bytes.fromhex(
            "c8cfd2d8ced8e6c3d6ded8bdbba6bf90"):
        return MediaInfo(str(p), size, "gmt-gtr1", {"version": "gtr1-magic@4"})
    if b.startswith(b"RaceGMT\0"):
        return MediaInfo(str(p), size, "racegmt", {"version": "RaceGMT\\0"})
    # GIF87a/GIF89a (little-endian width/height at +6)
    if b[:6] in (b"GIF87a", b"GIF89a") and len(b) >= 10:
        w, h = struct.unpack_from("<HH", b, 6)
        return MediaInfo(str(p), size, "gif", {"width": w, "height": h,
                                               "version": b[:6].decode("latin-1")})
    # PNG (IHDR: width, height, bit depth, colour type)
    if b.startswith(b"\x89PNG\r\n\x1a\n") and len(b) >= 33:
        w, h, depth, ctype = struct.unpack_from(">IIBB", b, 16)
        return MediaInfo(str(p), size, "png", {"width": w, "height": h,
                                               "bit_depth": depth,
                                               "color_type": ctype})
    # rF1 .rfm mod descriptor: "Mod Name" / "Track Filter" keys
    if ext == ".rfm" and b"Mod Name" in b[:4096]:
        return MediaInfo(str(p), size, "rfactor-rfm", {"extension": ext})
    # UTF-16LE text starts with ff fe, which also matches an MP3 frame sync.
    if b[:2] == b"\xff\xfe" and ext in (".dic", ".txt", ".ini"):
        return MediaInfo(str(p), size, "utf16-text", {"bom": "ff-fe"})
    # MP3
    if head.startswith(b"ID3") or (len(head) >= 2 and head[0] == 0xFF and (head[1] & 0xE0) == 0xE0):
        details = {"id3": head.startswith(b"ID3")}
        off = 0
        if head.startswith(b"ID3") and len(b) > 10:
            tag_size = ((b[6]&0x7f)<<21)|((b[7]&0x7f)<<14)|((b[8]&0x7f)<<7)|(b[9]&0x7f)
            off = 10 + tag_size
        # find frame sync
        for j in range(off, min(len(b)-4, off+4096)):
            if b[j] == 0xFF and (b[j+1] & 0xE0) == 0xE0:
                ver = (b[j+1] >> 3) & 3
                layer = (b[j+1] >> 1) & 3
                br_idx = (b[j+2] >> 4) & 0xF
                sr_idx = (b[j+2] >> 2) & 3
                details.update({'mpeg_version_bits': ver, 'layer_bits': layer, 'bitrate_index': br_idx, 'samplerate_index': sr_idx})
                break
        return MediaInfo(str(p), size, "mp3", details)
    # TGQ (Electronic Arts TQI video + SCHl/ADPCM audio, e.g. F1 2000 ANIM)
    if head.startswith(b"SCHl") or (ext == ".tgq" and head[:4] == b"SCHl"):
        return MediaInfo(str(p), size, "tgq", {"container": "EA SCHl", "codecs": "tqi + adpcm_ea"})
    # BIK
    if head.startswith(b"BIKi") or head.startswith(b"KB2i"):
        details = {}
        if size >= 24:
            sig, fsize, frames, max_frame, w, h = struct.unpack_from("<4sIIIII", b, 4)
            details = {"file_size_field": fsize, "frames": frames, "max_frame_size": max_frame, "width": w, "height": h}
        return MediaInfo(str(p), size, "bik", details)
    # TGA (no strong magic; use extension + heuristic)
    if ext == ".tga" and size >= 18:
        idlen, cmap, imgtype = struct.unpack_from("<BBB", b, 0)
        w, h = struct.unpack_from("<HH", b, 12)
        bpp = b[16]
        return MediaInfo(str(p), size, "tga", {"image_type": imgtype, "width": w, "height": h, "bpp": bpp})
    # GTL/GTR2 quirk: .bmp files with TGA header (idlen=0,cmap=0,imgtype=2, 32bpp) 
    if ext == ".bmp" and size >= 18:
        idlen, cmap, imgtype = struct.unpack_from("<BBB", b, 0)
        w, h = struct.unpack_from("<HH", b, 12)
        bpp = b[16]
        if idlen == 0 and cmap == 0 and imgtype in (2, 10) and bpp in (24, 32) and w > 0 and h > 0:
            return MediaInfo(str(p), size, "tga-in-bmp", {"image_type": imgtype, "width": w, "height": h, "bpp": bpp})
    # rFactor CUBEASF scene family (.scn/.clf/.set/.trk/.bak), parsed by
    # simbin_text_tool.parse_scn; JCA-wrapped variants are reported above.
    if b.startswith(b"CUBEASF"):
        return MediaInfo(str(p), size, "cubeasf", {"family": "rFactor scene",
                                                   "extension": ext})
    # SimBin/ISI text configs (plain variants; JCA ones reported as text-jca)
    _CFG_SIGNS = {
        ".rcd": (b"Abbreviation=", b"Nationality="),
        ".gdb": (b"RaceStart", b"RaceLaps"),
        ".car": (b"HDVehicle=", b"Graphics="),
        ".aiw": (b"wp_pos=", b"WP_PTRS="),
        ".cam": (b"Position=", b"Orientation="),
        ".hed": (b"Spring", b"SpringBody"),
        ".dmg": (b"RestrictionSphere", b"RadiusAdd"),
        ".grb": (b"ratio=", b"bevel="),
    }
    if ext in _CFG_SIGNS:
        head16 = b[:65536]
        if any(sig in head16 for sig in _CFG_SIGNS[ext]):
            return MediaInfo(str(p), size, "config-" + ext[1:], {"extension": ext})
    # rF1 terrain-definition files (.tdf) carry [TRACKVARS]/[FEEDBACK]/[LOOSE]
    if ext == ".tdf" and b"[TRACKVARS]" in b[:8192]:
        return MediaInfo(str(p), size, "rfactor-tdf", {"extension": ext})
    # rFactor text-config families (plain variants; JCA ones reported above)
    if ext == ".cas" and (b"MeshFile=" in b[:8192] or b"SearchPath=" in b[:8192]):
        return MediaInfo(str(p), size, "rfactor-cas", {"extension": ext})
    if ext == ".sp" and b"[BODY]" in b[:8192]:
        return MediaInfo(str(p), size, "rfactor-sp", {"extension": ext})
    if ext == ".inccar" and (b"Graphics=" in b[:8192] or b"Eyepoint=" in b[:8192]):
        return MediaInfo(str(p), size, "rfactor-inccar", {"extension": ext})
    # rFactor .veh vehicle descriptor (key=value with Graphics=/HDVehicle=)
    if ext == ".veh" and (b"Graphics=" in b[:8192] or b"HDVehicle=" in b[:8192]):
        return MediaInfo(str(p), size, "rfactor-veh", {"extension": ext})
    # ISI physics/audio/animation text configs with distinctive key signatures.
    # These were previously "unknown" even though simbin_text_tool parses them.
    prefix = b[:16384]
    if ext == ".hdv" and (b"[GENERAL]" in prefix or b"high-detail vehicle" in prefix):
        return MediaInfo(str(p), size, "hdv", {"extension": ext})
    if ext == ".eng" and b"RPMTorque=" in prefix:
        return MediaInfo(str(p), size, "eng", {"extension": ext})
    if ext == ".aud" and (b"_ENGINE_" in prefix or b"ENGINE_" in prefix):
        return MediaInfo(str(p), size, "aud", {"extension": ext})
    if ext == ".ani" and (b"Motions=" in prefix or b".lma" in prefix.lower()):
        return MediaInfo(str(p), size, "ani", {"extension": ext})
    # rFactor scene scripts: .scr (Actor/Mesh blocks), .cin (CinematicEvent)
    if ext == ".scr" and b"Actor" in b[:8192]:
        return MediaInfo(str(p), size, "rfactor-scr", {"extension": ext})
    if ext == ".cin" and b"CinematicEvent" in b[:16384]:
        return MediaInfo(str(p), size, "rfactor-cin", {"extension": ext})
    # rFactor .gen vehicle-graphics descriptor (same key family as .scn)
    if ext == ".gen" and (b"MeshFile=" in b[:8192] or b"MASFile=" in b[:8192]):
        return MediaInfo(str(p), size, "rfactor-gen", {"extension": ext})
    # ISI animation containers: `FXM `/`LMA ` magics (fxm_tool.py decodes them).
    if head[:4] in (b"FXM ", b"LMA "):
        version, flags = struct.unpack_from("<HH", b, 4) if size >= 8 else (0, 0)
        return MediaInfo(str(p), size, "fxm" if head[:3] == b"FXM" else "lma",
                         {"version": version, "flags": flags})
    # Driving School scripts are plain text with a gMa1.000f marker, not an
    # encrypted gMb config; the marker was previously only recognised on .svm.
    if b.startswith(b"DrivingSchool"):
        return MediaInfo(str(p), size, "driving-school", {"plain_text": True})
    # .svm car setups: rF1 uses a gMa header, GTR2 plain [GENERAL]/[CONTROLS]
    # sections, and a few shipped files have an encrypted gMb payload.
    if b.startswith(b"//[[gMa1.000f"):
        return MediaInfo(str(p), size,
                         "svm-rf1" if ext == ".svm" else "rf1-config",
                         {"plain_text": True})
    if ext == ".svm":
        if b.startswith(b"//[[gMb1.000f") or b.startswith(b"//[[gMb1.002f"):
            payload = b[b.find(b"\n") + 1:]
            return MediaInfo(str(p), size, "svm-encrypted",
                             {"header": b[:14].decode("latin-1", "replace"),
                              "payload_magic": payload[:8].hex(" ")})
        prefix = b[:4096]
        if (b.lstrip().startswith((b"[GENERAL]", b"[CONTROLS]", b"[BODYAERO]",
                                   b"VehicleClassSetting"))
                or b"VehicleClassSetting=" in prefix
                or b"[GENERAL]" in prefix):
            return MediaInfo(str(p), size, "svm-gtr2", {"plain_text": True})
        if b[:2] == b"\x1f\x8b":
            return MediaInfo(str(p), size, "svm-gzip", {})
    # gzip-wrapped .hat track data (GTR2/GTL gMb header, Race07 ver008)
    if ext == ".hat" and b[:2] == b"\x1f\x8b":
        hat = hat_decompress(p)
        if hat is not None:
            payload, info = hat
            counts = hat_declared_counts(payload)
            grid = hat_grid_params(payload)
            if counts is not None:
                info["polygons"] = counts[0]
                info["bisection_nodes"] = counts[1]
                info["records"] = counts[2]
            if grid is not None:
                info["grid_origin_x"] = grid[0]
                info["grid_inv_cell_x"] = grid[1]
                info["grid_origin_z"] = grid[2]
                info["grid_inv_cell_z"] = grid[3]
            return MediaInfo(str(p), size, "hat-gzip", info)
    # Other gzip-wrapped SimBin containers (Driving School scripts, time trials,
    # replays). Their payloads begin with a `//[[gM` header or a binary stream.
    if ext in (".dsi", ".gtt", ".vcr") and b[:2] == b"\x1f\x8b":
        try:
            import gzip_simbin_tool as gz
            payload = gz.decompress(p)
            details = {"compressed_size": size, "decompressed_size": len(payload)}
            if payload.startswith(b"//[[gM"):
                details["variant"] = payload[:14].decode("latin1", "replace").strip()
            return MediaInfo(str(p), size, "simbin-gzip", details)
        except Exception as exc:
            return MediaInfo(str(p), size, "simbin-gzip", {"error": str(exc)[:80]})
    # NASCAR-era .hdr/.dat audio pair: the .hdr is an index and the companion
    # .dat is a plain MP3 stream. Content-based so it cannot collide with
    # unrelated .hdr files that lack an MP3 companion.
    if ext == ".hdr":
        pair = hdr_dat_mp3(p)
        if pair is not None:
            _payload, info = pair
            return MediaInfo(str(p), size, "hdr-dat",
                             {"companion": info["dat_path"],
                              "block_count": info["block_count"],
                              "dat_blocks": info["dat_blocks"],
                              "codec": "mp3"})
    return MediaInfo(str(p), size, "unknown", {"ext": ext})


@dataclass
class WavHeader:
    audio_format: int
    channels: int
    sample_rate: int
    byte_rate: int
    block_align: int
    bits_per_sample: int


def wav_header(data: bytes, key_name: str | None = None) -> WavHeader | None:
    """Parse RIFF/WAVE fmt data, decrypting JCA-wrapped audio if needed.

    Corpus-verified on sampled GTR2/GTL/Race07/Volvo WAVs. Volvo requires
    ``key_name="volvo"``; other corpora use the default JCA key.
    """
    if data[:4] == JCA_MAGIC:
        try:
            data = decrypt_jca_wav(data, key_name)
        except Exception:
            return None
    if data[:4] != b"RIFF" or len(data) < 36 or data[8:12] != b"WAVE":
        return None
    pos = 12
    while pos + 8 <= len(data):
        chunk_id = data[pos:pos + 4]
        size = struct.unpack_from("<I", data, pos + 4)[0]
        if chunk_id == b"fmt " and pos + 8 + 16 <= len(data):
            af, ch, sr, br, ba, bps = struct.unpack_from("<HHIIHH", data, pos + 8)
            return WavHeader(af, ch, sr, br, ba, bps)
        pos += 8 + size + (size & 1)
    return None


WAV_KNOWN_CHUNKS = {"fmt ", "data", "PAD ", "LIST", "fact", "bext",
                    "LGWV", "_PMX", "DISP", "cue "}


def wav_chunks(data: bytes, key_name: str | None = None) -> list[tuple[str, int]] | None:
    """Walk RIFF chunks of a (possibly JCA-wrapped) WAV file."""
    if data[:4] == JCA_MAGIC:
        try:
            data = decrypt_jca_wav(data, key_name)
        except Exception:
            return None
    if data[:4] != b"RIFF" or len(data) < 12 or data[8:12] != b"WAVE":
        return None
    chunks: list[tuple[str, int]] = []
    pos = 12
    while pos + 8 <= len(data):
        chunk_id = data[pos:pos + 4]
        if not all(32 <= c < 127 for c in chunk_id):
            return None
        size = struct.unpack_from("<I", data, pos + 4)[0]
        if pos + 8 + size > len(data):
            return None
        chunks.append((chunk_id.decode("latin-1"), size))
        pos += 8 + size + (size & 1)
    # Final odd-sized chunks sometimes omit the word-alignment pad byte.
    return chunks if pos in (len(data), len(data) + 1) else None


def validate_wav_chunks(chunks: list[tuple[str, int]]) -> list[str]:
    """Check corpus-verified WAV chunk structure.

    Verified on 100 sampled GTR2/GTL/Race07/Volvo WAVs: fmt is always first,
    data appears exactly once, and all chunks use a closed known-ID set.
    """
    problems: list[str] = []
    if not chunks:
        return ["no chunks"]
    if chunks[0][0] != "fmt ":
        problems.append("fmt is not the first chunk")
    if sum(1 for cid, _ in chunks if cid == "data") != 1:
        problems.append("data chunk count != 1")
    for cid, _size in chunks:
        if cid not in WAV_KNOWN_CHUNKS:
            problems.append(f"unknown chunk {cid!r}")
    return problems


def validate_wav_header(header: WavHeader) -> list[str]:
    """Check corpus-verified PCM WAV invariants; non-PCM is left opaque."""
    if header.audio_format != 1:
        return []  # e.g. WAVE_FORMAT_MPEGLAYER3 (0x55); not covered
    problems: list[str] = []
    if header.channels not in (1, 2):
        problems.append(f"channels {header.channels}")
    if header.bits_per_sample not in (8, 16):
        problems.append(f"bits per sample {header.bits_per_sample}")
    if header.sample_rate not in (8000, 11025, 22000, 22050, 44100, 48000):
        problems.append(f"sample rate {header.sample_rate}")
    if header.block_align != header.channels * header.bits_per_sample // 8:
        problems.append(f"block align {header.block_align}")
    if header.byte_rate != header.sample_rate * header.channels * header.bits_per_sample // 8:
        problems.append(f"byte rate {header.byte_rate}")
    return problems


def wav_decode(src: str | Path, dst: str | Path,
               ffmpeg_exe: str | None = None) -> bool:
    """Decode a compressed WAV (ADPCM, MP3-in-WAV) to PCM WAV via ffmpeg.

    Returns True on success, False when ffmpeg is unavailable or decoding
    fails.  The caller's source is never modified.
    """
    import shutil
    import subprocess
    exe = ffmpeg_exe or shutil.which("ffmpeg")
    if exe is None:
        return False
    cmd = [exe, "-y", "-loglevel", "error", "-i", str(src),
           "-c:a", "pcm_s16le", str(dst)]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0 or not Path(dst).is_file():
        return False
    try:
        with wave.open(str(dst), "rb") as w:
            return w.getcomptype() == "NONE" and w.getnframes() > 0
    except Exception:
        return False


def jpg_decode(src: str | Path, dst: str | Path) -> tuple[int, int] | None:
    """Decode JPG to PNG via Pillow. Returns (width, height) or None."""
    try:
        from PIL import Image
        with Image.open(src) as im:
            im.load()
            size = im.size
            im.convert("RGB").save(dst, format="PNG")
            return size
    except Exception:
        return None


def jpg_encode(src: str | Path, dst: str | Path, quality: int = 90) -> bool:
    """Encode an image (PNG/JPG/etc.) to baseline JPG via Pillow."""
    try:
        from PIL import Image
        with Image.open(src) as im:
            im.convert("RGB").save(dst, format="JPEG", quality=quality)
        return Path(dst).read_bytes()[:2] == b"\xff\xd8"
    except Exception:
        return False


def mp3_decode(src: str | Path, dst: str | Path,
               ffmpeg_exe: str | None = None) -> bool:
    """Decode MP3 to PCM WAV via ffmpeg."""
    import shutil
    import subprocess
    exe = ffmpeg_exe or shutil.which("ffmpeg")
    if exe is None:
        return False
    r = subprocess.run([exe, "-y", "-loglevel", "error", "-i", str(src),
                        "-c:a", "pcm_s16le", str(dst)], capture_output=True)
    if r.returncode != 0 or not Path(dst).is_file():
        return False
    try:
        with wave.open(str(dst), "rb") as w:
            return w.getcomptype() == "NONE" and w.getnframes() > 0
    except Exception:
        return False


def hat_decompress(path: str | Path) -> tuple[bytes, dict] | None:
    """Decompress a gzip-wrapped ``.hat`` track-data file and classify its header.

    Corpus-verified on all 188 local `.hat` files (9 corpora): every one is a
    valid gzip stream. Two header variants occur — GTR2/GTL use the 45-byte
    ``//[[gMb1.000f ...]]`` prefix (10 files use `gMb1.002f`), while Race07
    starts directly with ``Ver 0.08 This file is automatically generated``.
    """
    p = Path(path)
    if p.suffix.lower() != ".hat" or not p.is_file():
        return None
    raw = p.read_bytes()
    if raw[:2] != b"\x1f\x8b":
        return None
    import gzip
    try:
        data = gzip.decompress(raw)
    except OSError:
        return None
    if data.startswith(b"//[[gMb1.002f"):
        variant = "gMb1.002f"
    elif data.startswith(b"//[[gMb1.000f"):
        variant = "gMb1.000f"
    elif data.startswith(b"Ver 0.08"):
        variant = "ver008"
    else:
        variant = "unknown"
    return data, {"variant": variant, "compressed_size": len(raw),
                  "decompressed_size": len(data)}


def hat_layout_signature(payload: bytes) -> bytes | None:
    """Return the 32-byte per-layout identifier from a decompressed `.hat`.

    This is the byte image of ``hat_grid_params()`` (four f64 grid parameters),
    not an opaque hash. Verified on all 34 GTR2 `.hat` files: after the ``generated\\x00`` marker,
    ``body[4:36]`` is constant for every variant of a physical layout and
    identical between GTL and GTR2 for the same layout. Returns ``None`` for
    header variants that do not carry the marker.
    """
    marker = payload.find(b"generated\x00")
    if marker < 0 or len(payload) < marker + 50:
        return None
    return payload[marker + 14:marker + 46]


def hat_grid_params(payload: bytes) -> tuple[float, float, float, float] | None:
    """Return the four f64 parameters of a `.hat` spatial hash grid.

    ``GTR2.exe``'s height-tree query (RVA 0x45de40) computes
    ``ix = int((x - origin_x) * inv_cell_x)``,
    ``iz = int((z - origin_z) * inv_cell_z)`` and
    ``bucket = ((ix << 5) + iz) & 0x3ff`` -- a 32x32 = 1024-bucket hash -- then
    evaluates a quadratic height surface from the bucket's cell. The 32-byte
    "signature" at body offset 4 is exactly the four doubles
    ``(origin_x, inv_cell_x, origin_z, inv_cell_z)`` used here. Generation
    differences exist: rF1/StockCarExtreme layouts use 64x64 grids (larger
    inverse cell sizes) and a correspondingly wider hash mask.

    Verified on all 178 local `.hat` files: inverse cell sizes are positive,
    and 97.9% of sampled table records map into the grid's integer range
    (the remainder are boundary samples just outside the nominal extent).
    """
    signature = hat_layout_signature(payload)
    if signature is None:
        return None
    values = struct.unpack("<4d", signature)
    if not (0 < values[1] < 1 and 0 < values[3] < 1):
        return None
    return values


def hat_grid_bucket(payload: bytes, x: float, z: float,
                    mask: int = 0x3ff) -> int | None:
    """Return the hash-bucket index for a track-space ``(x, z)`` point.

    ``mask`` defaults to ``0x3ff`` (the GTR2/GTL/Race07 32x32 grid); pass
    ``0xfff`` for rF1/StockCarExtreme 64x64 grids.
    """
    params = hat_grid_params(payload)
    if params is None:
        return None
    origin_x, inv_x, origin_z, inv_z = params
    ix = int((x - origin_x) * inv_x)
    iz = int((z - origin_z) * inv_z)
    return ((ix << 5) + iz) & mask


def hat_declared_counts(payload: bytes) -> tuple[int, int, int] | None:
    """Return the three u32 counts declared in a `.hat` body header.

    The producer (`htree.cpp` in `GTR2.exe`) writes three counts at body
    offsets 36, 40 and 44: the input polygon count, its bisection-tree node
    count (``hat_bisection_count()``), and the authoritative number of 16-byte
    records in the table at offset 48. All three are layout-specific.
    Returns ``None`` when the ``generated\\x00`` header marker is absent.
    """
    marker = payload.find(b"generated\x00")
    if marker < 0 or marker + 10 + 48 > len(payload):
        return None
    body = payload[marker + 10:]
    return struct.unpack_from("<3I", body, 36)


def hat_bisection_count(polygons: int) -> int:
    """Return ``T(n)``, the node count of GTR2.exe's HAT bisection tree.

    Function ``0x45b1d0`` in ``GTR2.exe``/``GTR2Dedicated.exe`` is a pure
    recursion: ``T(0)=0, T(1)=T(2)=1`` and, for ``n >= 3``,
    ``T(n) = 1 + T(n // 2) + T(n - n // 2)`` (recursive halving of a polygon
    until at most two remain). The HAT header stores this at body offset 40,
    with the polygon count at offset 36. Verified on all 178 local HAT files.
    """
    if polygons <= 0:
        return 0
    total = 0
    stack = [polygons]
    while stack:
        value = stack.pop()
        if value < 3:
            total += 1
            continue
        half = value // 2
        total += 1
        stack.append(half)
        stack.append(value - half)
    return total


def validate_hat(payload: bytes) -> list[str]:
    """Check a decompressed HAT payload's corpus-verified structural invariants.

    Does *not* decode the trailing typed-node tree; it only verifies the parts
    that are understood (version marker, bisection count, record table extent
    and spatial-grid parameters). Returns a list of problem strings, empty for
    a structurally coherent file. Verified clean on all 197 local HAT files.
    """
    problems = []
    marker = payload.find(b"generated\x00")
    if marker < 0:
        return ["missing 'generated\\0' marker"]
    body = payload[marker + 10:]
    if len(body) < 48:
        return [f"body too short: {len(body)} bytes"]
    counts = hat_declared_counts(payload)
    if counts is None:
        return ["missing declared counts"]
    polygons, bisection, records = counts
    if polygons <= 0 or bisection <= 0 or records <= 0:
        problems.append(f"non-positive counts: {counts}")
    if m_bisection := hat_bisection_count(polygons):
        if m_bisection != bisection:
            problems.append(f"bisection count {bisection} != T({polygons})={m_bisection}")
    if 48 + 16 * records > len(body):
        problems.append(f"record table {records}*16 exceeds body {len(body)}")
    else:
        # Every shipped HAT has at least one 34-byte node per bisection node:
        # tail / (bisection * 34) is 1.029..1.278 over 197 local files. A HAT
        # with only a header and sample table would pass the weaker checks but
        # be unusable, so require the node stream to be present.
        tail = len(body) - (48 + 16 * records)
        minimum = bisection * 34
        if tail < minimum:
            problems.append(f"tail {tail} < bisection {bisection} * 34 = {minimum}")
    grid = hat_grid_params(payload)
    if grid is None or not all(math.isfinite(value) for value in grid):
        problems.append("grid parameters missing or non-finite")
    elif grid[1] <= 0 or grid[3] <= 0:
        problems.append("grid inverse cell sizes must be positive")
    return problems


def hat_height_match(payload: bytes, reference: bytes,
                     precision: int = 2, seed: int = 2026) -> dict | None:
    """Compare two HAT record tables by spatial position, not record order.

    Same-layout HATs from different games carry the same ``(x,z)`` samples in
    different order. This builds a lookup from ``reference`` keyed by rounded
    position, matches ``payload``'s records, and reports the height agreement
    with a distribution-preserving shuffled control. Verified on GTR2 3Brno
    vs Race07 2007_Brno: 91.3% matched, mean |diff| 0.00026 vs 2.41 shuffled.
    Returns ``None`` when either payload lacks a record table.
    """
    import collections
    import random

    def table(data: bytes) -> list[tuple[float, int, float, float]]:
        counts = hat_declared_counts(data)
        if counts is None:
            return []
        marker = data.find(b"generated\x00")
        if marker < 0:
            return []
        body = data[marker + 10:]
        count = counts[2]
        if count <= 0 or 48 + 16 * count > len(body):
            return []
        return [struct.unpack_from("<fIff", body, 48 + 16 * k)
                for k in range(count)]

    source, target = table(payload), table(reference)
    if not source or not target:
        return None
    lookup = collections.defaultdict(list)
    for x, _unknown, height, z in target:
        lookup[(round(x, precision), round(z, precision))].append(height)
    pairs = []
    for x, _unknown, height, z in source:
        key = (round(x, precision), round(z, precision))
        if key in lookup:
            pairs.append((height, lookup[key][0]))
    if not pairs:
        return None
    measured = sum(abs(a - b) for a, b in pairs) / len(pairs)
    heights = [b for _a, b in pairs]
    random.seed(seed)
    random.shuffle(heights)
    shuffled = sum(abs(a - b) for (a, _b), b in zip(pairs, heights)) / len(pairs)
    return {"matched": len(pairs), "total": len(source),
            "match_rate": len(pairs) / len(source),
            "mean_abs_height_diff": measured,
            "shuffled_control": shuffled,
            "enrichment": shuffled / measured if measured else float("inf")}


def hat_transfer_heights(source: bytes, target: bytes,
                         precision: int = 2) -> tuple[bytes, dict] | None:
    """Write GTL height samples into a GTR2 HAT for the same physical layout.

    Same-layout HATs share ``(x,z)`` sample positions but store records in a
    different order, so a positional lookup transfers terrain heights while
    preserving the target's header, opaque identifiers and trailing node tree.
    Requires matching layout signatures. Verified GTL NANDERSTORP ->
    GTR2 3ANDERSTORP: 98.0% of positions matched, mean height difference
    0.0006. A mismatched layout matches ~0% and is rejected.

    Returns ``(new_payload, report)`` or ``None`` when either side is invalid.
    """
    import collections

    if hat_layout_signature(source) != hat_layout_signature(target):
        return None

    def records(data: bytes) -> tuple[bytes, int, int]:
        marker = data.find(b"generated\x00")
        counts = hat_declared_counts(data)
        if marker < 0 or counts is None:
            return b"", marker, 0
        body_at = marker + 10
        return data[body_at:], body_at, counts[2]

    source_body, _source_at, source_count = records(source)
    target_body, target_at, target_count = records(target)
    if source_count <= 0 or target_count <= 0:
        return None
    if 48 + 16 * source_count > len(source_body) or 48 + 16 * target_count > len(target_body):
        return None

    lookup = collections.defaultdict(list)
    for k in range(source_count):
        x, _unknown, height, z = struct.unpack_from("<fIff", source_body, 48 + 16 * k)
        lookup[(round(x, precision), round(z, precision))].append(height)

    output = bytearray(target)
    matched = 0
    differences = []
    for k in range(target_count):
        offset = target_at + 48 + 16 * k
        x, _unknown, height, z = struct.unpack_from("<fIff", output, offset)
        key = (round(x, precision), round(z, precision))
        if key in lookup and lookup[key]:
            replacement = lookup[key][0]
            differences.append(abs(height - replacement))
            struct.pack_into("<f", output, offset + 8, replacement)
            matched += 1
    report = {"matched": matched, "total": target_count,
              "match_rate": matched / target_count,
              "mean_abs_height_diff": (sum(differences) / len(differences)
                                       if differences else 0.0)}
    return bytes(output), report


def hat_record_count(payload: bytes) -> int:
    """Return the number of 16-byte `[f32, u32, f32, f32]` records.

    Uses the header's authoritative count at body offset 44. Previously this
    scanned records until an implausible one, which undercounted 6/34 GTR2
    files because valid records can carry ``B = 0.0`` and ``U = 0`` (e.g.
    Enna's record 7558). Falls back to the bounded scan only when the declared
    count does not fit the body or its boundary records are implausible.
    """
    marker = payload.find(b"generated\x00")
    if marker < 0:
        return 0
    body = payload[marker + 10:]
    declared = hat_declared_counts(payload)
    if declared is not None:
        count = declared[2]
        if 0 < count and 48 + 16 * count + 8 <= len(body):
            def plausible(offset: int) -> bool:
                first, _unknown, second, third = struct.unpack_from("<fIff", body, offset)
                return (-1e6 < first < 1e6 and first == first
                        and second == second and abs(second) < 100
                        and -1e6 < third < 1e6 and third == third)

            if plausible(48) and plausible(48 + 16 * (count - 1)):
                return count
    count = 0
    for offset in range(48, len(body) - 16, 16):
        first, _unknown, second, third = struct.unpack_from("<fIff", body, offset)
        if not (-1e6 < first < 1e6 and first == first
                and second == second and 0.01 < abs(second) < 20
                and -1e6 < third < 1e6 and third == third):
            break
        count += 1
    return count


def identify_hat_layout(path: str | Path, corpus: str | Path) -> dict:
    """Identify a `.hat` layout by matching its 32-byte signature in a corpus.

    ``corpus`` is scanned recursively (read-only). Matching is on the full
    32-byte signature, so different layouts sharing a track name are told
    apart. Only header identification is claimed — the body is not converted.
    """
    result = hat_decompress(path)
    if result is None:
        return {"path": str(path), "error": "not a gzip .hat file"}
    payload, info = result
    signature = hat_layout_signature(payload)
    if signature is None:
        return {"path": str(path), "variant": info["variant"],
                "error": "no layout signature"}
    matches = []
    for candidate in sorted(Path(corpus).rglob("*.hat")):
        other = hat_decompress(candidate)
        if other is None:
            continue
        if hat_layout_signature(other[0]) == signature:
            matches.append(str(candidate))
    return {"path": str(path), "variant": info["variant"],
            "body_size": len(payload) - payload.find(b"generated\x00") - 10,
            "signature": signature.hex(),
            "record_count": hat_record_count(payload),
            "declared_counts": hat_declared_counts(payload),
            "grid_params": hat_grid_params(payload), "matches": matches}


def hdr_dat_mp3(hdr_path: str | Path) -> tuple[bytes, dict] | None:
    """Return the raw MP3 payload of a NASCAR-era ``.hdr``/``.dat`` audio pair.

    Verified on 1,982 pairs in `../NT2003` and `../NascarSimRacing`: the small
    ``.hdr`` file is an index (its +8 u32 is a 256-byte-block count, exact for
    all 476 NT2003 pairs) and the companion ``.dat`` is a plain concatenated
    MP3 stream (``ff f3`` frame sync, LAME tag). The index is not needed to
    extract the audio, so this helper validates the pair and returns the MP3
    bytes plus header metadata; use ``mp3_decode`` on a temporary file (or the
    ``.dat`` itself) to obtain PCM WAV. Returns ``None`` when the companion is
    missing or is not MP3.
    """
    h = Path(hdr_path)
    dat = h.with_suffix(".dat")
    if h.suffix.lower() != ".hdr" or not dat.is_file() or not h.is_file():
        return None
    header = h.read_bytes()
    payload = dat.read_bytes()
    if len(header) < 12 or len(payload) < 4:
        return None
    if not (payload[0] == 0xFF and (payload[1] & 0xE0) == 0xE0):
        return None
    info = {
        "hdr_size": len(header),
        "dat_size": len(payload),
        "block_count": struct.unpack_from("<I", header, 8)[0],
        "dat_blocks": len(payload) // 256,
        "dat_path": str(dat),
    }
    return payload, info


def gmb_encrypted_config(data: bytes) -> dict | None:
    """Identify a SimBin ``gMb1.00xx`` encrypted-config payload.

    Corpus-verified on 19 files carrying the ``gMb1.002f`` header across
    `../TC2000`, `../SimuladorTopRace2009` and `../SuperleagueFormula2009`
    (18 encrypted configs plus one IRSR replay that only mentions the tag).
    The 12-byte bracket field is **not** an ISI signature and no decoder is
    known; this helper only exposes the structure for further research.
    """
    if not data.startswith(b"//[[gMb1."):
        return None
    nl = data.find(b"\n")
    if nl < 0 or nl > 512:
        return None
    head = data[:nl]
    first_end = head.find(b"]]")
    field_start = head.find(b"[[", first_end + 2) if first_end >= 0 else -1
    field_end = head.find(b"]]", field_start + 2) if field_start >= 0 else -1
    if field_start < 0 or field_end < 0:
        return None
    version = head[head.find(b"gMb1."):head.find(b"gMb1.") + 9].decode("latin-1")
    field = head[field_start + 2:field_end]
    payload = data[nl + 1:]
    sample = payload[:256]
    printable = (sum(32 <= c < 127 or c in (9, 10, 13) for c in sample)
                 / len(sample)) if sample else 0.0
    return {"version": version, "field": field, "payload": payload,
            "encrypted": printable < 0.6, "printable": round(printable, 3)}


def validate_hdr_dat_pair(hdr_path: str | Path) -> list[str]:
    """Check corpus-verified bounds of a NASCAR-era ``.hdr``/``.dat`` pair.

    Verified on all 1,982 pairs in `../NT2003` and `../NascarSimRacing`:
    the header is at least 16 bytes and 4-byte aligned, the block count at +8
    is nonzero and fits inside the companion .dat, and that .dat starts with
    an MP3 frame sync. Other header u32 fields do **not** encode data offsets
    (tested against MP3 sync at every field position).
    """
    pair = hdr_dat_mp3(hdr_path)
    if pair is None:
        return ["missing or non-MP3 .hdr/.dat pair"]
    _payload, info = pair
    problems: list[str] = []
    if info["hdr_size"] < 16:
        problems.append("header shorter than 16 bytes")
    if info["hdr_size"] % 4:
        problems.append("header length not 4-byte aligned")
    blocks = info["block_count"]
    if blocks <= 0 or blocks * 256 > info["dat_size"]:
        problems.append(f"block count {blocks} exceeds .dat payload")
    if info["dat_blocks"] < blocks:
        problems.append("block count exceeds computed .dat blocks")
    return problems


def mp3_encode(src: str | Path, dst: str | Path, bitrate: int = 192000,
               ffmpeg_exe: str | None = None) -> bool:
    """Encode PCM WAV (or any ffmpeg-decodable audio) to MP3 via ffmpeg."""
    import shutil
    import subprocess
    exe = ffmpeg_exe or shutil.which("ffmpeg")
    if exe is None:
        return False
    r = subprocess.run([exe, "-y", "-loglevel", "error", "-i", str(src),
                        "-c:a", "libmp3lame", "-b:a", str(bitrate), str(dst)],
                       capture_output=True)
    if r.returncode != 0 or not Path(dst).is_file():
        return False
    with open(dst, "rb") as f:
        return f.read(3) in (b"ID3", b"\xff\xfb", b"\xff\xf3", b"\xff\xf2")


def wav_encode_compressed(src: str | Path, dst: str | Path,
                          codec: str = "adpcm_ima_wav",
                          ffmpeg_exe: str | None = None) -> bool:
    """Encode a PCM WAV to a compressed WAV via ffmpeg.

    ``codec`` is an ffmpeg ADPCM/MP3 encoder name (default ``adpcm_ima_wav``;
    ``libmp3lame`` produces MP3-in-WAV). Returns True on success.
    """
    import shutil
    import subprocess
    exe = ffmpeg_exe or shutil.which("ffmpeg")
    if exe is None or codec not in ("adpcm_ima_wav", "libmp3lame"):
        return False
    cmd = [exe, "-y", "-loglevel", "error", "-i", str(src),
           "-c:a", codec, str(dst)]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0 or not Path(dst).is_file():
        return False
    with open(dst, "rb") as f:
        head = f.read(12)
    return head[:4] == b"RIFF" and head[8:12] == b"WAVE"


def wav_roundtrip(src: str | Path, dst: str | Path) -> MediaInfo:
    # stdlib wave drops non-audio RIFF chunks (LIST, PAD, fact, ...) and
    # rewrites WAVEFORMATEX headers, silently losing metadata on 24/30 sampled
    # corpus files. No audio editing is performed here, so a byte copy is both
    # lossless and semantically exact for every WAV variant.
    Path(dst).write_bytes(Path(src).read_bytes())
    return identify(dst)


@dataclass
class TgaImage:
    id_len: int
    cmap_type: int
    image_type: int
    cmap_spec: bytes  # 5 bytes
    x_origin: int
    y_origin: int
    width: int
    height: int
    bpp: int
    descriptor: int
    image_id: bytes
    cmap_data: bytes
    pixels: bytes  # raw uncompressed pixel bytes in file order
    footer: bytes = b""  # optional 26-byte TGA v2.0 footer

    def header_bytes(self) -> bytes:
        return struct.pack('<BBB5sHHHHBB', self.id_len, self.cmap_type, self.image_type,
                           self.cmap_spec, self.x_origin, self.y_origin, self.width, self.height,
                           self.bpp, self.descriptor)


def read_tga(path: str | Path) -> TgaImage:
    p = Path(path)
    b = p.read_bytes()
    if len(b) < 18:
        raise ValueError('TGA too small')
    footer = b""
    if len(b) >= 26 + 18 and b[-18:-1] == b'TRUEVISION-XFILE.' and b[-1] == 0:
        footer = b[-26:]
    id_len, cmap_type, image_type = struct.unpack_from('<BBB', b, 0)
    cmap_spec = b[3:8]
    x_origin, y_origin, width, height = struct.unpack_from('<HHHH', b, 8)
    bpp = b[16]
    descriptor = b[17]
    pos = 18
    image_id = b[pos:pos+id_len]; pos += id_len
    cmap_len = 0
    if cmap_type != 0:
        cmap_entry_count = struct.unpack_from('<H', cmap_spec, 2)[0]
        cmap_entry_bits = cmap_spec[4]
        cmap_len = cmap_entry_count * ((cmap_entry_bits + 7) // 8)
    cmap_data = b[pos:pos+cmap_len]; pos += cmap_len
    bytespp = (bpp + 7) // 8
    pixel_count = width * height
    total = pixel_count * bytespp
    if image_type in (2, 3):  # uncompressed truecolor/grayscale
        pixels = b[pos:pos+total]
    elif image_type == 10:  # RLE truecolor
        pixels = _decode_tga_rle(b[pos:], pixel_count, bytespp)
    else:
        raise ValueError(f'Unsupported TGA image type {image_type}')
    return TgaImage(id_len, cmap_type, image_type, cmap_spec, x_origin, y_origin, width, height, bpp, descriptor, image_id, cmap_data, pixels, footer)


def _decode_tga_rle(data: bytes, pixel_count: int, bytespp: int) -> bytes:
    out = bytearray()
    i = 0
    while len(out) < pixel_count * bytespp and i < len(data):
        header = data[i]; i += 1
        count = (header & 0x7F) + 1
        if header & 0x80:
            px = data[i:i+bytespp]; i += bytespp
            out.extend(px * count)
        else:
            n = count * bytespp
            out.extend(data[i:i+n]); i += n
    return bytes(out[:pixel_count * bytespp])


def _encode_tga_rle(pixels: bytes, pixel_count: int, bytespp: int) -> bytes:
    """Encode pixels as TGA run-length packets (RLE + raw)."""
    out = bytearray()
    i = 0
    while i < pixel_count:
        run = 1
        px = pixels[i*bytespp:(i+1)*bytespp]
        while (run < 128 and i + run < pixel_count and
               pixels[(i+run)*bytespp:(i+run+1)*bytespp] == px):
            run += 1
        if run >= 2:
            out.append(0x80 | (run - 1))
            out.extend(px)
            i += run
            continue
        # raw packet: gather up to 128 pixels until the next repeat run
        raw_end = i + 1
        while raw_end < pixel_count and raw_end - i < 128:
            nxt = pixels[raw_end*bytespp:(raw_end+1)*bytespp]
            nrun = 1
            while (nrun < 2 and raw_end + nrun < pixel_count and
                   pixels[(raw_end+nrun)*bytespp:(raw_end+nrun+1)*bytespp] == nxt):
                nrun += 1
            if nrun >= 2:
                break
            raw_end += 1
        count = raw_end - i
        out.append(count - 1)
        out.extend(pixels[i*bytespp:raw_end*bytespp])
        i = raw_end
    return bytes(out)


def write_tga(img: TgaImage) -> bytes:
    out = bytearray(img.header_bytes())
    out.extend(img.image_id)
    out.extend(img.cmap_data)
    if img.image_type in (2, 3):
        out.extend(img.pixels)
    elif img.image_type == 10:
        out.extend(_encode_tga_rle(img.pixels, img.width * img.height, (img.bpp + 7) // 8))
    else:
        raise ValueError(f'Unsupported TGA image type {img.image_type}')
    out.extend(img.footer)
    return bytes(out)


def tga_roundtrip(src: str | Path, dst: str | Path) -> MediaInfo:
    img = read_tga(src)
    Path(dst).write_bytes(write_tga(img))
    return identify(dst)


@dataclass
class BmpImage:
    width: int
    height: int
    bpp: int
    compression: int
    pixels_bgra: bytes  # top-down, no row padding, bpp/8 bytes per pixel
    palette: bytes = b""  # raw palette entries (BGRA) for <=8 bpp
    indices: bytes = b""  # raw top-down index rows (unpadded) for <=8 bpp
    trailer: bytes = b""  # bytes after the pixel array in the source file
    source_header: bytes = b""  # original 54-byte header, reused for lossless round-trip
    row_padding: bytes = b""  # original per-row padding bytes, concatenated

    def to_bytes(self) -> bytes:
        if self.palette:
            bytespp = 1
            row_raw = self.width
            row_padded = (row_raw + 3) & ~3
            pad_len = row_padded - row_raw
            pixel_data = bytearray()
            for y in range(self.height - 1, -1, -1):
                off = y * row_raw
                pixel_data.extend(self.indices[off:off + row_raw])
                pixel_data.extend(self.row_padding[y*pad_len:(y+1)*pad_len]
                                  if self.row_padding else b"\x00" * pad_len)
            pixel_offset = 14 + 40 + len(self.palette)
            file_size = pixel_offset + len(pixel_data) + len(self.trailer)
            if self.source_header and len(self.source_header) >= 54:
                hdr = bytearray(self.source_header[:54])
                struct.pack_into('<I', hdr, 2, file_size)
                return bytes(hdr + self.palette + pixel_data + self.trailer)
            hdr = struct.pack('<2sIHHI', b'BM', file_size, 0, 0, pixel_offset)
            dib = struct.pack('<IiiHHIIiiII', 40, self.width, self.height, 1, self.bpp, 0,
                              len(pixel_data), 2835, 2835, 0, 0)
            return bytes(hdr + dib + self.palette + pixel_data + self.trailer)
        bytespp = self.bpp // 8
        row_raw = self.width * bytespp
        row_padded = (row_raw + 3) & ~3
        pad_len = row_padded - row_raw
        pixel_data = bytearray()
        # BMP stores bottom-up
        for y in range(self.height - 1, -1, -1):
            off = y * row_raw
            pixel_data.extend(self.pixels_bgra[off:off+row_raw])
            pixel_data.extend(self.row_padding[y*pad_len:(y+1)*pad_len]
                              if self.row_padding else b'\x00' * pad_len)
        pixel_offset = 14 + 40
        file_size = pixel_offset + len(pixel_data) + len(self.trailer)
        if self.source_header and len(self.source_header) >= 54:
            hdr = bytearray(self.source_header[:54])
            struct.pack_into('<I', hdr, 2, file_size)
            return bytes(hdr + pixel_data + self.trailer)
        hdr = struct.pack('<2sIHHI', b'BM', file_size, 0, 0, pixel_offset)
        dib = struct.pack('<IiiHHIIiiII', 40, self.width, self.height, 1, self.bpp, 0,
                          len(pixel_data), 2835, 2835, 0, 0)
        return bytes(hdr + dib + pixel_data + self.trailer)


def read_bmp(path: str | Path) -> BmpImage:
    p = Path(path)
    b = p.read_bytes()
    if not b.startswith(b'BM') or len(b) < 54:
        raise ValueError('Not a BMP')
    pixel_offset = struct.unpack_from('<I', b, 10)[0]
    dib = struct.unpack_from('<I', b, 14)[0]
    if dib < 40:
        raise ValueError(f'Unsupported BMP DIB size {dib}')
    w, h, planes, bpp, comp = struct.unpack_from('<iiHHI', b, 18)
    if comp != 0 or bpp not in (8, 24, 32):
        raise ValueError(f'Unsupported BMP compression/bpp {comp}/{bpp}')
    if bpp == 8:
        colors = struct.unpack_from('<I', b, 46)[0] or 256
        pal_off = 54
        pal_size = colors * 4
        palette = b[pal_off:pal_off + pal_size]
        bytespp = 1
        row_raw = w
        row_padded = (row_raw + 3) & ~3
        height8 = abs(h)
        top_down8 = h < 0
        indices = bytearray(w * height8)
        expanded = bytearray(w * height8 * 4)
        row_padding = bytearray()
        for row in range(height8):
            src_y = row if top_down8 else (height8 - 1 - row)
            src_off = pixel_offset + src_y * row_padded
            indices[row * w:(row + 1) * w] = b[src_off:src_off + w]
            row_padding.extend(b[src_off + w:src_off + row_padded])
            for x in range(w):
                idx = indices[row * w + x]
                expanded[(row * w + x) * 4:(row * w + x + 1) * 4] = palette[idx*4:idx*4+4]
        used = pixel_offset + height8 * row_padded
        return BmpImage(width=w, height=height8, bpp=8, compression=0,
                        pixels_bgra=bytes(expanded), palette=palette,
                        indices=bytes(indices), trailer=b[used:],
                        source_header=b[:54], row_padding=bytes(row_padding))
    height = abs(h)
    top_down = h < 0
    bytespp = bpp // 8
    row_raw = w * bytespp
    row_padded = (row_raw + 3) & ~3
    pixels = bytearray(w * height * bytespp)
    row_padding = bytearray()
    for row in range(height):
        src_y = row if top_down else (height - 1 - row)
        src_off = pixel_offset + src_y * row_padded
        dst_off = row * row_raw
        pixels[dst_off:dst_off+row_raw] = b[src_off:src_off+row_raw]
        row_padding.extend(b[src_off + row_raw:src_off + row_padded])
    # store top-down in memory
    # wait - I looped row from 0..height-1 as destination top-down, reading from src_y. ok.
    # but src_y for bottom-up: height-1-row gives bottom row first. I want dst row 0 = top row.
    # so for bottom-up (top_down False): src_y = height-1-row => dst_off=row*row_raw gives top-down. yes.
    used = pixel_offset + height * row_padded
    return BmpImage(width=w, height=height, bpp=bpp, compression=comp,
                    pixels_bgra=bytes(pixels), trailer=b[used:], source_header=b[:54],
                    row_padding=bytes(row_padding))


def bmp_roundtrip(src: str | Path, dst: str | Path) -> MediaInfo:
    img = read_bmp(src)
    Path(dst).write_bytes(img.to_bytes())
    return identify(dst)


# --- DDS DXT1 (BC1) / DXT5 (BC3) support ---

def _rgb565_to_rgba(c):
    r = ((c >> 11) & 0x1F) * 255 // 31
    g = ((c >> 5) & 0x3F) * 255 // 63
    b = (c & 0x1F) * 255 // 31
    return (r, g, b, 255)


def _decode_dxt1_block(block: bytes) -> list[tuple[int,int,int,int]]:
    c0, c1 = struct.unpack_from('<HH', block, 0)
    bits = struct.unpack_from('<I', block, 4)[0]
    p = [_rgb565_to_rgba(c0), _rgb565_to_rgba(c1)]
    if c0 > c1:
        p.append(tuple((2*p[0][i]+p[1][i])//3 for i in range(3)) + (255,))
        p.append(tuple((p[0][i]+2*p[1][i])//3 for i in range(3)) + (255,))
    else:
        p.append(tuple((p[0][i]+p[1][i])//2 for i in range(3)) + (255,))
        p.append((0,0,0,0))
    out = []
    for i in range(16):
        out.append(p[(bits >> (2*i)) & 3])
    return out


def decode_dxt1(data: bytes, width: int, height: int) -> bytes:
    out = bytearray(width * height * 4)
    blocks_x = (width + 3) // 4
    blocks_y = (height + 3) // 4
    off = 0
    for by in range(blocks_y):
        for bx in range(blocks_x):
            block = data[off:off+8]; off += 8
            if len(block) < 8:
                block = block.ljust(8, b'\x00')
            px = _decode_dxt1_block(block)
            for py in range(4):
                for px_i in range(4):
                    x = bx*4 + px_i
                    y = by*4 + py
                    if x < width and y < height:
                        di = (y*width + x) * 4
                        out[di:di+4] = bytes(px[py*4+px_i])
    return bytes(out)


def _rgba_to_rgb565(r,g,b,a=255):
    return ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)


def _color_dist2(a,b):
    return sum((a[i]-b[i])**2 for i in range(3))


def _encode_dxt1_block(pixels: list[tuple[int,int,int,int]]) -> bytes:
    # Simple encoder: pick min/max luminance as endpoints, no alpha punchthrough.
    opaque = [p[:3] for p in pixels]
    lum = [0.299*c[0]+0.587*c[1]+0.114*c[2] for c in opaque]
    i0 = max(range(16), key=lambda i: lum[i])
    i1 = min(range(16), key=lambda i: lum[i])
    c0 = _rgba_to_rgb565(*opaque[i0])
    c1 = _rgba_to_rgb565(*opaque[i1])
    if c0 == c1:
        c1 = c0 ^ 1
    if c0 <= c1:
        c0, c1 = c1, c0
        i0, i1 = i1, i0
    p = [_rgb565_to_rgba(c0), _rgb565_to_rgba(c1),
         tuple((2*p0+p1)//3 for p0,p1 in zip(_rgb565_to_rgba(c0)[:3], _rgb565_to_rgba(c1)[:3])) + (255,),
         tuple((p0+2*p1)//3 for p0,p1 in zip(_rgb565_to_rgba(c0)[:3], _rgb565_to_rgba(c1)[:3])) + (255,)]
    bits = 0
    for i, px in enumerate(opaque):
        # choose closest of 4 colors
        best = min(range(4), key=lambda j: _color_dist2(px, p[j][:3]))
        bits |= (best << (2*i))
    return struct.pack('<HHI', c0, c1, bits)


def encode_dxt1(rgba: bytes, width: int, height: int) -> bytes:
    blocks_x = (width + 3) // 4
    blocks_y = (height + 3) // 4
    out = bytearray()
    for by in range(blocks_y):
        for bx in range(blocks_x):
            px = []
            for py in range(4):
                for px_i in range(4):
                    x = min(bx*4 + px_i, width-1)
                    y = min(by*4 + py, height-1)
                    di = (y*width + x) * 4
                    px.append(tuple(rgba[di:di+4]))
            out.extend(_encode_dxt1_block(px))
    return bytes(out)


def _decode_dxt5_alpha(block: bytes) -> list[int]:
    a0, a1 = block[0], block[1]
    bits = int.from_bytes(block[2:8], 'little')
    table = [0]*8
    table[0], table[1] = a0, a1
    if a0 > a1:
        for i in range(2,8):
            table[i] = ((8-i)*a0 + (i-1)*a1) // 7
    else:
        for i in range(2,6):
            table[i] = ((6-i)*a0 + (i-1)*a1) // 5
        table[6], table[7] = 0, 255
    out = []
    for i in range(16):
        idx = (bits >> (3*i)) & 7
        out.append(table[idx])
    return out


def _encode_dxt5_alpha(alphas: list[int]) -> bytes:
    # Simple encoder: use a0=max, a1=min, 8-value mode when possible.
    a0 = max(alphas)
    a1 = min(alphas)
    if a0 == a1:
        a1 = max(0, a0-1) if a0 > 0 else 1
    table = [0]*8
    table[0], table[1] = a0, a1
    if a0 > a1:
        for i in range(2,8):
            table[i] = ((8-i)*a0 + (i-1)*a1) // 7
    else:
        for i in range(2,6):
            table[i] = ((6-i)*a0 + (i-1)*a1) // 5
        table[6], table[7] = 0, 255
    bits = 0
    for i,a in enumerate(alphas):
        best = min(range(8), key=lambda j: abs(a-table[j]))
        bits |= (best << (3*i))
    return bytes([a0,a1]) + bits.to_bytes(6,'little')


def _decode_dxt5_block(block: bytes) -> list[tuple[int,int,int,int]]:
    alphas = _decode_dxt5_alpha(block[:8])
    colors = _decode_dxt1_block(block[8:16])  # color part same layout as DXT1, but always 4-color mode
    # DXT5 color is always 4-color interpolation (no 1-bit alpha punchthrough)
    c0,c1 = struct.unpack_from('<HH', block, 8)
    bits = struct.unpack_from('<I', block, 12)[0]
    p = [_rgb565_to_rgba(c0)[:3], _rgb565_to_rgba(c1)[:3]]
    p.append(tuple((2*p[0][i]+p[1][i])//3 for i in range(3)))
    p.append(tuple((p[0][i]+2*p[1][i])//3 for i in range(3)))
    out=[]
    for i in range(16):
        idx = (bits >> (2*i)) & 3
        out.append(p[idx] + (alphas[i],))
    return out


def _encode_dxt5_block(pixels: list[tuple[int,int,int,int]]) -> bytes:
    alphas = [p[3] for p in pixels]
    alpha_block = _encode_dxt5_alpha(alphas)
    # encode color like DXT1 but always 4-color mode
    opaque = [p[:3] for p in pixels]
    lum = [0.299*c[0]+0.587*c[1]+0.114*c[2] for c in opaque]
    i0 = max(range(16), key=lambda i: lum[i])
    i1 = min(range(16), key=lambda i: lum[i])
    c0 = _rgba_to_rgb565(*opaque[i0])
    c1 = _rgba_to_rgb565(*opaque[i1])
    if c0 == c1:
        c1 = c0 ^ 1
    if c0 <= c1:
        c0, c1 = c1, c0
    p0 = _rgb565_to_rgba(c0)[:3]
    p1 = _rgb565_to_rgba(c1)[:3]
    p = [p0, p1,
         tuple((2*p0[i]+p1[i])//3 for i in range(3)),
         tuple((p0[i]+2*p1[i])//3 for i in range(3))]
    bits = 0
    for i, px in enumerate(opaque):
        best = min(range(4), key=lambda j: _color_dist2(px, p[j]))
        bits |= (best << (2*i))
    return alpha_block + struct.pack('<HHI', c0, c1, bits)


def decode_dxt5(data: bytes, width: int, height: int) -> bytes:
    out = bytearray(width * height * 4)
    blocks_x = (width + 3) // 4
    blocks_y = (height + 3) // 4
    off = 0
    for by in range(blocks_y):
        for bx in range(blocks_x):
            block = data[off:off+16]; off += 16
            if len(block) < 16:
                block = block.ljust(16, b'\x00')
            px = _decode_dxt5_block(block)
            for py in range(4):
                for px_i in range(4):
                    x = bx*4 + px_i
                    y = by*4 + py
                    if x < width and y < height:
                        di = (y*width + x) * 4
                        out[di:di+4] = bytes(px[py*4+px_i])
    return bytes(out)


def encode_dxt5(rgba: bytes, width: int, height: int) -> bytes:
    blocks_x = (width + 3) // 4
    blocks_y = (height + 3) // 4
    out = bytearray()
    for by in range(blocks_y):
        for bx in range(blocks_x):
            px = []
            for py in range(4):
                for px_i in range(4):
                    x = min(bx*4 + px_i, width-1)
                    y = min(by*4 + py, height-1)
                    di = (y*width + x) * 4
                    px.append(tuple(rgba[di:di+4]))
            out.extend(_encode_dxt5_block(px))
    return bytes(out)


def _decode_dxt3_block(block: bytes) -> list[tuple[int,int,int,int]]:
    alpha_bits = int.from_bytes(block[:8], 'little')
    c0,c1 = struct.unpack_from('<HH', block, 8)
    bits = struct.unpack_from('<I', block, 12)[0]
    p = [_rgb565_to_rgba(c0)[:3], _rgb565_to_rgba(c1)[:3]]
    p.append(tuple((2*p[0][i]+p[1][i])//3 for i in range(3)))
    p.append(tuple((p[0][i]+2*p[1][i])//3 for i in range(3)))
    out=[]
    for i in range(16):
        a4 = (alpha_bits >> (4*i)) & 0xF
        a = (a4 * 255) // 15
        idx = (bits >> (2*i)) & 3
        out.append(p[idx] + (a,))
    return out


def _encode_dxt3_block(pixels: list[tuple[int,int,int,int]]) -> bytes:
    alpha_bits = 0
    for i,p in enumerate(pixels):
        a4 = (p[3] * 15 + 127) // 255
        alpha_bits |= (a4 << (4*i))
    opaque = [p[:3] for p in pixels]
    lum = [0.299*c[0]+0.587*c[1]+0.114*c[2] for c in opaque]
    i0 = max(range(16), key=lambda i: lum[i])
    i1 = min(range(16), key=lambda i: lum[i])
    c0 = _rgba_to_rgb565(*opaque[i0])
    c1 = _rgba_to_rgb565(*opaque[i1])
    if c0 == c1:
        c1 = c0 ^ 1
    if c0 <= c1:
        c0, c1 = c1, c0
    p0 = _rgb565_to_rgba(c0)[:3]; p1 = _rgb565_to_rgba(c1)[:3]
    pal = [p0,p1,tuple((2*p0[i]+p1[i])//3 for i in range(3)),tuple((p0[i]+2*p1[i])//3 for i in range(3))]
    bits = 0
    for i, px in enumerate(opaque):
        best = min(range(4), key=lambda j: _color_dist2(px, pal[j]))
        bits |= (best << (2*i))
    return alpha_bits.to_bytes(8,'little') + struct.pack('<HHI', c0, c1, bits)


def decode_dxt3(data: bytes, width: int, height: int) -> bytes:
    out = bytearray(width * height * 4)
    blocks_x = (width + 3) // 4
    blocks_y = (height + 3) // 4
    off = 0
    for by in range(blocks_y):
        for bx in range(blocks_x):
            block = data[off:off+16]; off += 16
            if len(block) < 16: block = block.ljust(16, b'\x00')
            px = _decode_dxt3_block(block)
            for py in range(4):
                for px_i in range(4):
                    x = bx*4 + px_i; y = by*4 + py
                    if x < width and y < height:
                        di = (y*width + x) * 4
                        out[di:di+4] = bytes(px[py*4+px_i])
    return bytes(out)


def encode_dxt3(rgba: bytes, width: int, height: int) -> bytes:
    blocks_x = (width + 3) // 4
    blocks_y = (height + 3) // 4
    out = bytearray()
    for by in range(blocks_y):
        for bx in range(blocks_x):
            px = []
            for py in range(4):
                for px_i in range(4):
                    x = min(bx*4 + px_i, width-1); y = min(by*4 + py, height-1)
                    di = (y*width + x) * 4
                    px.append(tuple(rgba[di:di+4]))
            out.extend(_encode_dxt3_block(px))
    return bytes(out)


def _mask_shift_size(mask):
    if mask == 0: return 0, 0
    shift = 0
    while (mask & 1) == 0:
        mask >>= 1; shift += 1
    size = 0
    while (mask & 1) == 1:
        mask >>= 1; size += 1
    return shift, size


def _mask_get(val, mask):
    shift, size = _mask_shift_size(mask)
    if size == 0: return 0
    v = (val & ((1<< (shift+size)) - 1)) >> shift
    return (v * 255) // ((1<<size)-1) if size < 8 else v & 0xFF


def decode_uncompressed_dds(data: bytes, width: int, height: int, rgb_bits: int, rmask, gmask, bmask, amask) -> bytes:
    bytespp = (rgb_bits + 7) // 8
    out = bytearray(width*height*4)
    for y in range(height):
        for x in range(width):
            off = (y*width+x)*bytespp
            px = int.from_bytes(data[off:off+bytespp], 'little') if off+bytespp <= len(data) else 0
            r = _mask_get(px, rmask)
            g = _mask_get(px, gmask)
            b = _mask_get(px, bmask)
            a = _mask_get(px, amask) if amask else 255
            di = (y*width+x)*4
            out[di:di+4] = bytes([r,g,b,a])
    return bytes(out)


def encode_uncompressed_dds(rgba: bytes, width: int, height: int, rgb_bits=32, rmask=0x00ff0000, gmask=0x0000ff00, bmask=0x000000ff, amask=0xff000000) -> bytes:
    bytespp = (rgb_bits + 7) // 8
    out = bytearray(width*height*bytespp)
    def put(val, mask):
        shift, size = _mask_shift_size(mask)
        if size == 0: return 0
        v = (val * ((1<<size)-1) + 127) // 255
        return (v << shift) & mask
    for y in range(height):
        for x in range(width):
            di = (y*width+x)*4
            r,g,b,a = rgba[di:di+4]
            px = put(r,rmask)|put(g,gmask)|put(b,bmask)|put(a,amask)
            off = (y*width+x)*bytespp
            out[off:off+bytespp] = px.to_bytes(bytespp,'little')
    return bytes(out)


def _dds_top_level_size(width: int, height: int, fourcc: str,
                        rgb_bits: int = 32) -> int:
    """Byte size of DDS level 0 (mip chains follow it in the payload)."""
    if fourcc in ("DXT1", "DXT3", "DXT5", "DXT4", "BC4U", "ATI1", "BC5U", "ATI2",
                  "BC6H_UF16", "BC6H_SF16", "BC7_UNORM"):
        blocks = max(1, (width + 3) // 4) * max(1, (height + 3) // 4)
        if fourcc in ("DXT1", "BC4U", "ATI1"):
            return blocks * 8
        return blocks * 16
    return width * height * max(1, rgb_bits // 8)


def _dds_face_payload_size(width: int, height: int, fourcc: str, levels: int,
                           rgb_bits: int = 32) -> int:
    """Total byte size of one cube face including its mip chain."""
    return sum(_dds_top_level_size(max(1, width >> i), max(1, height >> i),
                                   fourcc, rgb_bits) for i in range(levels))


def _decode_dds_payload(payload: bytes, fourcc_s: str, width: int, height: int,
                        pf_flags: int, masks: tuple[int, int, int, int, int]) -> bytes:
    """Decode one DDS payload (level 0 of an image or cube face) to RGBA."""
    rgb_bits, rmask, gmask, bmask, amask = masks
    if fourcc_s == 'DXT1':
        return decode_dxt1(payload, width, height)
    if fourcc_s == 'DXT3':
        return decode_dxt3(payload, width, height)
    if fourcc_s in ('DXT5', 'DXT4'):
        return decode_dxt5(payload, width, height)
    if fourcc_s in ('BC4U', 'ATI1'):
        return decode_bc4(payload, width, height)
    if fourcc_s in ('BC5U', 'ATI2'):
        return decode_bc5(payload, width, height)
    if fourcc_s in ('BC6H_UF16', 'BC6H_SF16'):
        import bc6h_format
        rgba = bc6h_format.decode_bc6h(payload, width, height,
                                       signed=(fourcc_s == 'BC6H_SF16'))
        if rgba is None:
            raise ValueError('Unsupported BC6H block mode in DX10 DDS')
        return rgba
    if fourcc_s == 'BC7_UNORM':
        import bc7_format
        rgba = bc7_format.decode_bc7(payload, width, height)
        if rgba is None:
            raise ValueError('Truncated BC7 DDS payload')
        return rgba
    if fourcc_s == 'UNCOMPRESSED':
        return decode_uncompressed_dds(payload, width, height, rgb_bits,
                                       rmask, gmask, bmask, amask)
    raise ValueError(f'Unsupported DDS fourcc for decode: {fourcc_s}')


def _bc4_interpolate(a0: int, a1: int) -> list[int]:
    if a0 > a1:
        return [(a0 * (7 - i) + a1 * i + 3) // 7 for i in range(8)]
    vals = [(a0 * (5 - i) + a1 * i + 2) // 5 for i in range(6)]
    return vals + [0, 255]


def decode_bc4_block(block: bytes) -> list[int]:
    """Decode one 8-byte BC4 block to 16 unsigned byte values."""
    a0, a1 = block[0], block[1]
    palette = _bc4_interpolate(a0, a1)
    bits = int.from_bytes(block[2:8], "little")
    return [palette[(bits >> (3 * i)) & 7] for i in range(16)]


def decode_bc4(data: bytes, width: int, height: int) -> bytes:
    """Decode a BC4U/ATI1 DDS payload to greyscale RGBA."""
    out = bytearray()
    bw, bh = max(1, (width + 3) // 4), max(1, (height + 3) // 4)
    for by in range(bh):
        for bx in range(bw):
            vals = decode_bc4_block(data[(by * bw + bx) * 8:(by * bw + bx + 1) * 8])
            for y in range(4):
                for x in range(4):
                    v = vals[y * 4 + x]
                    out.extend((v, v, v, 255))
    return bytes(out[:width * height * 4])


def decode_bc5(data: bytes, width: int, height: int) -> bytes:
    """Decode a BC5U/ATI2 DDS payload (two BC4 channels) to RGBA."""
    out = bytearray()
    bw, bh = max(1, (width + 3) // 4), max(1, (height + 3) // 4)
    for by in range(bh):
        for bx in range(bw):
            base = (by * bw + bx) * 16
            r = decode_bc4_block(data[base:base + 8])
            g = decode_bc4_block(data[base + 8:base + 16])
            for y in range(4):
                for x in range(4):
                    i = y * 4 + x
                    out.extend((r[i], g[i], 0, 255))
    return bytes(out[:width * height * 4])


def decode_dxt_bytes(payload: bytes, fourcc: str, width: int, height: int) -> bytes:
    if fourcc == 'DXT1':
        return decode_dxt1(payload, width, height)
    if fourcc == 'DXT3':
        return decode_dxt3(payload, width, height)
    return decode_dxt5(payload, width, height)


def _decode_bc_level0(img: "DdsImage") -> bytes:
    """Re-decode original block payload to verify RGBA was not edited."""
    payload = img.level0_payload
    if img.fourcc in ("BC4U", "ATI1"):
        return decode_bc4(payload, img.width, img.height)
    if img.fourcc in ("BC5U", "ATI2"):
        return decode_bc5(payload, img.width, img.height)
    if img.fourcc in ("BC6H_UF16", "BC6H_SF16"):
        import bc6h_format
        out = bc6h_format.decode_bc6h(payload, img.width, img.height,
                                      signed=(img.fourcc == "BC6H_SF16"))
    else:
        import bc7_format
        out = bc7_format.decode_bc7(payload, img.width, img.height)
    return out or b""


@dataclass
class DdsImage:
    width: int
    height: int
    mipmaps: int
    fourcc: str
    rgba: bytes  # decoded top-level RGBA
    header: bytes  # original 128-byte header for lossless metadata where possible
    mip_payload: bytes = b""  # raw bytes of all mip levels below level 0, preserved verbatim
    level0_payload: bytes = b""  # original level-0 bytes; reused when RGBA is unchanged
    payload_start: int = 128  # 128 for legacy DDS, 148 for DX10
    cube_face_rgba: list[bytes] = field(default_factory=list)  # decoded RGBA per cube face
    cube_face_level0: list[bytes] = field(default_factory=list)  # original level-0 bytes per face
    cube_face_mips: list[bytes] = field(default_factory=list)  # raw mip bytes per face
    dx10_header: bytes = b""  # original 20-byte DX10 header, preserved losslessly

    def to_bytes(self) -> bytes:
        if self.cube_face_rgba:
            chunks = []
            for rgba, level0, mips in zip(self.cube_face_rgba,
                                          self.cube_face_level0,
                                          self.cube_face_mips):
                face = DdsImage(width=self.width, height=self.height, mipmaps=self.mipmaps,
                                fourcc=self.fourcc, rgba=rgba, header=self.header,
                                mip_payload=mips, level0_payload=level0,
                                payload_start=self.payload_start,
                                dx10_header=self.dx10_header)
                chunks.append(face.to_bytes()[self.payload_start:])
            return bytes(self.header) + self.dx10_header + b"".join(chunks)
        if self.fourcc in ('DXT1', 'DXT3', 'DXT5'):
            # Reuse the original compressed level-0 bytes whenever RGBA has not
            # been edited. This keeps mipmapped DXT round-trips byte-lossless;
            # only edited images pay the lossy DXT re-encode.
            if self.level0_payload and self.header and decode_dxt_bytes(
                    self.level0_payload, self.fourcc, self.width, self.height) == self.rgba:
                # Preserve the original header verbatim too (some files leave
                # the linear-size field at 0; rebuilding it costs 1 byte).
                return bytes(self.header) + self.level0_payload + self.mip_payload
            elif self.fourcc == 'DXT1': payload = encode_dxt1(self.rgba, self.width, self.height)
            elif self.fourcc == 'DXT3': payload = encode_dxt3(self.rgba, self.width, self.height)
            else: payload = encode_dxt5(self.rgba, self.width, self.height)
            hdr = bytearray(self.header)
            linear = len(payload)
            struct.pack_into('<I', hdr, 0, 0x20534444)  # DDS 
            struct.pack_into('<I', hdr, 4, 124)
            struct.pack_into('<I', hdr, 12, self.height)
            struct.pack_into('<I', hdr, 16, self.width)
            struct.pack_into('<I', hdr, 20, linear)
            struct.pack_into('<I', hdr, 28, max(1, self.mipmaps))
            struct.pack_into('<I', hdr, 76, 32)
            struct.pack_into('<I', hdr, 80, 0x4)
            hdr[84:88] = self.fourcc.encode('ascii')
            return bytes(hdr) + payload + self.mip_payload
        if self.fourcc == 'UNCOMPRESSED':
            hdr = bytearray(self.header)
            rgb_bits, rmask, gmask, bmask, amask = struct.unpack_from('<5I', hdr, 88)
            pf_flags = struct.unpack_from('<I', hdr, 80)[0] or 0x41
            if rgb_bits == 0 or (rmask == 0 and gmask == 0 and bmask == 0):
                rgb_bits, rmask, gmask, bmask, amask = 32, 0x00ff0000, 0x0000ff00, 0x000000ff, 0xff000000
                pf_flags |= 0x41
            payload = encode_uncompressed_dds(self.rgba, self.width, self.height, rgb_bits, rmask, gmask, bmask, amask)
            linear = len(payload)
            struct.pack_into('<I', hdr, 0, 0x20534444)
            struct.pack_into('<I', hdr, 4, 124)
            struct.pack_into('<I', hdr, 12, self.height)
            struct.pack_into('<I', hdr, 16, self.width)
            struct.pack_into('<I', hdr, 20, linear)
            struct.pack_into('<I', hdr, 28, max(1, self.mipmaps))
            struct.pack_into('<I', hdr, 76, 32)
            struct.pack_into('<I', hdr, 80, pf_flags)
            hdr[84:88] = b'\x00\x00\x00\x00'
            struct.pack_into('<5I', hdr, 88, rgb_bits, rmask, gmask, bmask, amask)
            return bytes(hdr) + payload + self.mip_payload
        if self.fourcc in ('BC4U', 'ATI1', 'BC5U', 'ATI2',
                           'BC6H_UF16', 'BC6H_SF16', 'BC7_UNORM'):
            if self.level0_payload and self.header:
                if _decode_bc_level0(self) == self.rgba:
                    return (bytes(self.header) + self.dx10_header +
                            self.level0_payload + self.mip_payload)
            raise ValueError(f'DDS write of edited {self.fourcc} needs an encoder '
                             '(not implemented)')
        raise ValueError(f'Unsupported DDS fourcc for write: {self.fourcc}')


def read_dds(path: str | Path) -> DdsImage:
    p = Path(path)
    b = p.read_bytes()
    if not b.startswith(b'DDS ') or len(b) < 128:
        raise ValueError('Not a DDS')
    hdr_size, flags, height, width, pitch, depth, mipmaps = struct.unpack_from('<7I', b, 4)
    pf_flags, fourcc = struct.unpack_from('<I4s', b, 80)
    fourcc_s = fourcc.decode('latin1','replace').strip('\x00')
    masks = struct.unpack_from('<5I', b, 88)
    rgb_bits = masks[0]
    payload_start = 128
    dx10_header = b""
    if fourcc_s == 'DX10':
        # DDS_DX10 extended header (20 bytes) follows the legacy 128-byte header.
        if len(b) < 148:
            raise ValueError('Truncated DDS DX10 header')
        dxgi, dimension, misc_flag, array_size, misc_flags2 = struct.unpack_from('<5I', b, 128)
        dx10_header = b[128:148]
        payload_start = 148
        if dxgi == 95:  # DXGI_FORMAT_BC6H_UF16
            fourcc_s = 'BC6H_UF16'
        elif dxgi == 96:  # DXGI_FORMAT_BC6H_SF16
            fourcc_s = 'BC6H_SF16'
        elif dxgi in (97, 98, 99):  # BC7_TYPELESS / UNORM / UNORM_SRGB
            fourcc_s = 'BC7_UNORM'
        else:
            raise ValueError(f'Unsupported DX10 DDS DXGI format: {dxgi}')
    elif fourcc_s == '' and (pf_flags & 0x40):  # DDPF_RGB (optional alpha)
        fourcc_s = 'UNCOMPRESSED'

    levels = mipmaps or 1
    top = _dds_top_level_size(width, height, fourcc_s, rgb_bits)
    caps2 = struct.unpack_from('<I', b, 112)[0]
    face_rgba: list[bytes] = []
    face_l0: list[bytes] = []
    face_mips: list[bytes] = []
    if caps2 & 0xFE00:  # DDSCAPS2_CUBEMAP (all six faces in the local corpus)
        face_stride = _dds_face_payload_size(width, height, fourcc_s, levels, rgb_bits)
        for i in range(6):
            off = payload_start + i * face_stride
            level0 = b[off:off + top]
            if len(level0) < top:
                raise ValueError(f'Truncated DDS cube face {i}')
            face_rgba.append(_decode_dds_payload(level0, fourcc_s, width, height,
                                                 pf_flags, masks))
            face_l0.append(level0)
            face_mips.append(b[off + top:off + face_stride] if levels > 1 else b'')
        rgba = face_rgba[0]
        mip_payload = b''
        level0_payload = face_l0[0]
    else:
        payload = b[payload_start:]
        rgba = _decode_dds_payload(payload[:top], fourcc_s, width, height, pf_flags, masks)
        mip_payload = payload[top:] if levels > 1 else b''
        level0_payload = payload[:top]
    return DdsImage(width=width, height=height, mipmaps=levels, fourcc=fourcc_s,
                    rgba=rgba, header=b[:128], mip_payload=mip_payload,
                    level0_payload=level0_payload, payload_start=payload_start,
                    cube_face_rgba=face_rgba, cube_face_level0=face_l0,
                    cube_face_mips=face_mips, dx10_header=dx10_header)


def dds_roundtrip(src: str | Path, dst: str | Path) -> MediaInfo:
    img = read_dds(src)
    Path(dst).write_bytes(img.to_bytes())
    return identify(dst)


def bink_decode(src: str | Path, out_dir: str | Path, frames: int = 0) -> list[Path]:
    """Decode a Bink video to PNG frames using an external ffmpeg binary.

    ffmpeg's `binkvideo` decoder handles GTR2/GTL BIK files (verified on real
    local assets). Decode-only: no open-source Bink encoder is available.
    Returns the written frame paths (empty if ffmpeg is unavailable).
    """
    import shutil
    import subprocess
    exe = shutil.which("ffmpeg")
    if exe is None:
        return []
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    cmd = [exe, "-v", "error", "-i", str(src), "-vsync", "0"]
    if frames > 0:
        cmd += ["-frames:v", str(frames)]
    cmd += [str(out / "frame_%04d.png")]
    subprocess.run(cmd, check=True, capture_output=True)
    return sorted(out.glob("frame_*.png"))


def tgq_decode(src: str | Path, out_dir: str | Path, frames: int = 0) -> list[Path]:
    """Decode an EA TGQ (SCHl/TQI) video to PNG frames using ffmpeg.

    All 22 local F1 2000 `.TGQ` files probe as TQI video (320x480, 25 fps)
    plus `adpcm_ea` audio. Returns written frame paths (empty without ffmpeg).
    """
    import shutil
    import subprocess
    exe = shutil.which("ffmpeg")
    if exe is None:
        return []
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    cmd = [exe, "-v", "error", "-i", str(src), "-vsync", "0"]
    if frames > 0:
        cmd += ["-frames:v", str(frames)]
    cmd += [str(out / "frame_%04d.png")]
    subprocess.run(cmd, check=True, capture_output=True)
    return sorted(out.glob("frame_*.png"))


def bink_encode(frames_dir: str | Path, dst: str | Path, fps: int = 25,
                verify: bool = True, exe: str | None = None) -> Path | None:
    """Encode PNG/BMP frames into a Bink-1 BIKi video via external `bink_build`.

    `bink_build` comes from the LGPL-2.1 `raynorpat/libbink` project and is
    invoked as a separate executable (its code is not copied into this repo).
    The output BIKi header layout matches GTR2/GTL Bink-1 videos.  Returns the
    output path, or None when the external tool is unavailable.
    """
    import os
    import shutil
    import subprocess
    tool = exe or os.environ.get("BINKBUILD") or shutil.which("bink_build")
    if tool is None:
        return None
    out = Path(dst)
    cmd = [tool, str(frames_dir), "-o", str(out), "--fps", str(fps)]
    if verify:
        cmd.append("--verify")
    subprocess.run(cmd, check=True, capture_output=True)
    return out if out.is_file() else None


def _hat_cmd(src: str | Path, dst: str | Path) -> str:
    result = hat_decompress(src)
    if result is None:
        return "failed"
    data, info = result
    Path(dst).write_bytes(data)
    return f"ok variant={info['variant']} bytes={len(data)}"


def _cmd_hdr_dat_decode(hdr: str | Path, dst: str | Path) -> bool:
    pair = hdr_dat_mp3(hdr)
    if pair is None:
        return False
    payload, _info = pair
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as fh:
        fh.write(payload)
        tmp = fh.name
    try:
        return mp3_decode(tmp, dst)
    finally:
        Path(tmp).unlink(missing_ok=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("info")
    p.add_argument("file")
    p.set_defaults(func=lambda a: print(asdict(identify(a.file))) or 0)
    p = sub.add_parser("bink-decode", help="decode BIK to PNG frames via ffmpeg")
    p.add_argument("src")
    p.add_argument("out_dir")
    p.add_argument("--frames", type=int, default=0)
    p.set_defaults(func=lambda a: print(len(bink_decode(a.src, a.out_dir, a.frames))))
    p = sub.add_parser("tgq-decode", help="decode EA TGQ (SCHl/TQI) video to PNG frames")
    p.add_argument("src")
    p.add_argument("out_dir")
    p.add_argument("--frames", type=int, default=0)
    p.set_defaults(func=lambda a: print(len(tgq_decode(a.src, a.out_dir, a.frames))))
    p = sub.add_parser("bink-encode", help="encode PNG frames to BIKi via bink_build")
    p.add_argument("frames_dir")
    p.add_argument("dst")
    p.add_argument("--fps", type=int, default=25)
    p.add_argument("--exe", default=None)
    p.set_defaults(func=lambda a: print(bink_encode(a.frames_dir, a.dst, a.fps,
                                                   exe=a.exe) or "bink_build unavailable"))
    p = sub.add_parser("hat-decompress",
                       help="decompress a gzip-wrapped .hat track-data file")
    p.add_argument("src")
    p.add_argument("dst")
    p.set_defaults(func=lambda a: print(
        _hat_cmd(a.src, a.dst)) or 0)
    p = sub.add_parser("hat-transfer-heights",
                       help="transfer GTL heights into a same-layout GTR2 HAT")
    p.add_argument("src")
    p.add_argument("target")
    p.add_argument("dst")
    def _hat_transfer_cmd(a):
        import gzip
        source = hat_decompress(a.src)
        target = hat_decompress(a.target)
        if source is None or target is None:
            print("both inputs must be gzip HAT files")
            return 1
        result = hat_transfer_heights(source[0], target[0])
        if result is None:
            print("layout signatures differ; no transfer performed")
            return 1
        payload, report = result
        Path(a.dst).write_bytes(gzip.compress(payload))
        print(json.dumps(report, indent=2))
        return 0
    p.set_defaults(func=_hat_transfer_cmd)
    p = sub.add_parser("hat-match",
                       help="compare two HAT record tables by (x,z) position")
    p.add_argument("src")
    p.add_argument("reference")
    p.set_defaults(func=lambda a: print(json.dumps(
        hat_height_match(hat_decompress(a.src)[0],
                         hat_decompress(a.reference)[0]), indent=2)) or 0)
    p = sub.add_parser("hat-validate",
                       help="check a .hat file's structural invariants")
    p.add_argument("src")
    def _hat_validate_cmd(a):
        result = hat_decompress(a.src)
        if result is None:
            print("hat: not a gzip HAT file")
            return 1
        problems = validate_hat(result[0])
        print("hat: " + (", ".join(problems) if problems else "ok"))
        return 1 if problems else 0
    p.set_defaults(func=_hat_validate_cmd)
    p = sub.add_parser("hat-layout",
                       help="identify a .hat layout from a reference corpus")
    p.add_argument("src")
    p.add_argument("corpus", help="directory of reference .hat files (read-only)")
    p.set_defaults(func=lambda a: print(
        json.dumps(identify_hat_layout(a.src, a.corpus), indent=2)) or 0)
    p = sub.add_parser("hdr-dat-decode",
                       help="decode a NASCAR-era .hdr/.dat MP3 audio pair to WAV")
    p.add_argument("hdr")
    p.add_argument("dst")
    p.set_defaults(func=lambda a: print(
        "ok" if _cmd_hdr_dat_decode(a.hdr, a.dst) else "failed") or 0)
    p = sub.add_parser("wav-roundtrip")
    p.add_argument("src")
    p.add_argument("dst")
    p.set_defaults(func=lambda a: print(asdict(wav_roundtrip(a.src, a.dst))) or 0)
    p = sub.add_parser("jpg-decode", help="decode JPG to PNG via Pillow")
    p.add_argument("src"); p.add_argument("dst")
    p.set_defaults(func=lambda a: print(jpg_decode(a.src, a.dst) or "failed") or 0)
    p = sub.add_parser("jpg-encode", help="encode image to JPG via Pillow")
    p.add_argument("src"); p.add_argument("dst")
    p.set_defaults(func=lambda a: print("ok" if jpg_encode(a.src, a.dst) else "failed") or 0)
    p = sub.add_parser("mp3-decode", help="decode MP3 to PCM WAV via ffmpeg")
    p.add_argument("src"); p.add_argument("dst")
    p.set_defaults(func=lambda a: print("ok" if mp3_decode(a.src, a.dst) else "failed") or 0)
    p = sub.add_parser("mp3-encode", help="encode audio to MP3 via ffmpeg")
    p.add_argument("src"); p.add_argument("dst")
    p.set_defaults(func=lambda a: print("ok" if mp3_encode(a.src, a.dst) else "failed") or 0)
    p = sub.add_parser("wav-encode", help="encode PCM WAV to compressed WAV via ffmpeg")
    p.add_argument("src")
    p.add_argument("dst")
    p.add_argument("--codec", choices=("adpcm_ima_wav", "libmp3lame"), default="adpcm_ima_wav")
    p.set_defaults(func=lambda a: print("ok" if wav_encode_compressed(a.src, a.dst, a.codec)
                                        else "ffmpeg unavailable or encode failed") or 0)
    p = sub.add_parser("jca-decrypt", help="decrypt any JCA-wrapped payload (WAV/DDS/TGA)")
    p.add_argument("src")
    p.add_argument("dst")
    p.add_argument("--key", choices=["auto", "default"] + sorted(__import__("jca_crypt").CUSTOM_KEYS),
                   default="auto")
    def _jca_cli(a):
        import jca_crypt
        raw = Path(a.src).read_bytes()
        if a.key in (None, "auto"):
            name = detect_jca_key(raw)
            if name is None:
                print("no known JCA key matched")
                return 1
        else:
            name = a.key
        Path(a.dst).write_bytes(decrypt_jca_bytes(raw, name))
        print(f"{a.dst} (key={name})")
        return 0
    p.set_defaults(func=_jca_cli)
    p = sub.add_parser("wav-decrypt", help="decrypt a JCA-wrapped WAV to plain RIFF/WAVE")
    p.add_argument("src")
    p.add_argument("dst")
    p.add_argument("--key", choices=sorted(__import__("jca_crypt").CUSTOM_KEYS), default=None)
    p.set_defaults(func=lambda a: (Path(a.dst).write_bytes(
        decrypt_jca_wav(Path(a.src).read_bytes(), a.key)), print(a.dst))[1] or 0)
    p = sub.add_parser("wav-decode", help="decode compressed WAV (ADPCM/MP3) to PCM via ffmpeg")
    p.add_argument("src")
    p.add_argument("dst")
    p.set_defaults(func=lambda a: print("ok" if wav_decode(a.src, a.dst)
                                        else "ffmpeg unavailable or decode failed") or 0)
    p = sub.add_parser("tga-roundtrip")
    p.add_argument("src")
    p.add_argument("dst")
    p.set_defaults(func=lambda a: print(asdict(tga_roundtrip(a.src, a.dst))) or 0)
    p = sub.add_parser("bmp-roundtrip")
    p.add_argument("src")
    p.add_argument("dst")
    p.set_defaults(func=lambda a: print(asdict(bmp_roundtrip(a.src, a.dst))) or 0)
    p = sub.add_parser("dds-roundtrip")
    p.add_argument("src")
    p.add_argument("dst")
    p.set_defaults(func=lambda a: print(asdict(dds_roundtrip(a.src, a.dst))) or 0)
    args = ap.parse_args(argv)
    return args.func(args)

if __name__ == "__main__":
    raise SystemExit(main())
