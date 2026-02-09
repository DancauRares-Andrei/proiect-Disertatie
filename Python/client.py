from myAES import AESClient
from riscv import RISCVProcessor
import requests
import base64
import time
import threading

SERVER = "http://localhost:5080"

riscvProcessor = RISCVProcessor()
# ======================
# RSA (manual)
# ======================
class RSAClient:
    def __init__(self, e, n):
        self.e = int(e)
        self.n = int(n)

    def encrypt_block(self, data: bytes):
        m = int.from_bytes(data, "big")
        return pow(m, self.e, self.n)

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
    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.jwt = None
        self.aes = AESClient()

    def login(self):
        r = requests.post(
            f"{SERVER}/api/auth/login",
            json={"username": self.email, "password": self.password}
        )
        r.raise_for_status()
        self.jwt = r.json()["token"]

    def get_rsa(self):
        r = requests.get(f"{SERVER}/api/crypto/publickey")
        r.raise_for_status()
        j = r.json()
        return RSAClient(j["e"], j["n"])

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
        riscvProcessor = RISCVProcessor()
        runner = ProcessorRunner(riscvProcessor)
        while True:
            r = requests.get(
                f"{SERVER}/api/crypto/program",
                headers={"Authorization": f"Bearer {self.jwt}"}
            )

            # 🔹 nimic de executat
            if r.status_code == 204:
                time.sleep(2)
                continue

            # 🔹 orice altă eroare reală
            r.raise_for_status()

            encrypted = base64.b64decode(r.text)
            plaintext = self.aes.decrypt(encrypted)
            runner.start_program(plaintext)


# ======================
# MAIN
# ======================
client = SecureClient(
    "admin",
    "2F7NJdA85qw_BXV"
)

client.login()
rsa = client.get_rsa()
client.handshake(rsa)

print("Handshake complet!")
client.loop()
