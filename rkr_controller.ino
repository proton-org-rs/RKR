/* RKR keyboard platform v1. No external Arduino libraries.
   Logical positive = tighten. INIT sets electrical direction signs and limits.
   Counts represent STEP pulses, NOT encoder measurements. See README.md.
   Constant-rate coordinated DDA; no acceleration ramp in this version. */
#include <Arduino.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>

const uint8_t STEP_PIN[2] = {2, 5}, DIR_PIN[2] = {3, 6}, EN_PIN[2] = {4, 7};
const uint8_t ENABLE_ACTIVE = LOW; // Matches uploaded sketches; verify driver wiring.
const long HARD_LIMIT = 20000, MAX_RATE = 1000;
const unsigned long WATCHDOG_MS = 500;
long pos[2] = {0, 0}, target[2], lowLimit[2], highLimit[2];
long magnitude[2], accum[2], ticks = 0, doneTicks = 0;
int direction[2], motorSign[2] = {1, 1};
bool busy = false, armed = false, referenced = false, configured = false;
unsigned long intervalUs, nextTick, lastContact;
char input[100]; uint8_t used = 0; bool overflowed = false;

void halt() { busy = false; }
void status() {
  Serial.print(F("STATE ")); Serial.print(pos[0]); Serial.print(' ');
  Serial.print(pos[1]); Serial.print(' '); Serial.print(busy ? 1 : 0);
  Serial.print(' '); Serial.print(armed ? 1 : 0); Serial.print(' ');
  Serial.println(referenced ? 1 : 0);
}
void error(const char *why) { Serial.print(F("ERR ")); Serial.println(why); }
bool inLimits(long a, long b) {
  return a >= lowLimit[0] && a <= highLimit[0] && b >= lowLimit[1] && b <= highLimit[1];
}
void serviceMotion() {
  if (armed && millis() - lastContact > WATCHDOG_MS) { halt(); armed = false; }
  if (!busy || (long)(micros() - nextTick) < 0) return;
  // Never catch up with a burst after a delayed loop. Delay extends move time.
  nextTick = micros() + intervalUs;
  bool pulse[2] = {false, false};
  for (uint8_t i = 0; i < 2; i++) {
    accum[i] += magnitude[i];
    if (accum[i] >= ticks) {
      accum[i] -= ticks; pulse[i] = true;
      digitalWrite(STEP_PIN[i], HIGH); pos[i] += direction[i];
    }
  }
  delayMicroseconds(5);
  for (uint8_t i = 0; i < 2; i++) if (pulse[i]) digitalWrite(STEP_PIN[i], LOW);
  if (++doneTicks >= ticks) busy = false;
}
void command(char *line) {
  char *word = strtok(line, " \t"); if (!word) { error("empty"); return; }
  long a[6]; int n = 0; char *part;
  while ((part = strtok(NULL, " \t")) != NULL) {
    if (n == 6) { error("arguments"); return; }
    char *end; errno = 0; long v = strtol(part, &end, 10);
    if (*end || end == part || errno == ERANGE) { error("integer"); return; }
    a[n++] = v;
  }
  if (!strcmp(word, "HELLO") && n == 0) { Serial.println(F("RKR 1")); return; }
  if (!strcmp(word, "STOP") && n == 0) { halt(); lastContact = millis(); status(); return; }
  if (!strcmp(word, "DISARM") && n == 0) { halt(); armed = false; status(); return; }
  if (!strcmp(word, "STATE") && n == 0) { lastContact = millis(); status(); return; }
  if (!strcmp(word, "INIT") && n == 6 && !busy && !armed) {
    if ((a[0] != 1 && a[0] != -1) || (a[1] != 1 && a[1] != -1) || a[2] < -HARD_LIMIT || a[3] > HARD_LIMIT ||
        a[4] < -HARD_LIMIT || a[5] > HARD_LIMIT || a[2] >= 0 || a[3] <= 0 || a[4] >= 0 || a[5] <= 0) {
      error("config"); return;
    }
    motorSign[0] = a[0]; motorSign[1] = a[1];
    lowLimit[0] = a[2]; highLimit[0] = a[3]; lowLimit[1] = a[4]; highLimit[1] = a[5];
    configured = true; referenced = false; status(); return;
  }
  if (!strcmp(word, "ZERO") && n == 0 && configured && !busy && !armed) {
    pos[0] = pos[1] = 0; referenced = true; status(); return;
  }
  if (!strcmp(word, "ARM") && n == 0 && configured && referenced && !busy) {
    armed = true; lastContact = millis(); status(); return;
  }
  if (!strcmp(word, "MOVE") && n == 3) {
    if (!armed || !referenced || !configured) { error("unarmed"); return; }
    if (busy) { error("busy"); return; }
    if (!inLimits(a[0], a[1]) || a[2] < 1 || a[2] > MAX_RATE) { error("range"); return; }
    ticks = 0; doneTicks = 0;
    for (uint8_t i = 0; i < 2; i++) {
      target[i] = a[i]; long delta = target[i] - pos[i];
      direction[i] = delta >= 0 ? 1 : -1;
      magnitude[i] = labs(delta); accum[i] = 0;
      if (magnitude[i] > ticks) ticks = magnitude[i];
      digitalWrite(DIR_PIN[i], direction[i] * motorSign[i] > 0 ? HIGH : LOW);
    }
    intervalUs = 1000000UL / (unsigned long)a[2];
    nextTick = micros() + intervalUs; busy = ticks > 0;
    lastContact = millis(); status(); return;
  }
  error("command_or_state");
}
void setup() {
  for (uint8_t i = 0; i < 2; i++) {
    pinMode(STEP_PIN[i], OUTPUT); digitalWrite(STEP_PIN[i], LOW);
    pinMode(DIR_PIN[i], OUTPUT);
    digitalWrite(EN_PIN[i], ENABLE_ACTIVE); pinMode(EN_PIN[i], OUTPUT);
  }
  // Hold torque even disarmed/stopped. Disarm only inhibits STEP pulses.
  Serial.begin(115200); lastContact = millis(); Serial.println(F("RKR 1"));
}
void loop() {
  serviceMotion();
  // Bounded input work avoids starving the pulse scheduler.
  for (uint8_t k = 0; k < 16 && Serial.available(); k++) {
    char c = Serial.read();
    if (c == '\r') continue;
    if (c == '\n') {
      if (overflowed) error("line_too_long");
      else { input[used] = 0; command(input); }
      used = 0; overflowed = false;
    } else if (!overflowed) {
      if (used < sizeof(input) - 1) input[used++] = c;
      else { overflowed = true; halt(); armed = false; }
    }
    serviceMotion();
  }
}
