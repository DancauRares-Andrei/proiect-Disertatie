import gmpy2

def power(base, exponent, mod):
    result = 1
    base %= mod
    while exponent > 0:
        if exponent & 1:
            result = (result * base) % mod
        base = (base * base) % mod
        exponent >>= 1
    return result

class RSAClient:
    def __init__(self, e, n):
        self.e = int(e)
        self.n = int(n)

    def encrypt_bytes(self, data: bytes):
        return [power(b, self.e, self.n) for b in data]

from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad

class AESClient:
    def __init__(self):
        self.key = get_random_bytes(32)  # 256-bit
        self.iv = get_random_bytes(16)

    def encrypt(self, data: bytes):
        cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
        return cipher.encrypt(pad(data, 16))

    def decrypt(self, data: bytes):
        cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
        return unpad(cipher.decrypt(data), 16)

import requests
import json
import base64

SERVER = "http://localhost:5080"

class SecureClient:
    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.jwt = None
        self.aes = AESClient()

    def login(self):
        r = requests.post(
            f"{SERVER}/api/auth/login",
            json={
                "username": self.email,
                "password": self.password
            }
        )
        r.raise_for_status()
        self.jwt = r.json()["token"]

    def get_rsa_public_key(self):
        r = requests.get(f"{SERVER}/api/crypto/publickey")
        print(r.status_code, r.text)
        r.raise_for_status()
        data = r.json()
        return RSAClient(data["e"], data["n"])


    def exchange_aes_key(self, rsa: RSAClient):
        payload = self.aes.key + self.aes.iv       # 48 bytes
        payload_int = int.from_bytes(payload, 'big')
        encrypted_int = pow(payload_int, rsa.e, rsa.n)

        r = requests.post(
            f"{SERVER}/api/crypto/handshake",
            headers={
                "Authorization": f"Bearer {self.jwt}",
                "Content-Type": "application/json"
            },
            json={"encryptedKey": [str(encrypted_int)]}  # un singur int în listă
        )
        r.raise_for_status()


    
    def send_message(self, message: str):
        r = requests.post(
            f"{SERVER}/api/crypto/send",
            headers={
                "Authorization": f"Bearer {self.jwt}",
                "Content-Type": "application/json"
            },
            json={
                "plainText": message
            }
        )
        r.raise_for_status()
        data = r.json()
        ciphertext = base64.b64decode(data["cipherText"])
        return self.aes.decrypt(ciphertext)


client = SecureClient(
    "rares.dancau24@student.ub.ro",
    "2F7NJdA85qw_BXV"
)

client = SecureClient(
    "rares.dancau24@student.ub.ro",
    "2F7NJdA85qw_BXV"
)

# 1️⃣ Login + JWT
client.login()

# 2️⃣ Obține cheile RSA
rsa = client.get_rsa_public_key()

# 3️⃣ Handshake (schimb AES key)
client.exchange_aes_key(rsa)
print("Handshake complet. AES activ.")

# 4️⃣ Trimite mesaj către server
plaintext = client.send_message("Salut client!")
print("Mesaj primit decriptat:", plaintext.decode())


