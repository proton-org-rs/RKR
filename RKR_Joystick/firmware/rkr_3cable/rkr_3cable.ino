/* RKR three-cable controller, protocol RKR3 1.
   Uno R3 / classic Nano / Mega 2560, three STEP/DIR/ENABLE drivers.
   Positions count emitted STEP pulses. Positive means cable take-up.
   Fixed-rate jogging, maximum 1000 pulses/s per motor. No acceleration ramp.
*/
#include <Arduino.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>

const uint8_t STEP_PIN[3] = {2, 5, 8};
const uint8_t DIR_PIN[3] = {3, 6, 9};
const uint8_t ENABLE_PIN[3] = {4, 7, 10};
// Verify each driver's enable polarity. Set HIGH for an active-high input.
const uint8_t ENABLE_ACTIVE[3] = {LOW, LOW, LOW};
const uint32_t WATCHDOG_MS = 400;
const int32_t MAX_RATE_MILLI = 1000000; // 1000 pulses/s, units of 0.001 pulse/s.
const int32_t HARD_LIMIT = 20000;
const uint8_t PULSE_US = 10;

int32_t position[3] = {0, 0, 0};
int32_t rateMilli[3] = {0, 0, 0};
int32_t lowLimit[3], highLimit[3];
int8_t motorSign[3] = {1, 1, 1};
uint32_t intervalUs[3], nextStep[3];
bool armed = false, referenced = false, configured = false;
uint8_t faultCode = 0; // 0 OK, 1 watchdog, 2/3/4 motor limit, 5 bad input.
uint32_t lastContact = 0;
char inputLine[128];
uint8_t used = 0;
bool overflowed = false;

void stopMotion() {
  for (uint8_t i = 0; i < 3; ++i) rateMilli[i] = 0;
}

void disarmWithFault(uint8_t code) {
  stopMotion();
  armed = false;
  faultCode = code;
}

void sendState(long sequence) {
  Serial.print(sequence);
  Serial.print(F(" STATE"));
  for (uint8_t i = 0; i < 3; ++i) { Serial.print(' '); Serial.print(position[i]); }
  Serial.print(' '); Serial.print(armed ? 1 : 0);
  Serial.print(' '); Serial.print(referenced ? 1 : 0);
  Serial.print(' '); Serial.print(faultCode);
  for (uint8_t i = 0; i < 3; ++i) { Serial.print(' '); Serial.print(rateMilli[i]); }
  Serial.println();
}

void sendError(long sequence, const char *message) {
  disarmWithFault(5);
  Serial.print(sequence); Serial.print(F(" ERR ")); Serial.println(message);
}

void serviceMotion() {
  if (armed && uint32_t(millis() - lastContact) >= WATCHDOG_MS) disarmWithFault(1);
  if (!armed) return;
  const uint32_t now = micros();
  bool pulse[3] = {false, false, false};
  bool anyPulse = false;
  for (uint8_t i = 0; i < 3; ++i) {
    if (rateMilli[i] == 0 || int32_t(now - nextStep[i]) < 0) continue;
    const int8_t direction = rateMilli[i] > 0 ? 1 : -1;
    if ((direction > 0 && position[i] >= highLimit[i]) ||
        (direction < 0 && position[i] <= lowLimit[i])) {
      disarmWithFault(i + 2); // Stop the whole requested motion on any limit.
      return;
    }
    pulse[i] = true;
    anyPulse = true;
  }
  if (!anyPulse) return;
  for (uint8_t i = 0; i < 3; ++i) {
    if (!pulse[i]) continue;
    digitalWrite(STEP_PIN[i], HIGH);
    position[i] += rateMilli[i] > 0 ? 1 : -1;
    // Preserve cadence under small delays, but never emit catch-up bursts.
    nextStep[i] += intervalUs[i];
    if (int32_t(now - nextStep[i]) >= 0) nextStep[i] = now + intervalUs[i];
  }
  delayMicroseconds(PULSE_US);
  for (uint8_t i = 0; i < 3; ++i) if (pulse[i]) digitalWrite(STEP_PIN[i], LOW);
}

bool readInteger(const char *text, long &value) {
  if (!text || !*text) return false;
  char *end;
  errno = 0;
  value = strtol(text, &end, 10);
  return *end == '\0' && errno != ERANGE;
}

