# run r2026-11-03-port-build-split

**Refused.** timeout 1800s is outside 1..900

Nothing was executed. The entry points this runner knows:

* `gpu-status`: `uv run python tools/gpu_status.py --watch 20`
* `m1-gate`: `bash tools/m1_pipeline_gate.sh`
* `minimal`: `uv run python -m minimal`
* `minimal-small`: `xvfb-run -a uv run python -m minimal`
* `minimal-unfused`: `uv run python -m minimal`
* `model-small-extract`: `uv run python experiments/opendlss_weights/extract.py --dll native/nvngx_dlssnr.dll --magic 0x06c9dfdf --out /opt/neuralscreen/model-small`
* `ngx-live`: `xvfb-run -a uv run python -m minimal --frames 3 --headless --source synthetic --size 2560x1440 --save-after ngx-live.png --worker-log`
* `ngx-matrix`: `xvfb-run -a uv run python tools/ngx_matrix.py --baseline`
* `ngx-new`: `uv run python -m minimal`
* `ngx-old`: `uv run python -m minimal`
* `port-build`: `bash experiments/opendlss_port/rebuild.sh`
* `port-profile`: `bash tools/port_profile.sh`
* `pytest`: `uv run pytest tests/ -q`
