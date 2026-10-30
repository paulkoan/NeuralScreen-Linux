# run r2026-10-30-o

runner `e44571d7dd12` · entry `ngx-old` · env from policy: DISPLAY, NS_NR_PRESET, NS_WORKER_CMD

`uv run python -m minimal --frames 120 --headless --source synthetic --size 2560x1440 --save-after ngx-old-120.png --worker-log`

exit **0** after 11.1s

```
source synthetic  capture 2560x1440  ->  work 2560x1440 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: bash /opt/neuralscreen/state/repo/native/run_worker.sh --prefix /opt/neuralscreen/wine
version: repo 5847809 (+14 uncommitted) · worker reports no stamp · unknown — the worker reports no stamp (not the native mode, or not rebuilt)
frame 0 is the worker's warm-up: the window stays black until its first answer lands
pygame 2.6.1 (SDL 2.28.4, Python 3.11.15)
Hello from the pygame community. https://www.pygame.org/contribute.html
frames: 120 done, 0 skipped, 9.479s (12.66 fps headline, 17.52 fps steady), worker exit 0
timing: capture 3.5ms  send 35.0ms  recv 34.9ms  display 3.3ms   (mean 76.7ms/frame, 13.0 fps; median 57.1ms/frame, 17.5 fps steady)
send spread: min 10.8  median 16.1  max 2307.7 ms at frame 0 of 120   (one-off at frame 0 — the worker's warm-up, not a per-frame cost)
recv spread: min 29.0  median 34.3  max 61.9 ms at frame 0 of 120   (one-off at frame 0 — the worker's warm-up, not a per-frame cost)
worker clock: 119 frames in 6.84s = 57.48 ms/frame (17 fps, from the worker's own timestamps)
  after  -> ngx-old-120.png

```

stderr:

```
 supports VK_EXT_descriptor_buffer!
[worker] 283939.705:0020:0024:info:vkd3d-proton:vkd3d_bindless_state_add_binding: Device supports VK_EXT_descriptor_buffer!
[worker] 283939.851:0020:0024:info:vkd3d-proton:d3d12_device_caps_init_shader_model: Enabling support for SM 6.6.
[worker] 283939.851:0020:0024:info:vkd3d-proton:d3d12_device_caps_init_shader_model: Enabling support for SM 6.7.
[worker] 283939.851:0020:0024:info:vkd3d-proton:d3d12_device_caps_init_shader_model: Enabling support for SM 6.8.
[worker] 283939.851:0020:0024:fixme:vkd3d-proton:d3d12_device_caps_init_feature_options1: TotalLaneCount = 7680, may be inaccurate.
[worker] 283939.851:0020:0024:info:vkd3d-proton:d3d12_device_determine_ray_tracing_tier: DXR support enabled.
[worker] 283939.851:0020:0024:info:vkd3d-proton:d3d12_device_determine_ray_tracing_tier: DXR 1.1 support enabled.
[worker] 283939.851:0020:0024:info:vkd3d-proton:d3d12_device_caps_init_feature_level: DX Ultimate supported!
[worker] 283939.851:0020:0024:info:vkd3d-proton:vkd3d_pipeline_library_init_disk_cache: Remapping VKD3D_SHADER_CACHE to: vkd3d-proton.cache.
[worker] 283939.851:0020:0024:info:vkd3d-proton:vkd3d_pipeline_library_init_disk_cache: Attempting to load disk cache from: vkd3d-proton.cache.
[worker] 15:45:42.206  [host] DRED settings unavailable (settings1=0x80004002, settings=0x80004002)
[worker] 15:45:42.206  [pure] standalone D3D12 device ready; no swapchain or carrier modules
[worker] 283939.852:0020:0154:info:vkd3d-proton:vkd3d_pipeline_library_disk_thread_main: Performing async setup of stream archive ...
[worker] 283939.852:0020:0154:info:vkd3d-proton:vkd3d_pipeline_library_disk_cache_merge: No write cache exists. No need to merge any disk caches.
[worker] 283939.852:0020:0154:info:vkd3d-proton:vkd3d_pipeline_library_disk_cache_initial_setup: Merging pipeline libraries took 0.118 ms.
[worker] 283939.852:0020:0154:info:vkd3d-proton:vkd3d_pipeline_library_disk_cache_initial_setup: Failed to map read-only cache: vkd3d-proton.cache.
[worker] 283939.852:0020:0154:info:vkd3d-proton:vkd3d_pipeline_library_disk_thread_main: Done performing async setup of stream archive.
[worker] 0024:fixme:d3dkmt:NtGdiDdDDIQueryAdapterInfo type 48 not handled.
[worker] 0024:fixme:d3dkmt:NtGdiDdDDIQueryAdapterInfo type 48 not handled.
[worker] 0024:fixme:cryptasn:CryptDecodeObjectEx Unsupported decoder for lpszStructType 1.3.6.1.4.1.311.2.1.4
[worker] 0024:fixme:cryptasn:CryptDecodeObjectEx Unsupported decoder for lpszStructType 1.3.6.1.4.1.311.2.1.4
[worker] err:   readMonitorEdidFromKey: Failed to get EDID reg key size
[worker] err:   DXGI: Failed to parse display metadata + colorimetry info, using blank.
[worker] err:   readMonitorEdidFromKey: Failed to get EDID reg key size
[worker] err:   DXGI: Failed to parse display metadata + colorimetry info, using blank.
[worker] 0024:fixme:d3dkmt:NtGdiDdDDIQueryAdapterInfo type 48 not handled.
[worker] 15:45:42.395  [host] NVSDK_NGX_D3D12_Init -> 0x00000001 (Success)
[worker] 15:45:42.396  [arch] patch installed: 1 cards cached, architecture 0x190 (spoofed to the DLL's accepted value)
[worker] 15:45:42.479  [pure] direct DLSSNR Init_Ext -> 0x00000001 (Success)
[worker] 15:45:42.479  [video] stream 2560x1440, LIVE (unbounded), warmup=2
[worker] 15:45:42.821  [pure] direct feature 18 ready: 2560x1440 preset=1 result=0x00000001
[worker] 283940.495:0020:0024:fixme:vkd3d-proton:vkd3d_texture_view_desc_fixup: Remapping 2D to 2D_ARRAY. Needs Vulkan spec tightening to match D3D12 properly.
[worker] 15:45:42.869  [pure] direct feature 18 confirmed after 2 discarded warmup frames
[worker] 15:45:42.893  [video] delivered frame 1 (live)
[worker] 15:45:42.954  [video] delivered frame 2 (live)
[worker] 15:45:43.002  [video] delivered frame 3 (live)
[worker] 15:45:44.543  [video] delivered frame 30 (live)
[worker] 15:45:46.168  [video] delivered frame 60 (live)
[worker] 15:45:47.896  [video] delivered frame 90 (live)
[worker] 15:45:49.733  [video] delivered frame 120 (live)

```
