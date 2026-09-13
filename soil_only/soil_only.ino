#include <Arduino.h>

#define SOIL_TX_PIN 17   // ESP TX -> RXD ตัวแปลง
#define SOIL_RX_PIN 18   // ESP RX <- TXD ตัวแปลง

HardwareSerial soilSerial(2);

const uint8_t requestSoil[8] = {
  0x01, 0x03, 0x00, 0x00,
  0x00, 0x07, 0x04, 0x08
};

uint16_t modbusCRC(const uint8_t *data, size_t length) {
  uint16_t crc = 0xFFFF;

  for (size_t i = 0; i < length; i++) {
    crc ^= data[i];

    for (uint8_t bit = 0; bit < 8; bit++) {
      if (crc & 0x0001) {
        crc = (crc >> 1) ^ 0xA001;
      } else {
        crc >>= 1;
      }
    }
  }

  return crc;
}

void printHex(const uint8_t *data, size_t length) {
  for (size_t i = 0; i < length; i++) {
    if (data[i] < 0x10) Serial.print("0");
    Serial.print(data[i], HEX);
    Serial.print(" ");
  }
  Serial.println();
}

bool readSoil() {
  while (soilSerial.available()) {
    soilSerial.read();
  }

  Serial.print("TX: ");
  printHex(requestSoil, sizeof(requestSoil));

  soilSerial.write(requestSoil, sizeof(requestSoil));
  soilSerial.flush();

  uint8_t response[64];
  size_t received = 0;
  unsigned long start = millis();

  while (millis() - start < 1500 && received < sizeof(response)) {
    while (soilSerial.available() && received < sizeof(response)) {
      response[received++] = soilSerial.read();
    }
    delay(1);
  }

  Serial.printf("RX (%u bytes): ", (unsigned)received);
  printHex(response, received);

  // ค้นหาเฟรมที่ถูกต้อง เผื่อตัวแปลงส่ง echo มาก่อน
  for (size_t offset = 0; offset + 19 <= received; offset++) {
    uint8_t *frame = &response[offset];

    if (frame[0] != 0x01 ||
        frame[1] != 0x03 ||
        frame[2] != 0x0E) {
      continue;
    }

    uint16_t calculatedCRC = modbusCRC(frame, 17);
    uint16_t receivedCRC =
      frame[17] | ((uint16_t)frame[18] << 8);

    if (calculatedCRC != receivedCRC) {
      Serial.println("CRC ERROR");
      continue;
    }

    auto reg = [&](uint8_t index) -> uint16_t {
      uint8_t pos = 3 + index * 2;
      return ((uint16_t)frame[pos] << 8) |
             frame[pos + 1];
    };

    float moisture    = reg(0) / 10.0;
    float temperature = (int16_t)reg(1) / 10.0;
    uint16_t ec       = reg(2);
    float ph          = reg(3) / 10.0;
    uint16_t n        = reg(4);
    uint16_t p        = reg(5);
    uint16_t k        = reg(6);

    Serial.println("=== SOIL DATA OK ===");
    Serial.printf("Moisture    : %.1f %%\n", moisture);
    Serial.printf("Temperature : %.1f C\n", temperature);
    Serial.printf("EC          : %u us/cm\n", ec);
    Serial.printf("pH          : %.1f\n", ph);
    Serial.printf("Nitrogen    : %u mg/kg\n", n);
    Serial.printf("Phosphorus  : %u mg/kg\n", p);
    Serial.printf("Potassium   : %u mg/kg\n", k);

    return true;
  }

  Serial.println("FAILED: no valid 19-byte Modbus frame");
  return false;
}

void setup() {
  Serial.begin(115200);

  unsigned long start = millis();
  while (!Serial && millis() - start < 5000) {
    delay(10);
  }

  soilSerial.setRxBufferSize(256);
  soilSerial.begin(
    4800,
    SERIAL_8N1,
    SOIL_RX_PIN,
    SOIL_TX_PIN
  );

  Serial.println();
  Serial.println("=== SOIL ONLY TEST ===");
  Serial.printf("UART2 RX=GPIO%d TX=GPIO%d\n", SOIL_RX_PIN, SOIL_TX_PIN);
  Serial.println("พิมพ์ T เพื่ออ่านค่าดิน");

  delay(1000);
  readSoil();
}

void loop() {
  if (Serial.available()) {
    char command = Serial.read();

    if (command == 'T' || command == 't') {
      Serial.println();
      Serial.println("Manual soil test");
      readSoil();
    }
  }
}
