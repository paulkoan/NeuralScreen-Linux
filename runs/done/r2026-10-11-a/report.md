# run r2026-10-11-a

`uv run python -m minimal --source image --input-image fixtures/youtube-1440p.png --headless --frames 60 --worker-log --shm --no-motion --send-ahead 2`

exit **3** after 15.4s

```
source image (fixtures/youtube-1440p.png)  capture 2560x1440  ->  work 2560x1440 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: bash /opt/neuralscreen/state/repo/native/run_worker.sh
version: repo 62fe4b2 (+2 uncommitted) · worker reports no stamp · unknown — the worker reports no stamp (not the native mode, or not rebuilt)
frame 0 is the worker's warm-up: the window stays black until its first answer lands

```

stderr:

```
 warning: egl: failed to create dri2 screen
[worker] MESA-EGL: warning: pci id for fd 45: 10de:2702, driver (null)
[worker] pci id for fd 46: 10de:2702, driver (null)
[worker] pci id for fd 47: 10de:2702, driver (null)
[worker] MESA-EGL: warning: egl: failed to create dri2 screen
[worker] MESA-EGL: warning: pci id for fd 45: 10de:2702, driver (null)
[worker] 01cc:fixme:ntdll:NtQuerySystemInformation info_class SYSTEM_PERFORMANCE_INFORMATION
[worker] 21:00:20.226  [host] adapter 0: NVIDIA GeForce RTX 4080 SUPER vendor=0x10DE
[worker] 21:00:20.358  [host] DRED settings unavailable (settings1=0x80004002, settings=0x80004002)
[worker] 21:00:20.359  [pure] standalone D3D12 device ready; no swapchain or carrier modules
[worker] 01cc:fixme:d3dkmt:NtGdiDdDDIQueryAdapterInfo type 48 not handled.
[worker] 01cc:fixme:d3dkmt:NtGdiDdDDIQueryAdapterInfo type 48 not handled.
[worker] 21:00:20.363  [host] NVSDK_NGX_D3D12_Init -> 0xBAD00001 (?)
[worker] 01cc:fixme:d3dkmt:NtGdiDdDDIQueryAdapterInfo type 48 not handled.
[worker] 01cc:fixme:d3dkmt:NtGdiDdDDIQueryAdapterInfo type 48 not handled.
[worker] 21:00:20.363  [host] Init_with_ProjectID -> 0xBAD00001 (?)
[worker] 21:00:20.363  [host] NGX unavailable
[main] shared memory refused (the worker stopped after 0 of 4 reply bytes); frames stay on the pipe
pipeline failed: the worker died during the run; last stderr:
  pci id for fd 46: 10de:2702, driver (null)
  pci id for fd 47: 10de:2702, driver (null)
  MESA-EGL: warning: egl: failed to create dri2 screen
  MESA-EGL: warning: pci id for fd 45: 10de:2702, driver (null)
  01cc:fixme:ntdll:NtQuerySystemInformation info_class SYSTEM_PERFORMANCE_INFORMATION
  21:00:20.226  [host] adapter 0: NVIDIA GeForce RTX 4080 SUPER vendor=0x10DE
  21:00:20.358  [host] DRED settings unavailable (settings1=0x80004002, settings=0x80004002)
  21:00:20.359  [pure] standalone D3D12 device ready; no swapchain or carrier modules
  01cc:fixme:d3dkmt:NtGdiDdDDIQueryAdapterInfo type 48 not handled.
  01cc:fixme:d3dkmt:NtGdiDdDDIQueryAdapterInfo type 48 not handled.
  21:00:20.363  [host] NVSDK_NGX_D3D12_Init -> 0xBAD00001 (?)
  01cc:fixme:d3dkmt:NtGdiDdDDIQueryAdapterInfo type 48 not handled.
  01cc:fixme:d3dkmt:NtGdiDdDDIQueryAdapterInfo type 48 not handled.
  21:00:20.363  [host] Init_with_ProjectID -> 0xBAD00001 (?)
  21:00:20.363  [host] NGX unavailable
Traceback (most recent call last):
  File "/opt/neuralscreen/state/repo/minimal/__main__.py", line 241, in main
    summary = pipe.run(frames=args.frames,
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/neuralscreen/state/repo/minimal/loop.py", line 323, in run
    pair_before, last_after, index = self._pipelined_loop(
                                     ^^^^^^^^^^^^^^^^^^^^^
  File "/opt/neuralscreen/state/repo/minimal/loop.py", line 472, in _pipelined_loop
    self._check_alive()
  File "/opt/neuralscreen/state/repo/minimal/loop.py", line 380, in _check_alive
    raise RuntimeError(
RuntimeError: the worker died during the run; last stderr:
  pci id for fd 46: 10de:2702, driver (null)
  pci id for fd 47: 10de:2702, driver (null)
  MESA-EGL: warning: egl: failed to create dri2 screen
  MESA-EGL: warning: pci id for fd 45: 10de:2702, driver (null)
  01cc:fixme:ntdll:NtQuerySystemInformation info_class SYSTEM_PERFORMANCE_INFORMATION
  21:00:20.226  [host] adapter 0: NVIDIA GeForce RTX 4080 SUPER vendor=0x10DE
  21:00:20.358  [host] DRED settings unavailable (settings1=0x80004002, settings=0x80004002)
  21:00:20.359  [pure] standalone D3D12 device ready; no swapchain or carrier modules
  01cc:fixme:d3dkmt:NtGdiDdDDIQueryAdapterInfo type 48 not handled.
  01cc:fixme:d3dkmt:NtGdiDdDDIQueryAdapterInfo type 48 not handled.
  21:00:20.363  [host] NVSDK_NGX_D3D12_Init -> 0xBAD00001 (?)
  01cc:fixme:d3dkmt:NtGdiDdDDIQueryAdapterInfo type 48 not handled.
  01cc:fixme:d3dkmt:NtGdiDdDDIQueryAdapterInfo type 48 not handled.
  21:00:20.363  [host] Init_with_ProjectID -> 0xBAD00001 (?)
  21:00:20.363  [host] NGX unavailable

```
