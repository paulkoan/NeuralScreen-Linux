# run r2026-11-08-ffn4-2-1080p

runner `005dd2c6ea9e` · entry `port-profile` · env from policy: none

`bash tools/port_profile.sh 1920 1080`

exit **0** after 4.2s

gpu before: WARN (resident but not contending: signal-desktop (pid 18889, 151.0 MiB); resident but not contending: chromium (pid 18945, 60.0 MiB); resident but not contending: msedge (pid 54723, 342.0 MiB)); after: BUSY (utilization 93%; signal-desktop (pid 18889, 151.0 MiB); chromium (pid 18945, 60.0 MiB); msedge (pid 54723, 342.0 MiB))

```
4%  gemmv_ptx 8640x256->256 f5
     0.375 ms    1.3%  qkv_ptx 2160w x2 K64
     0.365 ms    1.3%  ffn_ptx 34560x128 e4 r4
     0.265 ms    0.9%  qkv_ptx 160w x8 K256
     0.264 ms    0.9%  qkv_ptx 540w x4 K128
     0.252 ms    0.9%  qkv_ptx 135w x8 K256
     0.251 ms    0.9%  qkv_ptx 558w x4 K128
     0.251 ms    0.9%  qkv_ptx 2257w x2 K64
     0.249 ms    0.9%  qkv_ptx 589w x4 K128
     0.239 ms    0.9%  qkv_ptx 570w x4 K128
     0.237 ms    0.8%  qkv_ptx 150w x8 K256
     0.235 ms    0.8%  qkv_ptx 144w x8 K256
     0.233 ms    0.8%  block32_ptx 8760w f66
     0.231 ms    0.8%  ffn_ptx 138240x64 e2 r4
     0.229 ms    0.8%  qkv_ptx 2196w x2 K64
     0.227 ms    0.8%  block32_ptx 8760w f2
     0.225 ms    0.8%  qkv_ptx 2220w x2 K64
     0.224 ms    0.8%  global_attention_stream_ptx 640t x32
     0.201 ms    0.7%  gemm_ptx 138240x64->64 f13
     0.150 ms    0.5%  global_normalize_ptx 640t x32
     0.122 ms    0.4%  gemm_ptx 34560x64->128 f4
     0.106 ms    0.4%  downsample2x

by stage:
     5.448 ms   19.4%  block 0 c32
     3.089 ms   11.0%  block 70 c32
     0.988 ms    3.5%  block 66 c32
     0.756 ms    2.7%  block 31 vit
     0.694 ms    2.5%  block 1 c32
     0.581 ms    2.1%  block 34 vit
     0.544 ms    1.9%  block 32 vit
     0.538 ms    1.9%  block 33 vit
     0.487 ms    1.7%  transition ->62
     0.469 ms    1.7%  block 35 vit
     0.463 ms    1.6%  block 37 vit
     0.462 ms    1.6%  block 38 vit
     0.457 ms    1.6%  block 36 vit
     0.427 ms    1.5%  block 8 c64
     0.393 ms    1.4%  block 67 c32
     0.379 ms    1.3%  block 9 c128
     0.356 ms    1.3%  block 5 c64
     0.341 ms    1.2%  block 6 c64
     0.312 ms    1.1%  block 63 c64
     0.263 ms    0.9%  block 23 split512
     0.263 ms    0.9%  block 65 c64
     0.262 ms    0.9%  block 15 c256
     0.253 ms    0.9%  transition ->56
     0.250 ms    0.9%  block 62 c64
     0.237 ms    0.8%  block 7 c64
     0.234 ms    0.8%  block 64 c64
     0.233 ms    0.8%  block 4 c32
     0.230 ms    0.8%  block 16 c256
     0.229 ms    0.8%  block 10 c128
     0.229 ms    0.8%  block 3 c32
     0.227 ms    0.8%  block 14 c128
     0.227 ms    0.8%  block 68 c32
     0.227 ms    0.8%  block 69 c32
     0.226 ms    0.8%  block 2 c32
     0.223 ms    0.8%  block 48 c256
     0.216 ms    0.8%  block 49 c256
     0.213 ms    0.8%  block 61 c128
     0.211 ms    0.8%  block 57 c128
     0.210 ms    0.7%  block 17 c256
     0.209 ms    0.7%  block 11 c128
     0.205 ms    0.7%  transition 8
     0.200 ms    0.7%  block 58 c128
     0.197 ms    0.7%  block 56 c128
     0.194 ms    0.7%  block 12 c128
     0.190 ms    0.7%  block 59 c128
     0.186 ms    0.7%  block 22 c256
     0.185 ms    0.7%  block 53 c256
     0.185 ms    0.7%  block 20 c256
     0.184 ms    0.7%  block 50 c256
     0.183 ms    0.7%  block 60 c128
     0.182 ms    0.6%  block 18 c256
     0.181 ms    0.6%  block 19 c256
     0.181 ms    0.6%  block 51 c256
     0.181 ms    0.6%  block 55 c256
     0.180 ms    0.6%  block 52 c256
     0.179 ms    0.6%  block 54 c256
     0.179 ms    0.6%  block 21 c256
     0.179 ms    0.6%  block 13 c128
     0.168 ms    0.6%  block 24 split512
     0.159 ms    0.6%  block 30 split512
     0.157 ms    0.6%  block 40 split512
     0.156 ms    0.6%  block 46 split512
     0.156 ms    0.6%  block 41 split512
     0.155 ms    0.5%  block 26 split512
     0.153 ms    0.5%  block 43 split512
     0.153 ms    0.5%  block 27 split512
     0.152 ms    0.5%  block 44 split512
     0.152 ms    0.5%  block 42 split512
     0.152 ms    0.5%  block 28 split512
     0.152 ms    0.5%  block 25 split512
     0.152 ms    0.5%  block 29 split512
     0.152 ms    0.5%  block 47 split512
     0.150 ms    0.5%  block 45 split512
     0.116 ms    0.4%  transition ->48
     0.072 ms    0.3%  transition 39
     0.059 ms    0.2%  transition 30-31
     0.051 ms    0.2%  transition ->66
     0.034 ms    0.1%  transition 22
     0.033 ms    0.1%  transition 14
     0.027 ms    0.1%  transition 4-5

```

stderr:

```

```
