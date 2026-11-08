# run r2026-11-08-ffn-720p

runner `005dd2c6ea9e` · entry `port-profile` · env from policy: none

`bash tools/port_profile.sh 1280 720`

exit **0** after 3.8s

gpu before: WARN (resident but not contending: signal-desktop (pid 18889, 151.0 MiB); resident but not contending: chromium (pid 18945, 60.0 MiB); resident but not contending: msedge (pid 54723, 341.0 MiB)); after: BUSY (utilization 60%; signal-desktop (pid 18889, 151.0 MiB); chromium (pid 18945, 60.0 MiB); msedge (pid 54723, 342.0 MiB))

```
 block32_ptx 4165w f2
     0.255 ms    1.5%  block32_ptx 4080w f2
     0.254 ms    1.5%  upsampleResidual
     0.218 ms    1.3%  block32_ptx 4032w f2
     0.169 ms    1.0%  ffn_ptx 16128x128 e4 r4
     0.154 ms    0.9%  qkv_ptx 1008w x2 K64
     0.147 ms    0.9%  qkv_ptx 286w x4 K128
     0.138 ms    0.8%  qkv_ptx 273w x4 K128
     0.137 ms    0.8%  qkv_ptx 264w x4 K128
     0.137 ms    0.8%  qkv_ptx 252w x4 K128
     0.136 ms    0.8%  qkv_ptx 1075w x2 K64
     0.132 ms    0.8%  block32_ptx 4116w f66
     0.130 ms    0.8%  qkv_ptx 1032w x2 K64
     0.129 ms    0.8%  ffn_ptx 64512x64 e2 r4
     0.128 ms    0.8%  block32_ptx 4116w f2
     0.128 ms    0.8%  qkv_ptx 1050w x2 K64
     0.107 ms    0.6%  global_attention_stream_ptx 288t x32
     0.084 ms    0.5%  global_normalize_ptx 288t x32
     0.045 ms    0.3%  gemmv_ptx 288x512->1024 f4
     0.034 ms    0.2%  gemm_ptx 64512x64->64 f13
     0.033 ms    0.2%  downsample2x
     0.030 ms    0.2%  gemmt_ptx 288x1024->512 f0 p256 s4

by stage:
     2.711 ms   15.9%  block 0 c32
     1.248 ms    7.3%  block 70 c32
     0.608 ms    3.6%  block 32 vit
     0.589 ms    3.5%  block 31 vit
     0.531 ms    3.1%  block 33 vit
     0.474 ms    2.8%  block 34 vit
     0.445 ms    2.6%  block 66 c32
     0.428 ms    2.5%  block 35 vit
     0.398 ms    2.3%  block 36 vit
     0.392 ms    2.3%  block 38 vit
     0.392 ms    2.3%  block 37 vit
     0.218 ms    1.3%  block 1 c32
     0.200 ms    1.2%  block 15 c256
     0.177 ms    1.0%  block 23 split512
     0.171 ms    1.0%  block 10 c128
     0.164 ms    1.0%  block 8 c64
     0.162 ms    0.9%  block 16 c256
     0.161 ms    0.9%  block 14 c128
     0.161 ms    0.9%  transition ->62
     0.160 ms    0.9%  block 11 c128
     0.158 ms    0.9%  block 61 c128
     0.156 ms    0.9%  block 65 c64
     0.149 ms    0.9%  block 22 c256
     0.147 ms    0.9%  block 9 c128
     0.146 ms    0.9%  block 49 c256
     0.146 ms    0.9%  block 18 c256
     0.146 ms    0.9%  block 53 c256
     0.145 ms    0.9%  block 51 c256
     0.145 ms    0.9%  block 55 c256
     0.145 ms    0.9%  block 20 c256
     0.145 ms    0.8%  block 62 c64
     0.144 ms    0.8%  block 48 c256
     0.144 ms    0.8%  block 63 c64
     0.144 ms    0.8%  block 6 c64
     0.142 ms    0.8%  block 7 c64
     0.141 ms    0.8%  block 21 c256
     0.141 ms    0.8%  block 52 c256
     0.140 ms    0.8%  block 19 c256
     0.140 ms    0.8%  block 17 c256
     0.139 ms    0.8%  block 54 c256
     0.139 ms    0.8%  block 50 c256
     0.138 ms    0.8%  block 59 c128
     0.138 ms    0.8%  block 64 c64
     0.138 ms    0.8%  block 5 c64
     0.138 ms    0.8%  block 57 c128
     0.137 ms    0.8%  block 60 c128
     0.137 ms    0.8%  block 12 c128
     0.134 ms    0.8%  block 58 c128
     0.134 ms    0.8%  block 13 c128
     0.133 ms    0.8%  block 2 c32
     0.132 ms    0.8%  block 4 c32
     0.132 ms    0.8%  block 24 split512
     0.131 ms    0.8%  block 30 split512
     0.129 ms    0.8%  block 68 c32
     0.129 ms    0.8%  block 67 c32
     0.128 ms    0.8%  block 69 c32
     0.126 ms    0.7%  block 3 c32
     0.126 ms    0.7%  block 26 split512
     0.125 ms    0.7%  block 28 split512
     0.125 ms    0.7%  block 40 split512
     0.124 ms    0.7%  block 45 split512
     0.124 ms    0.7%  block 43 split512
     0.123 ms    0.7%  block 41 split512
     0.122 ms    0.7%  block 29 split512
     0.122 ms    0.7%  block 46 split512
     0.122 ms    0.7%  block 47 split512
     0.122 ms    0.7%  block 44 split512
     0.122 ms    0.7%  block 27 split512
     0.122 ms    0.7%  block 25 split512
     0.121 ms    0.7%  block 56 c128
     0.121 ms    0.7%  block 42 split512
     0.072 ms    0.4%  transition ->56
     0.055 ms    0.3%  transition 39
     0.051 ms    0.3%  transition ->48
     0.050 ms    0.3%  transition 30-31
     0.035 ms    0.2%  transition 22
     0.029 ms    0.2%  transition 8
     0.027 ms    0.2%  transition 14
     0.019 ms    0.1%  transition 4-5
     0.015 ms    0.1%  transition ->66

```

stderr:

```

```
