# run r2026-11-10-15-gap4-2-720p

runner `415e2181914a` · entry `port-profile` · env from policy: NEURALSCREEN_MODEL_DIR

policy `92cc2c01922f` at /opt/neuralscreen/policy.toml · the file itself is beside this report as policy.toml

`bash tools/port_profile.sh 1280 720`

exit **0** after 3.9s

gpu before: WARN [util 24% of the 25% bar] (resident but not contending: Telegram (pid 16290, 30.0 MiB); resident but not contending: signal-desktop (pid 18889, 155.0 MiB); resident but not contending: msedge (pid 1300500, 293.0 MiB); resident but not contending: chromium (pid 3132450, 326.0 MiB)); after: BUSY [util 47% of the 25% bar] (utilization 47%; Telegram (pid 16290, 30.0 MiB); signal-desktop (pid 18889, 155.0 MiB); msedge (pid 1300500, 293.0 MiB); chromium (pid 3132450, 244.0 MiB))

```
 288x1024->1024 f5 s4
     0.050 ms    1.5%  qkv_ptx 286w x4 K128
     0.049 ms    1.5%  qkv_ptx 1008w x2 K64
     0.049 ms    1.4%  qkv_ptx 273w x4 K128
     0.049 ms    1.4%  qkv_ptx 1075w x2 K64
     0.049 ms    1.4%  qkv_ptx 1050w x2 K64
     0.048 ms    1.4%  qkv_ptx 1032w x2 K64
     0.048 ms    1.4%  qkv_ptx 264w x4 K128
     0.045 ms    1.3%  qkv_ptx 252w x4 K128
     0.045 ms    1.3%  block32_ptx 4032w f130
     0.045 ms    1.3%  block32_ptx 4116w f66
     0.044 ms    1.3%  ffn_ptx 64512x64 e2 r4
     0.043 ms    1.3%  block32_ptx 4116w f2
     0.043 ms    1.3%  ffn_ptx 16128x128 e4 r4
     0.043 ms    1.3%  block32_ptx 4032w f2
     0.038 ms    1.1%  global_attention_stream_ptx 288t x32
     0.031 ms    0.9%  global_normalize_ptx 288t x32
     0.027 ms    0.8%  upsampleResidual
     0.013 ms    0.4%  gemm_ptx 64512x64->64 f13
     0.010 ms    0.3%  gemmt_ptx 288x1024->512 f0 p256 s4
     0.010 ms    0.3%  gemm_ptx 64512x64->64 f5
     0.009 ms    0.3%  downsample2x

by stage:
     0.170 ms    5.0%  block 0 c32
     0.162 ms    4.8%  block 70 c32
     0.064 ms    1.9%  block 8 c64
     0.064 ms    1.9%  block 31 vit
     0.064 ms    1.9%  block 32 vit
     0.064 ms    1.9%  block 34 vit
     0.063 ms    1.9%  block 33 vit
     0.063 ms    1.9%  block 35 vit
     0.062 ms    1.8%  block 38 vit
     0.062 ms    1.8%  block 37 vit
     0.062 ms    1.8%  block 36 vit
     0.061 ms    1.8%  block 65 c64
     0.052 ms    1.5%  block 6 c64
     0.052 ms    1.5%  block 64 c64
     0.052 ms    1.5%  block 63 c64
     0.050 ms    1.5%  block 7 c64
     0.049 ms    1.5%  block 14 c128
     0.048 ms    1.4%  block 61 c128
     0.047 ms    1.4%  block 5 c64
     0.046 ms    1.4%  block 62 c64
     0.045 ms    1.3%  block 66 c32
     0.045 ms    1.3%  block 4 c32
     0.043 ms    1.3%  block 69 c32
     0.043 ms    1.3%  block 67 c32
     0.043 ms    1.3%  block 2 c32
     0.043 ms    1.3%  block 1 c32
     0.042 ms    1.3%  block 3 c32
     0.042 ms    1.2%  block 59 c128
     0.042 ms    1.2%  block 68 c32
     0.042 ms    1.2%  block 10 c128
     0.041 ms    1.2%  block 57 c128
     0.041 ms    1.2%  block 18 c256
     0.041 ms    1.2%  block 11 c128
     0.041 ms    1.2%  block 12 c128
     0.041 ms    1.2%  block 60 c128
     0.040 ms    1.2%  block 22 c256
     0.040 ms    1.2%  block 16 c256
     0.040 ms    1.2%  block 20 c256
     0.040 ms    1.2%  block 13 c128
     0.040 ms    1.2%  block 55 c256
     0.040 ms    1.2%  block 58 c128
     0.039 ms    1.2%  block 21 c256
     0.039 ms    1.2%  block 19 c256
     0.039 ms    1.2%  block 48 c256
     0.039 ms    1.2%  block 54 c256
     0.039 ms    1.2%  block 51 c256
     0.039 ms    1.2%  block 49 c256
     0.039 ms    1.2%  block 15 c256
     0.039 ms    1.1%  block 50 c256
     0.039 ms    1.1%  block 52 c256
     0.038 ms    1.1%  block 53 c256
     0.037 ms    1.1%  block 17 c256
     0.037 ms    1.1%  block 56 c128
     0.037 ms    1.1%  block 9 c128
     0.037 ms    1.1%  block 30 split512
     0.037 ms    1.1%  block 28 split512
     0.037 ms    1.1%  block 47 split512
     0.036 ms    1.1%  block 24 split512
     0.036 ms    1.1%  block 26 split512
     0.036 ms    1.1%  block 45 split512
     0.036 ms    1.1%  block 43 split512
     0.035 ms    1.0%  block 41 split512
     0.035 ms    1.0%  block 40 split512
     0.034 ms    1.0%  block 44 split512
     0.034 ms    1.0%  block 23 split512
     0.034 ms    1.0%  block 25 split512
     0.033 ms    1.0%  block 46 split512
     0.033 ms    1.0%  block 27 split512
     0.033 ms    1.0%  block 29 split512
     0.033 ms    1.0%  block 42 split512
     0.017 ms    0.5%  transition ->62
     0.016 ms    0.5%  transition 39
     0.011 ms    0.3%  transition ->56
     0.010 ms    0.3%  transition 8
     0.009 ms    0.3%  transition ->48
     0.008 ms    0.2%  transition 30-31
     0.008 ms    0.2%  transition 4-5
     0.007 ms    0.2%  transition 14
     0.007 ms    0.2%  transition 22
     0.005 ms    0.2%  transition ->66

```

stderr:

```

```
