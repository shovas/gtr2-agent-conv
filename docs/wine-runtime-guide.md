# Running GTR2 under Wine — reproducible setup and known limits

This guide records everything that was required to get `GTR2Dedicated.exe`
and `GTR2.exe` running under Wine, so an agent or end-user can reproduce the
setup without rediscovering it. It is a **runtime validation** guide, not a
conversion guide: it does not claim that converted content is accepted in
game.

Status at time of writing (see `docs/runtime-validation.md` for the full
experiment log):

| Component | Status |
|---|---|
| `GTR2Dedicated.exe` | Runs a full session; reads GameData `.gdb`/`.trk`/`.hat`; accepts converted TRK/AIW. Never opens track mesh archives (also true for stock content). |
| `GTR2.exe` client | Starts, reaches a D3D-initialised `CUBERealtime` window and loads UI archives. Menu text is blank; no route into a driving session has been found. |
| Converted geometry | **Not verified in game.** |

## 1. Prerequisites

- A Wine build with working wined3d/OpenGL (development used Wine **11.21**
  in `~/wine/bin/wine`; it was not on `PATH`).
- Xvfb with a **persistent** display. `xvfb-run -a` did not reliably pass
  `DISPLAY` through to Wine; use an explicit background Xvfb instead.
- Mesa software rendering (`LIBGL_ALWAYS_SOFTWARE=1` with llvmpipe).
- `7z` for extracting DLLs from redistributables.
- The GTR2 install available read-only; all experiments must run in an
  isolated overlay (see section 5).

Write these into your shell once:

```sh
export PATH="$HOME/wine/bin:$PATH"
export WINEPREFIX=/tmp/opencode/winefresh   # dedicated sandbox prefix
export DISPLAY=:77
export LIBGL_ALWAYS_SOFTWARE=1
```

## 2. Build a fresh prefix and install `mfc100.dll`

`GTR2Dedicated.exe` imports `Net_dedicated.dll`, which imports `mfc100.dll`.
Without it the process exits with `status c0000135`.

```sh
wineboot -i

# From the freely redistributable VC++ 2010 runtime (vcredist_x86.exe):
7z x -y vcredist_x86.exe -oout '././././vc_red.cab'
7z x -y out/vc_red.cab -odlls '*mfc100*'
cp dlls/F_CENTRAL_mfc100_x86 \
   "$WINEPREFIX/drive_c/windows/system32/mfc100.dll"
cp dlls/F_CENTRAL_mfc100_x86 \
   "$WINEPREFIX/drive_c/windows/syswow64/mfc100.dll"
```

`winetricks vcrun2010` was tried but failed at a regedit step; the manual
extraction is reliable.

## 3. Force Wine's X11 graphics driver

Wine may otherwise fall back to `nodrv`, producing:

```
err:winediag:nodrv_CreateWindow ... no driver could be loaded
err:d3d:wined3d_caps_gl_ctx_create Failed to create a window
```

Set the registry key in the prefix:

```sh
wine reg add 'HKCU\Software\Wine\Drivers' /v Graphics /t REG_SZ /d x11 /f
```

Start a persistent display and verify it before launching Wine:

```sh
Xvfb :77 -screen 0 1280x1024x24 >/tmp/opencode/xvfb.log 2>&1 &
xdpyinfo | head -2          # must report display :77
```

With this combination wined3d obtains a GL context; expect a line like:

```
fixme:d3d:wined3d_guess_card ... GL_RENDERER "llvmpipe (LLVM ...)"
```

`GALLIUM_DRIVER=zink` with lavapipe also gives a context but did not improve
anything. Wine itself reports "built without Vulkan support".

## 4. Fix the client startup crash (`VIDEOMODE`)

The client crashed at `0x59D46C` in `TvOverlayMan::CreateOverlays`.
Implementation tracing found the cause: a hardware watchpoint on `0x6FCD44`
showed the value being written from parsing the **`VIDEOMODE`** key in
`Config.ini`, then used as an unchecked list index.

Controlled result:

| `VIDEOMODE` | Outcome |
|---|---|
| `0` or `1` | Client stays alive; `CUBERealtime` window titled `GTR2` appears |
| `2`, `3`, `4`, `8` | Crash at `0x59D46C` |

So the required edit to a **sandbox copy** of `Config.ini` is:

```ini
VIDEOMODE=0
VIDEORAM=256
```

The project helper does this safely:

```python
from runtime_sandbox import patch_client_config
patched = patch_client_config(open("Config.ini", "rb").read())
```

Earlier attempts that did **not** help: `SHADERLEVEL`, `VIDEODRIVER`,
`TEXDETAIL`/`OBJDETAIL`, `MESA_GL_VERSION_OVERRIDE`, zink, and patching the
single null-dereference instruction. Do not repeat them.

Optional VRAM gate: `GTR2Config.exe` refuses to start with less than 32 MB
reported. On an **isolated copy only**, file offset `0x53C0` can be changed
from `0x7D` (`jge`) to `0xEB` (`jmp`) to skip the warning; the check is
`cmp eax,0x18`. With `VIDEOMODE=0` this is usually unnecessary for the
dedicated server, which does not show the client configuration dialog.

Optional native D3DX: Microsoft's freely redistributable DirectX June 2010
runtime supplies the correct `d3dx9_41.dll` (extract
`Mar2009_d3dx9_41_x86.cab`). Install it **into the sandbox prefix only** and
run with `WINEDLLOVERRIDES='d3dx9_41=n'`. It removes the
`d3dx_load_pixels_from_pixels Unhandled filter 0x4` fixmes (29 → 0) but does
**not** restore readable menu text.