void handleCommand(char *line) {
  long sequence = 0;
  if (!readInteger(strtok(line, " \t"), sequence) || sequence < 0 || sequence > 1000000) {
    sendError(0, "SEQUENCE"); return;
  }
  const char *operation = strtok(NULL, " \t");
  if (!operation) { sendError(sequence, "COMMAND"); return; }
  long args[9];
  uint8_t count = 0;
  char *token;
  while ((token = strtok(NULL, " \t")) != NULL) {
    if (count == 9 || !readInteger(token, args[count])) {
      sendError(sequence, "ARGUMENTS"); return;
    }
    ++count;
  }
  if (!strcmp(operation, "HELLO") && count == 0) {
    disarmWithFault(0);
    Serial.print(sequence); Serial.println(F(" RKR3 1")); return;
  }
  if (!strcmp(operation, "STOP") && count == 0) {
    stopMotion(); lastContact = millis(); sendState(sequence); return;
  }
  if (!strcmp(operation, "DISARM") && count == 0) {
    stopMotion(); armed = false; sendState(sequence); return;
  }
  if (!strcmp(operation, "STATE") && count == 0) {
    // STATE is observational. Only a fresh V command renews motion authorization.
    sendState(sequence); return;
  }
  if (!strcmp(operation, "CONFIG") && count == 9 && !armed) {
    for (uint8_t i = 0; i < 3; ++i) {
      if ((args[i] != 1 && args[i] != -1) || args[3 + i*2] < -HARD_LIMIT ||
          args[3 + i*2] >= 0 || args[4 + i*2] <= 0 || args[4 + i*2] > HARD_LIMIT) {
        sendError(sequence, "CONFIG_RANGE"); return;
      }
    }
    stopMotion();
    for (uint8_t i = 0; i < 3; ++i) {
      motorSign[i] = args[i]; lowLimit[i] = args[3 + i*2]; highLimit[i] = args[4 + i*2];
    }
    configured = true; referenced = false; faultCode = 0;
    sendState(sequence); return;
  }
  if (!strcmp(operation, "ZERO") && count == 0 && configured && !armed) {
    for (uint8_t i = 0; i < 3; ++i) position[i] = 0;
    referenced = true; faultCode = 0; sendState(sequence); return;
  }
  if (!strcmp(operation, "ARM") && count == 0 && configured && referenced && !armed) {
    stopMotion();
    for (uint8_t i = 0; i < 3; ++i) digitalWrite(ENABLE_PIN[i], ENABLE_ACTIVE[i]);
    armed = true; faultCode = 0; lastContact = millis(); sendState(sequence); return;
  }
  if (!strcmp(operation, "V") && count == 3 && configured && referenced && armed) {
    for (uint8_t i = 0; i < 3; ++i) {
      if (args[i] < -MAX_RATE_MILLI || args[i] > MAX_RATE_MILLI) {
        sendError(sequence, "RATE_RANGE"); return;
      }
    }
    const uint32_t now = micros();
    for (uint8_t i = 0; i < 3; ++i) {
      if (args[i] == rateMilli[i]) continue;
      rateMilli[i] = args[i];
      if (rateMilli[i] == 0) continue;
      digitalWrite(DIR_PIN[i], (rateMilli[i] > 0 ? 1 : -1) * motorSign[i] > 0 ? HIGH : LOW);
      intervalUs[i] = 1000000000UL / uint32_t(labs(rateMilli[i]));
      nextStep[i] = now + intervalUs[i];
    }
    lastContact = millis(); sendState(sequence); return;
  }
  sendError(sequence, "COMMAND_OR_STATE");
}

void setup() {
  for (uint8_t i = 0; i < 3; ++i) {
    digitalWrite(ENABLE_PIN[i], !ENABLE_ACTIVE[i]); pinMode(ENABLE_PIN[i], OUTPUT);
    digitalWrite(STEP_PIN[i], LOW); pinMode(STEP_PIN[i], OUTPUT);
    digitalWrite(DIR_PIN[i], LOW); pinMode(DIR_PIN[i], OUTPUT);
  }
  Serial.begin(115200);
  Serial.println(F("RKR3 READY 1"));
}

void loop() {
  serviceMotion();
  for (uint8_t count = 0; count < 16 && Serial.available(); ++count) {
    const char ch = Serial.read();
    if (ch == '\r') continue;
    if (ch == '\n') {
      if (overflowed) sendError(0, "LINE_TOO_LONG_OR_BINARY");
      else { inputLine[used] = '\0'; handleCommand(inputLine); }
      used = 0; overflowed = false;
    } else if (!overflowed) {
      if (ch < ' ' || ch > '~' || used == sizeof(inputLine) - 1) {
        overflowed = true; disarmWithFault(5);
      } else inputLine[used++] = ch;
    }
    serviceMotion();
  }
}
