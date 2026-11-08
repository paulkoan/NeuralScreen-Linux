# run r2026-11-08-ffn6-2-1080p-b

runner `005dd2c6ea9e` · entry `port-profile` · env from policy: none

`bash tools/port_profile.sh 1920 1080`

exit **0** after 6.1s

gpu before: BUSY (utilization 90%; signal-desktop (pid 18889, 165.0 MiB); chromium (pid 18945, 62.0 MiB); msedge (pid 54723, 342.0 MiB); DyingLightGame_TheBeast_x64_rwdi.exe (pid 3135381, 6184.0 MiB)) after waiting 298s; after: BUSY (utilization 93%; signal-desktop (pid 18889, 165.0 MiB); chromium (pid 18945, 62.0 MiB); msedge (pid 54723, 342.0 MiB); DyingLightGame_TheBeast_x64_rwdi.exe (pid 3135381, 6184.0 MiB))

```
0w x8 K256
     0.089 ms    1.0%  qkv_ptx 2220w x2 K64
     0.088 ms    1.0%  qkv_ptx 2196w x2 K64
     0.087 ms    1.0%  block32_ptx 8640w f130
     0.087 ms    1.0%  qkv_ptx 558w x4 K128
     0.087 ms    1.0%  qkv_ptx 150w x8 K256
     0.086 ms    1.0%  qkv_ptx 144w x8 K256
     0.086 ms    1.0%  ffn_ptx 34560x128 e4 r4
     0.086 ms    1.0%  qkv_ptx 570w x4 K128
     0.085 ms    1.0%  block32_ptx 8760w f66
     0.085 ms    1.0%  qkv_ptx 589w x4 K128
     0.085 ms    1.0%  qkv_ptx 135w x8 K256
     0.084 ms    1.0%  ffn_ptx 138240x64 e2 r4
     0.083 ms    1.0%  block32_ptx 8640w f2
     0.082 ms    1.0%  qkv_ptx 540w x4 K128
     0.081 ms    0.9%  global_attention_stream_ptx 640t x32
     0.080 ms    0.9%  block32_ptx 8760w f2
     0.056 ms    0.7%  global_normalize_ptx 640t x32
     0.045 ms    0.5%  upsampleResidual
     0.022 ms    0.3%  gemm_ptx 138240x64->64 f13
     0.017 ms    0.2%  gemm_ptx 138240x64->64 f5
     0.015 ms    0.2%  gemmt_ptx 640x1024->512 f0 p256 s4

by stage:
     1.508 ms   17.7%  block 70 c32
     1.296 ms   15.2%  block 8 c64
     0.352 ms    4.1%  block 0 c32
     0.131 ms    1.5%  block 34 vit
     0.121 ms    1.4%  block 36 vit
     0.121 ms    1.4%  block 35 vit
     0.120 ms    1.4%  block 33 vit
     0.120 ms    1.4%  block 32 vit
     0.119 ms    1.4%  block 38 vit
     0.119 ms    1.4%  block 37 vit
     0.118 ms    1.4%  block 31 vit
     0.110 ms    1.3%  block 65 c64
     0.100 ms    1.2%  block 63 c64
     0.098 ms    1.2%  block 6 c64
     0.096 ms    1.1%  block 64 c64
     0.094 ms    1.1%  block 14 c128
     0.092 ms    1.1%  block 61 c128
     0.092 ms    1.1%  block 7 c64
     0.090 ms    1.1%  block 5 c64
     0.087 ms    1.0%  block 66 c32
     0.087 ms    1.0%  block 62 c64
     0.085 ms    1.0%  block 4 c32
     0.083 ms    1.0%  block 2 c32
     0.083 ms    1.0%  block 1 c32
     0.082 ms    1.0%  block 67 c32
     0.082 ms    1.0%  block 10 c128
     0.081 ms    1.0%  block 3 c32
     0.081 ms    1.0%  block 11 c128
     0.081 ms    0.9%  block 57 c128
     0.081 ms    0.9%  block 60 c128
     0.080 ms    0.9%  block 59 c128
     0.080 ms    0.9%  block 68 c32
     0.080 ms    0.9%  block 69 c32
     0.080 ms    0.9%  block 12 c128
     0.079 ms    0.9%  block 58 c128
     0.079 ms    0.9%  block 13 c128
     0.072 ms    0.8%  block 56 c128
     0.071 ms    0.8%  block 9 c128
     0.069 ms    0.8%  block 22 c256
     0.069 ms    0.8%  block 48 c256
     0.068 ms    0.8%  block 20 c256
     0.068 ms    0.8%  block 16 c256
     0.068 ms    0.8%  block 49 c256
     0.067 ms    0.8%  block 15 c256
     0.066 ms    0.8%  block 50 c256
     0.066 ms    0.8%  block 21 c256
     0.066 ms    0.8%  block 53 c256
     0.066 ms    0.8%  block 17 c256
     0.066 ms    0.8%  block 19 c256
     0.065 ms    0.8%  block 51 c256
     0.065 ms    0.8%  block 18 c256
     0.065 ms    0.8%  block 54 c256
     0.065 ms    0.8%  block 55 c256
     0.064 ms    0.7%  block 52 c256
     0.057 ms    0.7%  block 40 split512
     0.056 ms    0.7%  block 23 split512
     0.055 ms    0.7%  block 46 split512
     0.055 ms    0.7%  block 44 split512
     0.055 ms    0.7%  block 25 split512
     0.055 ms    0.6%  block 42 split512
     0.055 ms    0.6%  block 41 split512
     0.055 ms    0.6%  block 47 split512
     0.055 ms    0.6%  block 26 split512
     0.055 ms    0.6%  block 24 split512
     0.054 ms    0.6%  block 30 split512
     0.054 ms    0.6%  block 43 split512
     0.054 ms    0.6%  block 29 split512
     0.053 ms    0.6%  block 28 split512
     0.053 ms    0.6%  block 27 split512
     0.053 ms    0.6%  block 45 split512
     0.029 ms    0.3%  transition ->62
     0.021 ms    0.2%  transition 39
     0.018 ms    0.2%  transition ->56
     0.015 ms    0.2%  transition 8
     0.014 ms    0.2%  transition 4-5
     0.013 ms    0.2%  transition ->48
     0.011 ms    0.1%  transition ->66
     0.011 ms    0.1%  transition 14
     0.009 ms    0.1%  transition 22
     0.008 ms    0.1%  transition 30-31

```

stderr:

```

```
