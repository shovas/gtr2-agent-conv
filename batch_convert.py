#!/usr/bin/env python3
"""Batch-convert ancestral ISIMotor meshes into verified GTR2-layout GMTs.

Walks ``../SportsCarGtUsa`` type-2 MAS archives for ``.vrl`` members,
``../GTR1Vanilla`` archives for third-magic ``.gmt`` members and
``../CopaPetrobrasdeMarcas`` MAS archives for ISI-encrypted GSC GMT members,
converts each with :mod:`vrl_to_gmt` / :mod:`gtr1_to_gmt` /
:mod:`gmt_layout.gsc_member_to_gtr2`, verifies the result by re-parsing and by
material-tail checks, and writes only verified outputs to an explicit output
directory. Game data is never copied into this repository.
"""
from __future__ import annotations

import argparse
import struct
from pathlib import Path

import gmt_format
import gmt_layout
import gmt_semantic
import gtr1_to_gmt
import mas_tool
import simbin_text_tool as stt
import validate_materials
import vrl_to_gmt

ROOT = Path(__file__).resolve().parent
DEFAULT_ROOTS = {
    "vrl": ROOT.parent / "SportsCarGtUsa",
    "gtr1": ROOT.parent / "GTR1Vanilla",
    # All four ISI-encrypted GSC-family corpora use the same member decoder;
    # sampled conversions from each pass geometry/UV validation 20/20.
    "gsc": (
        ROOT.parent / "CopaPetrobrasdeMarcas",
        ROOT.parent / "GameStockCar",
        ROOT.parent / "StockCarExtreme",
        ROOT.parent / "Automobilista",
    ),
}


def archive_members(root: Path, extension: str, kind: str):
    """Yield (archive_path, entry) for members with the given extension."""
    patterns = ("*.gtr", "*.GTR") if kind == "gtr1" else ("*.mas", "*.MAS")
    paths = []
    for pattern in patterns:
        paths.extend(root.rglob(pattern))
    for arc in sorted(paths):
        try:
            _, entries = mas_tool.read_archive(arc)
        except Exception:
            continue
        for entry in entries:
            if entry.name.lower().endswith(extension) and entry.data:
                yield arc, entry


def verify_gsc_uvs(decoded: dict, parsed) -> list[str]:
    """Byte-exact UV check between a decoded GSC member and its GTR2 output."""
    def packed(pairs):
        return b"".join(struct.pack("<2f", u, v) for u, v in pairs)

    source = [uv for sub in decoded.get("submeshes", []) for uv in sub.get("uvs", [])]
    output = [uv for mesh in parsed.meshes
              for uv in (gmt_format.read_mesh_uvs(mesh) or [])]
    if not source:
        return []
    if len(source) != len(output):
        return ["uv_count_mismatch"]
    return [] if packed(source) == packed(output) else ["uv_mismatch"]


def convert_member(kind: str, data: bytes, template: bytes, name: str,
                   reasons: dict[str, int] | None = None) -> bytes | None:
    """Convert and verify one member; return GMT bytes or None when skipped."""
    def skip(reason: str) -> None:
        if reasons is not None:
            reasons[reason] = reasons.get(reason, 0) + 1

    if kind == "gsc":
        decoded = gmt_semantic.decode_gsc_member(data)
        if decoded is None:
            skip("no_gsc_geometry")
            return None
        try:
            output = gmt_layout.gsc_member_to_gtr2(data)
        except (ValueError, struct.error) as exc:
            skip(f"gsc_build:{type(exc).__name__}:{exc}")
            return None
        problems = []
        parsed = gmt_format.parse_gmt("out.gmt", output)
        expected = sum(len(s["positions"]) for s in decoded["submeshes"])
        if sum(len(m.base_vertices) for m in parsed.meshes) != expected:
            problems.append("vertex_count_mismatch")
        problems.extend(verify_gsc_uvs(decoded, parsed))
    elif kind == "vrl":
        vrl = stt.read_vrl(data)
        if not vrl or vrl["vertex_count"] == 0:
            skip("no_vrl_geometry")
            return None
        try:
            output = vrl_to_gmt.vrl_to_gmt(vrl, template)
        except (ValueError, struct.error) as exc:
            skip(f"vrl_build:{type(exc).__name__}:{exc}")
            return None
        problems = vrl_to_gmt.verify_gmt(output, vrl)
    else:
        geometry = gtr1_to_gmt.geometry_from_gtr1(data)
        if geometry is None:
            skip("no_gtr1_geometry")
            return None
        positions, normals, triangles = geometry
        try:
            output = gtr1_to_gmt.gtr1_to_gmt(data, template)
        except (ValueError, struct.error) as exc:
            skip(f"gtr1_build:{type(exc).__name__}:{exc}")
            return None
        problems = vrl_to_gmt.verify_gmt_geometry(output, positions, triangles, normals)
    material_problems = validate_materials.check_gmt(output, name)
    problems.extend(material_problems)
    if problems:
        skip(f"verify:{problems[0] if not material_problems else 'material:' + material_problems[0]}")
        return None
    if reasons is not None:
        reasons["ok"] = reasons.get("ok", 0) + 1
    return output


def batch_convert(template: bytes, out_dir: Path, limit: int = 0,
                  roots: dict[str, Path] | None = None,
                  reasons: dict[str, int] | None = None) -> dict:
    """Convert up to ``limit`` members per family; return a report."""
    roots = roots or DEFAULT_ROOTS
    out_dir.mkdir(parents=True, exist_ok=True)
    report: dict[str, int] = {}
    reasons = reasons if reasons is not None else {}
    for kind, ext in (("vrl", ".vrl"), ("gtr1", ".gmt"), ("gsc", ".gmt")):
        target = out_dir / kind
        target.mkdir(exist_ok=True)
        scanned = written = 0
        selected = roots[kind]
        if not isinstance(selected, (list, tuple)):
            selected = (selected,)
        for root in selected:
            for arc, entry in archive_members(Path(root), ext, kind):
                data = convert_member(kind, entry.data, template, entry.name, reasons)
                scanned += 1
                if data is not None:
                    safe = arc.stem + "_" + Path(entry.name).stem + ".gmt"
                    (target / safe).write_bytes(data)
                    written += 1
                if limit and scanned >= limit:
                    break
            if limit and scanned >= limit:
                break
        report[f"{kind}_scanned"] = scanned
        report[f"{kind}_written"] = written
    return report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--template", required=True, help="real GTR2 .gmt template")
    ap.add_argument("--out", required=True, help="output directory (outside the repo)")
    ap.add_argument("--limit", type=int, default=0, help="max members per family (0 = all)")
    args = ap.parse_args(argv)
    template = Path(args.template).read_bytes()
    gmt_format.parse_gmt("template.gmt", data=template)  # fail early on bad template
    reasons: dict[str, int] = {}
    report = batch_convert(template, Path(args.out), args.limit, reasons=reasons)
    for key, value in report.items():
        print(f"{key}={value}")
    for reason, count in sorted(reasons.items(), key=lambda kv: -kv[1]):
        print(f"reason[{reason}]={count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
