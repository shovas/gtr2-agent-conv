"""Basic media format identification and limited semantic read/write.

Supported semantic R/W: WAV (PCM via stdlib wave; lossless copy for unsupported formats like MP3-in-WAV).
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


JCA_MAGIC = b"\x0f\xb1\xff\xff"


def _looks_like_media(data: bytes) -> bool:
    return (data[:4] in (b"DDS ", b"RIFF") or
            (len(data) >= 18 and data[1] == 0 and data[2] in (2, 3, 10)))


def detect_jca_key(data: bytes) -> str | None:
    """Try each known JCA key and return the name that yields a valid payload.

    Corpus-verified: Race07/GTL/Volvo default vs Volvo's custom key. Returns
    ``None`` if no key produces a recognisable DDS/WAV/TGA payload.
    """
    import jca_crypt
    for name in [None] + sorted(jca_crypt.CUSTOM_KEYS):
        try:
            out = jca_crypt.decrypt_bytes(data, jca_crypt.CUSTOM_KEYS.get(name))
            if _looks_like_media(out):
                return name or "default"
        except Exception:
            continue
    return None


def decrypt_jca_bytes(data: bytes, key_name: str | None = None) -> bytes:
    """Decrypt a JCA-wrapped payload (WAV, DDS, TGA) with the given JCA key."""
    import jca_crypt
    if data[:4] != JCA_MAGIC:
        raise ValueError("not a JCA-encrypted file")
    custom = jca_crypt.CUSTOM_KEYS.get(key_name) if key_name else None
    return jca_crypt.decrypt_bytes(data, custom)


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
    return MediaInfo(str(p), size, "unknown", {"ext": ext})


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
    try:
        with wave.open(str(src), "rb") as r:
            params = r.getparams()
            frames = r.readframes(r.getnframes())
        with wave.open(str(dst), "wb") as w:
            w.setparams(params)
            w.writeframes(frames)
    except Exception:
        # Unsupported by stdlib wave (e.g. MP3-in-WAV format 0x55): lossless byte copy.
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

    def to_bytes(self) -> bytes:
        if self.palette:
            bytespp = 1
            row_raw = self.width
            row_padded = (row_raw + 3) & ~3
            pad = b"\x00" * (row_padded - row_raw)
            pixel_data = bytearray()
            for y in range(self.height - 1, -1, -1):
                off = y * row_raw
                pixel_data.extend(self.indices[off:off + row_raw])
                pixel_data.extend(pad)
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
        pad = b'\x00' * (row_padded - row_raw)
        pixel_data = bytearray()
        # BMP stores bottom-up
        for y in range(self.height - 1, -1, -1):
            off = y * row_raw
            pixel_data.extend(self.pixels_bgra[off:off+row_raw])
            pixel_data.extend(pad)
        pixel_offset = 14 + 40
        file_size = pixel_offset + len(pixel_data)
        hdr = struct.pack('<2sIHHI', b'BM', file_size, 0, 0, pixel_offset)
        dib = struct.pack('<IiiHHIIiiII', 40, self.width, self.height, 1, self.bpp, 0,
                          len(pixel_data), 2835, 2835, 0, 0)
        return bytes(hdr + dib + pixel_data)


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
        for row in range(height8):
            src_y = row if top_down8 else (height8 - 1 - row)
            src_off = pixel_offset + src_y * row_padded
            indices[row * w:(row + 1) * w] = b[src_off:src_off + w]
            for x in range(w):
                idx = indices[row * w + x]
                expanded[(row * w + x) * 4:(row * w + x + 1) * 4] = palette[idx*4:idx*4+4]
        used = pixel_offset + height8 * row_padded
        return BmpImage(width=w, height=height8, bpp=8, compression=0,
                        pixels_bgra=bytes(expanded), palette=palette,
                        indices=bytes(indices), trailer=b[used:],
                        source_header=b[:54])
    height = abs(h)
    top_down = h < 0
    bytespp = bpp // 8
    row_raw = w * bytespp
    row_padded = (row_raw + 3) & ~3
    pixels = bytearray(w * height * bytespp)
    for row in range(height):
        src_y = row if top_down else (height - 1 - row)
        src_off = pixel_offset + src_y * row_padded
        dst_off = row * row_raw
        pixels[dst_off:dst_off+row_raw] = b[src_off:src_off+row_raw]
    # store top-down in memory
    # wait - I looped row from 0..height-1 as destination top-down, reading from src_y. ok.
    # but src_y for bottom-up: height-1-row gives bottom row first. I want dst row 0 = top row.
    # so for bottom-up (top_down False): src_y = height-1-row => dst_off=row*row_raw gives top-down. yes.
    return BmpImage(width=w, height=height, bpp=bpp, compression=comp, pixels_bgra=bytes(pixels))


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
    if fourcc in ("DXT1", "DXT3", "DXT5", "BC4U", "ATI1", "BC5U", "ATI2"):
        blocks = max(1, (width + 3) // 4) * max(1, (height + 3) // 4)
        if fourcc in ("DXT1", "BC4U", "ATI1"):
            return blocks * 8
        return blocks * 16
    return width * height * max(1, rgb_bits // 8)


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

    def to_bytes(self) -> bytes:
        if self.fourcc in ('DXT1', 'DXT3', 'DXT5'):
            # Reuse the original compressed level-0 bytes whenever RGBA has not
            # been edited. This keeps mipmapped DXT round-trips byte-lossless;
            # only edited images pay the lossy DXT re-encode.
            if self.level0_payload and self.header and decode_dxt_bytes(
                    self.level0_payload, self.fourcc, self.width, self.height) == self.rgba:
                payload = self.level0_payload
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
        raise ValueError(f'Unsupported DDS fourcc for write: {self.fourcc}')


def read_dds(path: str | Path) -> DdsImage:
    p = Path(path)
    b = p.read_bytes()
    if not b.startswith(b'DDS ') or len(b) < 128:
        raise ValueError('Not a DDS')
    hdr_size, flags, height, width, pitch, depth, mipmaps = struct.unpack_from('<7I', b, 4)
    pf_flags, fourcc = struct.unpack_from('<I4s', b, 80)
    fourcc_s = fourcc.decode('latin1','replace').strip('\x00')
    rgb_bits = struct.unpack_from('<I', b, 88)[0]
    if fourcc_s == 'DXT1':
        rgba = decode_dxt1(b[128:], width, height)
    elif fourcc_s == 'DXT3':
        rgba = decode_dxt3(b[128:], width, height)
    elif fourcc_s in ('DXT5', 'DXT4'):
        # DXT4 uses the same 8-index alpha interpolation as DXT5 in practice;
        # verified against ffmpeg on the local DXT4 corpus sample.
        rgba = decode_dxt5(b[128:], width, height)
        if fourcc_s == 'DXT4':
            fourcc_s = 'DXT4'
    elif fourcc_s in ('BC4U', 'ATI1'):
        rgba = decode_bc4(b[128:], width, height)
    elif fourcc_s in ('BC5U', 'ATI2'):
        rgba = decode_bc5(b[128:], width, height)
    elif fourcc_s == '' and (pf_flags & 0x40):  # DDPF_RGB (optional alpha)
        rgb_bits, rmask, gmask, bmask, amask = struct.unpack_from('<5I', b, 88)
        rgba = decode_uncompressed_dds(b[128:], width, height, rgb_bits, rmask, gmask, bmask, amask)
        fourcc_s = 'UNCOMPRESSED'
    else:
        raise ValueError(f'Unsupported DDS fourcc for decode: {fourcc_s}')
    top = _dds_top_level_size(width, height, fourcc_s, rgb_bits)
    mip_payload = b[128 + top:] if (mipmaps or 1) > 1 else b""
    return DdsImage(width=width, height=height, mipmaps=mipmaps or 1, fourcc=fourcc_s,
                    rgba=rgba, header=b[:128], mip_payload=mip_payload,
                    level0_payload=b[128:128 + top])


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
