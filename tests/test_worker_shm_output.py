"""The shared-memory OUTS section's size under --publish-work.

On the pipe, --publish-work moves the reader's expected byte count to the work-size picture.
On the shared-memory route the pixels land in a POSIX section whose size is fixed when it is
opened, so a work-size reply into a frame-size section is unreadable: the reader's
set_output_size cannot reach into a section it did not size. The worker therefore has to open
OUTS at the work size when the flag is on, and at the frame size when it is off.

No device or native binary is needed here: the handshake functions are stubbed and only the
sizes passed to open_out/send_out are asserted.
"""
import protocol
from minimal.worker import Worker

W, H = 64, 48
WORK_W, WORK_H = 48, 36


class _FakeShm:
    def __init__(self):
        self.negotiated = True
        self.name = "fake-in"
        self.out_name = "fake-out"
        self.size = 1
        self.out_bytes = 1
        self.opened = []

    def open_out(self, w, h):
        self.opened.append((w, h))


class _FakeReader:
    def wait_oak(self, timeout):
        return None


def _worker(monkeypatch, publish_work):
    worker = Worker(W, H, WORK_W, WORK_H, {}, warmup=0, shm=True,
                    publish_work=publish_work)
    worker.shm = _FakeShm()
    worker.reader = _FakeReader()
    worker.proc = object()

    monkeypatch.setattr(protocol, "_negotiate_shm",
                        lambda proc, reader, shm: None)
    sent = []
    monkeypatch.setattr(protocol, "send_out",
                        lambda proc, w, h, name: sent.append((w, h, name)))
    worker._open_shared_channels()
    return worker, sent


def test_publish_work_opens_the_output_section_at_the_work_size(monkeypatch):
    worker, sent = _worker(monkeypatch, publish_work=True)
    assert worker.shm.opened == [(WORK_W, WORK_H)], worker.shm.opened
    assert sent == [(WORK_W, WORK_H, "fake-out")], sent


def test_publish_work_off_opens_the_output_section_at_the_frame_size(monkeypatch):
    worker, sent = _worker(monkeypatch, publish_work=False)
    assert worker.shm.opened == [(W, H)], worker.shm.opened
    assert sent == [(W, H, "fake-out")], sent