## 5. Never write through the read-only install

A past incident damaged two stock files because a sandbox event directory was
a symlink into the game install. Use the helper that creates real directories
for every mutable path:

```sh
python3 runtime_sandbox.py /path/to/GTR2 /tmp/opencode/sandbox \
  --substitute GameData/Locations/Hockenheim/NTHockenheim.trk=/path/to/converted.trk
```

It symlinks untouched stock files, writes substituted files into real
directories, creates a real `UserData/` with `DedicatedServer.ini`, and can
be checked with:

```python
from runtime_sandbox import assert_no_mutable_symlinks
assert assert_no_mutable_symlinks(dest, substituted_paths) == []
```

## 6. Dedicated server — repeatable session

`GTR2Dedicated.exe` uses `UserData/DedicatedServer.ini`. The verified schema
was extracted from the executable's strings:

```ini
[SETTINGS]
GameDatabase="GAMEDATA\Locations\Anderstorp\3Anderstorp.gdb"
RaceName="Probe"
MaxPlayers=2
LobbyBroadcast=0
SessionRace=1
SessionWarmup=0
SessionQualify1=0
SessionPractice1=1
SessionRaceLaps=1
EnableCollisions=1
DifficultyMode=1
SkipFormation=1
RaceStart=0
StartHour=12
DamageMultiplier=0
TireUsage=0
FuelUsage=0
MechFailures=0
Weather=0
RainAmount=0.0
FlagRules=0
AllowAIControl=1
ForceCockpit=0
ConnectionType=0
UploadSpeed=1000
DSFM=0
[TRACKS]
```

`runtime_sandbox.write_ini()` writes this schema. The ini is read, but does
not by itself select the raced track — the server wizard does. The wizard is
a native Win32 dialog; drive it with `BM_CLICK` on child control IDs:

1. `Next` with control ID `1` (mode/class page).
2. `Next` with control ID `1032` (events page; 34 stock events are already selected).
3. `Start` on the final options page.

The server writes `UserData/Log_Dedicated/Results/*.txt`. Parse and check them
with:

```python
from runtime_sandbox import parse_session_results, acceptance_report
results = parse_session_results(sandbox / "UserData/Log_Dedicated/Results")
print(acceptance_report(results, "NTHockenheim.TRK", 656.7))
```

A successful converted-content run looked like:

```
Scene=GAMEDATA\LOCATIONS\Hockenheim\NTHockenheim.TRK
AIDB=GAMEDATA\LOCATIONS\Hockenheim\NTHockenheim.AIW
Track Length=656.6953     (stock Hockenheim: 3685.7964)
```

**Caveat:** this proves the engine used converted TRK/AIW data. It does not
prove geometry acceptance — the dedicated server never opens track `.gtr`
archives, even for stock tracks.

## 7. Client verification checklist

Launch:

```sh
cd /path/to/sandbox
wine GTR2.exe > client.log 2>&1
```

Expected signs of a healthy start:

- process stays alive;
- top-level window `#32770` "GTR2 Configuration" (accept with `OK`) followed by
  `CUBERealtime` window titled `GTR2`;
- `.gtr` opens: `GFX.GTR`, `UIASSETS.GTR`, `UIDATA\GTR2*.GTR`;
- zero `invalid frame` SEH errors.

Known remaining limits:

- Menu text renders as blank rectangles. XTEST clicks/keys, Win32
  `WM_LBUTTONDOWN`, DirectInput polling, vtable breakpoints, `+auto`,
  `+connect`, `RUNBENCHMARKS` and PLR edits did not enter a session.
- GTR2.exe contains an 869-entry UI element-name table at VA `0x6E61E0`
  (e.g. `APP_Button_GameModeSelect_QuickRace` at index 75); its name-to-ID
  function is `0x4C21F0` and the dispatch jump table is `0x4CD57C`. The
  QuickRace factory is `0x4C3B3F` → `0x4CF1D0` with vtable `0x68B954`.
  No activation handler was reachable by the methods tried — this is the
  next research target.
- A readable UI (working renderer or native Windows) is the practical
  unblock for client-side geometry acceptance.

## 8. Troubleshooting quick reference

| Symptom | Cause / fix |
|---|---|
| `Library mfc100.dll ... not found` | Copy `mfc100.dll` into prefix `system32` and `syswow64` |
| `nodrv_CreateWindow ... no driver could be loaded` | Set `Graphics=x11`; use persistent Xvfb, not `xvfb-run` |
| `wined3d_caps_gl_ctx_create Failed to create a window` | Same as above; verify `xdpyinfo` on the chosen display |
| Client exits/crashes at `0x59D46C` | `VIDEOMODE` ≥ 2; set `VIDEOMODE=0` |
| "Insufficient video memory" dialog | `GTR2Config` VRAM check on an isolated copy, or ignore with `VIDEOMODE=0` |
| Menu text blank | Wine D3DX/font path; native d3dx9_41 removes fixmes but not the blank text |
| `File not found` after `+connect 127.0.0.1` | This token did not provide a usable direct-IP path |
| Test suite fails with `Errno 28` | Wine trace/minidump files filled `/tmp`; remove `*.log` and `Minidump/` directories and rerun |

For the chronological evidence behind each item, see `docs/runtime-validation.md`.
