# run r2026-11-10-13-gap2-0-build

runner `415e2181914a` · entry `port-build` · env from policy: none

policy `92cc2c01922f` at /opt/neuralscreen/policy.toml · the file itself is beside this report as policy.toml

`bash experiments/opendlss_port/rebuild.sh`

exit **0** after 13.8s

gpu before: WARN [util 0% of the 25% bar] (resident but not contending: Telegram (pid 16290, 30.0 MiB); resident but not contending: signal-desktop (pid 18889, 155.0 MiB); resident but not contending: msedge (pid 1300500, 293.0 MiB); resident but not contending: chromium (pid 3132450, 244.0 MiB); resident but not contending: fossilize_replay (pid 279012, 42.0 MiB); resident but not contending: fossilize_replay (pid 279329, 42.0 MiB); resident but not contending: fossilize_replay (pid 279353, 42.0 MiB); resident but not contending: fossilize_replay (pid 279356, 40.0 MiB); resident but not contending: fossilize_replay (pid 279461, 44.0 MiB)); after: WARN [util 17% of the 25% bar] (resident but not contending: Telegram (pid 16290, 30.0 MiB); resident but not contending: signal-desktop (pid 18889, 155.0 MiB); resident but not contending: msedge (pid 1300500, 294.0 MiB); resident but not contending: chromium (pid 3132450, 286.0 MiB); resident but not contending: fossilize_replay (pid 280163, 38.0 MiB); resident but not contending: fossilize_replay (pid 280438, 38.0 MiB); resident but not contending: fossilize_replay (pid 280513, 38.0 MiB); resident but not contending: fossilize_replay (pid 280540, 40.0 MiB); resident but not contending: fossilize_replay (pid 280713, 34.0 MiB))

```
rebuild: /opt/neuralscreen/port <- linux-port.patch (22337d051a3a)
port:   /opt/neuralscreen/port (9d08f41)
patch:  /opt/neuralscreen/state/repo/experiments/opendlss_port/linux-port.patch
commit: 22337d051a3a
removed scripts/build_linux.sh (added by the patch, not tracked here)
removed shaders/composite_serve.comp (added by the patch, not tracked here)
removed shaders/mid_warp.comp (added by the patch, not tracked here)
removed shaders/proxy_expand.comp (added by the patch, not tracked here)
removed shaders/resize_rgba8.comp (added by the patch, not tracked here)
removed src/nr_schedule.cpp (added by the patch, not tracked here)
removed src/nr_schedule.h (added by the patch, not tracked here)
removed src/serve.cpp (added by the patch, not tracked here)
applied: 19 file(s) changed or added in /opt/neuralscreen/port
stamped: /opt/neuralscreen/port/.ns-patch-id holds 22337d051a3a (the build bakes it in)
next:    (cd /opt/neuralscreen/port && bash scripts/build_linux.sh)   # then: build/dlss5vk stamp
glslang: /usr/bin/glslang (Glslang Version: 11:16.6.0)
shaders -> build/shaders (17 modules)
mlp_e4m3_K64
mlp_e4m3_K128
mlp_e4m3_K256
qkv_e4m3_K64
qkv_e4m3_K128
qkv_e4m3_K256
qkv_e4m3_K512
gemm2_e4m3_K32_f5
gemm2_e4m3_K32_f13
gemm2_e4m3_K32_f4
gemm2_e4m3_K32_f8
gemm2_e4m3_K32_f6
gemm2_e4m3_K64_f5
gemm2_e4m3_K64_f13
gemm2_e4m3_K64_f4
gemm2_e4m3_K64_f8
gemm2_e4m3_K64_f6
gemm2_e4m3_K128_f5
gemm2_e4m3_K128_f13
gemm2_e4m3_K128_f4
gemm2_e4m3_K128_f8
gemm2_e4m3_K128_f6
gemm2_e4m3_K256_f5
gemm2_e4m3_K256_f13
gemm2_e4m3_K256_f4
gemm2_e4m3_K256_f8
gemm2_e4m3_K256_f6
gemm2_e4m3_K512_f5
gemm2_e4m3_K512_f13
gemm2_e4m3_K512_f4
gemm2_e4m3_K512_f8
gemm2_e4m3_K512_f6
gemm2_e4m3_K1024_f5
gemm2_e4m3_K1024_f13
gemm2_e4m3_K1024_f4
gemm2_e4m3_K1024_f8
gemm2_e4m3_K1024_f6
ffn_e4m3_C64_R4 25600
ffn_e4m3_C64_R4_proj 25600
ffn_e4m3_C128_R4 46080
ffn_e4m3_C128_R4_proj 46080
ffn_e4m3_C256_R3 82688
ffn_e4m3_C256_R3_proj 82688
ffn_e4m3_C256_R4 87040
ffn_e4m3_C256_R4_proj 87040
gemmt_e4m3_K4096_f1_p32_s4 24576
gemmt_e4m3_K1024_f0_p16_s2 24576
gemmt_e4m3_K1024_f1_p8_s4 24576
gemmt_e4m3_K1024_f0_p8_s4 24576
reduce_e4m3_s4_f4
reduce_e4m3_s2_f8
reduce_e4m3_s4_f8
gemmv_e4m3_K1024_f6_s1 69632
gemmv_e4m3_K1024_f6_s1_m96 36864
gemmv_e4m3_K4096_f5_s4 94208
gemmv_e4m3_K4096_f5_s4_m96 49152
gemmv_e4m3_K1024_f8_s2 69632
gemmv_e4m3_K1024_f8_s2_m96 36864
gemmv_e4m3_K1024_f5_s4 94208
gemmv_e4m3_K1024_f5_s4_m96 49152
global_attention_e4m3_p64 6656
global_attention_e4m3_p128 10752
global_attention_e4m3_p192 14848
global_attention_e4m3_p256 18944
global_normalize_e4m3 0
global_attention_stream_e4m3 20480
gemmv_e4m3_K512_f4_s1_m96 36864
gemmv_e4m3_K512_f5_s1_m96 49152
gemmv_e4m3_K512_f13_s1_m96 49152
gemmv_e4m3_K256_f5_s1_m96 49152
gemmv_e4m3_K4096_f5_s1_m96 49152
gemmv_e4m3_K1024_f8_s1_m96 36864
gemmv_e4m3_K1024_f5_s1_m96 49152
block32_e4m3_f2
block32_e4m3_f66
block32_e4m3_f74
block32_e4m3_f130
block32_e4m3_f48
PTX -> build/ptx (78 kernels)
stamp -> port 9d08f41, 19 modified file(s), patch 22337d051a3ace9c0b5bfbd8b9722ec63fd1fded
built /opt/neuralscreen/port/build/dlss5vk
stamp:   port 9d08f41 (19 modified) patch 22337d051a3ace9c0b5bfbd8b9722ec63fd1fded
rebuilt: /opt/neuralscreen/port/build/dlss5vk is patch 22337d051a3ace9c0b5bfbd8b9722ec63fd1fded, which is the patch applied - runs will be in sync

```

stderr:

```
shaders/composite_serve.comp
shaders/fused_block32.comp
shaders/gemm_f16.comp
shaders/gemm_fp8.comp
shaders/gemm_mlp.comp
shaders/gemm_reduce.comp
shaders/global_attend.comp
shaders/global_attention.comp
shaders/global_normalize.comp
shaders/mid_warp.comp
shaders/ops.comp
shaders/preprocess.comp
shaders/proxy_expand.comp
shaders/qkv_attention.comp
shaders/resize_rgba8.comp
shaders/window_attend.comp
shaders/window_normalize.comp

```
