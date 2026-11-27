# Runtime validation status (2026-11-27)

Goal: observe GTR2 actually loading converted content. Status: **partial** —
the executable starts and enumerates/reads GameData, but cannot create a
Direct3D window in this environment.

## Environment discovered

- Wine **11.21** at `~/wine/bin/wine` (not on PATH by default).
- Existing prefix `~/.wine`, `winetricks` at `old-tmp-files/winetricks`.
- Network access available; winetricks cache at `~/.cache/winetricks/`.
- `Xvfb`, `7z`, `gdb`, `objdump`, `radare2` available. No `cabextract`,
  no system `wine` on PATH.

## Blockers resolved

1. **No Wine on PATH** — use `export PATH=~/wine/bin:$PATH`.
2. **`mfc100.dll` missing** (needed by `Net_dedicated.dll` →
   `GTR2Dedicated.exe`). `winetricks vcrun2010` downloaded the redistributable
   but failed at a regedit step. Extracted the DLL manually:
   - `7z x -y <vcredist_x86.exe> -oout '././././vc_red.cab'`
   - `7z x -y out/vc_red.cab -odlls '*mfc100*'`
   - copy `F_CENTRAL_mfc100_x86` to
     `~/.wine/drive_c/windows/{system32,syswow64}/mfc100.dll`
   (Earlier PHS research needed MFC42 for GTL's Net.dll; that is a different
   blocker. GTR2's own EXEs import no MFC at all.)

## What now works

`wine GTR2Dedicated.exe -h` starts, resolves all DLL imports, and:

- enumerates `GAMEDATA\Championships\Custom\*.gdb` (40+ files),
- opens every `GAMEDATA\LOCATIONS\<track>\<event>.gdb` and `.trk`
  (verified for Anderstorp, Barcelona, Brno, Donington, Dubai, Enna, Estoril,
  Hockenheim, Imola, Magny-Cours, ...),
- enumerates `GAMEDATA\LOCATIONS\HAT_Dedicated\` and all `.hat` filenames.

This is a real runtime consumer check: files our converters emit (`.trk`,
`.gdb`, `.hat`) are exactly the ones the engine opens/enumerates. The
`validate_gtr2_tree()` placement rule for `.hat` agrees with the observed
`HAT_Dedicated` enumeration.

Reproduce:

```
cd ../GTR2Steam
export PATH=~/wine/bin:$PATH WINEPREFIX=~/.wine
WINEDEBUG=+file timeout 60 wine GTR2Dedicated.exe -h > trace.txt 2>&1
grep -oE 'CreateFileW L"[^"]*GAMEDATA[^"]*"' trace.txt | sort -u
```

## Remaining blocker

Direct3D window creation fails under Xvfb:

```
err:d3d:wined3d_caps_gl_ctx_create Failed to create a window.
err:d3d:wined3d_adapter_gl_init Failed to get a GL context for adapter ...
```

Tried: `xvfb-run` with 1024x768 and 1280x1024, `LIBGL_ALWAYS_SOFTWARE=1`,
`GALLIUM_DRIVER=llvmpipe`, `MESA_GL_VERSION_OVERRIDE=3.3`, Wine DLL overrides
(disabling d3d9 breaks imports, so not viable). The environment's DRI3/EGL
setup does not provide a GL context to Wine.

## Decisive control: minimal D3D9 program fails identically (2026-11-27)

To rule out a GTR2-specific problem, a standalone 12-line D3D9 program was
compiled with `wineg++` against Wine's own headers and run under Xvfb:

```cpp
#include <windows.h>
#include <d3d9.h>
int main() {
    LPDIRECT3D9 d = Direct3DCreate9(D3D_SDK_VERSION);
    if (!d) return 1;
    D3DPRESENT_PARAMETERS p = {};
    p.Windowed = TRUE;
    p.SwapEffect = D3DSWAPEFFECT_DISCARD;
    IDirect3DDevice9* dev = 0;
    HRESULT hr = IDirect3D9_CreateDevice(
        d, D3DADAPTER_DEFAULT, D3DDEVTYPE_HAL, GetDesktopWindow(),
        D3DCREATE_SOFTWARE_VERTEXPROCESSING, &p, &dev);
    return hr == D3D_OK ? (dev ? 0 : 2) : 3;
}
```

```
wineg++ d3dtest.cpp -o d3dtest64.exe -ld3d9   # succeeds
xvfb-run -a wine d3dtest64.exe                 # exit 3
```

It fails with the **same** errors as GTR2Dedicated.exe:
`nodrv_CreateWindow L"The explorer process failed to start"` and
`wined3d_caps_gl_ctx_create Failed to create a window`. A 32-bit build was
not possible (`gnu/stubs-32.h` missing), but Wine is a WoW64 build with a
single shared wined3d, so the 64-bit control exercises the same code path.

**Conclusion:** the D3D failure is entirely environmental (Wine's window/GL
driver in this container), not a property of GTR2 or of any converted file.
No amount of conversion work can resolve it; see the unblock list below.

## What would unblock full runtime validation

- A working X server with Mesa software rendering that Wine can bind to
  (`glxinfo -B` currently unavailable), or
- Wine built with Vulkan/D3D support (this build reports built without
  Vulkan), or
- A headless loader / standalone track validator that consumes the same
  `.gdb`/`.trk`/`.hat` parsing path without D3D.

## Important caveat

File enumeration/reading is **not** in-game acceptance. Distinguish:
structural validity (our offline validators), semantic compatibility (field
meaning), runtime loading (files opened), visual correctness (rendering), and
functional in-game acceptance (driving). This setup reaches only the third.

## Additional D3D experiments (2026-11-29)

- `glxinfo -B` under Xvfb reports Mesa llvmpipe 26.1.1, OpenGL 4.6, direct
  rendering — so X/Mesa itself works. Wine still reports
  `wined3d_caps_gl_ctx_create Failed to create a window` at 16/24/32-bit
  depths, with or without `LIBGL_ALWAYS_SOFTWARE`/`GALLIUM_DRIVER=llvmpipe`.
- Only x86_64 `libGL.so.1` is installed. The i686 Mesa RPMs were downloaded
  and extracted locally (`dnf download --arch i686 mesa-libGL mesa-dri-drivers`
  + `rpm2cpio`), but `mesa-libGL.i686` provides only `libGLX_mesa.so.0`,
  not `libGL.so.1`; passwordless `sudo` is unavailable for a system install.
- Wine is a WoW64 build (i386-windows DLLs, x86_64-unix .so), so a 32-bit GL
  library may not be the issue. A virtual-desktop `explorer /desktop=` launch
  failed with `ShellExecuteEx failed: Module not found`.
- **What would unblock:** a Wine build with working wined3d window creation,
  or a headless loader that consumes `.gdb`/`.trk`/`.hat` without D3D.

## Runtime progress: GL context now works, device creation still fails (2026-11-27)

A follow-up control refined the earlier "purely environmental" conclusion.
The decisive difference is **how the X display is provided**: `xvfb-run -a
wine ...` did not propagate `DISPLAY` into the Wine processes reliably, so
`winex11.drv` never initialised and `nodrv_CreateWindow` fired. A persistent
Xvfb plus an explicit x11 driver setting gets much further:

```sh
export PATH="$HOME/wine/bin:$PATH"
export WINEPREFIX=/tmp/opencode/winefresh
wineboot -i
wine reg add 'HKCU\Software\Wine\Drivers' /v Graphics /t REG_SZ /d x11 /f
Xvfb :77 -screen 0 1280x1024x24 &
DISPLAY=:77 LIBGL_ALWAYS_SOFTWARE=1 wine d3dtest64.exe
```

Verified results:

- `wined3d_guess_card` now reports
  `GL_RENDERER "llvmpipe (LLVM 22.1.8, 256 bits)"` — a **real GL context is
  created**, so the old `wined3d_caps_gl_ctx_create Failed to create a window`
  blocker is a *configuration artifact*, not an intrinsic container limit.
- `Direct3DCreate9` succeeds, but `IDirect3D9_CreateDevice(...D3DDEVTYPE_HAL,
  D3DCREATE_SOFTWARE_VERTEXPROCESSING...)` still returns a failure HRESULT
  (control exit 3) and emits repeated `err:seh:call_seh_handlers invalid frame`
  messages from wined3d/WGL. With a real `CreateWindowA` window the control
  hangs instead. `GALLIUM_DRIVER=softpipe`, GL-version overrides and
  `MESA_LOADER_DRIVER_OVERRIDE=swrast` did not get past this.
- **The SEH failure was specific to the minimal control program, not to
  GTR2.** Running the real `GTR2Dedicated.exe -h` under the same setup (after
  copying `mfc100.dll` into the fresh prefix) gives exit 124 from a 75-second
  timeout — i.e. the process **stays alive** — with a working llvmpipe GL
  context and **zero** `invalid frame` SEH errors. The minimal control's
  `GetDesktopWindow()`/window path, not wined3d itself, triggered the crash.

## GTR2Dedicated now reaches a D3D-initialised, GameData-loaded state (2026-11-27)

```
cd ../GTR2Steam
export PATH="$HOME/wine/bin:$PATH"
export WINEPREFIX=/tmp/opencode/winefresh          # fresh prefix, Graphics=x11, mfc100.dll
DISPLAY=:77 LIBGL_ALWAYS_SOFTWARE=1 \
  WINEDEBUG=+file timeout 75 wine GTR2Dedicated.exe -h > trace.txt 2>&1
```

Observed:

- `wined3d_guess_card` with `GL_RENDERER "llvmpipe (LLVM 22.1.8, 256 bits)"`;
  **no** `wined3d_caps_gl_ctx_create` failures and **0** SEH frame errors.
- **958** distinct GameData paths opened, including **83 `.gdb`** and
  **34 `.trk`** files across the stock tracks (e.g.
  `GAMEDATA\LOCATIONS\Anderstorp\3ANDERSTORP.trk`).
- `HAT_Dedicated` is enumerated via directory scans.

This promotes the earlier file-trace check from a pre-D3D state to a
**D3D-initialised runtime consumer check**: the engine opens exactly the
`.gdb`/`.trk` files our converters emit, with graphics up. It is still **not**
in-game acceptance — no converted track has been selected for a session, and
the dedicated-server configuration schema (`DedicatedServer.ini`, `TrackName`,
`SessionRace`, ...) is not yet established. **Precise unblock:** determine the
dedicated-server session configuration needed to actually load and race a
converted track, then observe whether it accepts the converted files.

## Dedicated-server configuration and UI automation (2026-11-27)

Extracted from `GTR2Dedicated.exe` strings and verified against the running
process:

- The config file is **`UserData\DedicatedServer.ini`** (not the game root).
  Its schema is `[SETTINGS]` with keys `GameDatabase`, `RaceName`,
  `MaxPlayers`, `LobbyBroadcast`, `UniqueLobbyUsername/Password`,
  `SessionRace{,Laps,Mins}`, `SessionWarmup{,Mins}`,
  `SessionQualify1/2{,Mins}`, `SessionPractice1/2{,Mins}`,
  `EnableCollisions`, `DifficultyMode`, `SkipFormation`, `RaceStart`,
  `StartHour`, `DamageMultiplier`, allow/assist flags, `Weather`,
  `RainAmount`, `FlagRules`, `ConnectionType`, `UploadSpeed`, `DSFM`, plus a
  `[TRACKS]` section header. A sandbox with symlinked game files confirmed
  the engine opens this exact path (`CreateFileW L"UserData\\DedicatedServer.ini"`).
- Changing `GameDatabase` to a nonexistent file, and adding plausible
  `[TRACKS]` entries (`0=`, `1=`, `Track0=`), produced **identical** startup
  file traces (same 34 `.trk` / 83 `.gdb` opens, 0 SEH errors). The ini is
  read but does not by itself select a track at startup; the bundled
  `Support/GTR2_dedicated_server.txt` says track/session changes come from
  the server's **Next Event / Next Session** buttons or client votes.
- The native UI is fully reachable from Wine. `EnumWindows`/`EnumChildWindows`
  finds the `#32770` "GTR2 Dedicated Server" wizard with pages for
  mode/class, **"Available Events:" / "Selected Events:"** (ListBox id 1003
  has 34 items), server options, and race assists. `SendMessage(h, BM_CLICK)`
  works: clicking `+`, `Next`, `Next`, `Start` advanced the wizard and a
  `Afx:...:0 "Socket Notification Sink"` window appeared (network up).
- **Still not a race session:** after `Start`, file tracing shows the same
  34 `.trk` opens and **zero `.mas`/`.gtr`** archive opens, so no converted
  track's geometry was loaded.

**Correction to the "owner-drawn" hypothesis (2026-11-27):** the event
ListBox entries are ordinary **UTF-16LE strings**. `LB_GETTEXT` via
`SendMessageA` truncates at the first NUL byte of the UTF-16 code unit, which
produced the misleading single letters (`A`, `B`, `D`, ...). Dumping raw item
bytes and decoding as UTF-16LE yields all 34 stock event names: Anderstorp,
Barcelona, Brno GP, Donington, Enna Pergusa, Estoril, Hockenheim, Imola,
Magny-Cours, Monza, Oschersleben, Spa-Francorchamps, Valencia, Dubai and
Zhuhai variants. `LB_GETITEMDATA` is 0 because no per-item data is attached,
not because the control is owner-drawn.

**Unblock:** selecting an event is still unresolved. `LB_SETCURSEL`,
`LB_SETSEL`, `WM_COMMAND/LBN_SELCHANGE`, `BM_CLICK` on `+`/`>>`, and real
mouse clicks on both the item and the button all left the "Selected Events"
ListBox (id 1000) empty. Either the commit message is different or those
controls belong to a hidden wizard page. Once an event is committed and a
session starts, check whether GTR2 opens the converted `.mas`/`.gtr` members
and accepts them; alternatively connect a game client and use its Chat vote
buttons.

Sandbox recipe (keeps the read-only install untouched): create a directory of
symlinks to the GTR2 files, add `UserData/DedicatedServer.ini`, and run
`wine GTR2Dedicated.exe` from there under the persistent Xvfb setup.

## Converted rF1 track files in a live session (2026-11-27)

A sandbox (`/tmp/opencode/gtr2conv`) was built with symlinks to all stock GTR2
files, except that `GameData/Locations/Anderstorp` held the converted Joesville
tree: `3ANDERSTORP.trk` and `3ANDERSTORP.AIW` were replaced with the converted
rF1 versions, and the converted `JoesVille_Speedway*.gtr` /
`commonmaps.gtr` archives were placed beside them. A `Joesville` alias
directory made the converted TRK's `SearchPath=GameData\Locations\Joesville`
resolvable. The dedicated-server wizard was driven to `Start` as above.

Verified with `WINEDEBUG=+file`:

- The engine **opened the converted TRK** from the converted search path:
  `CreateFileW L"GAMEDATA\\LOCATIONS\\Joesville\\3ANDERSTORP.trk"`.
  No SEH errors occurred.
- It **enumerated** the converted archives (`FindNextFileW returning
  L"JoesVille_Speedway.gtr"`, `..._map.gtr`) but **did not open them**; the
  only `.gtr` files actually opened were shared stock archives
  (`CREW.GTR`, `STEX.GTR`, `TEAMMAPS.GTR`, `SKIES_*.GTR`).
- The server then advanced through the other 34 stock events (e.g. Hockenheim
  car files were loaded), so the substituted event was exercised only during
  initial load.

This is the first time **converter output** was consumed by a D3D-initialised
GTR2 process: the converted `.trk` was found and opened, with no crash. It is
still not geometry acceptance — the converted mesh archives were enumerated
but not loaded, which is consistent with a dedicated server not needing track
meshes for rendering.

**Unblock:** confirm whether the dedicated server ever loads track mesh
archives (a client-rendered session may be required), and whether `MASFile`
resolution in converted TRKs needs stock archive names. Then check whether a
client accepts the converted geometry.

## Full game client: D3D works, VRAM gate blocks session (2026-11-27)

`wine GTR2.exe` under the same persistent-Xvfb / x11 / llvmpipe setup starts
and creates a D3D device (`wined3d_device_set_software_vertex_processing device
014653A0`, 0 SEH errors), but stops at a `#32770 "GTR2 Configuration"` dialog
containing `Insufficient video memory detected. A minimum of 32 MB of free
video memory required.` Clicking `OK` leaves the dialog up; no session starts.

Tried without success:

- setting `VIDEORAM=256` in a local copy of `Config.ini` (the stock file has
  `VIDEORAM=-52`; the game recomputes it from D3D-reported VRAM);
- Wine registry `HKCU\Software\Wine\Direct3D\VideoMemorySize = 512`;
- `LIBGL_ALWAYS_SOFTWARE=1` with llvmpipe (already required for any GL context).

**Unblock:** a renderer that reports >=32 MB of video memory to D3D
(`IDirect3DDevice9::GetDeviceCaps` / `D3DCAPS9`, likely from wined3d's GL
renderer), or a code-level bypass of this configuration gate. Until then the
client path cannot load any track — converted or stock — so the dedicated
server remains the only runtime harness that reaches a session.

## Converted track accepted in a completed dedicated-server session (2026-11-27)

A controlled substitution proved the engine **parses converter output**, not
just opens the file:

- Sandbox `GameData/Locations/Hockenheim/NTHockenheim.trk` and
  `NTHockenheim.AIW` were replaced with the converted rF1 Joesville TRK/AIW;
  converted `.gtr` archives were placed beside them.
- The dedicated server was driven to `Start` and **completed a Practice1
  session**, writing `UserData/Log_Dedicated/Results/Probe_..._Practice1.txt`
  with `Scene=GAMEDATA\LOCATIONS\Hockenheim\NTHockenheim.TRK`,
  `AIDB=...NTHockenheim.AIW` and **`Track Length=656.6953`**.
- The stock Hockenheim GDB declares `Length = 2.294 mi/3.692 km`, and an
  earlier unmodified session wrote `Track Length=3685.7964`. The converted
  Joesville GDB declares `Length = .656 KM / .41 Miles`. The change to
  656.6953 m therefore comes from the **converted track files**, proving the
  engine consumed and used them. Zero SEH errors.

This is the first **game-accepted** consumption of converter output: a real
GTR2 process ran a full session using converted rF1 TRK/AIW data. Limits:
the dedicated server still did not open the converted `.gtr` mesh archives
(only `CREW.GTR`/`STEX.GTR`/`TEAMMAPS.GTR` were loaded), so **geometry
acceptance remains unverified**, and the client path is still blocked by the
VRAM/crash issue above.


## Dedicated server never loads track meshes — control (2026-11-27)

Decisive control for the "converted `.gtr` files are only enumerated" result:
with the **stock** `NTHockenheim.trk`/`.AIW` restored, a completed
Practice1 session again opened only `CREW.GTR`, `STEX.GTR`,
`TEAMMAPS.GTR`, `SKIES_*.GTR`. It never opened the stock `NTHockenheim.gtr`
(16 directory-enumeration mentions, zero `CreateFileW`). Therefore the
absence of converted `.gtr` opens is a property of the **dedicated server
harness** (which needs no rendered track geometry), not a defect in the
converted archives or their `MASFile` references.

**Unblock:** geometry acceptance cannot be tested with `GTR2Dedicated.exe`
at all; it requires a client-rendered session, which is currently blocked by
the post-config crash after the VRAM-gate bypass. Do not spend further time
adjusting converted `MASFile`/`SearchPath` lines for the dedicated server.

## Sandbox incident and repair (2026-11-27)

During the Hockenheim substitution, the sandbox event directory was a symlink
into the read-only `GTR2Steam` install. `rm`/`cp` therefore modified the stock
`NTHockenheim.trk` and `.AIW` in place, and the attempted restore created
self-referential symlinks (`ELOOP`). The damage was detected by the normal
test suite (`test_aiw_parse_from_reference_corpus`: 58 != 59; two
`test_gtl_to_gtr2` failures). Both files were restored from the independent
local install at `/vmhost-smbofficelinux/home_ollama/GTR2-Steam-231208/`;
the full normal suite passes again. Byte-identity with the previous copies is
not guaranteed, and no further experiments should mutate symlinked corpus
paths.


## Client crash diagnosis (2026-11-27)

`WINEDEBUG=+seh` on the patched-client run shows the fatal exception:
`EXCEPTION_ACCESS_VIOLATION` at `0x59D46C` (GTR2.exe RVA `0x19D46C`),
reading address `0x8`, i.e. a null pointer returned by `call 0x5FD1B0`
at `0x59D45F` and dereferenced unchecked by `mov edx,[eax+0x8]`
(`0x5FD1B0` looks up an element in an array at `this+0x120` and returns
NULL when out of range). The crash happens after the VRAM-gate patch and
`OK`, before any session files are opened.

A minimal patch of a **temporary sandbox copy** of `GTR2.exe` (file offset
`0x19C86C`, `8b 50 08` -> `31 d2 90`, skipping only that dereference) made
the process exit quietly with no session and no `.gtr` opens — so the crash
is one symptom of a broader D3D/renderer capability mismatch, not a single
fixable instruction. Original game binaries were not modified.

**Unblock:** a renderer supporting the D3D capabilities GTR2 expects (or a
native Windows run). Do not continue binary-patching on llvmpipe.

## Client crash call-site detail (2026-11-27)

`0x59D450` dereferences the result of `0x5FD1B0(this, index)` without a
null check. Static call sites show the index comes from the global at
`0x6FCD44` (`0x59EB8E` -> push eax -> `0x59D450`, and the getter at
`0x59D4D0`), against a lookup object at `0xF3A468`. Under llvmpipe that
lookup returns NULL, so the game crashes during graphics setup. No write to
`0x6FCD44` appears in static code, so the value is set through an imported
/path imported table; identifying which capability it represents would need
dynamic tracing in a working renderer. Binary patching is not a productive
route here.


## Config sweep for the client crash — negative (2026-11-27)

Tried `SHADERLEVEL` 0/1/2 and `VIDEODRIVER` 0/1 in a real sandbox copy of
`Config.ini` (with the VRAM gate already bypassed). Every combination still
crashed after `OK`; `VIDEODRIVER=1` merely left the crash dialog on screen.
So the null lookup at `0x59D46C` is not selected by those user settings.
This closes the simple config route; a working renderer remains the unblock.

