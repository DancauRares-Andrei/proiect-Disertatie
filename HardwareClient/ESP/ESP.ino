#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>

const char *ap_ssid     = "ESP_SERVER";
const char *ap_password = "12345678";

IPAddress laptopIP(192, 168, 4, 2);
const int  port = 5080;

const char *username = "hardware";
const char *password = "R72Khgk4fvmI43W5dGYY0OEs4";

String jwtToken = "";
WiFiClient wifiClient;

#define BIG_LIMBS 64

struct BigInt {
  uint32_t d[BIG_LIMBS];
  int      len;

  BigInt() : len(1) { memset(d, 0, sizeof(d)); }
};

void bi_zero(BigInt &a) {
  memset(a.d, 0, sizeof(a.d));
  a.len = 1;
}

void bi_normalize(BigInt &a) {
  a.len = BIG_LIMBS;
  while (a.len > 1 && a.d[a.len - 1] == 0) a.len--;
}

bool bi_is_zero(const BigInt &a) {
  for (int i = 0; i < a.len; i++) if (a.d[i]) return false;
  return true;
}

void bi_copy(BigInt &dst, const BigInt &src) {
  memcpy(dst.d, src.d, sizeof(src.d));
  dst.len = src.len;
}

// Compară: -1 a<b, 0 egal, +1 a>b
int bi_cmp(const BigInt &a, const BigInt &b) {
  int top = (a.len > b.len) ? a.len : b.len;
  for (int i = top - 1; i >= 0; i--) {
    uint32_t ai = (i < a.len) ? a.d[i] : 0;
    uint32_t bi = (i < b.len) ? b.d[i] : 0;
    if (ai < bi) return -1;
    if (ai > bi) return  1;
  }
  return 0;
}

void bi_from_dec(BigInt &r, const char *s) {
  bi_zero(r);
  while (*s) {
    uint64_t carry = (uint8_t)(*s++ - '0');
    for (int i = 0; i < BIG_LIMBS; i++) {
      uint64_t cur = (uint64_t)r.d[i] * 10 + carry;
      r.d[i] = (uint32_t)(cur & 0xFFFFFFFFULL);
      carry   = cur >> 32;
    }
  }
  bi_normalize(r);
}

void bi_from_bytes_be(BigInt &r, const uint8_t *buf, int len) {
  bi_zero(r);
  for (int i = 0; i < len; i++) {
    uint64_t carry = buf[i];
    for (int j = 0; j < BIG_LIMBS; j++) {
      uint64_t cur = (uint64_t)r.d[j] * 256 + carry;
      r.d[j] = (uint32_t)(cur & 0xFFFFFFFFULL);
      carry   = cur >> 32;
    }
  }
  bi_normalize(r);
}

String bi_to_dec(const BigInt &a) {
  if (bi_is_zero(a)) return "0";
  BigInt tmp; bi_copy(tmp, a);
  char buf[700];
  int pos = sizeof(buf) - 1;
  buf[pos] = '\0';
  while (!bi_is_zero(tmp)) {
    uint64_t rem = 0;
    for (int i = tmp.len - 1; i >= 0; i--) {
      uint64_t cur = (rem << 32) | tmp.d[i];
      tmp.d[i] = (uint32_t)(cur / 10);
      rem = cur % 10;
    }
    bi_normalize(tmp);
    buf[--pos] = '0' + (char)rem;
  }
  return String(buf + pos);
}

void bi_add(BigInt &r, const BigInt &a, const BigInt &b) {
  int top = ((a.len > b.len) ? a.len : b.len) + 1;
  if (top > BIG_LIMBS) top = BIG_LIMBS;
  uint64_t carry = 0;
  for (int i = 0; i < top; i++) {
    uint64_t s = carry
      + ((i < a.len) ? (uint64_t)a.d[i] : 0)
      + ((i < b.len) ? (uint64_t)b.d[i] : 0);
    r.d[i] = (uint32_t)(s & 0xFFFFFFFFULL);
    carry   = s >> 32;
  }
  r.len = top;
  bi_normalize(r);
}

