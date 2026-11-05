"""Place only a trial-owned process on a Windows virtual desktop."""
import subprocess
import time

from arena.adapters.agents.dsh import hidden_process_options


class WindowsDesktop:
    def __init__(self, executable, number):
        self.executable = str(executable)
        self.number = number
        if not isinstance(number, int) or number < 1:
            raise ValueError('Virtual desktop numbers start at 1')
        self.operator_desktop = self.current()

    def call(self, *arguments):
        return subprocess.run([self.executable, *arguments], capture_output=True,
                              text=True, timeout=10, **hidden_process_options())

    def current(self):
        result = self.call('/GetCurrentDesktop')
        if not 0 <= result.returncode < 100 or 'Current desktop:' not in result.stdout:
            raise RuntimeError('Could not identify the current virtual desktop')
        return result.returncode + 1

    def move(self, process_id):
        deadline = time.monotonic() + 10
        while True:
            result = self.call('/GetDesktop:' + str(self.number - 1), '/MoveWindow:' + str(process_id))
            if result.returncode == self.number - 1:
                break
            if time.monotonic() > deadline:
                raise RuntimeError('Could not move the owned recording window')
            time.sleep(.2)
        self.verify(process_id)

    def switch(self, number):
        result = self.call('/Switch:' + str(number - 1))
        if result.returncode != number - 1 or self.current() != number:
            raise RuntimeError('Could not switch to the declared recording desktop')

    def check_active(self):
        if self.current() != self.number:
            raise RuntimeError('Active desktop changed during native recording')

    def verify(self, process_id):
        result = self.call('/GetDesktopFromWindow:' + str(process_id))
        if result.returncode != self.number - 1 or self.current() != self.operator_desktop:
            raise RuntimeError('Recording desktop or operator desktop changed unexpectedly')
        return {'recordingVirtualDesktop': self.number, 'operatorVirtualDesktop': self.operator_desktop}
