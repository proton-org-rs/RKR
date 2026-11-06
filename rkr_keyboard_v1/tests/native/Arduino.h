#pragma once
#include <cstdint>
#include <string>
#include <deque>
#include <algorithm>
#include <iostream>
using std::uint8_t;
#define LOW 0
#define HIGH 1
#define OUTPUT 1
#define F(x) x
extern unsigned long fakeUs;
extern long pulses[8];
inline unsigned long micros() { return fakeUs; }
inline unsigned long millis() { return fakeUs / 1000; }
inline void delayMicroseconds(unsigned long t) { fakeUs += t; }
inline void pinMode(int, int) {}
inline void digitalWrite(int pin, int level) { if (level && (pin == 2 || pin == 5)) pulses[pin]++; }
struct SerialMock {
  std::string output;
  std::deque<char> input;
  void begin(int) {}
  int available() { return input.size(); }
  char read() { char c = input.front(); input.pop_front(); return c; }
  void print(const char* s) { output += s; }
  void print(char c) { output += c; }
  void print(long v) { output += std::to_string(v); }
  void print(int v) { output += std::to_string(v); }
  template<class T> void println(T v) { print(v); output += '\n'; }
};
extern SerialMock Serial;
