#include <AccelStepper.h>

const int M1_STEP = 2;
const int M1_DIR  = 3;
const int M1_ENA  = 4;
const int M2_STEP = 5;
const int M2_DIR  = 6;
const int M2_ENA  = 7;

AccelStepper stepper1(AccelStepper::DRIVER, M1_STEP, M1_DIR);
AccelStepper stepper2(AccelStepper::DRIVER, M2_STEP, M2_DIR);

static char lineBuf[80];
static uint8_t lineLen = 0;

float maxSpeed1 = 800.0f;
float maxSpeed2 = 800.0f;
float accel1 = 400.0f;
float accel2 = 400.0f;
bool useEnablePin = true;
bool enabled1 = true;
bool enabled2 = true;

void setEnable1(bool en) {
  enabled1 = en;
  if (useEnablePin) {
    digitalWrite(M1_ENA, en ? LOW : HIGH); 
  }
}
void setEnable2(bool en) {
  enabled2 = en;
  if (useEnablePin) {
    digitalWrite(M2_ENA, en ? LOW : HIGH); 
  }
}

void setup() {
  pinMode(M1_STEP, OUTPUT); 
  pinMode(M1_DIR, OUTPUT); 
  pinMode(M1_ENA, OUTPUT);
  pinMode(M2_STEP, OUTPUT); 
  pinMode(M2_DIR, OUTPUT); 
  pinMode(M2_ENA, OUTPUT);

  Serial.begin(115200);
  Serial.setTimeout(5);

  stepper1.setMaxSpeed(maxSpeed1);
  stepper1.setAcceleration(accel1);
  stepper2.setMaxSpeed(maxSpeed2);
  stepper2.setAcceleration(accel2);

  setEnable1(true);
  setEnable2(true);

  Serial.println(F("2x TB6600 spremno."));
  Serial.println(F("EN1/EN2, SPEED1/SPEED2, ACCEL1/ACCEL2, MOVE1/MOVE2, STOP1/STOP2"));
}

void handleLine(char *s) {
  while (*s == ' ' || *s == '\t') s++;
  if (*s == 0) return;


  if (!strncmp(s, "EN1", 3)) {
    int v;
    if (sscanf(s, "EN1 %d", &v) == 1) { setEnable1(v != 0); Serial.println(F("OK en1")); }
    else Serial.println(F("los en1"));
    return;
  }
  if (!strncmp(s, "EN2", 3)) {
    int v;
    if (sscanf(s, "EN2 %d", &v) == 1) { setEnable2(v != 0); Serial.println(F("OK en2")); }
    else Serial.println(F("los en2"));
    return;
  }

  if (!strncmp(s, "SPEED1", 6)) {
    float v;
    if (sscanf(s, "SPEED1 %f", &v) == 1 && v > 0) {
      maxSpeed1 = v; stepper1.setMaxSpeed(maxSpeed1); Serial.println(F("OK speed1"));
    } else Serial.println(F("los speed1"));
    return;
  }
  if (!strncmp(s, "SPEED2", 6)) {
    float v;
    if (sscanf(s, "SPEED2 %f", &v) == 1 && v > 0) {
      maxSpeed2 = v; stepper2.setMaxSpeed(maxSpeed2); Serial.println(F("OK speed2"));
    } else Serial.println(F("los speed2"));
    return;
  }

  if (!strncmp(s, "ACCEL1", 6)) {
    float v;
    if (sscanf(s, "ACCEL1 %f", &v) == 1 && v >= 0) {
      accel1 = v; stepper1.setAcceleration(accel1); Serial.println(F("OK accel1"));
    } else Serial.println(F("los accel1"));
    return;
  }
  if (!strncmp(s, "ACCEL2", 6)) {
    float v;
    if (sscanf(s, "ACCEL2 %f", &v) == 1 && v >= 0) {
      accel2 = v; stepper2.setAcceleration(accel2); Serial.println(F("OK accel2"));
    } else Serial.println(F("los accel2"));
    return;
  }

  if (!strncmp(s, "MOVE1", 5)) {
    long steps;
    if (sscanf(s, "MOVE1 %ld", &steps) == 1) {
      if (!enabled1) setEnable1(true);
      stepper1.move(steps);
      Serial.println(F("OK MOVE1"));
    } else Serial.println(F("los move1"));
    return;
  }
  if (!strncmp(s, "MOVE2", 5)) {
    long steps;
    if (sscanf(s, "MOVE2 %ld", &steps) == 1) {
      if (!enabled2) setEnable2(true);
      stepper2.move(steps);
      Serial.println(F("OK MOVE2"));
    } else Serial.println(F("los move2"));
    return;
  }

  if (!strncmp(s, "STOP1", 5)) {
    stepper1.stop();
    Serial.println(F("OK STOP1"));
    return;
  }
  if (!strncmp(s, "STOP2", 5)) {
    stepper2.stop();
    Serial.println(F("OK STOP2"));
    return;
  }

  Serial.println(F("NE postojeca komanda"));
}

void loop() {
  stepper1.run();
  stepper2.run();

  while (Serial.available() > 0) {
    char c = (char)Serial.read();
    if (c == '\r') continue;
    if (c == '\n') {
      lineBuf[lineLen] = 0;
      handleLine(lineBuf);
      lineLen = 0;
    } else {
      if (lineLen < sizeof(lineBuf) - 1) lineBuf[lineLen++] = c;
      else { lineLen = 0; Serial.println(F("predugacka komanda")); }
    }
  }
}
