import socket
import json
import time
import subprocess
import os
from PyQt6.QtCore import QThread, pyqtSignal

class LinkThread(QThread):
    """
    Gère la communication avec Carabiner (Ableton Link Bridge).
    Carabiner doit être présent (Carabiner.exe) ou lancé séparément.
    Ecoute sur TCP 17000 par défaut.
    """
    bpm_changed = pyqtSignal(float)
    beat_changed = pyqtSignal(float)
    num_peers_changed = pyqtSignal(int)
    connection_status = pyqtSignal(bool)

    def __init__(self, host='127.0.0.1', port=17000):
        super().__init__()
        self.host = host
        self.port = port
        self.running = False
        self.socket = None
        self.carabiner_process = None

    def run(self):
        self.running = True
        
        # Tentative de démarrage de Carabiner si non connecté
        if not self._check_connection():
            if os.path.exists("Carabiner.exe"):
                try:
                    # Démarrage silencieux
                    self.carabiner_process = subprocess.Popen(
                        ["Carabiner.exe"], 
                        stdout=subprocess.DEVNULL, 
                        stderr=subprocess.DEVNULL
                    )
                    time.sleep(1) # Laisser le temps de démarrer
                except Exception as e:
                    print(f"Failed to start Carabiner: {e}")

        while self.running:
            try:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.settimeout(1.0)
                self.socket.connect((self.host, self.port))
                self.connection_status.emit(True)
                
                buffer = ""
                while self.running:
                    try:
                        data = self.socket.recv(4096)
                        if not data: break
                        
                        buffer += data.decode('utf-8')
                        while '\n' in buffer:
                            line, buffer = buffer.split('\n', 1)
                            self.parse_message(line)
                    except socket.timeout:
                        continue
                    except Exception:
                        break
            except Exception:
                self.connection_status.emit(False)
                time.sleep(2)
            finally:
                if self.socket:
                    self.socket.close()
                    self.socket = None

    def _check_connection(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.5)
            s.connect((self.host, self.port))
            s.close()
            return True
        except:
            return False

    def parse_message(self, line):
        line = line.strip()
        # Carabiner envoie des messages type: status { "bpm": 120.0, ... }
        if line.startswith("status"):
            try:
                json_str = line[line.find('{'):]
                data = json.loads(json_str)
                if 'bpm' in data: self.bpm_changed.emit(float(data['bpm']))
                if 'beat' in data: self.beat_changed.emit(float(data['beat']))
                if 'num_peers' in data: self.num_peers_changed.emit(int(data['num_peers']))
            except: pass

    def stop(self):
        self.running = False
        if self.carabiner_process:
            self.carabiner_process.terminate()
        self.wait()