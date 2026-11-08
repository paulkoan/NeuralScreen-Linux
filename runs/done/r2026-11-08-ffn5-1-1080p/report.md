# run r2026-11-08-ffn5-1-1080p

runner `005dd2c6ea9e` · entry `port-profile` · env from policy: none

`bash tools/port_profile.sh 1920 1080`

exit **0** after 4.4s

gpu before: WARN (resident but not contending: signal-desktop (pid 18889, 151.0 MiB); resident but not contending: chromium (pid 18945, 60.0 MiB); resident but not contending: msedge (pid 54723, 342.0 MiB)); after: WARN (resident but not contending: signal-desktop (pid 18889, 151.0 MiB); resident but not contending: chromium (pid 18945, 60.0 MiB); resident but not contending: msedge (pid 54723, 341.0 MiB))

```
5%  gemmv_ptx 8640x256->256 f5
     0.379 ms    1.2%  ffn_ptx 34560x128 e4 r4
     0.368 ms    1.2%  qkv_ptx 2160w x2 K64
     0.328 ms    1.1%  qkv_ptx 160w x8 K256
     0.314 ms    1.0%  qkv_ptx 540w x4 K128
     0.310 ms    1.0%  qkv_ptx 589w x4 K128
     0.307 ms    1.0%  qkv_ptx 150w x8 K256
     0.305 ms    1.0%  qkv_ptx 558w x4 K128
     0.303 ms    1.0%  qkv_ptx 2257w x2 K64
     0.303 ms    1.0%  qkv_ptx 135w x8 K256
     0.297 ms    1.0%  qkv_ptx 570w x4 K128
     0.295 ms    1.0%  qkv_ptx 144w x8 K256
     0.294 ms    1.0%  block32_ptx 8760w f66
     0.286 ms    0.9%  qkv_ptx 2196w x2 K64
     0.284 ms    0.9%  qkv_ptx 2220w x2 K64
     0.281 ms    0.9%  block32_ptx 8760w f2
     0.278 ms    0.9%  global_attention_stream_ptx 640t x32
     0.264 ms    0.9%  ffn_ptx 138240x64 e2 r4
     0.201 ms    0.7%  gemm_ptx 138240x64->64 f13
     0.172 ms    0.6%  global_normalize_ptx 640t x32
     0.132 ms    0.4%  downsample2x
     0.127 ms    0.4%  gemm_ptx 34560x64->128 f4

by stage:
     5.463 ms   17.8%  block 0 c32
     3.105 ms   10.1%  block 70 c32
     0.972 ms    3.2%  block 66 c32
     0.763 ms    2.5%  block 31 vit
     0.692 ms    2.3%  block 1 c32
     0.619 ms    2.0%  block 34 vit
     0.588 ms    1.9%  block 33 vit
     0.571 ms    1.9%  block 32 vit
     0.509 ms    1.7%  block 36 vit
     0.506 ms    1.6%  block 37 vit
     0.505 ms    1.6%  block 38 vit
     0.504 ms    1.6%  block 35 vit
     0.504 ms    1.6%  transition ->62
     0.486 ms    1.6%  block 8 c64
     0.383 ms    1.2%  block 9 c128
     0.377 ms    1.2%  block 67 c32
     0.375 ms    1.2%  block 6 c64
     0.356 ms    1.2%  block 5 c64
     0.328 ms    1.1%  block 65 c64
     0.326 ms    1.1%  block 63 c64
     0.306 ms    1.0%  block 15 c256
     0.294 ms    1.0%  block 4 c32
     0.294 ms    1.0%  block 64 c64
     0.290 ms    0.9%  block 7 c64
     0.286 ms    0.9%  block 68 c32
     0.286 ms    0.9%  block 3 c32
     0.284 ms    0.9%  block 2 c32
     0.281 ms    0.9%  block 69 c32
     0.281 ms    0.9%  block 14 c128
     0.276 ms    0.9%  block 23 split512
     0.276 ms    0.9%  block 62 c64
     0.269 ms    0.9%  block 10 c128
     0.262 ms    0.9%  block 61 c128
     0.260 ms    0.8%  block 16 c256
     0.257 ms    0.8%  transition ->56
     0.255 ms    0.8%  block 49 c256
     0.253 ms    0.8%  block 57 c128
     0.253 ms    0.8%  block 48 c256
     0.251 ms    0.8%  block 11 c128
     0.240 ms    0.8%  block 17 c256
     0.233 ms    0.8%  block 22 c256
     0.232 ms    0.8%  block 59 c128
     0.231 ms    0.8%  transition 8
     0.229 ms    0.7%  block 12 c128
     0.229 ms    0.7%  block 58 c128
     0.228 ms    0.7%  block 60 c128
     0.227 ms    0.7%  block 53 c256
     0.227 ms    0.7%  block 56 c128
     0.227 ms    0.7%  block 20 c256
     0.225 ms    0.7%  block 13 c128
     0.225 ms    0.7%  block 18 c256
     0.224 ms    0.7%  block 51 c256
     0.224 ms    0.7%  block 55 c256
     0.223 ms    0.7%  block 50 c256
     0.222 ms    0.7%  block 21 c256
     0.221 ms    0.7%  block 54 c256
     0.220 ms    0.7%  block 19 c256
     0.220 ms    0.7%  block 52 c256
     0.205 ms    0.7%  block 24 split512
     0.192 ms    0.6%  block 40 split512
     0.192 ms    0.6%  block 30 split512
     0.190 ms    0.6%  block 25 split512
     0.187 ms    0.6%  block 46 split512
     0.187 ms    0.6%  block 26 split512
     0.186 ms    0.6%  block 28 split512
     0.186 ms    0.6%  block 41 split512
     0.186 ms    0.6%  block 43 split512
     0.186 ms    0.6%  block 44 split512
     0.186 ms    0.6%  block 45 split512
     0.185 ms    0.6%  block 27 split512
     0.185 ms    0.6%  block 29 split512
     0.185 ms    0.6%  block 42 split512
     0.185 ms    0.6%  block 47 split512
     0.109 ms    0.4%  transition ->48
     0.078 ms    0.3%  transition 39
     0.063 ms    0.2%  transition 30-31
     0.049 ms    0.2%  transition ->66
     0.036 ms    0.1%  transition 22
     0.036 ms    0.1%  transition 14
     0.029 ms    0.1%  transition 4-5

```

stderr:

```

```
