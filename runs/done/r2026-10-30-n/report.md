# run r2026-10-30-n

runner `e44571d7dd12` · entry `ngx-old` · env from policy: DISPLAY, NS_NR_PRESET, NS_WORKER_CMD

`uv run python -m minimal --frames 3 --headless --source synthetic --size 2560x1440 --save-after ngx-old.png --worker-log`

exit **0** after 4.2s

```
source synthetic  capture 2560x1440  ->  work 2560x1440 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: bash /opt/neuralscreen/state/repo/native/run_worker.sh --prefix /opt/neuralscreen/wine
version: repo 4df23db (+13 uncommitted) · worker reports no stamp · unknown — the worker reports no stamp (not the native mode, or not rebuilt)
frame 0 is the worker's warm-up: the window stays black until its first answer lands
pygame 2.6.1 (SDL 2.28.4, Python 3.11.15)
Hello from the pygame community. https://www.pygame.org/contribute.html
frames: 3 done, 0 skipped, 2.673s (1.12 fps headline, 18.36 fps steady), worker exit 0
timing: capture 4.9ms  send 772.1ms  recv 40.0ms  display 2.6ms   (mean 819.6ms/frame, 1.2 fps; median 54.5ms/frame, 18.4 fps steady)
worker clock: 2 frames in 0.11s = 55.0 ms/frame (18 fps, from the worker's own timestamps)
  after  -> ngx-old.png

```

stderr:

```
descriptor_type.
[worker] 283659.610:0020:0024:info:vkd3d-proton:vkd3d_bindless_state_add_binding: Device supports VK_EXT_descriptor_buffer!
[worker] 283659.610:0020:0024:info:vkd3d-proton:vkd3d_bindless_state_add_binding: Device supports VK_EXT_descriptor_buffer!
[worker] 283659.610:0020:0024:info:vkd3d-proton:vkd3d_bindless_state_add_binding: Device supports VK_EXT_descriptor_buffer!
[worker] 283659.757:0020:0024:info:vkd3d-proton:d3d12_device_caps_init_shader_model: Enabling support for SM 6.6.
[worker] 283659.757:0020:0024:info:vkd3d-proton:d3d12_device_caps_init_shader_model: Enabling support for SM 6.7.
[worker] 283659.757:0020:0024:info:vkd3d-proton:d3d12_device_caps_init_shader_model: Enabling support for SM 6.8.
[worker] 283659.757:0020:0024:fixme:vkd3d-proton:d3d12_device_caps_init_feature_options1: TotalLaneCount = 7680, may be inaccurate.
[worker] 283659.757:0020:0024:info:vkd3d-proton:d3d12_device_determine_ray_tracing_tier: DXR support enabled.
[worker] 283659.757:0020:0024:info:vkd3d-proton:d3d12_device_determine_ray_tracing_tier: DXR 1.1 support enabled.
[worker] 283659.757:0020:0024:info:vkd3d-proton:d3d12_device_caps_init_feature_level: DX Ultimate supported!
[worker] 283659.757:0020:0024:info:vkd3d-proton:vkd3d_pipeline_library_init_disk_cache: Remapping VKD3D_SHADER_CACHE to: vkd3d-proton.cache.
[worker] 283659.757:0020:0024:info:vkd3d-proton:vkd3d_pipeline_library_init_disk_cache: Attempting to load disk cache from: vkd3d-proton.cache.
[worker] 15:41:02.112  [host] DRED settings unavailable (settings1=0x80004002, settings=0x80004002)
[worker] 15:41:02.112  [pure] standalone D3D12 device ready; no swapchain or carrier modules
[worker] 283659.758:0020:0154:info:vkd3d-proton:vkd3d_pipeline_library_disk_thread_main: Performing async setup of stream archive ...
[worker] 283659.758:0020:0154:info:vkd3d-proton:vkd3d_pipeline_library_disk_cache_merge: No write cache exists. No need to merge any disk caches.
[worker] 283659.758:0020:0154:info:vkd3d-proton:vkd3d_pipeline_library_disk_cache_initial_setup: Merging pipeline libraries took 0.185 ms.
[worker] 283659.758:0020:0154:info:vkd3d-proton:vkd3d_pipeline_library_disk_cache_initial_setup: Failed to map read-only cache: vkd3d-proton.cache.
[worker] 283659.758:0020:0154:info:vkd3d-proton:vkd3d_pipeline_library_disk_thread_main: Done performing async setup of stream archive.
[worker] 0024:fixme:d3dkmt:NtGdiDdDDIQueryAdapterInfo type 48 not handled.
[worker] 0024:fixme:d3dkmt:NtGdiDdDDIQueryAdapterInfo type 48 not handled.
[worker] 0024:fixme:cryptasn:CryptDecodeObjectEx Unsupported decoder for lpszStructType 1.3.6.1.4.1.311.2.1.4
[worker] 0024:fixme:cryptasn:CryptDecodeObjectEx Unsupported decoder for lpszStructType 1.3.6.1.4.1.311.2.1.4
[worker] err:   readMonitorEdidFromKey: Failed to get EDID reg key size
[worker] err:   DXGI: Failed to parse display metadata + colorimetry info, using blank.
[worker] err:   readMonitorEdidFromKey: Failed to get EDID reg key size
[worker] err:   DXGI: Failed to parse display metadata + colorimetry info, using blank.
[worker] 0024:fixme:d3dkmt:NtGdiDdDDIQueryAdapterInfo type 48 not handled.
[worker] 15:41:02.295  [host] NVSDK_NGX_D3D12_Init -> 0x00000001 (Success)
[worker] 15:41:02.296  [arch] patch installed: 1 cards cached, architecture 0x190 (spoofed to the DLL's accepted value)
[worker] 15:41:02.378  [pure] direct DLSSNR Init_Ext -> 0x00000001 (Success)
[worker] 15:41:02.378  [video] stream 2560x1440, LIVE (unbounded), warmup=2
[worker] 15:41:02.695  [pure] direct feature 18 ready: 2560x1440 preset=1 result=0x00000001
[worker] 283660.370:0020:0024:fixme:vkd3d-proton:vkd3d_texture_view_desc_fixup: Remapping 2D to 2D_ARRAY. Needs Vulkan spec tightening to match D3D12 properly.
[worker] 15:41:02.744  [pure] direct feature 18 confirmed after 2 discarded warmup frames
[worker] 15:41:02.765  [video] delivered frame 1 (live)
[worker] 15:41:02.824  [video] delivered frame 2 (live)
[worker] 15:41:02.875  [video] delivered frame 3 (live)

```
