#include <WiFi.h>
#include "wifi_secret.h"
#include <WebServer.h>

// ใช้ Wi-Fi เดียวกับคอม (คัดลอกจาก Gateway เดิม)

WebServer server(80);

String qualityText(int32_t rssi) {
  if (rssi >= -60) return "ดีมาก";
  if (rssi >= -70) return "ดี";
  if (rssi >= -75) return "พอใช้";
  if (rssi >= -80) return "อ่อน";
  return "อ่อนมาก/เสี่ยงหลุด";
}

String qualityColor(int32_t rssi) {
  if (rssi >= -70) return "#159947";
  if (rssi >= -75) return "#d68b00";
  return "#d52b2b";
}

void sendPage() {
  bool connected = WiFi.status() == WL_CONNECTED;
  int32_t rssi = connected ? WiFi.RSSI() : -100;
  String page;
  page.reserve(1800);
  page += F("<!doctype html><html><head><meta charset='utf-8'>");
  page += F("<meta name='viewport' content='width=device-width,initial-scale=1'>");
  page += F("<meta http-equiv='refresh' content='2'>");
  page += F("<title>Wi-Fi Range Test</title><style>");
  page += F("body{font-family:Arial,sans-serif;background:#eef2f5;margin:0;padding:24px;text-align:center}");
  page += F(".card{max-width:520px;margin:auto;background:white;border-radius:18px;padding:28px;box-shadow:0 5px 20px #0002}");
  page += F("h1{font-size:25px}.rssi{font-size:64px;font-weight:bold;margin:20px 0 4px}.status{font-size:28px;font-weight:bold}");
  page += F(".small{color:#555;margin-top:18px;line-height:1.7}.guide{margin-top:22px;text-align:left;background:#f5f7f9;padding:14px;border-radius:10px}");
  page += F("</style></head><body><div class='card'><h1>ทดสอบระยะ Wi-Fi</h1>");
  page += "<div class='rssi' style='color:" + qualityColor(rssi) + "'>";
  page += connected ? String(rssi) + " dBm" : "หลุด";
  page += F("</div><div class='status'>");
  page += connected ? qualityText(rssi) : "กำลังเชื่อมต่อใหม่";
  page += F("</div><div class='small'>SSID: ");
  page += WIFI_SSID;
  page += F("<br>IP บอร์ด: ");
  page += WiFi.localIP().toString();
  page += F("<br>ทำงานมาแล้ว: ");
  page += String(millis() / 1000);
  page += F(" วินาที<br>หน้านี้รีเฟรชทุก 2 วินาที</div>");
  page += F("<div class='guide'><b>เกณฑ์ติดตั้ง</b><br>-60 ถึง -70: ดี<br>-71 ถึง -75: ใช้ได้<br>-76 ถึง -80: ไม่เสถียร<br>ต่ำกว่า -80: ไม่ควรติด</div>");
  page += F("</div></body></html>");
  server.send(200, "text/html; charset=utf-8", page);
}

void connectWiFi() {
  if (WiFi.status() == WL_CONNECTED) return;
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.print("Connecting");
  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < 20000) {
    delay(500);
    Serial.print('.');
  }
  Serial.println();
  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("OPEN IN BROWSER: http://");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("Wi-Fi connection failed; retrying automatically");
  }
}

void setup() {
  Serial.begin(115200);
  delay(500);
  connectWiFi();
  server.on("/", sendPage);
  server.onNotFound(sendPage);
  server.begin();
}

void loop() {
  server.handleClient();
  static unsigned long lastReconnect = 0;
  if (WiFi.status() != WL_CONNECTED && millis() - lastReconnect >= 5000) {
    lastReconnect = millis();
    connectWiFi();
  }
  delay(2);
}