void bi_sub(BigInt &r, const BigInt &a, const BigInt &b) {
  uint64_t borrow = 0;
  for (int i = 0; i < a.len; i++) {
    uint64_t ai = a.d[i];
    uint64_t bi = (i < b.len) ? (uint64_t)b.d[i] : 0;
    uint64_t s;
    if (ai >= bi + borrow) {
      s = ai - bi - borrow; borrow = 0;
    } else {
      s = ai + (1ULL << 32) - bi - borrow; borrow = 1;
    }
    r.d[i] = (uint32_t)s;
  }
  r.len = a.len;
  bi_normalize(r);
}

void bi_mul(BigInt &r, const BigInt &a, const BigInt &b) {
  bi_zero(r);
  for (int i = 0; i < a.len; i++) {
    uint64_t carry = 0;
    for (int j = 0; j < b.len; j++) {
      if (i + j >= BIG_LIMBS) break;
      uint64_t cur = (uint64_t)a.d[i] * b.d[j] + r.d[i+j] + carry;
      r.d[i+j] = (uint32_t)(cur & 0xFFFFFFFFULL);
      carry = cur >> 32;
    }
    int nxt = i + b.len;
    if (nxt < BIG_LIMBS) r.d[nxt] += (uint32_t)carry;
  }
  r.len = a.len + b.len;
  if (r.len > BIG_LIMBS) r.len = BIG_LIMBS;
  bi_normalize(r);
}

void bi_mod(BigInt &r, const BigInt &a, const BigInt &m) {
  bi_copy(r, a);

  int mBit = 0;
  for (int i = m.len * 32 - 1; i >= 0; i--) {
    if (m.d[i/32] & (1u << (i%32))) { mBit = i; break; }
  }

  int rBit = 0;
  for (int i = BIG_LIMBS * 32 - 1; i >= 0; i--) {
    if (r.d[i/32] & (1u << (i%32))) { rBit = i; break; }
  }

  for (int s = rBit - mBit; s >= 0; s--) {

    BigInt ms; bi_zero(ms);
    int ws = s / 32, bs = s % 32;
    for (int i = 0; i < m.len && i + ws < BIG_LIMBS; i++) {
      ms.d[i + ws] |= m.d[i] << bs;
      if (bs && i + ws + 1 < BIG_LIMBS)
        ms.d[i + ws + 1] |= m.d[i] >> (32 - bs);
    }
    ms.len = m.len + ws + 1;
    if (ms.len > BIG_LIMBS) ms.len = BIG_LIMBS;
    bi_normalize(ms);

    if (bi_cmp(r, ms) >= 0) {
      BigInt tmp; bi_sub(tmp, r, ms); bi_copy(r, tmp);
    }
  }
  bi_normalize(r);
}

void bi_modexp(BigInt &r, const BigInt &base, const BigInt &exp, const BigInt &mod) {
  bi_zero(r); r.d[0] = 1; r.len = 1;   // r = 1
  BigInt b; bi_mod(b, base, mod);

  int expBits = exp.len * 32;
  for (int i = 0; i < expBits; i++) {
    if (exp.d[i/32] & (1u << (i%32))) {
      BigInt tmp; bi_mul(tmp, r, b); bi_mod(r, tmp, mod);
    }
    BigInt b2; bi_mul(b2, b, b); bi_mod(b, b2, mod);
  }
  bi_normalize(r);
}

