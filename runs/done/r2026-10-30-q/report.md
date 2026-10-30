# run r2026-10-30-q

runner `e44571d7dd12` · entry `port-build` · env from policy: none

`bash experiments/opendlss_port/rebuild.sh`

exit **0** after 9.6s

```
rebuild: /opt/neuralscreen/port <- linux-port.patch (0aabc30ec374)
port:   /opt/neuralscreen/port (9d08f41)
patch:  /opt/neuralscreen/state/repo/experiments/opendlss_port/linux-port.patch
commit: 0aabc30ec374
removed scripts/build_linux.sh (added by the patch, not tracked here)
removed shaders/composite_serve.comp (added by the patch, not tracked here)
removed shaders/proxy_expand.comp (added by the patch, not tracked here)
removed src/nr_schedule.cpp (added by the patch, not tracked here)
removed src/nr_schedule.h (added by the patch, not tracked here)
removed src/serve.cpp (added by the patch, not tracked here)
applied: 17 file(s) changed or added in /opt/neuralscreen/port
stamped: /opt/neuralscreen/port/.ns-patch-id holds 0aabc30ec374 (the build bakes it in)
next:    (cd /opt/neuralscreen/port && bash scripts/build_linux.sh)   # then: build/dlss5vk stamp
glslang: /usr/bin/glslang (Glslang Version: 11:16.6.0)
shaders -> build/shaders (15 modules)
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
stamp -> port 9d08f41, 17 modified file(s), patch 0aabc30ec374cc01893092ebb8538d537e6cd888
built /opt/neuralscreen/port/build/dlss5vk
stamp:   port 9d08f41 (17 modified) patch 0aabc30ec374cc01893092ebb8538d537e6cd888
rebuilt: /opt/neuralscreen/port/build/dlss5vk is patch 0aabc30ec374cc01893092ebb8538d537e6cd888, which is the patch applied - runs will be in sync

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
shaders/ops.comp
shaders/preprocess.comp
shaders/proxy_expand.comp
shaders/qkv_attention.comp
shaders/window_attend.comp
shaders/window_normalize.comp

```
