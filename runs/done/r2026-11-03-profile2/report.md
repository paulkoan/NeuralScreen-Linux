# run r2026-11-03-profile2

runner `005dd2c6ea9e` · entry `port-profile` · env from policy: none

`bash tools/port_profile.sh`

exit **0** after 6.9s

gpu before: BUSY (utilization 94%; chromium (pid 43069, 221.0 MiB); signal-desktop (pid 43509, 61.0 MiB); msedge (pid 73501, 175.0 MiB); Telegram (pid 988444, 36.0 MiB); signon-ui (pid 3062205, 17.0 MiB); DyingLightGame_TheBeast_x64_rwdi.exe (pid 2215293, 6181.0 MiB)) after waiting 298s; after: BUSY (utilization 79%; chromium (pid 43069, 221.0 MiB); signal-desktop (pid 43509, 61.0 MiB); msedge (pid 73501, 175.0 MiB); Telegram (pid 988444, 36.0 MiB); signon-ui (pid 3062205, 17.0 MiB); DyingLightGame_TheBeast_x64_rwdi.exe (pid 2215293, 6181.0 MiB))

```
 x2 K64
     0.151 ms    1.1%  global_attention_stream_ptx 960t x32
     0.147 ms    1.0%  qkv_ptx 3680w x2 K64
     0.146 ms    1.0%  block32_ptx 14880w f66
     0.145 ms    1.0%  qkv_ptx 984w x4 K128
     0.144 ms    1.0%  block32_ptx 14720w f130
     0.141 ms    1.0%  ffn_ptx 58880x128 e4 r4
     0.140 ms    1.0%  gemmv_ptx 3840x512->512 f4
     0.139 ms    1.0%  qkv_ptx 77w x16 K512
     0.139 ms    1.0%  block32_ptx 14720w f2
     0.139 ms    1.0%  qkv_ptx 943w x4 K128
     0.137 ms    1.0%  qkv_ptx 960w x4 K128
     0.137 ms    1.0%  block32_ptx 14880w f2
     0.133 ms    0.9%  qkv_ptx 920w x4 K128
     0.132 ms    0.9%  qkv_ptx 70w x16 K512
     0.129 ms    0.9%  qkv_ptx 66w x16 K512
     0.125 ms    0.9%  gemmv_ptx 960x1024->1024 f5 s4
     0.121 ms    0.9%  qkv_ptx 60w x16 K512
     0.078 ms    0.6%  global_normalize_ptx 960t x32
     0.077 ms    0.5%  upsampleResidual
     0.051 ms    0.4%  gemm_ptx 235520x64->64 f13
     0.027 ms    0.2%  gemm_ptx 235520x64->64 f5

by stage:
     1.748 ms   12.4%  block 70 c32
     1.325 ms    9.4%  block 59 c128
     1.318 ms    9.4%  block 10 c128
     1.311 ms    9.3%  block 3 c32
     0.615 ms    4.4%  block 0 c32
     0.206 ms    1.5%  block 8 c64
     0.186 ms    1.3%  block 65 c64
     0.162 ms    1.1%  block 7 c64
     0.161 ms    1.1%  block 62 c64
     0.157 ms    1.1%  block 14 c128
     0.157 ms    1.1%  block 6 c64
     0.155 ms    1.1%  block 64 c64
     0.154 ms    1.1%  block 5 c64
     0.150 ms    1.1%  block 61 c128
     0.148 ms    1.1%  block 63 c64
     0.146 ms    1.0%  block 4 c32
     0.144 ms    1.0%  block 66 c32
     0.139 ms    1.0%  block 2 c32
     0.139 ms    1.0%  block 1 c32
     0.138 ms    1.0%  block 67 c32
     0.137 ms    1.0%  block 68 c32
     0.137 ms    1.0%  block 69 c32
     0.134 ms    1.0%  block 31 vit
     0.133 ms    0.9%  block 57 c128
     0.133 ms    0.9%  block 11 c128
     0.133 ms    0.9%  block 38 vit
     0.133 ms    0.9%  block 12 c128
     0.133 ms    0.9%  block 36 vit
     0.132 ms    0.9%  block 60 c128
     0.132 ms    0.9%  block 37 vit
     0.132 ms    0.9%  block 33 vit
     0.131 ms    0.9%  block 34 vit
     0.131 ms    0.9%  block 32 vit
     0.131 ms    0.9%  block 13 c128
     0.131 ms    0.9%  block 58 c128
     0.129 ms    0.9%  block 35 vit
     0.117 ms    0.8%  block 56 c128
     0.115 ms    0.8%  block 9 c128
     0.108 ms    0.8%  block 22 c256
     0.108 ms    0.8%  block 50 c256
     0.107 ms    0.8%  block 15 c256
     0.107 ms    0.8%  block 52 c256
     0.107 ms    0.8%  block 17 c256
     0.107 ms    0.8%  block 21 c256
     0.107 ms    0.8%  block 48 c256
     0.106 ms    0.8%  block 54 c256
     0.106 ms    0.8%  block 20 c256
     0.106 ms    0.8%  block 53 c256
     0.105 ms    0.7%  block 49 c256
     0.105 ms    0.7%  block 16 c256
     0.104 ms    0.7%  block 19 c256
     0.104 ms    0.7%  block 51 c256
     0.104 ms    0.7%  block 18 c256
     0.103 ms    0.7%  block 55 c256
     0.076 ms    0.5%  block 30 split512
     0.075 ms    0.5%  block 24 split512
     0.074 ms    0.5%  block 47 split512
     0.074 ms    0.5%  block 28 split512
     0.074 ms    0.5%  block 45 split512
     0.074 ms    0.5%  block 26 split512
     0.074 ms    0.5%  block 41 split512
     0.073 ms    0.5%  block 29 split512
     0.073 ms    0.5%  block 25 split512
     0.073 ms    0.5%  block 43 split512
     0.073 ms    0.5%  block 42 split512
     0.072 ms    0.5%  block 40 split512
     0.072 ms    0.5%  block 46 split512
     0.072 ms    0.5%  block 23 split512
     0.070 ms    0.5%  block 44 split512
     0.069 ms    0.5%  block 27 split512
     0.049 ms    0.3%  transition ->62
     0.028 ms    0.2%  transition ->56
     0.026 ms    0.2%  transition 8
     0.021 ms    0.2%  transition 4-5
     0.019 ms    0.1%  transition ->48
     0.019 ms    0.1%  transition 39
     0.016 ms    0.1%  transition 14
     0.015 ms    0.1%  transition ->66
     0.011 ms    0.1%  transition 22
     0.009 ms    0.1%  transition 30-31

```

stderr:

```

```
