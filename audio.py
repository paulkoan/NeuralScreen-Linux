"""audio.py — Linux stub for the NeuralScreen audio capture module.

On Linux, system audio capture for recordings is not wired (the GFN stream
carries its own audio). This stub provides the same class interface so the
recorder module imports cleanly, but all methods are no-ops.

To add real system audio capture on Linux later:
- PipeWire: pw-cat --record + loopback module
- PulseAudio: parecord with monitor source
- ALSA: dsnoop device
"""

from __future__ import annotations


class LoopbackCapture:
    """Stub — no system audio capture on Linux.

    Matches the interface of the Windows WASAPI-based LoopbackCapture
    but does nothing.
    """

    def __init__(self):
        self.sample_rate = 48000
        self.channels = 2

    def start(self):
        pass

    def read(self) -> bytes:
        return b""

    def stop(self):
        pass

    def close(self):
        pass