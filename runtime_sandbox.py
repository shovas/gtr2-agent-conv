#!/usr/bin/env python3
"""Build a safe GTR2 runtime sandbox from a read-only game install.

The sandbox overlays a game install in a temporary directory. Stock files are
referenced by symlink; any file that will be *written* (substituted config or
track files, `DedicatedServer.ini`) lives in a **real directory**, so a
mistaken ``rm``/``cp`` cannot mutate the read-only reference install.

This encodes the rule learned from an incident where a symlinked event
directory was written through, damaging two stock files.
"""
from __future__ import annotations

import argparse
from pathlib import Path

# Keys used by GTR2Dedicated.exe, extracted from its embedded strings.
INI_SETTINGS = {
    "GameDatabase": '"GAMEDATA\\Locations\\Anderstorp\\3Anderstorp.gdb"',
    "RaceName": '"Probe"',
    "MaxPlayers": "2",
    "LobbyBroadcast": "0",
    "SessionRace": "1",
    "SessionWarmup": "0",
    "SessionQualify1": "0",
    "SessionPractice1": "1",
    "SessionRaceLaps": "1",
    "EnableCollisions": "1",
    "DifficultyMode": "1",
    "SkipFormation": "1",
    "RaceStart": "0",
    "StartHour": "12",
    "DamageMultiplier": "0",
    "TireUsage": "0",
    "FuelUsage": "0",
    "MechFailures": "0",
    "Weather": "0",
    "RainAmount": "0.0",
    "FlagRules": "0",
    "AllowAIControl": "1",
    "ForceCockpit": "0",
    "ConnectionType": "0",
    "UploadSpeed": "1000",
    "DSFM": "0",
}