const uint8_t SBOX[256] PROGMEM = {
  0x63,0x7C,0x77,0x7B,0xF2,0x6B,0x6F,0xC5,0x30,0x01,0x67,0x2B,0xFE,0xD7,0xAB,0x76,
  0xCA,0x82,0xC9,0x7D,0xFA,0x59,0x47,0xF0,0xAD,0xD4,0xA2,0xAF,0x9C,0xA4,0x72,0xC0,
  0xB7,0xFD,0x93,0x26,0x36,0x3F,0xF7,0xCC,0x34,0xA5,0xE5,0xF1,0x71,0xD8,0x31,0x15,
  0x04,0xC7,0x23,0xC3,0x18,0x96,0x05,0x9A,0x07,0x12,0x80,0xE2,0xEB,0x27,0xB2,0x75,
  0x09,0x83,0x2C,0x1A,0x1B,0x6E,0x5A,0xA0,0x52,0x3B,0xD6,0xB3,0x29,0xE3,0x2F,0x84,
  0x53,0xD1,0x00,0xED,0x20,0xFC,0xB1,0x5B,0x6A,0xCB,0xBE,0x39,0x4A,0x4C,0x58,0xCF,
  0xD0,0xEF,0xAA,0xFB,0x43,0x4D,0x33,0x85,0x45,0xF9,0x02,0x7F,0x50,0x3C,0x9F,0xA8,
  0x51,0xA3,0x40,0x8F,0x92,0x9D,0x38,0xF5,0xBC,0xB6,0xDA,0x21,0x10,0xFF,0xF3,0xD2,
  0xCD,0x0C,0x13,0xEC,0x5F,0x97,0x44,0x17,0xC4,0xA7,0x7E,0x3D,0x64,0x5D,0x19,0x73,
  0x60,0x81,0x4F,0xDC,0x22,0x2A,0x90,0x88,0x46,0xEE,0xB8,0x14,0xDE,0x5E,0x0B,0xDB,
  0xE0,0x32,0x3A,0x0A,0x49,0x06,0x24,0x5C,0xC2,0xD3,0xAC,0x62,0x91,0x95,0xE4,0x79,
  0xE7,0xC8,0x37,0x6D,0x8D,0xD5,0x4E,0xA9,0x6C,0x56,0xF4,0xEA,0x65,0x7A,0xAE,0x08,
  0xBA,0x78,0x25,0x2E,0x1C,0xA6,0xB4,0xC6,0xE8,0xDD,0x74,0x1F,0x4B,0xBD,0x8B,0x8A,
  0x70,0x3E,0xB5,0x66,0x48,0x03,0xF6,0x0E,0x61,0x35,0x57,0xB9,0x86,0xC1,0x1D,0x9E,
  0xE1,0xF8,0x98,0x11,0x69,0xD9,0x8E,0x94,0x9B,0x1E,0x87,0xE9,0xCE,0x55,0x28,0xDF,
  0x8C,0xA1,0x89,0x0D,0xBF,0xE6,0x42,0x68,0x41,0x99,0x2D,0x0F,0xB0,0x54,0xBB,0x16
};

const uint8_t INV_SBOX[256] PROGMEM = {
  0x52,0x09,0x6A,0xD5,0x30,0x36,0xA5,0x38,0xBF,0x40,0xA3,0x9E,0x81,0xF3,0xD7,0xFB,
  0x7C,0xE3,0x39,0x82,0x9B,0x2F,0xFF,0x87,0x34,0x8E,0x43,0x44,0xC4,0xDE,0xE9,0xCB,
  0x54,0x7B,0x94,0x32,0xA6,0xC2,0x23,0x3D,0xEE,0x4C,0x95,0x0B,0x42,0xFA,0xC3,0x4E,
  0x08,0x2E,0xA1,0x66,0x28,0xD9,0x24,0xB2,0x76,0x5B,0xA2,0x49,0x6D,0x8B,0xD1,0x25,
  0x72,0xF8,0xF6,0x64,0x86,0x68,0x98,0x16,0xD4,0xA4,0x5C,0xCC,0x5D,0x65,0xB6,0x92,
  0x6C,0x70,0x48,0x50,0xFD,0xED,0xB9,0xDA,0x5E,0x15,0x46,0x57,0xA7,0x8D,0x9D,0x84,
  0x90,0xD8,0xAB,0x00,0x8C,0xBC,0xD3,0x0A,0xF7,0xE4,0x58,0x05,0xB8,0xB3,0x45,0x06,
  0xD0,0x2C,0x1E,0x8F,0xCA,0x3F,0x0F,0x02,0xC1,0xAF,0xBD,0x03,0x01,0x13,0x8A,0x6B,
  0x3A,0x91,0x11,0x41,0x4F,0x67,0xDC,0xEA,0x97,0xF2,0xCF,0xCE,0xF0,0xB4,0xE6,0x73,
  0x96,0xAC,0x74,0x22,0xE7,0xAD,0x35,0x85,0xE2,0xF9,0x37,0xE8,0x1C,0x75,0xDF,0x6E,
  0x47,0xF1,0x1A,0x71,0x1D,0x29,0xC5,0x89,0x6F,0xB7,0x62,0x0E,0xAA,0x18,0xBE,0x1B,
  0xFC,0x56,0x3E,0x4B,0xC6,0xD2,0x79,0x20,0x9A,0xDB,0xC0,0xFE,0x78,0xCD,0x5A,0xF4,
  0x1F,0xDD,0xA8,0x33,0x88,0x07,0xC7,0x31,0xB1,0x12,0x10,0x59,0x27,0x80,0xEC,0x5F,
  0x60,0x51,0x7F,0xA9,0x19,0xB5,0x4A,0x0D,0x2D,0xE5,0x7A,0x9F,0x93,0xC9,0x9C,0xEF,
  0xA0,0xE0,0x3B,0x4D,0xAE,0x2A,0xF5,0xB0,0xC8,0xEB,0xBB,0x3C,0x83,0x53,0x99,0x61,
  0x17,0x2B,0x04,0x7E,0xBA,0x77,0xD6,0x26,0xE1,0x69,0x14,0x63,0x55,0x21,0x0C,0x7D
};

