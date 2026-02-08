try:
    from pythonosc import dispatcher, osc_server, udp_client
    OSC_AVAILABLE = True
except ImportError:
    OSC_AVAILABLE = False

from PyQt6.QtCore import QThread, pyqtSignal

class OscThread(QThread):
    message_received = pyqtSignal(str, object) # address, value

    def __init__(self, ip="127.0.0.1", port=8000):
        super().__init__()
        self.ip = ip
        self.port = port
        self.server = None
        self.running = False

    def run(self):
        if not OSC_AVAILABLE:
            print("python-osc not installed. OSC disabled.")
            return

        try:
            disp = dispatcher.Dispatcher()
            disp.set_default_handler(self._handle_message)
            
            self.server = osc_server.ThreadingOSCUDPServer((self.ip, self.port), disp)
            self.running = True
            print(f"OSC Server started on {self.ip}:{self.port}")
            self.server.serve_forever()
        except Exception as e:
            print(f"OSC Error: {e}")
            self.running = False

    def _handle_message(self, address, *args):
        if not self.running: return
        val = args[0] if args else None
        self.message_received.emit(address, val)

    def stop(self):
        self.running = False
        if self.server:
            self.server.shutdown()
            self.server.server_close()
