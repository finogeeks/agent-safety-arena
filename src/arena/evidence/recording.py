"""Encode owned browser frames or record an explicit Windows screen rectangle."""

import queue
import subprocess
import threading
import time

from arena.adapters.agents.dsh import hidden_process_options


class DesktopRecorder:
    def __init__(self, ffmpeg, region=None):
        self.ffmpeg, self.region = str(ffmpeg), region
        self.process = None
        self.log = None
        self.source = "desktop"

    def start(self, output):
        arguments = [self.ffmpeg, "-hide_banner", "-loglevel", "warning", "-nostats", "-n",
                     "-progress", "pipe:1", "-stats_period", "0.2", "-f", "gdigrab",
                     "-framerate", "8", "-draw_mouse", "1"]
        if self.region:
            x, y, width, height = self.region
            if width < 2 or height < 2:
                raise ValueError("Recording region must be at least 2 by 2 pixels")
            arguments += ["-offset_x", str(x), "-offset_y", str(y), "-video_size", f"{width}x{height}"]
        arguments += ["-i", self.source, "-an", "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2",
                      "-c:v", "libx264", "-preset", "ultrafast", "-crf", "24", "-pix_fmt", "yuv420p",
                      "-movflags", "+frag_keyframe+empty_moov", str(output)]
        self.log = output.with_name("recorder.log").open("w", encoding="utf8")
        self.process = subprocess.Popen(arguments, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=self.log, text=True, **hidden_process_options())
        progress = queue.Queue()

        def consume():
            for line in self.process.stdout:
                if line.startswith("frame="):
                    progress.put(int(line.partition("=")[2].strip()))

        self.reader = threading.Thread(target=consume, daemon=True)
        self.reader.start()
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            self.check()
            try:
                if progress.get(timeout=.2) > 0:
                    self.started_at = time.monotonic()
                    return
            except queue.Empty:
                pass
        raise RuntimeError("FFmpeg did not capture its first frame; no prompt submitted")

    def check(self):
        if self.process is None or self.process.poll() is not None:
            raise RuntimeError("FFmpeg is not recording; inspect recorder.log")

    def stop(self):
        if not self.process:
            if self.log:
                self.log.close()
            return
        try:
            if self.process.poll() is None:
                self.process.stdin.write("q\n")
                self.process.stdin.flush()
            self.process.wait(timeout=15)
            if self.process.returncode:
                raise RuntimeError(f"FFmpeg exited with code {self.process.returncode}; inspect recorder.log")
        except (BrokenPipeError, subprocess.TimeoutExpired):
            self.process.kill()
            self.process.wait(timeout=5)
            raise RuntimeError("FFmpeg could not finalize the recording") from None
        finally:
            self.process.stdin.close()
            self.reader.join(timeout=2)
            self.process.stdout.close()
            self.log.close()


class BrowserRecorder:
    """Encode viewport screenshots on a wall-clock schedule, including idle waits."""

    def __init__(self, ffmpeg, browser):
        self.ffmpeg, self.browser = str(ffmpeg), browser
        self.process = None
        self.log = None
        self.error = None
        self.halt = threading.Event()
        self.source = None

    def select_window(self, title):
        if not isinstance(title, str) or not title.strip():
            raise ValueError("The owned DSH window title is required")
        self.source = "browser-viewport"

    def start(self, output):
        if self.source != "browser-viewport":
            raise RuntimeError("The owned DSH viewport was not selected")
        first = self.browser.frame()
        self.log = output.with_name("recorder.log").open("w", encoding="utf8")
        self.process = subprocess.Popen(
            [self.ffmpeg, "-hide_banner", "-loglevel", "warning", "-nostats", "-n",
             "-progress", "pipe:1", "-stats_period", "0.2",
             "-probesize", "32", "-analyzeduration", "0", "-fpsprobesize", "0", "-threads", "1",
             "-f", "image2pipe", "-framerate", "4", "-c:v", "png", "-i", "pipe:0",
             "-an", "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2", "-c:v", "libx264",
             "-threads", "2", "-preset", "ultrafast", "-crf", "24", "-pix_fmt", "yuv420p",
             "-movflags", "+frag_keyframe+empty_moov", str(output)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.log, **hidden_process_options())
        ready = threading.Event()

        def progress():
            for line in self.process.stdout:
                if line.startswith(b"frame=") and int(line.partition(b"=")[2].strip()) > 0:
                    ready.set()

        self.monitor = threading.Thread(target=progress, daemon=True)
        self.monitor.start()
        self.started_at = time.monotonic()
        self.process.stdin.write(first)
        self.process.stdin.flush()

        def capture():
            frame_number = 1
            previous = first
            try:
                while not self.halt.wait(max(0, self.started_at + frame_number / 4 - time.monotonic())):
                    current = self.browser.frame()
                    # Reproduce elapsed waiting time if one browser capture was slow.
                    due = max(frame_number, int((time.monotonic() - self.started_at) * 4))
                    while frame_number < due:
                        self.process.stdin.write(previous)
                        frame_number += 1
                    self.process.stdin.write(current)
                    self.process.stdin.flush()
                    frame_number += 1
                    previous = current
            except Exception as error:
                self.error = error

        self.reader = threading.Thread(target=capture, daemon=True)
        self.reader.start()
        deadline = time.monotonic() + 20
        while not ready.wait(.1):
            self.check()
            if time.monotonic() >= deadline:
                raise RuntimeError("FFmpeg did not encode its first DSH frame; no prompt submitted")
        self.check()

    def check(self):
        if self.error:
            raise RuntimeError(f"DSH viewport capture failed: {self.error}")
        if not self.process or self.process.poll() is not None:
            raise RuntimeError("Viewport encoder stopped; inspect recorder.log")

    def stop(self):
        self.halt.set()
        if not self.process:
            if self.log:
                self.log.close()
            return
        try:
            if hasattr(self, "reader"):
                self.reader.join(timeout=20)
                if self.reader.is_alive():
                    raise RuntimeError("Viewport capture did not stop")
            self.process.stdin.close()
            self.process.wait(timeout=15)
            if self.error or self.process.returncode:
                raise RuntimeError("Viewport recording was incomplete; inspect recorder.log")
        finally:
            if self.process.poll() is None:
                self.process.kill()
                self.process.wait(timeout=5)
            if not self.process.stdin.closed:
                self.process.stdin.close()
            self.monitor.join(timeout=2)
            self.process.stdout.close()
            self.log.close()
