# run r2026-11-10-13-gap2-2-720p

runner `415e2181914a` · entry `port-profile` · env from policy: NEURALSCREEN_MODEL_DIR

policy `92cc2c01922f` at /opt/neuralscreen/policy.toml · the file itself is beside this report as policy.toml

`bash tools/port_profile.sh 1280 720`

exit **0** after 5.0s

gpu before: WARN [util 0% of the 25% bar] (resident but not contending: Telegram (pid 16290, 30.0 MiB); resident but not contending: signal-desktop (pid 18889, 155.0 MiB); resident but not contending: msedge (pid 1300500, 293.0 MiB); resident but not contending: chromium (pid 3132450, 252.0 MiB); resident but not contending: fossilize_replay (pid 281463, 40.0 MiB); resident but not contending: fossilize_replay (pid 281815, 40.0 MiB); resident but not contending: fossilize_replay (pid 281839, 34.0 MiB); resident but not contending: fossilize_replay (pid 281870, 34.0 MiB); resident but not contending: fossilize_replay (pid 282164, 34.0 MiB)); after: BUSY [util 92% of the 25% bar] (utilization 92%; Telegram (pid 16290, 30.0 MiB); signal-desktop (pid 18889, 155.0 MiB); msedge (pid 1300500, 293.0 MiB); chromium (pid 3132450, 265.0 MiB); fossilize_replay (pid 281463, 42.0 MiB); fossilize_replay (pid 281815, 40.0 MiB); fossilize_replay (pid 281839, 42.0 MiB); fossilize_replay (pid 281870, 42.0 MiB); fossilize_replay (pid 282164, 38.0 MiB))

```
  2.0%  block32_ptx 4165w f2
     0.414 ms    2.0%  block32_ptx 4080w f2
     0.324 ms    1.5%  upsampleResidual
     0.274 ms    1.3%  ffn_ptx 16128x128 e4 r4
     0.239 ms    1.1%  block32_ptx 4032w f2
     0.231 ms    1.1%  qkv_ptx 286w x4 K128
     0.227 ms    1.1%  qkv_ptx 273w x4 K128
     0.218 ms    1.0%  qkv_ptx 264w x4 K128
     0.216 ms    1.0%  block32_ptx 4116w f66
     0.214 ms    1.0%  qkv_ptx 1075w x2 K64
     0.214 ms    1.0%  qkv_ptx 1008w x2 K64
     0.209 ms    1.0%  qkv_ptx 252w x4 K128
     0.205 ms    1.0%  qkv_ptx 1050w x2 K64
     0.205 ms    1.0%  qkv_ptx 1032w x2 K64
     0.205 ms    1.0%  block32_ptx 4116w f2
     0.180 ms    0.9%  ffn_ptx 64512x64 e2 r4
     0.166 ms    0.8%  global_attention_stream_ptx 288t x32
     0.120 ms    0.6%  global_normalize_ptx 288t x32
     0.055 ms    0.3%  gemm_ptx 64512x64->64 f13
     0.046 ms    0.2%  downsample2x
     0.045 ms    0.2%  gemmv_ptx 288x512->1024 f4
     0.039 ms    0.2%  gemm_ptx 16128x128->128 f13

by stage:
     2.960 ms   14.1%  block 0 c32
     1.355 ms    6.4%  block 70 c32
     0.680 ms    3.2%  block 32 vit
     0.675 ms    3.2%  block 31 vit
     0.622 ms    3.0%  block 33 vit
     0.542 ms    2.6%  block 34 vit
     0.523 ms    2.5%  block 35 vit
     0.476 ms    2.3%  block 66 c32
     0.460 ms    2.2%  block 37 vit
     0.458 ms    2.2%  block 36 vit
     0.456 ms    2.2%  block 38 vit
     0.262 ms    1.2%  block 8 c64
     0.253 ms    1.2%  block 9 c128
     0.244 ms    1.2%  block 65 c64
     0.239 ms    1.1%  block 1 c32
     0.225 ms    1.1%  block 14 c128
     0.222 ms    1.1%  block 6 c64
     0.219 ms    1.0%  block 63 c64
     0.216 ms    1.0%  block 4 c32
     0.214 ms    1.0%  block 61 c128
     0.213 ms    1.0%  block 7 c64
     0.212 ms    1.0%  transition ->62
     0.210 ms    1.0%  block 67 c32
     0.210 ms    1.0%  block 2 c32
     0.210 ms    1.0%  block 64 c64
     0.209 ms    1.0%  block 23 split512
     0.209 ms    1.0%  block 68 c32
     0.205 ms    1.0%  block 3 c32
     0.205 ms    1.0%  block 69 c32
     0.201 ms    1.0%  block 15 c256
     0.198 ms    0.9%  block 10 c128
     0.198 ms    0.9%  block 5 c64
     0.197 ms    0.9%  block 62 c64
     0.190 ms    0.9%  block 16 c256
     0.189 ms    0.9%  block 11 c128
     0.186 ms    0.9%  block 57 c128
     0.185 ms    0.9%  block 12 c128
     0.185 ms    0.9%  block 59 c128
     0.184 ms    0.9%  block 22 c256
     0.181 ms    0.9%  block 60 c128
     0.181 ms    0.9%  block 49 c256
     0.181 ms    0.9%  block 18 c256
     0.180 ms    0.9%  block 51 c256
     0.180 ms    0.9%  block 53 c256
     0.180 ms    0.9%  block 24 split512
     0.179 ms    0.9%  block 20 c256
     0.179 ms    0.9%  block 48 c256
     0.179 ms    0.9%  block 55 c256
     0.176 ms    0.8%  block 58 c128
     0.176 ms    0.8%  block 13 c128
     0.176 ms    0.8%  block 17 c256
     0.175 ms    0.8%  block 30 split512
     0.174 ms    0.8%  block 21 c256
     0.174 ms    0.8%  block 52 c256
     0.174 ms    0.8%  block 50 c256
     0.173 ms    0.8%  block 54 c256
     0.172 ms    0.8%  block 19 c256
     0.171 ms    0.8%  block 41 split512
     0.170 ms    0.8%  block 45 split512
     0.170 ms    0.8%  block 28 split512
     0.170 ms    0.8%  block 43 split512
     0.169 ms    0.8%  block 56 c128
     0.169 ms    0.8%  block 47 split512
     0.169 ms    0.8%  block 26 split512
     0.165 ms    0.8%  block 40 split512
     0.161 ms    0.8%  block 42 split512
     0.160 ms    0.8%  block 46 split512
     0.160 ms    0.8%  block 44 split512
     0.160 ms    0.8%  block 27 split512
     0.159 ms    0.8%  block 29 split512
     0.159 ms    0.8%  block 25 split512
     0.094 ms    0.4%  transition ->56
     0.064 ms    0.3%  transition 39
     0.058 ms    0.3%  transition ->48
     0.052 ms    0.2%  transition 30-31
     0.045 ms    0.2%  transition 8
     0.039 ms    0.2%  transition 22
     0.032 ms    0.2%  transition 14
     0.024 ms    0.1%  transition 4-5
     0.023 ms    0.1%  transition ->66

```

stderr:

```

```
