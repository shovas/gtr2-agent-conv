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
