import pygame.midi
from PyQt6.QtCore import QThread, pyqtSignal
import time

class MidiThread(QThread):
    """Thread to poll MIDI input without blocking the GUI"""
    message_received = pyqtSignal(int, int, int)  # status, data1, data2

    def __init__(self, device_id=None):
        super().__init__()
        self.device_id = device_id
        self.running = False
        self._init_midi()

    def _init_midi(self):
        try:
            pygame.midi.init()
        except Exception as e:
            print(f"MIDI Init Error: {e}")

    @staticmethod
    def get_devices():
        devices = []
        try:
            if not pygame.midi.get_init():
                pygame.midi.init()
            for i in range(pygame.midi.get_count()):
                info = pygame.midi.get_device_info(i)
                # info: (interf, name, input, output, opened)
                if info[2] == 1:  # Input device
                    name = info[1].decode()
                    devices.append((i, name))
        except Exception:
            pass
        return devices

    def set_device(self, device_id):
        self.device_id = device_id
        if self.running:
            self.stop()
            self.start()

    def run(self):
        if self.device_id is None:
            return

        try:
            inp = pygame.midi.Input(self.device_id)
            self.running = True
            while self.running:
                if inp.poll():
                    events = inp.read(10)
                    for e in events:
                        # e = [[status, data1, data2, data3], timestamp]
                        status = e[0][0]
                        data1 = e[0][1]
                        data2 = e[0][2]
                        self.message_received.emit(status, data1, data2)
                time.sleep(0.001)
            inp.close()
        except Exception as e:
            print(f"MIDI Runtime Error: {e}")
            self.running = False

    def stop(self):
        self.running = False
        self.wait()

    def __del__(self):
        self.stop()
        pygame.midi.quit()
