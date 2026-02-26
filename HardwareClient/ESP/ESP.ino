#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <SoftwareSerial.h>
SoftwareSerial picoSerial(3, 2); 

const char* ap_ssid = "ESP_SERVER";
const char* ap_password = "12345678";

IPAddress laptopIP(192,168,4,2);
const int port = 5080;

const char* username = "admin";
const char* password = "R72Khgk4fvmI43W5dGYY0OEs4";

String jwtToken = "";
String rsa_e = "";
String rsa_n = "";

void startAccessPoint() {
  WiFi.mode(WIFI_AP);
  WiFi.softAP(ap_ssid, ap_password);
  Serial.println("AP started");
  Serial.println(WiFi.softAPIP());
}

String waitForInit() {
  String line = "";
  while (true) {
    if (Serial.available()) {
      char c = Serial.read();
      if (c == '\n') break;
      line += c;
    }
  }
  return line;
}

void sendStart() {
  Serial.println("<START>");
}

void sendEnd() {
  Serial.println();
  Serial.println("<END>");
}

bool login() {
  WiFiClient client;
  HTTPClient http;

  String url = "http://" + laptopIP.toString() + ":" + port + "/api/auth/login";
  http.begin(client, url);
  http.addHeader("Content-Type", "application/json");

  String body = "{\"username\":\"" + String(username) +
                "\",\"password\":\"" + String(password) + "\"}";

  int code = http.POST(body);
  if (code != 200) {
    http.end();
    Serial.println("Login failed");
    return false;
  }

  String response = http.getString();
  http.end();

  int start = response.indexOf("token\":\"") + 8;
  int end = response.indexOf("\"", start);
  jwtToken = response.substring(start, end);

  Serial.println("Login OK");
  return true;
}

void sendPublicKeyToPico() {
  Serial2.print("PUBKEY:");
  Serial2.print(rsa_e);
  Serial2.print(":");
  Serial2.print(rsa_n);
  Serial2.print("\n");
}

bool getPublicKey() {
  WiFiClient client;
  HTTPClient http;

  String url = "http://" + laptopIP.toString() + ":" + port + "/api/crypto/publickey";
  http.begin(client, url);

  int code = http.GET();
  if (code != 200) {
    http.end();
    Serial.println("Public key failed");
    return false;
  }

  String response = http.getString();
  http.end();

  int e_start = response.indexOf("\"e\":") + 4;
  int e_end = response.indexOf(",", e_start);
  rsa_e = response.substring(e_start, e_end);

  int n_start = response.indexOf("\"n\":") + 4;
  int n_end = response.indexOf("}", n_start);
  rsa_n = response.substring(n_start, n_end);

  Serial.println("Public key OK");

  sendPublicKeyToPico();   // ← AICI trimite către Pico

  return true;
}

bool sendHandshake(String encryptedKey) {
  WiFiClient client;
  HTTPClient http;

  String url = "http://" + laptopIP.toString() + ":" + port + "/api/crypto/handshake";
  http.begin(client, url);

  http.addHeader("Content-Type", "application/json");
  http.addHeader("Authorization", "Bearer " + jwtToken);

  String body = "{\"encryptedKey\":[" + encryptedKey + "]}";

  int code = http.POST(body);
  http.end();

  if (code == 200) {
    Serial.println("Handshake OK");
    return true;
  }

  Serial.println("Handshake failed");
  return false;
}

bool getProgram() {
  WiFiClient client;
  HTTPClient http;

  String url = "http://" + laptopIP.toString() + ":" + port + "/api/crypto/program";
  http.begin(client, url);

  http.addHeader("Authorization", "Bearer " + jwtToken);

  int code = http.GET();

  if (code == 204) {
    http.end();
    return false;
  }

  if (code != 200) {
    http.end();
    Serial.println("Program fetch error");
    return false;
  }

  WiFiClient* stream = http.getStreamPtr();
  sendStart();

  uint8_t buffer[512];

  while (http.connected()) {
    size_t size = stream->available();
    if (size) {
      int c = stream->readBytes(buffer, min((int)size, 512));
      Serial.write(buffer, c);
    }
    delay(1);
  }

  sendEnd();
  http.end();
  return true;
}

void setup() {
  Serial.begin(115200);
  startAccessPoint();

  delay(2000);

  while (!login()) delay(2000);
  while (!getPublicKey()) delay(2000);
}


void loop() {

  if (Serial.available()) {

    String initLine = waitForInit();

    if (initLine.startsWith("INIT:")) {

      int first = initLine.indexOf(':');
      int second = initLine.indexOf(':', first + 1);

      String encryptedKey = initLine.substring(first + 1, second);

      if (!sendHandshake(encryptedKey)) {
        return;
      }

      delay(500);

      while (true) {
        getProgram();
        delay(2000);
      }
    }
  }
}
