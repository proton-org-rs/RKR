import serial
import time
import serial.tools.list_ports

TENSION = 40

def find_arduino_port():
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if 'Arduino' in port.description or 'USB-SERIAL' in port.description or 'CH340' in port.description:
            return port.device
    return 'COM3'

SERIAL_PORT = find_arduino_port()
print(f"PORT: {SERIAL_PORT}")

STEPS = 600
SPEED = 400
STEPS2 =200
SPEED2 = 200

try:
    arduino = serial.Serial(SERIAL_PORT, 115200, timeout=0.1)
    time.sleep(2)

    arduino.write(b'EN1 1\n')
    arduino.write(b'EN2 1\n')

    print("ARDUINO OK")
except Exception as e:
    print(f"ERROR: {e}")
    arduino = None


def send(cmd):
    if arduino and arduino.is_open:
        arduino.write((cmd + '\n').encode())


def move_pair(dir1, dir2):
    send(f"SPEED1 {SPEED}")
    send(f"SPEED2 {SPEED}")

    send(f"MOVE1 {dir1 * STEPS}")
    send(f"MOVE2 {dir2 * STEPS}")


def move_pair2(dir1, dir2):
    send(f"SPEED1 {SPEED2}")
    send(f"SPEED2 {SPEED2}")

    send(f"MOVE1 {dir1 * STEPS2}")
    send(f"MOVE2 {dir2 * STEPS2}")



print("START")

for i in range(2):
    print(f"CIKLUS {i+1}")

    # faza 1: M1 namotava, M2 otpusta

    # faza 2: M1 otpusta, M2 namotava
    move_pair(-1, 1)
    time.sleep(1.2)

    move_pair(1, -1)
    time.sleep(1.2)

    move_pair(-1, 1)
    time.sleep(1.2)

    move_pair(1, -1)
    time.sleep(1.2)

    #move_pair(-1, 1)
    #time.sleep(1.2)

    #move_pair(1, -1)
    #time.sleep(1.2)


print("GOTOVO")