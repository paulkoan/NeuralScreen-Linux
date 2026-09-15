"""minimal — the MVP NeuralScreen pipeline: capture -> NR pass -> display.

Deliberately small: one frame in, the DLSS5 neural pass, one frame out.
No menu, no hotkeys, no recording, no shared memory, no Wayland.
"""

from minimal.loop import Pipeline, run

__all__ = ["Pipeline", "run"]