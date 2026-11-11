# run r2026-11-11-3-profile-small-1080p

runner `415e2181914a` · entry `port-profile-small` · env from policy: NEURALSCREEN_MODEL_DIR

policy `92cc2c01922f` at /opt/neuralscreen/policy.toml · the file itself is beside this report as policy.toml

`bash tools/port_profile.sh 1920 1080`

exit **0** after 3.9s

gpu before: WARN [util 0% of the 25% bar] (resident but not contending: Telegram (pid 16290, 30.0 MiB); resident but not contending: signal-desktop (pid 18889, 156.0 MiB); resident but not contending: msedge (pid 1300500, 293.0 MiB); resident but not contending: chromium (pid 3132450, 235.0 MiB)); after: WARN [util 0% of the 25% bar] (resident but not contending: Telegram (pid 16290, 30.0 MiB); resident but not contending: signal-desktop (pid 18889, 156.0 MiB); resident but not contending: msedge (pid 1300500, 293.0 MiB); resident but not contending: chromium (pid 3132450, 234.0 MiB))

```
binary: /opt/neuralscreen/port/build/dlss5vk
model:  /opt/neuralscreen/model-small
size:   1920x1080, minimum of 7 frames per dispatch

maxComputeSharedMemorySize 49152 bytes
400 trivial dispatches + barriers: 0.411 ms (1.03 us each)
total 3.438 ms (sum of per-dispatch spans, 1920x1080), 125 dispatches, a barrier after every launch
production schedule (counter chaining): 125 dispatches, GPU 3.538 ms (min of 7, same graph and size, no client in the loop)
  the gap between the two totals is what a barrier per dispatch costs; what is left is the dispatches themselves

by kernel:
     0.354 ms   10.3%  block32_ptx 34560w f74
     0.339 ms    9.9%  block32_ptx 34945w f48
     0.243 ms    7.1%  gemmv_ptx 640x4096->1024 f5 s4
     0.241 ms    7.0%  gemmv_ptx 640x1024->4096 f6
     0.230 ms    6.7%  gemmv_ptx 640x1024->3072 f8 s2
     0.154 ms    4.5%  ffn_ptx 8640x256 e8 r4
     0.131 ms    3.8%  gemmv_ptx 640x1024->1024 f5 s4
     0.105 ms    3.1%  ffn_ptx 138240x64 e2 r4 +proj
     0.091 ms    2.6%  block32_ptx 8712w f130
     0.089 ms    2.6%  block32_ptx 8833w f66
     0.089 ms    2.6%  global_attention_stream_ptx 640t x32
     0.087 ms    2.5%  qkv_ptx 40w x16 K512
     0.085 ms    2.5%  ffn_ptx 138240x64 e2 r4
     0.085 ms    2.5%  block32_ptx 8640w f2
     0.085 ms    2.5%  block32_ptx 8760w f2
     0.084 ms    2.5%  ffn_ptx 34560x128 e4 r4 +proj
     0.077 ms    2.2%  ffn_ptx 34560x128 e4 r4
     0.063 ms    1.8%  gemmv_ptx 2160x512->512 f5
     0.056 ms    1.6%  global_normalize_ptx 640t x32
     0.050 ms    1.5%  qkv_ptx 2257w x2 K64
     0.050 ms    1.4%  qkv_ptx 2220w x2 K64
     0.049 ms    1.4%  qkv_ptx 2196w x2 K64
     0.049 ms    1.4%  upsampleResidual
     0.045 ms    1.3%  qkv_ptx 2160w x2 K64
     0.036 ms    1.0%  gemm_mlp 2160x64->256->64 x8
     0.035 ms    1.0%  gemmv_ptx 2160x512->512 f4
     0.031 ms    0.9%  qkv_ptx 558w x4 K128
     0.031 ms    0.9%  qkv_ptx 589w x4 K128
     0.031 ms    0.9%  qkv_ptx 570w x4 K128
     0.029 ms    0.8%  qkv_ptx 540w x4 K128
     0.028 ms    0.8%  gemmv_ptx 8640x256->256 f5
     0.024 ms    0.7%  qkv_ptx 160w x8 K256
     0.023 ms    0.7%  qkv_ptx 144w x8 K256
     0.023 ms    0.7%  qkv_ptx 150w x8 K256
     0.023 ms    0.7%  gemm_ptx 138240x64->64 f13
     0.022 ms    0.7%  qkv_ptx 135w x8 K256
     0.017 ms    0.5%  gemm_ptx 138240x64->64 f5
     0.016 ms    0.5%  gemm_ptx 34560x128->128 f13
     0.015 ms    0.4%  gemmt_ptx 640x1024->512 f0 p256 s4
     0.015 ms    0.4%  downsample2x

by stage:
     0.354 ms   10.3%  block 0 c32
     0.339 ms    9.9%  block 70 c32
     0.126 ms    3.7%  block 14 vit
     0.125 ms    3.6%  block 13 vit
     0.124 ms    3.6%  block 4 c64
     0.124 ms    3.6%  block 17 vit
     0.124 ms    3.6%  block 16 vit
     0.123 ms    3.6%  block 18 vit
     0.123 ms    3.6%  block 11 vit
     0.122 ms    3.6%  block 12 vit
     0.122 ms    3.5%  block 15 vit
     0.121 ms    3.5%  block 27 c64
     0.092 ms    2.7%  block 26 c64
     0.091 ms    2.6%  block 28 c32
     0.089 ms    2.6%  block 2 c32
     0.089 ms    2.6%  block 6 c128
     0.087 ms    2.5%  block 3 c64
     0.085 ms    2.5%  block 25 c128
     0.085 ms    2.5%  block 1 c32
     0.085 ms    2.5%  block 29 c32
     0.075 ms    2.2%  block 8 c256
     0.071 ms    2.1%  block 22 c256
     0.071 ms    2.1%  block 23 c256
     0.071 ms    2.1%  block 7 c256
     0.069 ms    2.0%  block 5 c128
     0.068 ms    2.0%  block 24 c128
     0.059 ms    1.7%  block 9 split512
     0.058 ms    1.7%  block 10 split512
     0.058 ms    1.7%  block 20 split512
     0.056 ms    1.6%  block 21 split512
     0.032 ms    0.9%  transition ->26
     0.023 ms    0.7%  transition 19
     0.019 ms    0.5%  transition ->24
     0.016 ms    0.5%  transition 4
     0.014 ms    0.4%  transition 4-5
     0.013 ms    0.4%  transition ->22
     0.010 ms    0.3%  transition 6
     0.010 ms    0.3%  transition ->28
     0.009 ms    0.3%  transition 10-11
     0.008 ms    0.2%  transition 8

```

stderr:

```

```