const uint8_t Rcon[10] = {0x01,0x02,0x04,0x08,0x10,0x20,0x40,0x80,0x1B,0x36};

uint8_t aes_key[16];
uint8_t aes_iv[16];
uint8_t roundKey[176];

uint8_t xtime_f(uint8_t a) {
  return (a & 0x80) ? ((a << 1) ^ 0x1B) : (a << 1);
}
uint8_t gf_mul(uint8_t a, uint8_t b) {
  uint8_t r = 0;
  for (int i = 0; i < 8; i++) {
    if (b & 1) r ^= a;
    a = xtime_f(a); b >>= 1;
  }
  return r;
}

void KeyExpansion() {
  memcpy(roundKey, aes_key, 16);
  int bytesGenerated = 16;
  int rconIdx = 0;
  uint8_t temp[4];

  while (bytesGenerated < 176) {
    for (int i = 0; i < 4; i++)
      temp[i] = roundKey[bytesGenerated - 4 + i];

    if (bytesGenerated % 16 == 0) {
      // RotWord
      uint8_t k = temp[0];
      temp[0]=temp[1]; temp[1]=temp[2]; temp[2]=temp[3]; temp[3]=k;
      // SubWord
      for (int i = 0; i < 4; i++) temp[i] = pgm_read_byte(&SBOX[temp[i]]);
      // Rcon
      temp[0] ^= Rcon[rconIdx++];
    }

    for (int a = 0; a < 4; a++) {
      roundKey[bytesGenerated] = roundKey[bytesGenerated-16] ^ temp[a];
      bytesGenerated++;
    }
  }
}

void AddRoundKey(uint8_t *state, int round) {
  for (int i = 0; i < 16; i++) state[i] ^= roundKey[round*16+i];
}

void inv_sub_bytes(uint8_t *s) {
  for (int i = 0; i < 16; i++) s[i] = pgm_read_byte(&INV_SBOX[s[i]]);
}

void inv_shift_rows(uint8_t *s) {
  uint8_t t[16] = {
    s[0],s[13],s[10],s[7],
    s[4],s[1], s[14],s[11],
    s[8],s[5], s[2], s[15],
    s[12],s[9],s[6], s[3]
  };
  memcpy(s, t, 16);
}

void inv_mix_columns(uint8_t *s) {
  for (int i = 0; i < 16; i += 4) {
    uint8_t a0=s[i],a1=s[i+1],a2=s[i+2],a3=s[i+3];
    s[i]  =gf_mul(a0,14)^gf_mul(a1,11)^gf_mul(a2,13)^gf_mul(a3,9);
    s[i+1]=gf_mul(a0,9) ^gf_mul(a1,14)^gf_mul(a2,11)^gf_mul(a3,13);
    s[i+2]=gf_mul(a0,13)^gf_mul(a1,9) ^gf_mul(a2,14)^gf_mul(a3,11);
    s[i+3]=gf_mul(a0,11)^gf_mul(a1,13)^gf_mul(a2,9) ^gf_mul(a3,14);
  }
}

