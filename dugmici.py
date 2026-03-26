import cv2
import serial
import time
import serial.tools.list_ports
import keyboard  # pip install keyboard

def find_arduino_port():
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if 'Arduino' in port.description or 'USB-SERIAL' in port.description or 'CH340' in port.description:
            return port.device
    return 'COM3'


SERIAL_PORT = find_arduino_port()
print(f"PORT: {SERIAL_PORT}")

# === SETTINGS ===
STEPS_CHUNK = 300
SPEED_VALUE = 400

mp_hands = None
cap = None

arduino = None
try:
    arduino = serial.Serial(SERIAL_PORT, 115200, timeout=0.1, dsrdtr=False, rtscts=False)
    arduino.dtr = False
    time.sleep(2)
    arduino.reset_input_buffer()
    arduino.write(b'EN1 1\n')
    time.sleep(0.05)
    arduino.write(b'EN2 1\n')
    time.sleep(0.05)
    print("ARDUINO OK")
except Exception as e:
    print(f"TEST MODE (greška: {e})")


def send_cmd(cmd: str):
    if arduino and arduino.is_open:
        try:
            arduino.write((cmd + '\n').encode())
            arduino.reset_input_buffer()
        except Exception as e:
            print(f"Serial greška: {e}")


#########
m1_moving_forward = False
m1_moving_backward = False
m2_moving_forward = False
m2_moving_backward = False

print("\nTASTER KONTROLA")
print("MOTOR 1 (LEVA):  R = NAPRED  |  E = NAZAD")
print("MOTOR 2 (DESNA): M = NAPRED  |  N = NAZAD")
print("SPACE = STOP SVI   |   Q = QUIT")
print('\n')


while True:
    if arduino:
        line = arduino.readline().decode('utf-8', errors='ignore').strip()
        if line:
            print(f"ARDUINO: {line}")

    if keyboard.is_pressed('r'):
        if not m1_moving_forward:
            print("M1 NAPRED (R)")
            send_cmd(f'SPEED1 {SPEED_VALUE}')
            send_cmd(f'MOVE1 {STEPS_CHUNK}')
            send_cmd(f'SPEED2 {SPEED_VALUE/4}')  #ako vam se previse vraca ovaj drugi motor obrisite za svaki taster ovu i sledecu liniju
            send_cmd(f'MOVE2 {-STEPS_CHUNK/4}')
            m1_moving_forward = True
        time.sleep(0.1)  # Anti-bounce

    elif keyboard.is_pressed('e'):
        if not m1_moving_backward:
            print("M1 NAZAD (E)")
            send_cmd(f'SPEED1 {SPEED_VALUE}')
            send_cmd(f'MOVE1 -{STEPS_CHUNK}')
            send_cmd(f'SPEED2 {SPEED_VALUE/4}')#ako vam se previse vraca ovaj drugi motor obrisite za svaki taster ovu i sledecu liniju
            send_cmd(f'MOVE2 {STEPS_CHUNK/4}')
            m1_moving_backward = True
        time.sleep(0.1)

    elif keyboard.is_pressed('m'):
        if not m2_moving_forward:
            print("M2 NAPRED (M)")
            send_cmd(f'SPEED2 {SPEED_VALUE}')
            send_cmd(f'MOVE2 {STEPS_CHUNK}')
            send_cmd(f'SPEED1 {SPEED_VALUE/4}')#ako vam se previse vraca ovaj drugi motor obrisite za svaki taster ovu i sledecu liniju
            send_cmd(f'MOVE1 {-STEPS_CHUNK/4}')
            m2_moving_forward = True
        time.sleep(0.1)

    elif keyboard.is_pressed('n'):
        if not m2_moving_backward:
            print("M2 NAZAD (N)")
            send_cmd(f'SPEED2 {SPEED_VALUE}')
            send_cmd(f'MOVE2 -{STEPS_CHUNK}')
            send_cmd(f'SPEED1 {SPEED_VALUE/4}')#ako vam se previse vraca ovaj drugi motor obrisite za svaki taster ovu i sledecu liniju
            send_cmd(f'MOVE1 {STEPS_CHUNK/4}')
            m2_moving_backward = True
        time.sleep(0.1)

    elif keyboard.is_pressed('space'):
        print("STOP SVI")
        send_cmd('STOP1')
        send_cmd('STOP2')
        m1_moving_forward = m1_moving_backward = False
        m2_moving_forward = m2_moving_backward = False
        time.sleep(0.2)

    elif keyboard.is_pressed('q'):
        break

    if not keyboard.is_pressed('r'):
        m1_moving_forward = False
    if not keyboard.is_pressed('e'):
        m1_moving_backward = False
    if not keyboard.is_pressed('m'):
        m2_moving_forward = False
    if not keyboard.is_pressed('n'):
        m2_moving_backward = False

    time.sleep(0.01)  # Mali delay za performanse

send_cmd('STOP1')
send_cmd('STOP2')
if arduino:
    arduino.close()
print("GOTOVO!")
