# run r2026-11-10-profile-small

runner `005dd2c6ea9e` · entry `port-profile-small` · env from policy: NS_WORKER_CMD

`bash tools/port_profile.sh 1920 1080`

exit **0** after 4.3s

gpu before: WARN (resident but not contending: signal-desktop (pid 18889, 155.0 MiB); resident but not contending: msedge (pid 1300500, 283.0 MiB); resident but not contending: chromium (pid 3132450, 203.0 MiB)) after waiting 15s; after: BUSY (utilization 73%; signal-desktop (pid 18889, 155.0 MiB); msedge (pid 1300500, 283.0 MiB); chromium (pid 3132450, 179.0 MiB))

```
x1024->1024 f5 s4
     0.321 ms    1.6%  block32_ptx 8760w f66
     0.320 ms    1.5%  qkv_ptx 144w x8 K256
     0.319 ms    1.5%  qkv_ptx 558w x4 K128
     0.317 ms    1.5%  qkv_ptx 570w x4 K128
     0.316 ms    1.5%  qkv_ptx 135w x8 K256
     0.316 ms    1.5%  block32_ptx 8640w f130
     0.313 ms    1.5%  qkv_ptx 2257w x2 K64
     0.311 ms    1.5%  qkv_ptx 2220w x2 K64
     0.308 ms    1.5%  qkv_ptx 540w x4 K128
     0.307 ms    1.5%  block32_ptx 8760w f2
     0.305 ms    1.5%  qkv_ptx 2196w x2 K64
     0.303 ms    1.5%  block32_ptx 8640w f2
     0.303 ms    1.5%  qkv_ptx 2160w x2 K64
     0.299 ms    1.4%  global_attention_stream_ptx 640t x32
     0.259 ms    1.3%  ffn_ptx 138240x64 e2 r4
     0.240 ms    1.2%  ffn_ptx 34560x128 e4 r4
     0.164 ms    0.8%  upsampleResidual
     0.140 ms    0.7%  global_normalize_ptx 640t x32
     0.077 ms    0.4%  gemm_ptx 138240x64->64 f13
     0.052 ms    0.3%  gemm_ptx 34560x128->128 f13
     0.048 ms    0.2%  gemm_ptx 138240x64->64 f5

by stage:
     1.260 ms    6.1%  block 0 c32
     1.232 ms    6.0%  block 70 c32
     0.393 ms    1.9%  block 8 c64
     0.362 ms    1.7%  block 65 c64
     0.344 ms    1.7%  block 31 vit
     0.343 ms    1.7%  block 32 vit
     0.343 ms    1.7%  block 35 vit
     0.343 ms    1.7%  block 37 vit
     0.343 ms    1.7%  block 38 vit
     0.343 ms    1.7%  block 33 vit
     0.342 ms    1.7%  block 36 vit
     0.341 ms    1.6%  block 34 vit
     0.321 ms    1.6%  block 4 c32
     0.316 ms    1.5%  block 6 c64
     0.316 ms    1.5%  block 66 c32
     0.314 ms    1.5%  block 63 c64
     0.310 ms    1.5%  block 67 c32
     0.308 ms    1.5%  block 7 c64
     0.307 ms    1.5%  block 69 c32
     0.307 ms    1.5%  block 64 c64
     0.306 ms    1.5%  block 2 c32
     0.305 ms    1.5%  block 68 c32
     0.304 ms    1.5%  block 3 c32
     0.303 ms    1.5%  block 1 c32
     0.303 ms    1.5%  block 14 c128
     0.281 ms    1.4%  block 62 c64
     0.281 ms    1.4%  block 61 c128
     0.281 ms    1.4%  block 5 c64
     0.252 ms    1.2%  block 10 c128
     0.252 ms    1.2%  block 59 c128
     0.249 ms    1.2%  block 22 c256
     0.247 ms    1.2%  block 57 c128
     0.246 ms    1.2%  block 60 c128
     0.246 ms    1.2%  block 11 c128
     0.245 ms    1.2%  block 12 c128
     0.243 ms    1.2%  block 49 c256
     0.243 ms    1.2%  block 20 c256
     0.242 ms    1.2%  block 16 c256
     0.242 ms    1.2%  block 13 c128
     0.241 ms    1.2%  block 58 c128
     0.241 ms    1.2%  block 53 c256
     0.240 ms    1.2%  block 51 c256
     0.240 ms    1.2%  block 55 c256
     0.239 ms    1.2%  block 18 c256
     0.237 ms    1.1%  block 17 c256
     0.236 ms    1.1%  block 48 c256
     0.236 ms    1.1%  block 21 c256
     0.235 ms    1.1%  block 52 c256
     0.235 ms    1.1%  block 54 c256
     0.235 ms    1.1%  block 15 c256
     0.234 ms    1.1%  block 50 c256
     0.234 ms    1.1%  block 19 c256
     0.226 ms    1.1%  block 56 c128
     0.223 ms    1.1%  block 9 c128
     0.201 ms    1.0%  block 30 split512
     0.198 ms    1.0%  block 40 split512
     0.198 ms    1.0%  block 41 split512
     0.198 ms    1.0%  block 23 split512
     0.197 ms    1.0%  block 43 split512
     0.196 ms    0.9%  block 27 split512
     0.196 ms    0.9%  block 29 split512
     0.196 ms    0.9%  block 44 split512
     0.196 ms    0.9%  block 26 split512
     0.196 ms    0.9%  block 28 split512
     0.195 ms    0.9%  block 46 split512
     0.195 ms    0.9%  block 24 split512
     0.195 ms    0.9%  block 47 split512
     0.195 ms    0.9%  block 25 split512
     0.195 ms    0.9%  block 45 split512
     0.194 ms    0.9%  block 42 split512
     0.105 ms    0.5%  transition ->62
     0.062 ms    0.3%  transition ->56
     0.053 ms    0.3%  transition 39
     0.043 ms    0.2%  transition 8
     0.041 ms    0.2%  transition ->48
     0.032 ms    0.2%  transition 14
     0.029 ms    0.1%  transition 4-5
     0.028 ms    0.1%  transition ->66
     0.025 ms    0.1%  transition 22
     0.024 ms    0.1%  transition 30-31

```

stderr:

```

```
