# run r2026-11-10-16-gap5-1-1080p

runner `415e2181914a` · entry `port-profile` · env from policy: NEURALSCREEN_MODEL_DIR

policy `92cc2c01922f` at /opt/neuralscreen/policy.toml · the file itself is beside this report as policy.toml

`bash tools/port_profile.sh 1920 1080`

exit **0** after 4.7s

gpu before: WARN [util 24% of the 25% bar] (resident but not contending: Telegram (pid 16290, 30.0 MiB); resident but not contending: signal-desktop (pid 18889, 198.0 MiB); resident but not contending: msedge (pid 1300500, 293.0 MiB); resident but not contending: chromium (pid 3132450, 177.0 MiB)) after waiting 15s; after: BUSY [util 51% of the 25% bar] (utilization 51%; Telegram (pid 16290, 30.0 MiB); signal-desktop (pid 18889, 198.0 MiB); msedge (pid 1300500, 293.0 MiB); chromium (pid 3132450, 177.0 MiB))

```
gemmv_ptx 640x1024->1024 f5 s4
     0.264 ms    1.5%  qkv_ptx 570w x4 K128
     0.263 ms    1.5%  block32_ptx 8760w f66
     0.263 ms    1.5%  block32_ptx 8640w f130
     0.263 ms    1.5%  qkv_ptx 558w x4 K128
     0.262 ms    1.5%  qkv_ptx 144w x8 K256
     0.260 ms    1.5%  qkv_ptx 2257w x2 K64
     0.260 ms    1.5%  qkv_ptx 135w x8 K256
     0.256 ms    1.5%  qkv_ptx 2220w x2 K64
     0.256 ms    1.5%  qkv_ptx 540w x4 K128
     0.252 ms    1.5%  qkv_ptx 2196w x2 K64
     0.252 ms    1.5%  block32_ptx 8760w f2
     0.250 ms    1.5%  qkv_ptx 2160w x2 K64
     0.249 ms    1.5%  block32_ptx 8640w f2
     0.245 ms    1.4%  global_attention_stream_ptx 640t x32
     0.215 ms    1.3%  ffn_ptx 138240x64 e2 r4
     0.198 ms    1.2%  ffn_ptx 34560x128 e4 r4
     0.136 ms    0.8%  upsampleResidual
     0.122 ms    0.7%  global_normalize_ptx 640t x32
     0.063 ms    0.4%  gemm_ptx 138240x64->64 f13
     0.043 ms    0.3%  gemm_ptx 34560x128->128 f13
     0.040 ms    0.2%  downsample2x

by stage:
     1.037 ms    6.1%  block 0 c32
     1.014 ms    5.9%  block 70 c32
     0.321 ms    1.9%  block 8 c64
     0.298 ms    1.7%  block 65 c64
     0.286 ms    1.7%  block 31 vit
     0.286 ms    1.7%  block 38 vit
     0.285 ms    1.7%  block 34 vit
     0.284 ms    1.7%  block 35 vit
     0.284 ms    1.7%  block 36 vit
     0.284 ms    1.7%  block 32 vit
     0.283 ms    1.7%  block 37 vit
     0.282 ms    1.7%  block 33 vit
     0.263 ms    1.5%  block 4 c32
     0.263 ms    1.5%  block 66 c32
     0.261 ms    1.5%  block 6 c64
     0.259 ms    1.5%  block 63 c64
     0.257 ms    1.5%  block 7 c64
     0.254 ms    1.5%  block 64 c64
     0.254 ms    1.5%  block 67 c32
     0.253 ms    1.5%  block 2 c32
     0.252 ms    1.5%  block 69 c32
     0.251 ms    1.5%  block 68 c32
     0.251 ms    1.5%  block 3 c32
     0.250 ms    1.5%  block 14 c128
     0.249 ms    1.5%  block 1 c32
     0.233 ms    1.4%  block 5 c64
     0.231 ms    1.4%  block 62 c64
     0.231 ms    1.4%  block 61 c128
     0.207 ms    1.2%  block 59 c128
     0.207 ms    1.2%  block 10 c128
     0.205 ms    1.2%  block 22 c256
     0.204 ms    1.2%  block 57 c128
     0.203 ms    1.2%  block 12 c128
     0.203 ms    1.2%  block 60 c128
     0.202 ms    1.2%  block 11 c128
     0.200 ms    1.2%  block 49 c256
     0.199 ms    1.2%  block 13 c128
     0.199 ms    1.2%  block 16 c256
     0.199 ms    1.2%  block 20 c256
     0.199 ms    1.2%  block 58 c128
     0.198 ms    1.2%  block 53 c256
     0.197 ms    1.2%  block 18 c256
     0.196 ms    1.2%  block 55 c256
     0.196 ms    1.2%  block 51 c256
     0.195 ms    1.1%  block 48 c256
     0.194 ms    1.1%  block 21 c256
     0.194 ms    1.1%  block 15 c256
     0.193 ms    1.1%  block 54 c256
     0.193 ms    1.1%  block 17 c256
     0.193 ms    1.1%  block 50 c256
     0.192 ms    1.1%  block 52 c256
     0.192 ms    1.1%  block 19 c256
     0.188 ms    1.1%  block 56 c128
     0.185 ms    1.1%  block 9 c128
     0.167 ms    1.0%  block 43 split512
     0.166 ms    1.0%  block 30 split512
     0.165 ms    1.0%  block 23 split512
     0.164 ms    1.0%  block 47 split512
     0.164 ms    1.0%  block 40 split512
     0.163 ms    1.0%  block 44 split512
     0.162 ms    1.0%  block 25 split512
     0.162 ms    1.0%  block 29 split512
     0.162 ms    1.0%  block 26 split512
     0.162 ms    0.9%  block 27 split512
     0.162 ms    0.9%  block 28 split512
     0.161 ms    0.9%  block 41 split512
     0.161 ms    0.9%  block 24 split512
     0.161 ms    0.9%  block 42 split512
     0.161 ms    0.9%  block 46 split512
     0.160 ms    0.9%  block 45 split512
     0.088 ms    0.5%  transition ->62
     0.051 ms    0.3%  transition ->56
     0.047 ms    0.3%  transition 39
     0.035 ms    0.2%  transition 8
     0.033 ms    0.2%  transition ->48
     0.026 ms    0.2%  transition 14
     0.024 ms    0.1%  transition 4-5
     0.022 ms    0.1%  transition ->66
     0.021 ms    0.1%  transition 22
     0.021 ms    0.1%  transition 30-31

```

stderr:

```

```
