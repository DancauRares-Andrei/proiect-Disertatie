from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad
import requests
import base64
import time

SERVER = "http://localhost:5080"

# ======================
# AES
# ======================
class AESClient:
    def __init__(self):
        self.key = get_random_bytes(32)
        self.iv = get_random_bytes(16)

    def decrypt(self, data: bytes):
        cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
        return unpad(cipher.decrypt(data), 16)

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
        while True:
            r = requests.get(
                f"{SERVER}/api/crypto/next",
                headers={"Authorization": f"Bearer {self.jwt}"}
            )
            r.raise_for_status()

            encrypted = base64.b64decode(r.text)
            plaintext = self.aes.decrypt(encrypted)

            print("=== RISC-V instructions ===")
            for i in range(0, len(plaintext), 4):
                word = int.from_bytes(plaintext[i:i+4], "little")
                print(f"0x{word:08X}")

            time.sleep(2)

# ======================
# MAIN
# ======================
client = SecureClient(
    "rares.dancau24@student.ub.ro",
    "2F7NJdA85qw_BXV"
)

client.login()
rsa = client.get_rsa()
client.handshake(rsa)

print("🔐 Secure channel established.")
client.loop()
