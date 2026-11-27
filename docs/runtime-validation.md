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
