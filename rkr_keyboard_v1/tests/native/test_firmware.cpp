#include "Arduino.h"
#include <cassert>
unsigned long fakeUs = 0;
long pulses[8] = {};
SerialMock Serial;
#include "../../firmware/rkr_controller/rkr_controller.ino"
std::string send(const std::string &s) {
  Serial.output.clear();
  for (char c : s + "\n") Serial.input.push_back(c);
  while (Serial.available()) loop();
  return Serial.output;
}
void advance(unsigned long us, bool heartbeat = true) {
  unsigned long end = fakeUs + us;
  while (fakeUs < end) {
    fakeUs += 100;
    loop();
    if (heartbeat && millis() - lastContact > 100) send("STATE");
  }
}
int main() {
  setup();
  assert(send("HELLO") == "RKR 1\n");
  assert(send("MOVE 10 0 100").find("ERR") == 0);
  assert(send("INIT 1 1 -560 560 -560 560").find("STATE") == 0);
  assert(send("ARM").find("ERR") == 0);
  send("ZERO"); send("ARM");
  assert(send("MOVE 100 -25 100").find("STATE") == 0);
  assert(send("MOVE 0 0 100") == "ERR busy\n");
  advance(1500000);
  assert(pos[0] == 100 && pos[1] == -25 && !busy);
  assert(pulses[2] == 100 && pulses[5] == 25);
  assert(send("MOVE 561 0 100") == "ERR range\n");
  assert(send("MOVE 0 0 0") == "ERR range\n");
  assert(send("MOVE 0.5 0 100") == "ERR integer\n");
  send("MOVE -400 400 200"); advance(200000); send("STOP");
  long a = pos[0], b = pos[1]; advance(1000000);
  assert(pos[0] == a && pos[1] == b && armed);
  send("MOVE 400 400 100"); advance(900000, false);
  assert(!armed && !busy);
  a = pos[0]; b = pos[1]; advance(1000000, false);
  assert(pos[0] == a && pos[1] == b);
  assert(send("MOVE 0 0 100") == "ERR unarmed\n");
  send("ARM"); send("MOVE 0 0 100");
  assert(send(std::string(120, 'x')) == "ERR line_too_long\n");
  assert(!busy && !armed);
  assert(send("ARM") .find("STATE") == 0);
  assert(send("ZERO").find("ERR") == 0);
  send("DISARM"); send("ZERO");
  assert(pos[0] == 0 && pos[1] == 0 && referenced);
  std::cout << "Firmware native harness: protocol, counts, limits, stop, watchdog, overflow passed\n";
}
