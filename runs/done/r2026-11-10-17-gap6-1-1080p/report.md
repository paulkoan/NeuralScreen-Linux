# run r2026-11-10-17-gap6-1-1080p

runner `415e2181914a` · entry `port-profile` · env from policy: NEURALSCREEN_MODEL_DIR

policy `92cc2c01922f` at /opt/neuralscreen/policy.toml · the file itself is beside this report as policy.toml

`bash tools/port_profile.sh 1920 1080`

exit **0** after 5.6s

gpu before: WARN [util 12% of the 25% bar] (resident but not contending: Telegram (pid 16290, 30.0 MiB); resident but not contending: signal-desktop (pid 18889, 198.0 MiB); resident but not contending: msedge (pid 1300500, 293.0 MiB); resident but not contending: chromium (pid 3132450, 177.0 MiB); resident but not contending: fossilize_replay (pid 479780, 60.0 MiB); resident but not contending: fossilize_replay (pid 479777, 60.0 MiB); resident but not contending: fossilize_replay (pid 490386, 60.0 MiB); resident but not contending: fossilize_replay (pid 493112, 58.0 MiB); resident but not contending: fossilize_replay (pid 494039, 58.0 MiB)); after: WARN [util 3% of the 25% bar] (resident but not contending: Telegram (pid 16290, 30.0 MiB); resident but not contending: signal-desktop (pid 18889, 198.0 MiB); resident but not contending: msedge (pid 1300500, 293.0 MiB); resident but not contending: chromium (pid 3132450, 177.0 MiB); resident but not contending: fossilize_replay (pid 490386, 60.0 MiB); resident but not contending: fossilize_replay (pid 493112, 58.0 MiB); resident but not contending: fossilize_replay (pid 494039, 58.0 MiB); resident but not contending: fossilize_replay (pid 496547, 34.0 MiB))

```
 2196w x2 K64
     0.096 ms    1.5%  qkv_ptx 2160w x2 K64
     0.096 ms    1.5%  qkv_ptx 2257w x2 K64
     0.094 ms    1.5%  qkv_ptx 2220w x2 K64
     0.092 ms    1.5%  qkv_ptx 589w x4 K128
     0.092 ms    1.5%  qkv_ptx 558w x4 K128
     0.092 ms    1.5%  qkv_ptx 150w x8 K256
     0.091 ms    1.5%  qkv_ptx 135w x8 K256
     0.091 ms    1.5%  qkv_ptx 570w x4 K128
     0.091 ms    1.4%  qkv_ptx 144w x8 K256
     0.090 ms    1.4%  block32_ptx 8640w f130
     0.089 ms    1.4%  block32_ptx 8760w f66
     0.086 ms    1.4%  global_attention_stream_ptx 640t x32
     0.086 ms    1.4%  qkv_ptx 540w x4 K128
     0.085 ms    1.3%  block32_ptx 8760w f2
     0.085 ms    1.3%  block32_ptx 8640w f2
     0.077 ms    1.2%  ffn_ptx 34560x128 e4 r4
     0.056 ms    0.9%  global_normalize_ptx 640t x32
     0.048 ms    0.8%  upsampleResidual
     0.023 ms    0.4%  gemm_ptx 138240x64->64 f13
     0.017 ms    0.3%  gemm_ptx 138240x64->64 f5
     0.016 ms    0.3%  gemmt_ptx 640x1024->512 f0 p256 s4

by stage:
     0.355 ms    5.6%  block 0 c32
     0.338 ms    5.4%  block 70 c32
     0.124 ms    2.0%  block 37 vit
     0.124 ms    2.0%  block 34 vit
     0.123 ms    2.0%  block 8 c64
     0.123 ms    1.9%  block 36 vit
     0.123 ms    1.9%  block 33 vit
     0.122 ms    1.9%  block 32 vit
     0.122 ms    1.9%  block 31 vit
     0.121 ms    1.9%  block 35 vit
     0.121 ms    1.9%  block 65 c64
     0.121 ms    1.9%  block 38 vit
     0.107 ms    1.7%  block 6 c64
     0.103 ms    1.6%  block 7 c64
     0.101 ms    1.6%  block 63 c64
     0.101 ms    1.6%  block 62 c64
     0.100 ms    1.6%  block 64 c64
     0.095 ms    1.5%  block 5 c64
     0.090 ms    1.4%  block 66 c32
     0.089 ms    1.4%  block 4 c32
     0.087 ms    1.4%  block 14 c128
     0.085 ms    1.4%  block 67 c32
     0.085 ms    1.3%  block 69 c32
     0.085 ms    1.3%  block 3 c32
     0.085 ms    1.3%  block 2 c32
     0.085 ms    1.3%  block 1 c32
     0.084 ms    1.3%  block 68 c32
     0.084 ms    1.3%  block 61 c128
     0.073 ms    1.2%  block 22 c256
     0.073 ms    1.2%  block 57 c128
     0.073 ms    1.2%  block 49 c256
     0.072 ms    1.1%  block 11 c128
     0.072 ms    1.1%  block 10 c128
     0.072 ms    1.1%  block 20 c256
     0.072 ms    1.1%  block 12 c128
     0.072 ms    1.1%  block 16 c256
     0.072 ms    1.1%  block 59 c128
     0.072 ms    1.1%  block 60 c128
     0.072 ms    1.1%  block 53 c256
     0.072 ms    1.1%  block 48 c256
     0.071 ms    1.1%  block 15 c256
     0.071 ms    1.1%  block 50 c256
     0.070 ms    1.1%  block 21 c256
     0.070 ms    1.1%  block 58 c128
     0.070 ms    1.1%  block 52 c256
     0.070 ms    1.1%  block 13 c128
     0.070 ms    1.1%  block 55 c256
     0.070 ms    1.1%  block 17 c256
     0.069 ms    1.1%  block 51 c256
     0.069 ms    1.1%  block 19 c256
     0.069 ms    1.1%  block 54 c256
     0.069 ms    1.1%  block 9 c128
     0.069 ms    1.1%  block 18 c256
     0.068 ms    1.1%  block 56 c128
     0.059 ms    0.9%  block 30 split512
     0.058 ms    0.9%  block 24 split512
     0.058 ms    0.9%  block 40 split512
     0.058 ms    0.9%  block 45 split512
     0.058 ms    0.9%  block 42 split512
     0.057 ms    0.9%  block 46 split512
     0.057 ms    0.9%  block 41 split512
     0.057 ms    0.9%  block 28 split512
     0.057 ms    0.9%  block 23 split512
     0.057 ms    0.9%  block 43 split512
     0.057 ms    0.9%  block 29 split512
     0.057 ms    0.9%  block 44 split512
     0.057 ms    0.9%  block 26 split512
     0.057 ms    0.9%  block 25 split512
     0.057 ms    0.9%  block 47 split512
     0.056 ms    0.9%  block 27 split512
     0.032 ms    0.5%  transition ->62
     0.023 ms    0.4%  transition 39
     0.019 ms    0.3%  transition ->56
     0.016 ms    0.3%  transition 8
     0.014 ms    0.2%  transition 4-5
     0.013 ms    0.2%  transition ->48
     0.010 ms    0.2%  transition 14
     0.009 ms    0.1%  transition ->66
     0.009 ms    0.1%  transition 30-31
     0.009 ms    0.1%  transition 22

```

stderr:

```

```
