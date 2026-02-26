from machine import UART, Pin
import os
import ucryptolib

UART_BAUD = 115200
uart = UART(0, baudrate=UART_BAUD)

gpio_pins = [Pin(i, Pin.OUT) for i in range(16)]

def read_line():
    buffer = b''
    while True:
        if uart.any():
            c = uart.read(1)
            if c == b'\n':
                break
            buffer += c
    return buffer.decode()

def receive_pubkey():
    while True:
        line = read_line()
        if line.startswith("PUBKEY:"):
            _, e_str, n_str = line.split(":")
            return int(e_str), int(n_str)
        
def rsa_encrypt(data: bytes, e, n):
    m = int.from_bytes(data, "big")
    c = pow(m, e, n)
    return str(c)

def generate_key_iv():
    return os.urandom(16), os.urandom(16)

def aes_decrypt(ciphertext, key, iv):
    aes = ucryptolib.aes(key, 2, iv)
    plaintext = b''

    for i in range(0, len(ciphertext), 16):
        block = ciphertext[i:i+16]
        plaintext += aes.decrypt(block)

    return plaintext.rstrip(b"\x00")

def receive_packet():
    buffer = b''
    while True:
        if uart.any():
            buffer += uart.read()
            if b"<END>" in buffer:
                break

    start = buffer.find(b"<START>")
    end = buffer.find(b"<END>")
    return buffer[start+8:end].strip()

def main():
    e, n = receive_pubkey()
    key, iv = generate_key_iv()
    payload = key + iv
    encrypted_key = rsa_encrypt(payload, e, n)
    uart.write("INIT:{}:X\n".format(encrypted_key))
    ciphertext = receive_packet()
    plaintext = aes_decrypt(ciphertext, key, iv)
    print(plaintext)
    
main()