def write_ini(path: Path, settings: dict[str, str] | None = None) -> None:
    """Write `UserData/DedicatedServer.ini` with the verified key schema."""
    values = dict(INI_SETTINGS)
    if settings:
        values.update(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["[SETTINGS]"]
    lines.extend(f"{key}={value}" for key, value in values.items())
    lines.append("[TRACKS]")
    path.write_bytes(("\r\n".join(lines) + "\r\n").encode("ascii"))


def build_sandbox(game_root: str | Path, target: str | Path,
                  substitutions: dict[str, bytes] | None = None,
                  ini_settings: dict[str, str] | None = None) -> Path:
    """Create a sandbox overlay of ``game_root`` at ``target``.

    ``substitutions`` maps relative paths (e.g.
    ``GameData/Locations/Hockenheim/NTHockenheim.trk``) to replacement bytes.
    Every ancestor of a substituted file is a real directory; untouched
    siblings and root files are symlinks into the read-only install.
    """
    source = Path(game_root).resolve()
    dest = Path(target).resolve()
    if not source.is_dir():
        raise ValueError(f"game root not a directory: {source}")
    if dest == source or source in dest.parents:
        raise ValueError("sandbox must not be inside the game install")
    substitutions = substitutions or {}

    # Relative strings for every ancestor of a substituted path.
    mutable_dirs: set[str] = set()
    for rel in substitutions:
        parts = Path(rel).parts
        for i in range(len(parts)):
            mutable_dirs.add("/".join(parts[:i]))
    dest.mkdir(parents=True, exist_ok=True)

    def link_tree(src: Path) -> None:
        for child in sorted(src.iterdir()):
            rel_child = str(child.relative_to(source)).replace("\\", "/")
            target_path = dest / rel_child
            if rel_child in substitutions:
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_bytes(substitutions[rel_child])
                continue
            if rel_child in mutable_dirs:
                if child.is_dir():
                    target_path.mkdir(parents=True, exist_ok=True)
                    link_tree(child)
                else:
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    if not target_path.exists():
                        target_path.symlink_to(child)
                continue
            if not target_path.is_symlink() and not target_path.exists():
                target_path.symlink_to(child)

    link_tree(source)

    link_tree(source)
    # UserData is always mutable: it holds the server config and logs.
    user = dest / "UserData"
    if user.is_symlink():
        user.unlink()
    user.mkdir(parents=True, exist_ok=True)
    write_ini(user / "DedicatedServer.ini", ini_settings)
    for child in sorted((source / "UserData").iterdir()):
        if child.name == "DedicatedServer.ini":
            continue
        link = user / child.name
        if not link.exists():
            link.symlink_to(child)
    return dest


def parse_session_results(directory: str | Path) -> list[dict]:
    """Parse dedicated-server Practice/Qualify/Race result files.

    GTR2 writes `//[[gMa1.000f]]` config-text files under
    `UserData/Log_Dedicated/Results` after a completed session. Returns one
    dict per file with the scene, AI database, and track length fields used
    to verify which converted track the engine actually loaded.
    """
    root = Path(directory)
    results = []
    if not root.is_dir():
        return results
    for path in sorted(root.glob("*.txt")):
        data = path.read_bytes().decode("latin-1")
        fields = {}
        for line in data.splitlines():
            if "=" in line:
                key, _, value = line.partition("=")
                fields[key.strip()] = value.strip().strip('"')
        results.append({
            "file": path.name,
            "scene": fields.get("Scene", ""),
            "aidb": fields.get("AIDB", ""),
            "track_length": float(fields["Track Length"])
            if "Track Length" in fields else None,
            "race_mode": fields.get("RaceMode", ""),
        })
    return results


def acceptance_report(results: list[dict], expected_scene: str,
                      expected_length: float | None = None,
                      tolerance: float = 1.0) -> dict:
    """Summarise whether a session actually used the expected track.

    Structural validity is not game acceptance; this checks the engine's
    own session output, which records the loaded `.trk`/`.aiw` paths and the
    computed track length.
    """
    matching = [r for r in results
                if r["scene"].upper().endswith(expected_scene.upper())]
    length_ok = []
    if expected_length is not None:
        length_ok = [r for r in matching
                     if r["track_length"] is not None
                     and abs(r["track_length"] - expected_length) <= tolerance]
    return {
        "sessions": len(results),
        "scene_matches": len(matching),
        "length_matches": len(length_ok),
        "accepted": bool(matching) and (expected_length is None
                                        or bool(length_ok)),
    }


def patch_client_config(data: bytes) -> bytes:
    """Return a client `Config.ini` that avoids the Wine/llvmpipe startup crash.

    Root cause (dynamic trace, 2026-11-27): `TvOverlayMan::CreateOverlays`
    looks up entry index `0x6FCD44` in a list at `global+0x120`. That index is
    written from parsing `VIDEOMODE`; values that map to 2 or higher return
    NULL under llvmpipe and are dereferenced unchecked at `0x59D46C`.
    `VIDEOMODE=0` (and 1) reach the full `CUBERealtime` game window.

    Only these two keys are changed; everything else is preserved verbatim.
    """
    text = data.decode("latin-1")
    out = []
    for line in text.splitlines(keepends=True):
        if line.strip().upper().startswith("VIDEOMODE="):
            out.append("VIDEOMODE=0\r\n")
        elif line.strip().upper().startswith("VIDEORAM="):
            out.append("VIDEORAM=256\r\n")
        else:
            out.append(line)
    return "".join(out).encode("latin-1")


def assert_no_mutable_symlinks(root: str | Path,
                               substituted: list[str] | None = None) -> list[str]:
    """Return writable locations that are (unsafely) symlinks.

    Checks the ``UserData`` root and every substituted file and its ancestor
    directories. Sibling leaves elsewhere are intentionally symlinks into the
    read-only install and are not flagged.
    """
    root = Path(root)
    candidates = [root / "UserData"]
    for rel in substituted or []:
        path = root / rel
        candidates.append(path)
        candidates.extend(path.parents)
    seen: set[Path] = set()
    bad = []
    for path in candidates:
        if path in seen or not path.is_relative_to(root):
            continue
        seen.add(path)
        if path.is_symlink():
            bad.append(str(path))
    return bad


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("game_root")
    parser.add_argument("target")
    parser.add_argument("--substitute", action="append", default=[],
                        metavar="REL=FILE", help="relative path = replacement file")
    args = parser.parse_args()
    substitutions = {}
    for item in args.substitute:
        rel, _, filename = item.partition("=")
        substitutions[rel] = Path(filename).read_bytes()
    dest = build_sandbox(args.game_root, args.target, substitutions)
    print(f"sandbox: {dest}")
    print(f"mutable symlinks: {assert_no_mutable_symlinks(dest, list(substitutions))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
