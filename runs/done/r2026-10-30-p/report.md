# run r2026-10-30-p

runner `e44571d7dd12` · entry `ngx-new` · env from policy: DISPLAY, NS_NR_PRESET, NS_WORKER_CMD

`uv run python -m minimal --frames 120 --headless --source synthetic --size 2560x1440 --save-after ngx-new-120.png --worker-log`

exit **0** after 11.5s

```
source synthetic  capture 2560x1440  ->  work 2560x1440 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: bash /opt/neuralscreen/state/repo/native/run_worker.sh --prefix /opt/neuralscreen/wine
version: repo 5847809 (+2305 uncommitted) · worker reports no stamp · unknown — the worker reports no stamp (not the native mode, or not rebuilt)
frame 0 is the worker's warm-up: the window stays black until its first answer lands
pygame 2.6.1 (SDL 2.28.4, Python 3.11.15)
Hello from the pygame community. https://www.pygame.org/contribute.html
frames: 120 done, 0 skipped, 9.219s (13.02 fps headline, 19.33 fps steady), worker exit 0
timing: capture 3.7ms  send 36.9ms  recv 30.4ms  display 3.2ms   (mean 74.1ms/frame, 13.5 fps; median 51.7ms/frame, 19.3 fps steady)
send spread: min 11.7  median 15.4  max 2581.1 ms at frame 0 of 120   (one-off at frame 0 — the worker's warm-up, not a per-frame cost)
recv spread: min 23.5  median 29.6  max 51.6 ms at frame 0 of 120   (one-off at frame 0 — the worker's warm-up, not a per-frame cost)
worker clock: 119 frames in 6.265s = 52.65 ms/frame (19 fps, from the worker's own timestamps)
  after  -> ngx-new-120.png

```

stderr:

```
 supports VK_EXT_descriptor_buffer!
[worker] 283955.862:0020:0024:info:vkd3d-proton:vkd3d_bindless_state_add_binding: Device supports VK_EXT_descriptor_buffer!
[worker] 283956.175:0020:0024:info:vkd3d-proton:d3d12_device_caps_init_shader_model: Enabling support for SM 6.6.
[worker] 283956.175:0020:0024:info:vkd3d-proton:d3d12_device_caps_init_shader_model: Enabling support for SM 6.7.
[worker] 283956.175:0020:0024:info:vkd3d-proton:d3d12_device_caps_init_shader_model: Enabling support for SM 6.8.
[worker] 283956.176:0020:0024:fixme:vkd3d-proton:d3d12_device_caps_init_feature_options1: TotalLaneCount = 7680, may be inaccurate.
[worker] 283956.176:0020:0024:info:vkd3d-proton:d3d12_device_determine_ray_tracing_tier: DXR support enabled.
[worker] 283956.176:0020:0024:info:vkd3d-proton:d3d12_device_determine_ray_tracing_tier: DXR 1.1 support enabled.
[worker] 283956.176:0020:0024:info:vkd3d-proton:d3d12_device_caps_init_feature_level: DX Ultimate supported!
[worker] 283956.176:0020:0024:info:vkd3d-proton:vkd3d_pipeline_library_init_disk_cache: Remapping VKD3D_SHADER_CACHE to: vkd3d-proton.cache.
[worker] 283956.176:0020:0024:info:vkd3d-proton:vkd3d_pipeline_library_init_disk_cache: Attempting to load disk cache from: vkd3d-proton.cache.
[worker] 15:45:58.530  [host] DRED settings unavailable (settings1=0x80004002, settings=0x80004002)
[worker] 15:45:58.530  [pure] standalone D3D12 device ready; no swapchain or carrier modules
[worker] 283956.176:0020:0158:info:vkd3d-proton:vkd3d_pipeline_library_disk_thread_main: Performing async setup of stream archive ...
[worker] 283956.176:0020:0158:info:vkd3d-proton:vkd3d_pipeline_library_disk_cache_merge: No write cache exists. No need to merge any disk caches.
[worker] 283956.177:0020:0158:info:vkd3d-proton:vkd3d_pipeline_library_disk_cache_initial_setup: Merging pipeline libraries took 0.236 ms.
[worker] 283956.177:0020:0158:info:vkd3d-proton:vkd3d_pipeline_library_disk_cache_initial_setup: Failed to map read-only cache: vkd3d-proton.cache.
[worker] 283956.177:0020:0158:info:vkd3d-proton:vkd3d_pipeline_library_disk_thread_main: Done performing async setup of stream archive.
[worker] 0024:fixme:d3dkmt:NtGdiDdDDIQueryAdapterInfo type 48 not handled.
[worker] 0024:fixme:d3dkmt:NtGdiDdDDIQueryAdapterInfo type 48 not handled.
[worker] 0024:fixme:cryptasn:CryptDecodeObjectEx Unsupported decoder for lpszStructType 1.3.6.1.4.1.311.2.1.4
[worker] 0024:fixme:cryptasn:CryptDecodeObjectEx Unsupported decoder for lpszStructType 1.3.6.1.4.1.311.2.1.4
[worker] err:   readMonitorEdidFromKey: Failed to get EDID reg key size
[worker] err:   DXGI: Failed to parse display metadata + colorimetry info, using blank.
[worker] err:   readMonitorEdidFromKey: Failed to get EDID reg key size
[worker] err:   DXGI: Failed to parse display metadata + colorimetry info, using blank.
[worker] 0024:fixme:d3dkmt:NtGdiDdDDIQueryAdapterInfo type 48 not handled.
[worker] 15:45:58.836  [host] NVSDK_NGX_D3D12_Init -> 0x00000001 (Success)
[worker] 15:45:58.836  [arch] patch installed: 1 cards cached, architecture 0x190 (spoofed to the DLL's accepted value)
[worker] 15:45:58.931  [pure] direct DLSSNR Init_Ext -> 0x00000001 (Success)
[worker] 15:45:58.931  [video] stream 2560x1440, LIVE (unbounded), warmup=2
[worker] 15:45:59.193  [pure] direct feature 18 ready: 2560x1440 preset=2 result=0x00000001
[worker] 283956.868:0020:0024:fixme:vkd3d-proton:vkd3d_texture_view_desc_fixup: Remapping 2D to 2D_ARRAY. Needs Vulkan spec tightening to match D3D12 properly.
[worker] 15:45:59.235  [pure] direct feature 18 confirmed after 2 discarded warmup frames
[worker] 15:45:59.256  [video] delivered frame 1 (live)
[worker] 15:45:59.315  [video] delivered frame 2 (live)
[worker] 15:45:59.364  [video] delivered frame 3 (live)
[worker] 15:46:00.686  [video] delivered frame 30 (live)
[worker] 15:46:02.180  [video] delivered frame 60 (live)
[worker] 15:46:03.909  [video] delivered frame 90 (live)
[worker] 15:46:05.521  [video] delivered frame 120 (live)

```
