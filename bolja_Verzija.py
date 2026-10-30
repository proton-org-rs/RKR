# import serial
# import time
# import serial.tools.list_ports
# import keyboard  # pip install keyboard
#
#
# def find_arduino_port():
#     ports = serial.tools.list_ports.comports()
#     for port in ports:
#         if 'Arduino' in port.description or 'USB-SERIAL' in port.description or 'CH340' in port.description:
#             return port.device
#     return 'COM3'
#
#
# SERIAL_PORT = find_arduino_port()
# print(f"PORT: {SERIAL_PORT}")
#
# # === SETTINGS ===
# STEPS_CHUNK = 300
# SPEED_VALUE = 400
# RATIO = 1.0   # r_levi / r_desni (izmeri šublerom, ako su isti ostavi 1.0)
#
# arduino = None
# try:
#     arduino = serial.Serial(SERIAL_PORT, 115200, timeout=0.1, dsrdtr=False, rtscts=False)
#     arduino.dtr = False
#     time.sleep(2)
#     while arduino.in_waiting:
#         print("BOOT:", arduino.readline().decode(errors='ignore').strip())
#     arduino.reset_input_buffer()
#     arduino.write(b'EN1 1\n')
#     time.sleep(0.05)
#     arduino.write(b'EN2 1\n')
#     time.sleep(0.05)
#     print("ARDUINO OK")
# except Exception as e:
#     print(f"TEST MODE (greška: {e})")
#
#
# def send_cmd(cmd: str):
#     if arduino and arduino.is_open:
#         try:
#             print(f"SEND: {cmd}")
#             arduino.write((cmd + '\n').encode())
#         except Exception as e:
#             print(f"Serial greška: {e}")
#
#
# def move_m1(steps):
#     # motor 1 vodi, motor 2 popušta srazmerno
#     send_cmd(f'SPEED1 {SPEED_VALUE}')
#     send_cmd(f'MOVE1 {steps}')
#     send_cmd(f'SPEED2 {int(SPEED_VALUE * RATIO)}')
#     send_cmd(f'MOVE2 {int(-steps * RATIO)}')
#
#
# def move_m2(steps):
#     # motor 2 vodi, motor 1 popušta srazmerno
#     send_cmd(f'SPEED2 {SPEED_VALUE}')
#     send_cmd(f'MOVE2 {steps}')
#     send_cmd(f'SPEED1 {int(SPEED_VALUE / RATIO)}')
#     send_cmd(f'MOVE1 {int(-steps / RATIO)}')
#
#
# m1_moving_forward = False
# m1_moving_backward = False
# m2_moving_forward = False
# m2_moving_backward = False
#
# print("\nTASTER KONTROLA")
# print("MOTOR 1 (LEVA):  R = NAPRED  |  E = NAZAD")
# print("MOTOR 2 (DESNA): M = NAPRED  |  N = NAZAD")
# print("SPACE = STOP SVI   |   Q = QUIT")
# print('\n')
#
# while True:
#     if arduino:
#         line = arduino.readline().decode('utf-8', errors='ignore').strip()
#         if line:
#             print(f"ARDUINO: {line}")
#
#     if keyboard.is_pressed('r'):
#         if not m1_moving_forward:
#             print("M1 NAPRED (R)")
#             move_m1(STEPS_CHUNK)
#             m1_moving_forward = True
#         time.sleep(0.1)
#
#     elif keyboard.is_pressed('e'):
#         if not m1_moving_backward:
#             print("M1 NAZAD (E)")
#             move_m1(-STEPS_CHUNK)
#             m1_moving_backward = True
#         time.sleep(0.1)
#
#     elif keyboard.is_pressed('m'):
#         if not m2_moving_forward:
#             print("M2 NAPRED (M)")
#             move_m2(STEPS_CHUNK)
#             m2_moving_forward = True
#         time.sleep(0.1)
#
#     elif keyboard.is_pressed('n'):
#         if not m2_moving_backward:
#             print("M2 NAZAD (N)")
#             move_m2(-STEPS_CHUNK)
#             m2_moving_backward = True
#         time.sleep(0.1)
#
#     elif keyboard.is_pressed('space'):
#         print("STOP SVI")
#         send_cmd('STOP1')
#         send_cmd('STOP2')
#         m1_moving_forward = m1_moving_backward = False
#         m2_moving_forward = m2_moving_backward = False
#         time.sleep(0.2)
#
#     elif keyboard.is_pressed('q'):
#         break
#
#     if not keyboard.is_pressed('r'):
#         m1_moving_forward = False
#     if not keyboard.is_pressed('e'):
#         m1_moving_backward = False
#     if not keyboard.is_pressed('m'):
#         m2_moving_forward = False
#     if not keyboard.is_pressed('n'):
#         m2_moving_backward = False
#
#     time.sleep(0.01)
#
# send_cmd('STOP1')
# send_cmd('STOP2')
# if arduino:
#     arduino.close()
# print("GOTOVO!")



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
STEP = 100         # koraka po slanju dok držiš taster
SPEED_VALUE = 400
INTERVAL = 0.08      # na koliko sekundi se šalje korak dok držiš taster

arduino = None
try:
    arduino = serial.Serial(SERIAL_PORT, 115200, timeout=0.01, dsrdtr=False, rtscts=False)
    arduino.dtr = False
    time.sleep(2)
    while arduino.in_waiting:
        print("BOOT:", arduino.readline().decode(errors='ignore').strip())
    arduino.reset_input_buffer()
    print("ARDUINO OK")
except Exception as e:
    print(f"TEST MODE (greška: {e})")


def send_cmd(cmd: str):
    if arduino and arduino.is_open:
        try:
            arduino.write((cmd + '\n').encode())
        except Exception as e:
            print(f"Serial greška: {e}")


# podešavanje se šalje samo jednom, isto za oba motora
send_cmd('EN1 1')
send_cmd('EN2 1')
send_cmd(f'SPEED1 {SPEED_VALUE}')
send_cmd(f'SPEED2 {SPEED_VALUE}')


def bend(direction):
    # direction: +1 = levo, -1 = desno
    send_cmd(f'MOVE1 {direction * STEP}')
    send_cmd(f'MOVE2 {-direction * STEP}')


print("\nSTRELICA LEVO / DESNO = savijanje  |  SPACE = STOP  |  Q = izlaz\n")

last_send = 0
was_moving = False

while True:
    if arduino:
        line = arduino.readline().decode('utf-8', errors='ignore').strip()
        if line and not line.startswith('OK'):
            print(f"ARDUINO: {line}")

    left = keyboard.is_pressed('left')
    right = keyboard.is_pressed('right')
    now = time.time()

    if left != right:  # tačno jedan taster
        if now - last_send >= INTERVAL:
            bend(+1 if left else -1)
            last_send = now
        was_moving = True
    elif was_moving:   # taster pušten
        send_cmd('STOP1')
        send_cmd('STOP2')
        was_moving = False

    if keyboard.is_pressed('space'):
        send_cmd('STOP1')
        send_cmd('STOP2')
        was_moving = False
        time.sleep(0.2)

    if keyboard.is_pressed('q'):
        break

    time.sleep(0.01)

send_cmd('STOP1')
send_cmd('STOP2')
if arduino:
    arduino.close()
print("GOTOVO!")