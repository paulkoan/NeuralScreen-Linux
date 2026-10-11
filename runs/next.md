# The plan

Work items in order, for whoever - or whatever - picks this up next. Take the top item, do it,
delete it, append what you learned at the bottom.

Not negotiable, because these are the difference between a loop and a runaway: one item per
pass; the test suite green before anything is pushed; never touch /etc or install system
packages; never touch the developer's checkout at /home/paul/dev/NeuralScreen-Linux; never edit
/opt/neuralscreen (policy, executor, key, unit); never queue a run that is not described here.

## 1. Does the cost scale with pixels? (ready - queue it)

serve spends ~22ms a frame: network+composite 12.5, proxy 4-5. The network alone measured
9.96ms in bench at 2560x1440, so the composite and the proxy expansion share a queue with it.
Half the work size separates what scales with pixels from what does not.

* id `r2026-10-11-e`, entry `minimal`, args `--source image --input-image
  fixtures/youtube-1440p.png --headless --size 1280x720 --frames 60 --worker-log --shm
  --no-motion --send-ahead 2`, artifacts none
* read it against the 2560x1440 numbers in runs/done/r2026-10-11-c
* learned: (fill in)

## 2. Temporal history, step one: let serve keep a frame

Every measurement so far is a single-frame NR: the client sends zero motion and the mode keeps
no history, so the network never sees a previous frame. That is the difference between what we
have and what the network is for. This step is plumbing only - a history feature buffer in
serve fed the previous frame - and claims nothing about quality until a run measures it.

* edit src/serve.cpp and src/kernels.{h,cpp} in the port, regenerate
  experiments/opendlss_port/linux-port.patch (steps in that directory's README)
* verify here: uv run pytest tests/ -q green, the shader compile test with GLSLANG set, and a
  pristine-clone apply-and-build
* then queue a run and compare network+composite against 12.5ms
* if the port's own parity mode objects, hand it back rather than papering over it

## 3. Ask first - do not start these alone

* Crop the fixture to the video area: the region has to be chosen by someone who can see it.
* The container: it needs nvidia-container-toolkit, a system package. The developer's call.
* Anything touching /etc, system packages or the box's configuration. Every time.
