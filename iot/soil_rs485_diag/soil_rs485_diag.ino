#include <Arduino.h>

// Wiring is fixed by the user. Do not auto-remap these pins.
static constexpr int SOIL_TX_PIN = 17;
static constexpr int SOIL_RX_PIN = 15;

HardwareSerial soilPort(2);

uint16_t modbusCrc(const uint8_t *data, size_t length) {
  uint16_t crc = 0xFFFF;
  for (size_t i = 0; i < length; ++i) {
    crc ^= data[i];
    for (uint8_t bit = 0; bit < 8; ++bit) {
      crc = (crc & 1U) ? ((crc >> 1) ^ 0xA001U) : (crc >> 1);
    }
  }
  return crc;
}

void printHex(const uint8_t *data, size_t length) {
  for (size_t i = 0; i < length; ++i) {
    if (data[i] < 0x10) Serial.print('0');
    Serial.print(data[i], HEX);
    Serial.print(' ');
  }
}

bool findValidFrame(const uint8_t *raw, size_t rawLength) {
  for (size_t start = 0; start + 5 <= rawLength; ++start) {
    const uint8_t functionCode = raw[start + 1];
    size_t frameLength = 0;

    if (functionCode == 0x03) {
      frameLength = 5U + raw[start + 2];
    } else if (functionCode == 0x83) {
      frameLength = 5U;
    } else {
      continue;
    }

    if (frameLength < 5 || start + frameLength > rawLength) continue;

    const uint16_t expected = modbusCrc(raw + start, frameLength - 2);
    const uint16_t actual = raw[start + frameLength - 2] |
                            (uint16_t(raw[start + frameLength - 1]) << 8);
    if (expected != actual) continue;

    Serial.print("VALID frame at offset ");
    Serial.print(start);
    Serial.print(": ");
    printHex(raw + start, frameLength);
    Serial.println();
    return true;
  }
  return false;
}

bool runQuery(uint32_t baud, uint8_t address, uint16_t registerCount) {
  uint8_t request[8] = {
    address, 0x03, 0x00, 0x00,
    uint8_t(registerCount >> 8), uint8_t(registerCount), 0x00, 0x00
  };
  const uint16_t crc = modbusCrc(request, 6);
  request[6] = uint8_t(crc);
  request[7] = uint8_t(crc >> 8);

  while (soilPort.available()) soilPort.read();
  delay(50);

  Serial.print("TEST baud=");
  Serial.print(baud);
  Serial.print(" address=0x");
  if (address < 0x10) Serial.print('0');
  Serial.print(address, HEX);
  Serial.print(" registers=");
  Serial.print(registerCount);
  Serial.print(" TX: ");
  printHex(request, sizeof(request));
  Serial.println();

  soilPort.write(request, sizeof(request));
  soilPort.flush();

  uint8_t raw[128];
  size_t received = 0;
  const uint32_t started = millis();
  uint32_t lastByteAt = started;
  while (millis() - started < 1300U && received < sizeof(raw)) {
    while (soilPort.available() && received < sizeof(raw)) {
      raw[received++] = uint8_t(soilPort.read());
      lastByteAt = millis();
    }
    if (received > 0 && millis() - lastByteAt > 100U) break;
    delay(1);
  }

  Serial.print("RX ");
  Serial.print(received);
  Serial.print(" bytes: ");
  printHex(raw, received);
  Serial.println();

  const bool valid = findValidFrame(raw, received);
  if (!valid) Serial.println("No CRC-valid Modbus frame");
  Serial.println();
  return valid;
}

void runScan() {
  const uint32_t baudRates[] = {4800, 9600, 2400};
  const uint8_t addresses[] = {0x01, 0xFF};
  const uint16_t registerCounts[] = {7, 4, 1};
  bool anyValid = false;

  Serial.println("=== SOIL RS485 DIAGNOSTIC: UART2 TX17 RX15 ===");
  for (uint32_t baud : baudRates) {
    soilPort.end();
    delay(100);
    soilPort.setRxBufferSize(512);
    soilPort.begin(baud, SERIAL_8N1, SOIL_RX_PIN, SOIL_TX_PIN);
    delay(100);

    // A healthy TTL UART receiver must rest HIGH between frames. A mostly LOW
    // or unstable line points to wrong TXD/RXD wiring, missing converter power,
    // incompatible logic level, or a floating output before Modbus is involved.
    uint32_t idleHigh = 0;
    uint32_t idleLow = 0;
    const uint32_t idleStarted = micros();
    while (micros() - idleStarted < 50000U) {
      if (digitalRead(SOIL_RX_PIN)) ++idleHigh;
      else ++idleLow;
    }
    Serial.print("RX18 idle at baud ");
    Serial.print(baud);
    Serial.print(": HIGH samples=");
    Serial.print(idleHigh);
    Serial.print(" LOW samples=");
    Serial.println(idleLow);

    for (uint8_t address : addresses) {
      for (uint16_t count : registerCounts) {
        anyValid = runQuery(baud, address, count) || anyValid;
        delay(150);
      }
    }
  }

  // Some RS485 products use opposite A/B naming. Inverting both UART TX and
  // RX is a diagnostic equivalent of reversing the differential polarity.
  soilPort.end();
  delay(100);
  soilPort.setRxBufferSize(512);
  soilPort.begin(4800, SERIAL_8N1, SOIL_RX_PIN, SOIL_TX_PIN, true);
  Serial.println("=== 4800 8N1 WITH UART TX/RX INVERTED ===");
  for (uint8_t address : addresses) {
    for (uint16_t count : registerCounts) {
      anyValid = runQuery(4800, address, count) || anyValid;
      delay(150);
    }
  }

  Serial.println(anyValid
    ? "SCAN RESULT: at least one valid Modbus response found"
    : "SCAN RESULT: no valid Modbus response on TX17/RX15");
  Serial.println("Send T to run the scan again.");
}

void runDigitalLoopbackTest() {
  soilPort.end();
  delay(100);
  pinMode(SOIL_TX_PIN, OUTPUT);
  pinMode(SOIL_RX_PIN, INPUT_PULLDOWN);

  uint32_t highFailures = 0;
  uint32_t lowFailures = 0;
  for (uint32_t i = 0; i < 1000; ++i) {
    digitalWrite(SOIL_TX_PIN, HIGH);
    delayMicroseconds(20);
    if (digitalRead(SOIL_RX_PIN) != HIGH) ++highFailures;

    digitalWrite(SOIL_TX_PIN, LOW);
    delayMicroseconds(20);
    if (digitalRead(SOIL_RX_PIN) != LOW) ++lowFailures;
  }
  digitalWrite(SOIL_TX_PIN, HIGH);

  Serial.print("GPIO17->GPIO15 digital loopback: HIGH failures=");
  Serial.print(highFailures);
  Serial.print("/1000 LOW failures=");
  Serial.print(lowFailures);
  Serial.println("/1000");
  Serial.println((highFailures == 0 && lowFailures == 0)
    ? "DIGITAL LOOPBACK PASSED"
    : "DIGITAL LOOPBACK FAILED: jumper/pin/wiring problem");
  Serial.println("Send T for RS485 scan or L to repeat loopback.");
}

void setup() {
  Serial.begin(115200);
  const uint32_t started = millis();
  while (!Serial && millis() - started < 5000U) delay(10);
  delay(500);
  runScan();
}

void loop() {
  while (Serial.available()) {
    const char command = char(Serial.read());
    if (command == 'T' || command == 't') runScan();
    if (command == 'L' || command == 'l') runDigitalLoopbackTest();
  }
  delay(10);
}
