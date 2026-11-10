# run r2026-11-10-profile-large-1080p

runner `cfeacf64d2c0` · entry `port-profile` · env from policy: NEURALSCREEN_MODEL_DIR

policy `e735408303da` at /opt/neuralscreen/policy.toml · the file itself is beside this report as policy.toml

`bash tools/port_profile.sh 1920 1080`

exit **0** after 4.5s

gpu before: WARN (resident but not contending: Telegram (pid 16290, 30.0 MiB); resident but not contending: signal-desktop (pid 18889, 155.0 MiB); resident but not contending: msedge (pid 1300500, 283.0 MiB); resident but not contending: chromium (pid 3132450, 108.0 MiB)) after waiting 90s; after: WARN (resident but not contending: Telegram (pid 16290, 30.0 MiB); resident but not contending: signal-desktop (pid 18889, 155.0 MiB); resident but not contending: msedge (pid 1300500, 283.0 MiB); resident but not contending: chromium (pid 3132450, 108.0 MiB))

```
    1.6%  qkv_ptx 150w x8 K256
     0.264 ms    1.5%  block32_ptx 8760w f66
     0.264 ms    1.5%  qkv_ptx 144w x8 K256
     0.263 ms    1.5%  qkv_ptx 570w x4 K128
     0.262 ms    1.5%  block32_ptx 8640w f130
     0.262 ms    1.5%  qkv_ptx 558w x4 K128
     0.262 ms    1.5%  qkv_ptx 135w x8 K256
     0.258 ms    1.5%  qkv_ptx 2257w x2 K64
     0.256 ms    1.5%  qkv_ptx 540w x4 K128
     0.254 ms    1.5%  qkv_ptx 2220w x2 K64
     0.252 ms    1.5%  block32_ptx 8760w f2
     0.252 ms    1.5%  qkv_ptx 2196w x2 K64
     0.250 ms    1.5%  qkv_ptx 2160w x2 K64
     0.249 ms    1.5%  block32_ptx 8640w f2
     0.247 ms    1.5%  global_attention_stream_ptx 640t x32
     0.215 ms    1.3%  ffn_ptx 138240x64 e2 r4
     0.198 ms    1.2%  ffn_ptx 34560x128 e4 r4
     0.137 ms    0.8%  upsampleResidual
     0.116 ms    0.7%  global_normalize_ptx 640t x32
     0.063 ms    0.4%  gemm_ptx 138240x64->64 f13
     0.043 ms    0.3%  gemm_ptx 34560x128->128 f13
     0.040 ms    0.2%  downsample2x

by stage:
     1.036 ms    6.1%  block 0 c32
     1.013 ms    5.9%  block 70 c32
     0.322 ms    1.9%  block 8 c64
     0.298 ms    1.7%  block 65 c64
     0.285 ms    1.7%  block 31 vit
     0.285 ms    1.7%  block 34 vit
     0.285 ms    1.7%  block 36 vit
     0.285 ms    1.7%  block 38 vit
     0.285 ms    1.7%  block 37 vit
     0.284 ms    1.7%  block 35 vit
     0.283 ms    1.7%  block 33 vit
     0.283 ms    1.7%  block 32 vit
     0.264 ms    1.5%  block 4 c32
     0.262 ms    1.5%  block 66 c32
     0.259 ms    1.5%  block 6 c64
     0.258 ms    1.5%  block 63 c64
     0.258 ms    1.5%  block 64 c64
     0.254 ms    1.5%  block 2 c32
     0.253 ms    1.5%  block 67 c32
     0.253 ms    1.5%  block 7 c64
     0.252 ms    1.5%  block 69 c32
     0.251 ms    1.5%  block 68 c32
     0.251 ms    1.5%  block 3 c32
     0.250 ms    1.5%  block 14 c128
     0.249 ms    1.5%  block 1 c32
     0.233 ms    1.4%  block 62 c64
     0.231 ms    1.4%  block 5 c64
     0.230 ms    1.3%  block 61 c128
     0.208 ms    1.2%  block 10 c128
     0.207 ms    1.2%  block 59 c128
     0.205 ms    1.2%  block 22 c256
     0.204 ms    1.2%  block 57 c128
     0.203 ms    1.2%  block 12 c128
     0.202 ms    1.2%  block 60 c128
     0.202 ms    1.2%  block 11 c128
     0.200 ms    1.2%  block 16 c256
     0.200 ms    1.2%  block 53 c256
     0.200 ms    1.2%  block 49 c256
     0.200 ms    1.2%  block 58 c128
     0.199 ms    1.2%  block 13 c128
     0.198 ms    1.2%  block 20 c256
     0.198 ms    1.2%  block 55 c256
     0.196 ms    1.2%  block 18 c256
     0.196 ms    1.1%  block 51 c256
     0.195 ms    1.1%  block 48 c256
     0.195 ms    1.1%  block 54 c256
     0.195 ms    1.1%  block 19 c256
     0.195 ms    1.1%  block 52 c256
     0.195 ms    1.1%  block 50 c256
     0.194 ms    1.1%  block 21 c256
     0.194 ms    1.1%  block 15 c256
     0.193 ms    1.1%  block 17 c256
     0.187 ms    1.1%  block 56 c128
     0.185 ms    1.1%  block 9 c128
     0.164 ms    1.0%  block 23 split512
     0.164 ms    1.0%  block 40 split512
     0.164 ms    1.0%  block 30 split512
     0.164 ms    1.0%  block 25 split512
     0.163 ms    1.0%  block 24 split512
     0.162 ms    1.0%  block 47 split512
     0.162 ms    1.0%  block 28 split512
     0.161 ms    0.9%  block 44 split512
     0.161 ms    0.9%  block 26 split512
     0.161 ms    0.9%  block 29 split512
     0.161 ms    0.9%  block 46 split512
     0.161 ms    0.9%  block 27 split512
     0.160 ms    0.9%  block 42 split512
     0.160 ms    0.9%  block 41 split512
     0.159 ms    0.9%  block 45 split512
     0.159 ms    0.9%  block 43 split512
     0.089 ms    0.5%  transition ->62
     0.051 ms    0.3%  transition ->56
     0.047 ms    0.3%  transition 39
     0.035 ms    0.2%  transition 8
     0.034 ms    0.2%  transition ->48
     0.026 ms    0.2%  transition 14
     0.026 ms    0.2%  transition 4-5
     0.023 ms    0.1%  transition ->66
     0.021 ms    0.1%  transition 22
     0.021 ms    0.1%  transition 30-31

```

stderr:

```

```
