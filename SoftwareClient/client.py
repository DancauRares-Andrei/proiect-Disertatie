import sys
import time
import threading
import base64
import requests

from PyQt6.QtWidgets import QApplication

from riscv import RISCVProcessor
from interfataGrafica import LedPanel
from myAES import AESClient

SERVER = "http://localhost:5080"

class RSAClient:
    def __init__(self, e, n):
        self.e = int(e)
        self.n = int(n)

    def encrypt_block(self, data: bytes):
        m = int.from_bytes(data, "big")
        return pow(m, self.e, self.n)

# ======================
# Processor runner
# ======================
class ProcessorRunner:
    def __init__(self, processor):
        self.processor = processor
        self.exec_thread = None

    def start_program(self, program):
        self.stop_program()

        self.processor.reset()
        self.processor.load_program(program)

        self.exec_thread = threading.Thread(
            target=self.processor.run,
            daemon=True
        )
        self.exec_thread.start()

    def stop_program(self):
        if self.exec_thread and self.exec_thread.is_alive():
            self.processor.stop()
            self.exec_thread.join(timeout=1)


# ======================
# Secure Client
# ======================
class SecureClient:
    def __init__(self, username, password, processor, runner):
        self.username = username
        self.password = password
        self.jwt = None
        self.aes = AESClient()
        self.processor = processor
        self.runner = runner

    def login(self):
        r = requests.post(
            f"{SERVER}/api/auth/login",
            json={"username": self.username, "password": self.password}
        )
        r.raise_for_status()
        self.jwt = r.json()["token"]

    def get_rsa(self):
        r = requests.get(f"{SERVER}/api/crypto/publickey")
        r.raise_for_status()
        j = r.json()
        return RSAClient(j["e"], j["n"])

    # -------- HANDSHAKE --------
    def handshake(self, rsa: RSAClient):
        payload = self.aes.key + self.aes.iv
        encrypted = rsa.encrypt_block(payload)

        r = requests.post(
            f"{SERVER}/api/crypto/handshake",
            headers={"Authorization": f"Bearer {self.jwt}"},
            json={"encryptedKey": [str(encrypted)]}
        )
        r.raise_for_status()

    def loop(self):
        while True:
            r = requests.get(
                f"{SERVER}/api/crypto/program",
                headers={"Authorization": f"Bearer {self.jwt}"}
            )

            if r.status_code == 204:
                time.sleep(2)
                continue

            r.raise_for_status()

            encrypted = base64.b64decode(r.text)
            plaintext = self.aes.decrypt(encrypted)

            self.runner.start_program(plaintext)


# ======================
# MAIN (client.py)
# ======================
app = QApplication(sys.argv)

# UN SINGUR procesor
processor = RISCVProcessor()
runner = ProcessorRunner(processor)

# UI
window = LedPanel(processor)
processor.signals.step_done.connect(
    window.reg_table.update_registers
)
processor.signals.result_updated.connect(window.update_leds_from_result)
processor.signals.print_text.connect(window.append_text)
processor.signals.reset_text.connect(window.reset_text)
window.show()

# Client
client = SecureClient(
    "software",
    "2F7NJdA85qw_BXV",
    processor,
    runner
)

client.login()
rsa = client.get_rsa()
client.handshake(rsa)

window.textbox.setPlainText("Handshake complet!")

# Thread polling server
threading.Thread(
    target=client.loop,
    daemon=True
).start()

sys.exit(app.exec())

