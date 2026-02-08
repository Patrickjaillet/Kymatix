import time
import threading
from PyQt6.QtCore import QThread

try:
    import sacn
    SACN_AVAILABLE = True
except ImportError:
    SACN_AVAILABLE = False

class DMXThread(QThread):
    """
    Gère l'envoi de données DMX via sACN (E1.31).
    """
    def __init__(self, universe=1):
        super().__init__()
        self.universe = universe
        self.running = False
        self.sender = None
        self.dmx_data = [0] * 512
        self.fps = 40 # Standard DMX refresh rate
        self.lock = threading.Lock()
        
    def run(self):
        if not SACN_AVAILABLE:
            print("❌ sACN library not found. Install with 'pip install sacn'")
            return

        try:
            self.sender = sacn.sACNsender()
            self.sender.start()
            self.sender.activate_output(self.universe)
            self.sender[self.universe].multicast = True
            
            self.running = True
            print(f"💡 DMX (sACN) Started on Universe {self.universe}")
            
            while self.running:
                with self.lock:
                    self.sender[self.universe].dmx_data = tuple(self.dmx_data)
                time.sleep(1.0 / self.fps)
                
            self.sender.stop()
        except Exception as e:
            print(f"❌ DMX Error: {e}")
        
        print("💡 DMX Stopped")

    def set_channel(self, channel, value):
        if 1 <= channel <= 512:
            with self.lock:
                self.dmx_data[channel-1] = int(max(0, min(255, value)))

    def stop(self):
        self.running = False
        self.wait()