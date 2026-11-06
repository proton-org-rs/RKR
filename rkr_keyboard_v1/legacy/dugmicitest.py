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
    return '/dev/ttyUSB0'


SERIAL_PORT = find_arduino_port()
print(f"PORT: {SERIAL_PORT}")

# === SETTINGS ===
STEPS_CHUNK = 100
SPEED_VALUE = 600

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

# NEW: arrow continuous mode
arrow_mode = False
current_arrow = None
last_arrow_send = 0
ARROW_INTERVAL = 0.05

print("\nTASTER KONTROLA")
print("MOTOR 1 (LEVA):  R = NAPRED  |  E = NAZAD")
print("MOTOR 2 (DESNA): M = NAPRED  |  N = NAZAD")
print("ARROWS = CONTINUOUS MOVE")
print("SPACE = STOP SVI   |   Q = QUIT")
print('\n')


while True:
    if arduino:
        line = arduino.readline().decode('utf-8', errors='ignore').strip()
        if line:
            print(f"ARDUINO: {line}")

    # ===== ARROW CONTINUOUS CONTROL =====
    if keyboard.is_pressed('up'):
        if current_arrow != 'up':
            print("ARROW UP")
            current_arrow = 'up'
            arrow_mode = True

    elif keyboard.is_pressed('down'):
        if current_arrow != 'down':
            print("ARROW DOWN")
            current_arrow = 'down'
            arrow_mode = True

    elif keyboard.is_pressed('left'):
        if current_arrow != 'left':
            print("ARROW LEFT")
            current_arrow = 'left'
            arrow_mode = True

    elif keyboard.is_pressed('right'):
        if current_arrow != 'right':
            print("ARROW RIGHT")
            current_arrow = 'right'
            arrow_mode = True

    if arrow_mode and current_arrow:
        now = time.time()
        if now - last_arrow_send > ARROW_INTERVAL:

            if current_arrow == 'up':
                send_cmd(f'SPEED1 {SPEED_VALUE}')
                send_cmd(f'SPEED2 {SPEED_VALUE}')
                send_cmd(f'MOVE1 {STEPS_CHUNK}')
                send_cmd(f'MOVE2 {STEPS_CHUNK}')

            elif current_arrow == 'down':
                send_cmd(f'SPEED1 {SPEED_VALUE}')
                send_cmd(f'SPEED2 {SPEED_VALUE}')
                send_cmd(f'MOVE1 -{STEPS_CHUNK}')
                send_cmd(f'MOVE2 -{STEPS_CHUNK}')

            elif current_arrow == 'left':
                send_cmd(f'SPEED1 {SPEED_VALUE}')
                send_cmd(f'SPEED2 {SPEED_VALUE}')
                send_cmd(f'MOVE1 -{STEPS_CHUNK}')
                send_cmd(f'MOVE2 {STEPS_CHUNK}')

            elif current_arrow == 'right':
                send_cmd(f'SPEED1 {SPEED_VALUE}')
                send_cmd(f'SPEED2 {SPEED_VALUE}')
                send_cmd(f'MOVE1 {STEPS_CHUNK}')
                send_cmd(f'MOVE2 -{STEPS_CHUNK}')

            last_arrow_send = now

    # ===== ORIGINAL CONTROLS (UNCHANGED) =====
    if keyboard.is_pressed('r'):
        if not m1_moving_forward:
            print("M1 NAPRED (R)")
            send_cmd(f'SPEED1 {SPEED_VALUE}')
            send_cmd(f'MOVE1 {STEPS_CHUNK}')
            send_cmd(f'SPEED2 {SPEED_VALUE}')
            send_cmd(f'MOVE2 {-STEPS_CHUNK}')
            m1_moving_forward = True
        time.sleep(0.01)

    elif keyboard.is_pressed('e'):
        if not m1_moving_backward:
            print("M1 NAZAD (E)")
            send_cmd(f'SPEED1 {SPEED_VALUE}')
            send_cmd(f'MOVE1 -{STEPS_CHUNK}')
            send_cmd(f'SPEED2 {SPEED_VALUE}')
            send_cmd(f'MOVE2 {STEPS_CHUNK}')
            m1_moving_backward = True
        time.sleep(0.01)

    elif keyboard.is_pressed('m'):
        if not m2_moving_forward:
            print("M2 NAPRED (M)")
            send_cmd(f'SPEED2 {SPEED_VALUE}')
            send_cmd(f'MOVE2 {STEPS_CHUNK}')
            send_cmd(f'SPEED1 {SPEED_VALUE}')
            send_cmd(f'MOVE1 {-STEPS_CHUNK}')
            m2_moving_forward = True
        time.sleep(0.01)

    elif keyboard.is_pressed('n'):
        if not m2_moving_backward:
            print("M2 NAZAD (N)")
            send_cmd(f'SPEED2 {SPEED_VALUE}')
            send_cmd(f'MOVE2 -{STEPS_CHUNK}')
            send_cmd(f'SPEED1 {SPEED_VALUE}')
            send_cmd(f'MOVE1 {STEPS_CHUNK}')
            m2_moving_backward = True
        time.sleep(0.01)

    elif keyboard.is_pressed('z'):
        if not m1_moving_forward:
            print("M1 NAPRED BEZ DRUGOG MOTORA (z)")
            send_cmd(f'SPEED1 {SPEED_VALUE}')
            send_cmd(f'MOVE1 {STEPS_CHUNK}')
            m1_moving_forward = True
        time.sleep(0.01)

    elif keyboard.is_pressed('x'):
        if not m1_moving_backward:
            print("M1 NAZAD BEZ DRUGOG MOTORA (x)")
            send_cmd(f'SPEED1 {SPEED_VALUE}')
            send_cmd(f'MOVE1 -{STEPS_CHUNK}')
            m1_moving_backward = True
        time.sleep(0.01)

    elif keyboard.is_pressed('c'):
        if not m2_moving_forward:
            print("M2 NAPRED BEZ DRUGOG MOTORA (c)")
            send_cmd(f'SPEED2 {SPEED_VALUE}')
            send_cmd(f'MOVE2 {STEPS_CHUNK}')
            m2_moving_forward = True
        time.sleep(0.01)

    elif keyboard.is_pressed('v'):
        if not m2_moving_backward:
            print("M2 NAZAD BEZ DRUGOG MOTORA (v)")
            send_cmd(f'SPEED2 {SPEED_VALUE}')
            send_cmd(f'MOVE2 -{STEPS_CHUNK}')
            m2_moving_backward = True
        time.sleep(0.01)

    elif keyboard.is_pressed('space'):
        print("STOP SVI")
        send_cmd('STOP1')
        send_cmd('STOP2')

        arrow_mode = False
        current_arrow = None

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

    time.sleep(0.01)

send_cmd('STOP1')
send_cmd('STOP2')
if arduino:
    arduino.close()
print("GOTOVO!")