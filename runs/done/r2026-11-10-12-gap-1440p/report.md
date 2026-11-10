# run r2026-11-10-12-gap-1440p

runner `415e2181914a` · entry `port-profile` · env from policy: NEURALSCREEN_MODEL_DIR

policy `92cc2c01922f` at /opt/neuralscreen/policy.toml · the file itself is beside this report as policy.toml

`bash tools/port_profile.sh 2560 1440`

exit **0** after 10.1s

gpu before: WARN [util 20% of the 25% bar] (resident but not contending: Telegram (pid 16290, 30.0 MiB); resident but not contending: signal-desktop (pid 18889, 155.0 MiB); resident but not contending: msedge (pid 1300500, 293.0 MiB); resident but not contending: chromium (pid 3132450, 258.0 MiB); resident but not contending: fossilize_replay (pid 235861, 40.0 MiB); resident but not contending: fossilize_replay (pid 236120, 38.0 MiB); resident but not contending: fossilize_replay (pid 236438, 38.0 MiB); resident but not contending: fossilize_replay (pid 236440, 38.0 MiB); resident but not contending: fossilize_replay (pid 237866, 34.0 MiB)); after: WARN [util 9% of the 25% bar] (resident but not contending: Telegram (pid 16290, 30.0 MiB); resident but not contending: signal-desktop (pid 18889, 155.0 MiB); resident but not contending: msedge (pid 1300500, 293.0 MiB); resident but not contending: chromium (pid 3132450, 253.0 MiB); resident but not contending: fossilize_replay (pid 235861, 40.0 MiB); resident but not contending: fossilize_replay (pid 237866, 34.0 MiB); resident but not contending: fossilize_replay (pid 238867, 34.0 MiB); resident but not contending: fossilize_replay (pid 239008, 34.0 MiB); resident but not contending: fossilize_replay (pid 239250, 34.0 MiB))

```
%  qkv_ptx 3726w x2 K64
     0.159 ms    1.7%  qkv_ptx 3680w x2 K64
     0.156 ms    1.7%  qkv_ptx 3807w x2 K64
     0.153 ms    1.6%  qkv_ptx 984w x4 K128
     0.148 ms    1.6%  block32_ptx 14880w f66
     0.148 ms    1.6%  block32_ptx 14720w f130
     0.145 ms    1.5%  gemmv_ptx 3840x512->512 f4
     0.144 ms    1.5%  qkv_ptx 943w x4 K128
     0.144 ms    1.5%  qkv_ptx 77w x16 K512
     0.144 ms    1.5%  qkv_ptx 960w x4 K128
     0.140 ms    1.5%  block32_ptx 14880w f2
     0.140 ms    1.5%  qkv_ptx 920w x4 K128
     0.139 ms    1.5%  block32_ptx 14720w f2
     0.135 ms    1.4%  qkv_ptx 70w x16 K512
     0.134 ms    1.4%  qkv_ptx 66w x16 K512
     0.130 ms    1.4%  gemmv_ptx 960x1024->1024 f5 s4
     0.123 ms    1.3%  qkv_ptx 60w x16 K512
     0.121 ms    1.3%  ffn_ptx 58880x128 e4 r4
     0.081 ms    0.9%  global_normalize_ptx 960t x32
     0.078 ms    0.8%  upsampleResidual
     0.051 ms    0.5%  gemm_ptx 235520x64->64 f13
     0.028 ms    0.3%  gemm_ptx 235520x64->64 f5

by stage:
     0.633 ms    6.7%  block 0 c32
     0.570 ms    6.1%  block 70 c32
     0.220 ms    2.3%  block 8 c64
     0.200 ms    2.1%  block 65 c64
     0.172 ms    1.8%  block 7 c64
     0.168 ms    1.8%  block 62 c64
     0.164 ms    1.7%  block 63 c64
     0.161 ms    1.7%  block 64 c64
     0.158 ms    1.7%  block 6 c64
     0.153 ms    1.6%  block 5 c64
     0.148 ms    1.6%  block 4 c32
     0.148 ms    1.6%  block 66 c32
     0.142 ms    1.5%  block 2 c32
     0.142 ms    1.5%  block 67 c32
     0.141 ms    1.5%  block 68 c32
     0.141 ms    1.5%  block 14 c128
     0.140 ms    1.5%  block 69 c32
     0.140 ms    1.5%  block 3 c32
     0.139 ms    1.5%  block 1 c32
     0.138 ms    1.5%  block 31 vit
     0.138 ms    1.5%  block 38 vit
     0.137 ms    1.5%  block 37 vit
     0.137 ms    1.5%  block 32 vit
     0.137 ms    1.5%  block 34 vit
     0.136 ms    1.5%  block 33 vit
     0.136 ms    1.5%  block 35 vit
     0.136 ms    1.5%  block 36 vit
     0.131 ms    1.4%  block 61 c128
     0.117 ms    1.3%  block 59 c128
     0.117 ms    1.2%  block 10 c128
     0.116 ms    1.2%  block 12 c128
     0.115 ms    1.2%  block 11 c128
     0.114 ms    1.2%  block 57 c128
     0.114 ms    1.2%  block 60 c128
     0.113 ms    1.2%  block 58 c128
     0.112 ms    1.2%  block 13 c128
     0.110 ms    1.2%  block 49 c256
     0.110 ms    1.2%  block 53 c256
     0.108 ms    1.2%  block 22 c256
     0.108 ms    1.2%  block 9 c128
     0.107 ms    1.1%  block 16 c256
     0.107 ms    1.1%  block 56 c128
     0.107 ms    1.1%  block 15 c256
     0.107 ms    1.1%  block 21 c256
     0.107 ms    1.1%  block 50 c256
     0.107 ms    1.1%  block 54 c256
     0.107 ms    1.1%  block 48 c256
     0.106 ms    1.1%  block 20 c256
     0.106 ms    1.1%  block 17 c256
     0.106 ms    1.1%  block 19 c256
     0.104 ms    1.1%  block 52 c256
     0.104 ms    1.1%  block 55 c256
     0.103 ms    1.1%  block 51 c256
     0.103 ms    1.1%  block 18 c256
     0.079 ms    0.8%  block 30 split512
     0.079 ms    0.8%  block 24 split512
     0.078 ms    0.8%  block 28 split512
     0.077 ms    0.8%  block 41 split512
     0.076 ms    0.8%  block 45 split512
     0.076 ms    0.8%  block 26 split512
     0.076 ms    0.8%  block 46 split512
     0.076 ms    0.8%  block 43 split512
     0.076 ms    0.8%  block 25 split512
     0.076 ms    0.8%  block 47 split512
     0.075 ms    0.8%  block 42 split512
     0.075 ms    0.8%  block 29 split512
     0.074 ms    0.8%  block 23 split512
     0.073 ms    0.8%  block 40 split512
     0.073 ms    0.8%  block 27 split512
     0.072 ms    0.8%  block 44 split512
     0.051 ms    0.5%  transition ->62
     0.030 ms    0.3%  transition ->56
     0.028 ms    0.3%  transition 8
     0.021 ms    0.2%  transition 4-5
     0.019 ms    0.2%  transition ->48
     0.019 ms    0.2%  transition 39
     0.016 ms    0.2%  transition 14
     0.014 ms    0.2%  transition ->66
     0.011 ms    0.1%  transition 22
     0.009 ms    0.1%  transition 30-31

```

stderr:

```

```
