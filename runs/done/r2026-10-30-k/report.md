# run r2026-10-30-k

runner `e44571d7dd12` · entry `ngx-matrix` · env from policy: WINEPREFIX

`xvfb-run -a uv run python tools/ngx_matrix.py --baseline`

exit **1** after 14.3s

```
matrix -> /tmp/ngx-matrix-20261030T150651
control DLL: /home/paul/dev/NeuralScreen-Linux/native/nvngx_dlssnr.dll
--- bundled preset 0, direct, spoof 1 ---
    evaluate 0xBAD00004  (3.8s)
--- bundled preset 0, direct, spoof 0 ---
    evaluate 0xBAD00004  (2.5s)
--- bundled preset 0, via core, spoof 1 ---
    create 0xBAD0000B  (2.1s)
--- old preset 0, direct, spoof 1 ---
    evaluate 0xBAD00004  (2.8s)

      dll  preset     path  spoof          init          create        evaluate     loop  verdict
-------------------------------------------------------------------------------------------------
  bundled       0   direct      1       Success              ok      0xBAD00004    0/300  evaluate 0xBAD00004
  bundled       0   direct      0       Success              ok      0xBAD00004    0/300  evaluate 0xBAD00004
  bundled       0     core      1       Success      0xBAD0000B               -        -  create 0xBAD0000B
      old       0   direct      1       Success              ok      0xBAD00004    0/300  evaluate 0xBAD00004

SUMMARY bundled-p0-direct-spoof1=evaluate 0xBAD00004  bundled-p0-direct-spoof0=evaluate 0xBAD00004  bundled-p0-core-spoof1=create 0xBAD0000B  old-p0-direct-spoof1=evaluate 0xBAD00004
4 of 4 failed:
  create 0xBAD0000B: bundled-p0-core-spoof1
  evaluate 0xBAD00004: bundled-p0-direct-spoof1, bundled-p0-direct-spoof0, old-p0-direct-spoof1
  -> the old DLL fails too: the harness, prefix or driver changed - not the DLL.
  -> the architecture spoof does not change the outcome: it is not the cause.
logs: /tmp/ngx-matrix-20261030T150651

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.

```
