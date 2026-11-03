# run r2026-11-03-profile

runner `005dd2c6ea9e` · entry `port-profile` · env from policy: none

`bash tools/port_profile.sh`

exit **0** after 4.6s

gpu before: WARN (resident but not contending: chromium (pid 43069, 220.0 MiB); resident but not contending: signal-desktop (pid 43509, 61.0 MiB); resident but not contending: msedge (pid 73501, 229.0 MiB); resident but not contending: Telegram (pid 988444, 36.0 MiB); resident but not contending: shelly-ui (pid 1045732, 46.0 MiB); resident but not contending: signon-ui (pid 3062205, 17.0 MiB)) after waiting 15s; after: BUSY (utilization 93%; chromium (pid 43069, 220.0 MiB); signal-desktop (pid 43509, 61.0 MiB); msedge (pid 73501, 229.0 MiB); Telegram (pid 988444, 36.0 MiB); shelly-ui (pid 1045732, 46.0 MiB); signon-ui (pid 3062205, 17.0 MiB))

```
global_attention_stream_ptx 960t x32
     0.161 ms    1.6%  qkv_ptx 3680w x2 K64
     0.154 ms    1.6%  qkv_ptx 984w x4 K128
     0.151 ms    1.6%  qkv_ptx 3807w x2 K64
     0.148 ms    1.5%  block32_ptx 14720w f130
     0.148 ms    1.5%  block32_ptx 14880w f66
     0.147 ms    1.5%  qkv_ptx 960w x4 K128
     0.146 ms    1.5%  gemmv_ptx 3840x512->512 f4
     0.146 ms    1.5%  qkv_ptx 77w x16 K512
     0.146 ms    1.5%  ffn_ptx 58880x128 e4 r4
     0.146 ms    1.5%  qkv_ptx 943w x4 K128
     0.142 ms    1.5%  block32_ptx 14880w f2
     0.141 ms    1.4%  qkv_ptx 920w x4 K128
     0.140 ms    1.4%  block32_ptx 14720w f2
     0.138 ms    1.4%  qkv_ptx 70w x16 K512
     0.135 ms    1.4%  qkv_ptx 66w x16 K512
     0.131 ms    1.3%  gemmv_ptx 960x1024->1024 f5 s4
     0.127 ms    1.3%  qkv_ptx 60w x16 K512
     0.081 ms    0.8%  global_normalize_ptx 960t x32
     0.078 ms    0.8%  upsampleResidual
     0.055 ms    0.6%  gemm_ptx 235520x64->64 f13
     0.029 ms    0.3%  downsample2x

by stage:
     0.617 ms    6.3%  block 0 c32
     0.571 ms    5.9%  block 70 c32
     0.225 ms    2.3%  block 8 c64
     0.198 ms    2.0%  block 65 c64
     0.167 ms    1.7%  block 14 c128
     0.167 ms    1.7%  block 5 c64
     0.166 ms    1.7%  block 62 c64
     0.164 ms    1.7%  block 7 c64
     0.163 ms    1.7%  block 6 c64
     0.163 ms    1.7%  block 64 c64
     0.160 ms    1.6%  block 63 c64
     0.160 ms    1.6%  block 61 c128
     0.148 ms    1.5%  block 66 c32
     0.148 ms    1.5%  block 4 c32
     0.143 ms    1.5%  block 67 c32
     0.142 ms    1.5%  block 2 c32
     0.142 ms    1.5%  block 69 c32
     0.142 ms    1.5%  block 59 c128
     0.142 ms    1.5%  block 68 c32
     0.142 ms    1.5%  block 10 c128
     0.141 ms    1.4%  block 3 c32
     0.141 ms    1.4%  block 31 vit
     0.140 ms    1.4%  block 1 c32
     0.140 ms    1.4%  block 57 c128
     0.140 ms    1.4%  block 11 c128
     0.139 ms    1.4%  block 60 c128
     0.139 ms    1.4%  block 12 c128
     0.138 ms    1.4%  block 58 c128
     0.138 ms    1.4%  block 13 c128
     0.137 ms    1.4%  block 35 vit
     0.137 ms    1.4%  block 38 vit
     0.137 ms    1.4%  block 33 vit
     0.137 ms    1.4%  block 36 vit
     0.136 ms    1.4%  block 34 vit
     0.136 ms    1.4%  block 37 vit
     0.136 ms    1.4%  block 32 vit
     0.121 ms    1.2%  block 56 c128
     0.121 ms    1.2%  block 9 c128
     0.116 ms    1.2%  block 16 c256
     0.115 ms    1.2%  block 53 c256
     0.114 ms    1.2%  block 49 c256
     0.113 ms    1.2%  block 48 c256
     0.113 ms    1.2%  block 22 c256
     0.112 ms    1.1%  block 54 c256
     0.111 ms    1.1%  block 21 c256
     0.111 ms    1.1%  block 50 c256
     0.111 ms    1.1%  block 17 c256
     0.110 ms    1.1%  block 20 c256
     0.109 ms    1.1%  block 51 c256
     0.109 ms    1.1%  block 15 c256
     0.109 ms    1.1%  block 19 c256
     0.109 ms    1.1%  block 52 c256
     0.108 ms    1.1%  block 18 c256
     0.108 ms    1.1%  block 55 c256
     0.079 ms    0.8%  block 28 split512
     0.079 ms    0.8%  block 24 split512
     0.079 ms    0.8%  block 41 split512
     0.079 ms    0.8%  block 30 split512
     0.078 ms    0.8%  block 45 split512
     0.077 ms    0.8%  block 47 split512
     0.077 ms    0.8%  block 43 split512
     0.076 ms    0.8%  block 46 split512
     0.076 ms    0.8%  block 42 split512
     0.076 ms    0.8%  block 29 split512
     0.076 ms    0.8%  block 26 split512
     0.075 ms    0.8%  block 25 split512
     0.075 ms    0.8%  block 23 split512
     0.074 ms    0.8%  block 40 split512
     0.074 ms    0.8%  block 44 split512
     0.073 ms    0.8%  block 27 split512
     0.050 ms    0.5%  transition ->62
     0.030 ms    0.3%  transition 8
     0.029 ms    0.3%  transition ->56
     0.021 ms    0.2%  transition 4-5
     0.019 ms    0.2%  transition ->48
     0.018 ms    0.2%  transition 39
     0.015 ms    0.2%  transition 14
     0.015 ms    0.2%  transition ->66
     0.013 ms    0.1%  transition 22
     0.010 ms    0.1%  transition 30-31

```

stderr:

```

```