void AES_decrypt_block(uint8_t *block) {
  uint8_t state[16]; memcpy(state, block, 16);
  AddRoundKey(state, 10);
  for (int r = 9; r >= 1; r--) {
    inv_shift_rows(state); inv_sub_bytes(state);
    AddRoundKey(state, r); inv_mix_columns(state);
  }
  inv_shift_rows(state); inv_sub_bytes(state); AddRoundKey(state, 0);
  memcpy(block, state, 16);
}

static const char b64ch[] =
  "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

int b64_decode(const String &in, uint8_t *out) {
  int outLen = 0; uint32_t buf = 0; int bits = 0;
  for (int i = 0; i < (int)in.length(); i++) {
    char c = in.charAt(i);
    if (c == '=') break;
    const char *p = strchr(b64ch, c);
    if (!p) continue;
    buf = (buf << 6) | (int)(p - b64ch);
    bits += 6;
    if (bits >= 8) { bits -= 8; out[outLen++] = (buf >> bits) & 0xFF; }
  }
  return outLen;
}

int pkcs7_unpad(uint8_t *data, int len) {
  if (len == 0) return 0;
  uint8_t pad = data[len-1];
  if (pad == 0 || pad > 16) return len;
  for (int i = len-pad; i < len; i++) if (data[i] != pad) return len;
  return len - pad;
}

bool login() {
  HTTPClient http;
  http.begin(wifiClient,
    "http://" + laptopIP.toString() + ":" + port + "/api/auth/login");
  http.addHeader("Content-Type","application/json");

  String body = "{\"username\":\"" + String(username) +
                "\",\"password\":\"" + String(password) + "\"}";
  int code = http.POST(body);
  if (code != 200) {
    Serial.printf("[LOGIN] HTTP %d\n", code); http.end(); return false;
  }

  String resp = http.getString(); http.end();
  int s = resp.indexOf("\"token\":\"");
  if (s < 0) return false;
  s += 9;
  jwtToken = resp.substring(s, resp.indexOf("\"", s));
  Serial.println("[LOGIN] OK");
  return true;
}

static String jsonExtractNum(const String &json, const char *key) {
  int pos = json.indexOf(key);
  if (pos < 0) return "";
  pos += strlen(key);
  while (pos < (int)json.length() &&
         (json.charAt(pos) == ' ' || json.charAt(pos) == ':' ||
          json.charAt(pos) == '"')) pos++;
  int end = pos;
  while (end < (int)json.length() && isDigit(json.charAt(end))) end++;
  return json.substring(pos, end);
}

bool getPublicKey(BigInt &e_out, BigInt &n_out) {
  HTTPClient http;
  http.begin(wifiClient,
    "http://" + laptopIP.toString() + ":" + port + "/api/crypto/publickey");
  int code = http.GET();
  if (code != 200) {
    Serial.printf("[PUBKEY] HTTP %d\n", code); http.end(); return false;
  }
  String resp = http.getString(); http.end();

  String e_str = jsonExtractNum(resp, "\"e\"");
  String n_str = jsonExtractNum(resp, "\"n\"");
  if (e_str.length() == 0 || n_str.length() == 0) {
    Serial.println("[PUBKEY] Parsare JSON esuata"); return false;
  }

  bi_from_dec(e_out, e_str.c_str());
  bi_from_dec(n_out, n_str.c_str());
  Serial.printf("[PUBKEY] e=%s... (%d cifre), n (%d cifre)\n",
    e_str.substring(0,8).c_str(), e_str.length(), n_str.length());
  return true;
}

void generateAES() {
  randomSeed(analogRead(A0) ^ micros());
  for (int i = 0; i < 16; i++) {
    aes_key[i] = random(0, 256);
    aes_iv[i]  = random(0, 256);
  }
  KeyExpansion();
}

