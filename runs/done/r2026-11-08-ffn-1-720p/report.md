# run r2026-11-08-ffn-1-720p

runner `005dd2c6ea9e` · entry `port-profile` · env from policy: none

`bash tools/port_profile.sh 1280 720`

exit **0** after 3.8s

gpu before: WARN (resident but not contending: signal-desktop (pid 18889, 151.0 MiB); resident but not contending: chromium (pid 18945, 60.0 MiB); resident but not contending: msedge (pid 54723, 342.0 MiB)); after: WARN (resident but not contending: signal-desktop (pid 18889, 151.0 MiB); resident but not contending: chromium (pid 18945, 60.0 MiB); resident but not contending: msedge (pid 54723, 342.0 MiB))

```
mmv_ptx 288x1024->1024 f5 s4
     0.089 ms    1.4%  ffn_ptx 16128x128 e4 r4
     0.089 ms    1.4%  qkv_ptx 286w x4 K128
     0.086 ms    1.4%  qkv_ptx 273w x4 K128
     0.085 ms    1.4%  qkv_ptx 264w x4 K128
     0.082 ms    1.3%  qkv_ptx 1075w x2 K64
     0.082 ms    1.3%  qkv_ptx 1008w x2 K64
     0.082 ms    1.3%  block32_ptx 4116w f66
     0.081 ms    1.3%  qkv_ptx 1050w x2 K64
     0.080 ms    1.3%  qkv_ptx 1032w x2 K64
     0.080 ms    1.3%  block32_ptx 4032w f130
     0.080 ms    1.3%  qkv_ptx 252w x4 K128
     0.078 ms    1.3%  ffn_ptx 64512x64 e2 r4
     0.078 ms    1.3%  block32_ptx 4116w f2
     0.076 ms    1.2%  block32_ptx 4032w f2
     0.066 ms    1.1%  global_attention_stream_ptx 288t x32
     0.053 ms    0.9%  global_normalize_ptx 288t x32
     0.051 ms    0.8%  upsampleResidual
     0.021 ms    0.3%  gemm_ptx 64512x64->64 f13
     0.018 ms    0.3%  downsample2x
     0.016 ms    0.3%  gemm_ptx 16128x128->128 f13
     0.015 ms    0.2%  gemm_ptx 64512x64->64 f5

by stage:
     0.361 ms    5.8%  block 0 c32
     0.293 ms    4.7%  block 70 c32
     0.125 ms    2.0%  block 32 vit
     0.124 ms    2.0%  block 31 vit
     0.121 ms    2.0%  block 33 vit
     0.116 ms    1.9%  block 34 vit
     0.113 ms    1.8%  block 36 vit
     0.113 ms    1.8%  block 35 vit
     0.113 ms    1.8%  block 38 vit
     0.112 ms    1.8%  block 37 vit
     0.104 ms    1.7%  block 8 c64
     0.100 ms    1.6%  block 14 c128
     0.099 ms    1.6%  block 65 c64
     0.095 ms    1.5%  block 61 c128
     0.085 ms    1.4%  block 63 c64
     0.084 ms    1.4%  block 6 c64
     0.084 ms    1.4%  block 64 c64
     0.084 ms    1.4%  block 10 c128
     0.083 ms    1.3%  block 59 c128
     0.083 ms    1.3%  block 7 c64
     0.083 ms    1.3%  block 60 c128
     0.083 ms    1.3%  block 12 c128
     0.083 ms    1.3%  block 57 c128
     0.082 ms    1.3%  block 4 c32
     0.082 ms    1.3%  block 11 c128
     0.081 ms    1.3%  block 58 c128
     0.080 ms    1.3%  block 5 c64
     0.080 ms    1.3%  block 13 c128
     0.080 ms    1.3%  block 62 c64
     0.080 ms    1.3%  block 66 c32
     0.079 ms    1.3%  block 67 c32
     0.078 ms    1.3%  block 2 c32
     0.078 ms    1.3%  block 69 c32
     0.076 ms    1.2%  block 68 c32
     0.076 ms    1.2%  block 1 c32
     0.076 ms    1.2%  block 3 c32
     0.073 ms    1.2%  block 9 c128
     0.073 ms    1.2%  block 56 c128
     0.071 ms    1.1%  block 16 c256
     0.071 ms    1.1%  block 22 c256
     0.071 ms    1.1%  block 53 c256
     0.071 ms    1.1%  block 55 c256
     0.070 ms    1.1%  block 15 c256
     0.070 ms    1.1%  block 18 c256
     0.070 ms    1.1%  block 20 c256
     0.070 ms    1.1%  block 48 c256
     0.070 ms    1.1%  block 51 c256
     0.069 ms    1.1%  block 49 c256
     0.068 ms    1.1%  block 17 c256
     0.068 ms    1.1%  block 54 c256
     0.068 ms    1.1%  block 21 c256
     0.068 ms    1.1%  block 52 c256
     0.067 ms    1.1%  block 19 c256
     0.067 ms    1.1%  block 30 split512
     0.065 ms    1.1%  block 50 c256
     0.065 ms    1.1%  block 45 split512
     0.064 ms    1.0%  block 24 split512
     0.064 ms    1.0%  block 23 split512
     0.063 ms    1.0%  block 28 split512
     0.063 ms    1.0%  block 26 split512
     0.063 ms    1.0%  block 47 split512
     0.063 ms    1.0%  block 41 split512
     0.062 ms    1.0%  block 43 split512
     0.062 ms    1.0%  block 42 split512
     0.062 ms    1.0%  block 40 split512
     0.061 ms    1.0%  block 27 split512
     0.061 ms    1.0%  block 44 split512
     0.060 ms    1.0%  block 46 split512
     0.060 ms    1.0%  block 29 split512
     0.059 ms    1.0%  block 25 split512
     0.032 ms    0.5%  transition ->62
     0.024 ms    0.4%  transition 39
     0.019 ms    0.3%  transition ->56
     0.018 ms    0.3%  transition 8
     0.017 ms    0.3%  transition ->48
     0.014 ms    0.2%  transition 14
     0.013 ms    0.2%  transition 22
     0.013 ms    0.2%  transition 30-31
     0.013 ms    0.2%  transition 4-5
     0.009 ms    0.1%  transition ->66

```

stderr:

```

```
