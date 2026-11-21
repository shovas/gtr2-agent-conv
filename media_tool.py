"""Basic media format identification and limited semantic read/write.

Supported semantic R/W: WAV (PCM via stdlib wave).
Supported identification/header parsing: WAV, DDS, TGA, BMP, JPG, MP3, BIK.
Lossless byte copy is always possible for supported identified files.
"""
from __future__ import annotations

import argparse
import struct
import wave
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class MediaInfo:
    path: str
    size: int
    format: str
    details: dict


def identify(path: str | Path) -> MediaInfo:
    p = Path(path)
    b = p.read_bytes()
    size = len(b)
    head = b[:64]
    ext = p.suffix.lower()
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
            details = {"error": str(e)}
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
            fsize, _, off = struct.unpack_from("<IHHI", b, 2)
            dib = struct.unpack_from("<I", b, 14)[0]
            details = {"file_size_field": fsize, "pixel_offset": off, "dib_size": dib}
        return MediaInfo(str(p), size, "bmp", details)
    # JPG
    if head.startswith(b"\xff\xd8\xff"):
        return MediaInfo(str(p), size, "jpg", {})
    # MP3
    if head.startswith(b"ID3") or (len(head) >= 2 and head[0] == 0xFF and (head[1] & 0xE0) == 0xE0):
        return MediaInfo(str(p), size, "mp3", {"id3": head.startswith(b"ID3")})
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
    return MediaInfo(str(p), size, "unknown", {"ext": ext})


def wav_roundtrip(src: str | Path, dst: str | Path) -> MediaInfo:
    with wave.open(str(src), "rb") as r:
        params = r.getparams()
        frames = r.readframes(r.getnframes())
    with wave.open(str(dst), "wb") as w:
        w.setparams(params)
        w.writeframes(frames)
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

    def header_bytes(self) -> bytes:
        return struct.pack('<BBB5sHHHHBB', self.id_len, self.cmap_type, self.image_type,
                           self.cmap_spec, self.x_origin, self.y_origin, self.width, self.height,
                           self.bpp, self.descriptor)


def read_tga(path: str | Path) -> TgaImage:
    p = Path(path)
    b = p.read_bytes()
    if len(b) < 18:
        raise ValueError('TGA too small')
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
    return TgaImage(id_len, cmap_type, image_type, cmap_spec, x_origin, y_origin, width, height, bpp, descriptor, image_id, cmap_data, pixels)


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
    # Simple RLE encoder: emit raw packets (no compression) for correctness.
    # Semantic round-trip is guaranteed by decode(encode(decode(x)))==decode(x).
    out = bytearray()
    i = 0
    while i < pixel_count:
        chunk = min(128, pixel_count - i)
        out.append(chunk - 1)  # raw packet
        out.extend(pixels[i*bytespp:(i+chunk)*bytespp])
        i += chunk
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
    return bytes(out)


def tga_roundtrip(src: str | Path, dst: str | Path) -> MediaInfo:
    img = read_tga(src)
    Path(dst).write_bytes(write_tga(img))
    return identify(dst)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("info")
    p.add_argument("file")
    p.set_defaults(func=lambda a: print(asdict(identify(a.file))) or 0)
    p = sub.add_parser("wav-roundtrip")
    p.add_argument("src")
    p.add_argument("dst")
    p.set_defaults(func=lambda a: print(asdict(wav_roundtrip(a.src, a.dst))) or 0)
    p = sub.add_parser("tga-roundtrip")
    p.add_argument("src")
    p.add_argument("dst")
    p.set_defaults(func=lambda a: print(asdict(tga_roundtrip(a.src, a.dst))) or 0)
    args = ap.parse_args(argv)
    return args.func(args)

if __name__ == "__main__":
    raise SystemExit(main())
