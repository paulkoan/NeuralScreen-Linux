# run r2026-11-01-aw

runner `e44571d7dd12` · entry `gpu-status` · env from policy: none

`uv run python tools/gpu_status.py --watch 20 --watch 20`

exit **0** after 21.2s

```
ode-override=/dev/dri/renderD129 --crashpad-handler-pid=73419 --enable-crash-reporter=? --change-stack-guard-on-fork=enable --gpu-preferences=YAAAAAAAAAAgAQAEAAAAAAAAAAAAAGAASAAAAAAAAAABAAAAAAAAAEAAAAAAAAAAAAAAAAAAAAACAAAAAAAAAAAAAAAAAAAAMAAAAAAAAAAwAAAAAAAAAAAAAAAAAAAACAAAAAAAAAAMAAAAAQAAAAAAAAAAAAAACAAAAAAAAAAIAAAAAAAAAA== --shared-files --metrics-shmem-handle=4?i?8428242807860764541?18110733236148166925?262144 --field-trial-handle=3?i?17070543719216482663?1725356133326100620?262144 --variations-seed-version --pseudonymization-salt-handle=7?i?2938691853852707949?3405654659910943945?4 --trace-process-track-uuid=3190708988185955192 (pid 73501, 219.0 MiB); /usr/bin/Telegram (pid 988444, 36.0 MiB); /usr/bin/shelly-ui (pid 1045732, 46.0 MiB); /usr/bin/signon-ui (pid 3062205, 17.0 MiB); S:\steamapps\common\Dying Light The Beast\ph_ft\work\bin\x64\DyingLightGame_TheBeast_x64_rwdi.exe (pid 4176838, 5670.0 MiB); SM clock 210 of 3105 MHz - the card is idling down
  NVIDIA GeForce RTX 4080 SUPER  util 7.0%  mem 9725.0/16376.0 MiB  sm 210.0/3105.0 MHz  47.0C  14.23W  P8
  holds the card: /usr/bin/kwin_wayland pid 41519 265.0 MiB
  holds the card: /usr/lib/chromium/chromium --type=gpu-process --gpu-recent-crash-count=0 --ozone-platform=wayland --render-node-override=/dev/dri/renderD129 --crashpad-handler-pid=42618 --enable-crash-reporter=?Arch Linux --change-stack-guard-on-fork=enable --gpu-preferences=YAAAAAAAAAAgAQAEAAAAAAAAAAAAAGAASAAAAAAAAAABAAAAAAAAAEAAAAAAAAAAAAAAAAAAAAACAAAAAAAAAAAAAAAAAAAAMAAAAAAAAAAwAAAAAAAAAAAAAAAAAAAACAAAAAAAAAAMAAAAAQAAAAAAAAAAAAAACAAAAAAAAAAIAAAAAAAAAA== --shared-files --metrics-shmem-handle=4?i?6129511831794278345?7686596331682273589?262144 --field-trial-handle=3?i?3358527140460585324?7671339858552317180?262144 --variations-seed-version --pseudonymization-salt-handle=7?i?8669116263537575375?9570697852985340351?4 --trace-process-track-uuid=3190708988185955192 pid 43069 214.0 MiB
  holds the card: /usr/lib/signal-desktop/signal-desktop --type=gpu-process --ozone-platform=wayland --render-node-override=/dev/dri/renderD129 --enable-crash-reporter=d7e7776f-64f4-49e5-81b1-3bbbd5df04fd?no_channel --user-data-dir=/home/paul/.config/Signal --gpu-preferences=YAAAAAAAAAAgAQAEAAAAAAAAAAAAAGAASAAAAAAAAAABAAAAAAAAAEAAAAAAAAAAAAAAAAAAAAACAAAAAAAAAAAAAAAAAAAAMAAAAAAAAAAwAAAAAAAAAAAAAAAAAAAACAAAAAAAAAAMAAAAAQAAAAAAAAAAAAAACAAAAAAAAAAIAAAAAAAAAA== --shared-files --field-trial-handle=3?i?3153280534364849167?709597223448560618?262144 --enable-features=PdfUseShowSaveFilePicker --disable-features=DropInputEventsWhilePaintHolding?HardwareMediaKeyHandling?LocalNetworkAccessChecks?ScreenAIOCREnabled?SpareRendererForSitePerProcess?TraceSiteInstanceGetProcessCreation --variations-seed-version --pseudonymization-salt-handle=7?i?3371186112357754672?17881890069939925240?4 --trace-process-track-uuid=3190708988185955192 pid 43509 60.0 MiB
  holds the card: /opt/microsoft/msedge/msedge --type=gpu-process --gpu-recent-crash-count=0 --ozone-platform=wayland --render-node-override=/dev/dri/renderD129 --crashpad-handler-pid=73419 --enable-crash-reporter=? --change-stack-guard-on-fork=enable --gpu-preferences=YAAAAAAAAAAgAQAEAAAAAAAAAAAAAGAASAAAAAAAAAABAAAAAAAAAEAAAAAAAAAAAAAAAAAAAAACAAAAAAAAAAAAAAAAAAAAMAAAAAAAAAAwAAAAAAAAAAAAAAAAAAAACAAAAAAAAAAMAAAAAQAAAAAAAAAAAAAACAAAAAAAAAAIAAAAAAAAAA== --shared-files --metrics-shmem-handle=4?i?8428242807860764541?18110733236148166925?262144 --field-trial-handle=3?i?17070543719216482663?1725356133326100620?262144 --variations-seed-version --pseudonymization-salt-handle=7?i?2938691853852707949?3405654659910943945?4 --trace-process-track-uuid=3190708988185955192 pid 73501 219.0 MiB
  holds the card: /usr/bin/Telegram pid 988444 36.0 MiB
  holds the card: /usr/bin/shelly-ui pid 1045732 46.0 MiB
  holds the card: /usr/bin/signon-ui pid 3062205 17.0 MiB
  holds the card: S:\steamapps\common\Dying Light The Beast\ph_ft\work\bin\x64\DyingLightGame_TheBeast_x64_rwdi.exe pid 4176838 5670.0 MiB
  worst of 20 samples

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.

```