bool sendHandshake(const BigInt &rsa_e, const BigInt &rsa_n) {
  Serial.println("[HANDSHAKE] Calculez RSA (poate dura cateva secunde)...");

  uint8_t payload[32];
  memcpy(payload,      aes_key, 16);
  memcpy(payload + 16, aes_iv,  16);

  BigInt m, c;
  bi_from_bytes_be(m, payload, 32);
  bi_modexp(c, m, rsa_e, rsa_n);

  String cStr = bi_to_dec(c);
  Serial.printf("[HANDSHAKE] c (%d cifre)\n", cStr.length());

  HTTPClient http;
  http.begin(wifiClient,
    "http://" + laptopIP.toString() + ":" + port + "/api/crypto/handshake");
  http.addHeader("Content-Type","application/json");
  http.addHeader("Authorization","Bearer " + jwtToken);

  String body = "{\"encryptedKey\":[\"" + cStr + "\"]}";
  int code = http.POST(body);
  http.end();

  if (code == 200) { Serial.println("[HANDSHAKE] OK"); return true; }
  Serial.printf("[HANDSHAKE] HTTP %d\n", code);
  return false;
}

bool getProgram() {
  HTTPClient http;
  http.begin(wifiClient,
    "http://" + laptopIP.toString() + ":" + port + "/api/crypto/program");
  http.addHeader("Authorization","Bearer " + jwtToken);

  int code = http.GET();
  if (code == 204) {
    Serial.println("[PROGRAM] Nimic disponibil."); http.end(); return false;
  }
  if (code != 200) {
    Serial.printf("[PROGRAM] HTTP %d\n", code); http.end(); return false;
  }

  String b64 = http.getString(); http.end();
  b64.trim();

  int maxLen = (b64.length() * 3) / 4 + 4;
  uint8_t *enc   = (uint8_t *)malloc(maxLen);
  uint8_t *plain = (uint8_t *)malloc(maxLen);
  if (!enc || !plain) {
    Serial.println("[PROGRAM] Memorie insuficienta!");
    free(enc); free(plain); return false;
  }

  int encLen = b64_decode(b64, enc);
  Serial.printf("[PROGRAM] %d bytes cifrati.\n", encLen);

  uint8_t prev[16]; memcpy(prev, aes_iv, 16);
  for (int i = 0; i < encLen; i += 16) {
    uint8_t block[16]; memcpy(block, enc + i, 16);
    AES_decrypt_block(block);
    for (int j = 0; j < 16; j++) plain[i+j] = block[j] ^ prev[j];
    memcpy(prev, enc + i, 16);  // prev = ciphertext original (CBC corect)
  }
  free(enc);

  int plainLen = pkcs7_unpad(plain, encLen);
  Serial.printf("[PROGRAM] Plaintext: %d bytes.\n", plainLen);

  Serial.println("[PROGRAM] --- BEGIN ---");
  for (int i = 0; i < plainLen; i++) {
    Serial.printf("%02X", plain[i]);
    Serial.print((i % 4 == 3) ? " " : "");
    if (i % 16 == 15) Serial.println();
  }
  Serial.println("\n[PROGRAM] --- END ---");

  free(plain);
  return true;
}

void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("\n[BOOT] ESP8266 Hardware Client");

  WiFi.mode(WIFI_AP);
  WiFi.softAP(ap_ssid, ap_password);
  Serial.print("[WIFI] AP pornit. IP ESP: ");
  Serial.println(WiFi.softAPIP());   // 192.168.4.1

  Serial.println("[WIFI] Asteapta conexiunea laptopului (5s)...");
  delay(5000);

  while (!login())       { Serial.println("[LOGIN] Reincerc..."); delay(3000); }

  BigInt rsa_e, rsa_n;
  while (!getPublicKey(rsa_e, rsa_n)) {
    Serial.println("[PUBKEY] Reincerc..."); delay(3000);
  }

  generateAES();

  while (!sendHandshake(rsa_e, rsa_n)) {
    Serial.println("[HANDSHAKE] Reincerc..."); delay(3000);
  }

  Serial.println("[SETUP] Gata. Pornesc polling...");
}

void loop() {
  getProgram();
  delay(2000);
}
