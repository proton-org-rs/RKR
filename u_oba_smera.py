# import cv2
# import mediapipe as mp
# import serial
# import time
# import serial.tools.list_ports
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
# STEPS_CHUNK = 2000
# SEND_INTERVAL = 0.3
# SPEED_PER_FINGER = 400
#
# mp_hands = mp.solutions.hands
# mp_drawing = mp.solutions.drawing_utils
# hands = mp_hands.Hands(
#     static_image_mode=False,
#     max_num_hands=2,
#     model_complexity=0,
#     min_detection_confidence=0.5,
#     min_tracking_confidence=0.5
# )
#
# cap = cv2.VideoCapture(0)
# cap.set(3, 640)
# cap.set(4, 480)
#
# arduino = None
# try:
#     arduino = serial.Serial(SERIAL_PORT, 115200, timeout=0.1, dsrdtr=False, rtscts=False)
#     arduino.dtr = False
#     time.sleep(2)
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
#             arduino.write((cmd + '\n').encode())
#             arduino.reset_input_buffer()
#         except Exception as e:
#             print(f"Serial greška: {e}")
#
#
# # === STANJE ===
# system_active = False
# right_fingers = 0
# left_fingers = 0
# last_right_send = 0.0
# last_left_send = 0.0
#
# print("NOVI SISTEM: PALAC = SMER | BROJ PRSTIJU = BRZINA")
# print("PALAC GORE = NAPRED (+) | PALAC DOLE = NAZAD (-)")
# print("START: SVI PRSTI GORE (5/5) | STOP: DLAN | Q=QUIT")
#
# while True:
#     if arduino:
#         line = arduino.readline()
#         if line:
#             print(line)
#
#     success, img = cap.read()
#     if not success:
#         continue
#
#     img = cv2.flip(img, 1)
#     imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
#     results = hands.process(imgRGB)
#
#     now = time.time()
#     right_fingers = 0
#     left_fingers = 0
#     detected_right = False
#     detected_left = False
#
#     if results.multi_hand_landmarks:
#         for idx, handLms in enumerate(results.multi_hand_landmarks):
#             handedness = results.multi_handedness[idx].classification[0].label
#             print(f"\n--- {handedness} R UKA ---")
#
#             tipIds = [4, 8, 12, 16, 20]  # vrhovi prstiju
#             pipIds = [2, 6, 10, 14, 18]  # PIP zglobovi
#
#             # === DETEKCIJA PALCA (SMER) ===
#             thumb_tip = handLms.landmark[4]  # vrh palca
#             thumb_base = handLms.landmark[2]  # baza palca (CMC zglob)
#
#             thumb_z_diff = thumb_tip.z - thumb_base.z
#             thumb_up = thumb_z_diff < 0.05  # PALAC GORE ako je bliži kameri
#             print(f"PALAC: z_tip={thumb_tip.z:.4f}, z_base={thumb_base.z:.4f}, diff={thumb_z_diff:.4f}")
#             print(f"PALAC STANJE: {'GORE (NAPRED +)' if thumb_up else 'DOLE (NAZAD -)'}")
#
#             # === DETEKCIJA OSTALIH PRSTIJU (BRZINA) ===
#             other_fingers = 0
#             for i in range(1, 5):  # index, srednji, domali, mali
#                 tip_y = handLms.landmark[tipIds[i]].y
#                 pip_y = handLms.landmark[pipIds[i]].y
#                 finger_up = tip_y < pip_y
#                 other_fingers += 1 if finger_up else 0
#                 print(f"Prst {i + 1}: tip_y={tip_y:.4f}, pip_y={pip_y:.4f}, {'GORE' if finger_up else 'DOLE'}")
#
#             # === UKUPNO ===
#             direction_multiplier = 1 if thumb_up else -1
#             speed_factor = 1 if other_fingers <= 2 else 2  # 1-2=sporije, 3-4=brže
#             fingers = other_fingers + (1 if thumb_up else 0)  # za kompatibilnost
#
#             print(f"UKUPNO: {other_fingers}/4 prstiju + palac = {fingers}/5")
#             print(f"SMER: {'NAPRED (+)' if direction_multiplier > 0 else 'NAZAD (-)'}")
#             print(f"BRZINA: {'SPOR (x1)' if speed_factor == 1 else 'BRZ (x2)'}")
#
#             # Sistem start/stop
#             if fingers == 5 and not system_active:
#                 system_active = True
#                 print("🎯 SISTEM START!")
#             elif fingers == 0 and system_active:
#                 system_active = False
#                 send_cmd('STOP1')
#                 send_cmd('STOP2')
#                 print("⏹️ SISTEM STOP!")
#
#             if handedness == 'Right':
#                 right_fingers = fingers
#                 right_direction_multiplier = direction_multiplier
#                 right_speed_factor = speed_factor
#                 detected_right = True
#             elif handedness == 'Left':
#                 left_fingers = fingers
#                 left_direction_multiplier = direction_multiplier
#                 left_speed_factor = speed_factor
#                 detected_left = True
#
#             mp_drawing.draw_landmarks(img, handLms, mp_hands.HAND_CONNECTIONS)
#
#     # === KONTROLA MOTORA ===
#     if system_active:
#         # DESNA RUKA → Motor 2
#         if detected_right and right_fingers > 0:
#             if (now - last_right_send) > SEND_INTERVAL:
#                 speed = right_fingers * SPEED_PER_FINGER * right_speed_factor
#                 steps = STEPS_CHUNK * right_direction_multiplier
#                 send_cmd(f'SPEED2 {int(speed)}')
#                 send_cmd(f'MOVE2 {steps}')
#                 print(f"🔵 RIGHT → {right_fingers}/5 | SMER:{steps > 0 and '+' or '-'} | SPEED:{speed}")
#                 last_right_send = now
#         elif detected_right and right_fingers == 0:
#             send_cmd('STOP2')
#
#         # LEVA RUKA → Motor 1
#         if detected_left and left_fingers > 0:
#             if (now - last_left_send) > SEND_INTERVAL:
#                 speed = left_fingers * SPEED_PER_FINGER * left_speed_factor
#                 steps = STEPS_CHUNK * left_direction_multiplier
#                 send_cmd(f'SPEED1 {int(speed)}')
#                 send_cmd(f'MOVE1 {steps}')
#                 print(f"🟡 LEFT  → {left_fingers}/5 | SMER:{steps > 0 and '+' or '-'} | SPEED:{speed}")
#                 last_left_send = now
#         elif detected_left and left_fingers == 0:
#             send_cmd('STOP1')
#
#     # === PRIKAZ ===
#     status_text = "AKTIVAN" if system_active else "CEKAM START (5 prstiju)"
#     cv2.putText(img, f"STATUS: {status_text}", (20, 30),
#                 cv2.FONT_HERSHEY_SIMPLEX, 0.7,
#                 (0, 255, 0) if system_active else (0, 100, 255), 2)
#
#     cv2.putText(img, f"DESNA M2: {right_fingers}/5", (20, 70),
#                 cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 150, 255), 2)
#     cv2.putText(img, f"LEVA M1:  {left_fingers}/5", (20, 110),
#                 cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 150, 0), 2)
#
#     # Debug info
#     cv2.putText(img, "PALAC GORE = + | DOLE = -", (20, 450),
#                 cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
#     cv2.putText(img, "1-2 prstija=SPOR | 3-4=BRZO", (20, 470),
#                 cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
#
#     cv2.imshow('GEST KONTROLA 2.0', img)
#     if cv2.waitKey(1) & 0xFF == ord('q'):
#         break
#
# send_cmd('STOP1')
# send_cmd('STOP2')
# cap.release()
# cv2.destroyAllWindows()
# if arduino:
#     arduino.close()
# print("GOTOVO!")
#
#
#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!11111

# import cv2
# import mediapipe as mp
# import serial
# import time
# import serial.tools.list_ports
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
# STEPS_CHUNK = 2000
# SEND_INTERVAL = 0.3
# SPEED_PER_FINGER = 400
#
# mp_hands = mp.solutions.hands
# mp_drawing = mp.solutions.drawing_utils
# hands = mp_hands.Hands(
#     static_image_mode=False,
#     max_num_hands=2,
#     model_complexity=0,
#     min_detection_confidence=0.5,
#     min_tracking_confidence=0.5
# )
#
# cap = cv2.VideoCapture(0)
# cap.set(3, 640)
# cap.set(4, 480)
#
# arduino = None
# try:
#     arduino = serial.Serial(SERIAL_PORT, 115200, timeout=0.1, dsrdtr=False, rtscts=False)
#     arduino.dtr = False
#     time.sleep(2)
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
#             arduino.write((cmd + '\n').encode())
#             arduino.reset_input_buffer()
#         except Exception as e:
#             print(f"Serial greška: {e}")
#
#
# # === STANJE ===
# system_active = False
# right_fingers = 0
# left_fingers = 0
# last_right_send = 0.0
# last_left_send = 0.0
#
# print("🎯 NOVI SISTEM: PALAC X = SMER | BROJ PRSTIJU = BRZINA")
# print("PALAC DESNO = NAPRED (+) | PALAC LIJEVO = NAZAD (-)")
# print("START: SVI PRSTI GORE | STOP: DLAN | Q=QUIT")
#
# while True:
#     if arduino:
#         line = arduino.readline()
#         if line:
#             print(line)
#
#     success, img = cap.read()
#     if not success:
#         continue
#
#     img = cv2.flip(img, 1)
#     imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
#     results = hands.process(imgRGB)
#
#     now = time.time()
#     right_fingers = 0
#     left_fingers = 0
#     detected_right = False
#     detected_left = False
#
#     if results.multi_hand_landmarks:
#         for idx, handLms in enumerate(results.multi_hand_landmarks):
#             handedness = results.multi_handedness[idx].classification[0].label
#             print(f"\n--- {handedness} RUK A ---")
#
#             tipIds = [4, 8, 12, 16, 20]
#             pipIds = [2, 6, 10, 14, 18]
#
#             # === 🔥 NOVI PALAC DETEKCIJA: X-KOORDINATA (LIJEVO-DESNO) ===
#             thumb_tip_x = handLms.landmark[4].x  # Vrh palca
#             thumb_base_x = handLms.landmark[2].x  # Baza palca
#             thumb_x_diff = thumb_tip_x - thumb_base_x
#
#             thumb_right = thumb_x_diff > 0.02  # PALAC DESNO = NAPRED
#             direction_multiplier = 1 if thumb_right else -1
#
#             print(f"PALAC X: x_tip={thumb_tip_x:.4f}, x_base={thumb_base_x:.4f}, diff={thumb_x_diff:.4f}")
#             print(f"PALAC: {'DESNO (NAPRED +)' if thumb_right else 'LIJEVO (NAZAD -)'}")
#
#             # === OSTALI PRSTI (Y-koordinata) ===
#             other_fingers = 0
#             for i in range(1, 5):
#                 tip_y = handLms.landmark[tipIds[i]].y
#                 pip_y = handLms.landmark[pipIds[i]].y
#                 finger_up = tip_y < pip_y
#                 other_fingers += 1 if finger_up else 0
#                 print(f"Prst {i + 1}: tip_y={tip_y:.4f}, pip_y={pip_y:.4f}, {'GORE' if finger_up else 'DOLE'}")
#
#             # === BRZINA ===
#             speed_factor = 1 if other_fingers <= 2 else 2
#             fingers = other_fingers + (1 if thumb_right else 0)
#
#             print(f"UKUPNO: {other_fingers}/4 prstiju + palac = {fingers}/5")
#             print(f"SMER: {'NAPRED (+)' if direction_multiplier > 0 else 'NAZAD (-)'}")
#             print(f"BRZINA: {'SPOR (x1)' if speed_factor == 1 else 'BRZ (x2)'}")
#
#             # Sistem start/stop
#             if fingers == 5 and not system_active:
#                 system_active = True
#                 print("🎯 SISTEM START!")
#             elif fingers == 0 and system_active:
#                 system_active = False
#                 send_cmd('STOP1')
#                 send_cmd('STOP2')
#                 print("⏹️ SISTEM STOP!")
#
#             if handedness == 'Right':
#                 right_fingers = fingers
#                 right_direction_multiplier = direction_multiplier
#                 right_speed_factor = speed_factor
#                 detected_right = True
#             elif handedness == 'Left':
#                 left_fingers = fingers
#                 left_direction_multiplier = direction_multiplier
#                 left_speed_factor = speed_factor
#                 detected_left = True
#
#             mp_drawing.draw_landmarks(img, handLms, mp_hands.HAND_CONNECTIONS)
#
#     # === KONTROLA MOTORA ===
#     if system_active:
#         # DESNA RUKA → Motor 2
#         if detected_right and right_fingers > 0:
#             if (now - last_right_send) > SEND_INTERVAL:
#                 speed = right_fingers * SPEED_PER_FINGER * right_speed_factor
#                 steps = int(STEPS_CHUNK * right_direction_multiplier)
#                 send_cmd(f'SPEED2 {int(speed)}')
#                 send_cmd(f'MOVE2 {steps}')
#                 print(f"🔵 RIGHT → {right_fingers}/5 | SMER:{'+' if steps > 0 else '-'} | SPEED:{speed}")
#                 last_right_send = now
#         elif detected_right and right_fingers == 0:
#             send_cmd('STOP2')
#
#         # LEVA RUKA → Motor 1
#         if detected_left and left_fingers > 0:
#             if (now - last_left_send) > SEND_INTERVAL:
#                 speed = left_fingers * SPEED_PER_FINGER * left_speed_factor
#                 steps = int(STEPS_CHUNK * left_direction_multiplier)
#                 send_cmd(f'SPEED1 {int(speed)}')
#                 send_cmd(f'MOVE1 {steps}')
#                 print(f"🟡 LEFT  → {left_fingers}/5 | SMER:{'+' if steps > 0 else '-'} | SPEED:{speed}")
#                 last_left_send = now
#         elif detected_left and left_fingers == 0:
#             send_cmd('STOP1')
#
#     # === PRIKAZ ===
#     status_text = "AKTIVAN" if system_active else "CEKAM START (5 prstiju)"
#     cv2.putText(img, f"STATUS: {status_text}", (20, 30),
#                 cv2.FONT_HERSHEY_SIMPLEX, 0.7,
#                 (0, 255, 0) if system_active else (0, 100, 255), 2)
#
#     cv2.putText(img, f"DESNA M2: {right_fingers}/5", (20, 70),
#                 cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 150, 255), 2)
#     cv2.putText(img, f"LEVA M1:  {left_fingers}/5", (20, 110),
#                 cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 150, 0), 2)
#
#     cv2.putText(img, "PALAC DESNO=+ | LIJEVO=-", (20, 450),
#                 cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
#     cv2.putText(img, "1-2 prst=SPOR | 3-4=BRZO", (20, 470),
#                 cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
#
#     cv2.imshow('GEST KONTROLA 3.0 - X PALAC', img)
#     if cv2.waitKey(1) & 0xFF == ord('q'):
#         break
#
# send_cmd('STOP1')
# send_cmd('STOP2')
# cap.release()
# cv2.destroyAllWindows()
# if arduino:
#     arduino.close()
# print("GOTOVO!")

#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

import cv2
import mediapipe as mp
import serial
import time
import serial.tools.list_ports


def find_arduino_port():
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if 'Arduino' in port.description or 'USB-SERIAL' in port.description or 'CH340' in port.description:
            return port.device
    return 'COM3'


SERIAL_PORT = find_arduino_port()
print(f"PORT: {SERIAL_PORT}")

# === SETTINGS ===
STEPS_CHUNK = 2000
SEND_INTERVAL = 0.3
SPEED_PER_FINGER = 150
MOVE_PER_FINGER = 300

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=2,
    model_complexity=0,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

cap = cv2.VideoCapture(0)
cap.set(3, 640)
cap.set(4, 480)

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


# === STANJE ===
system_active = False
right_fingers = 0
left_fingers = 0
last_right_send = 0.0
last_left_send = 0.0

print("SVI PRSTI = START | OK ZNAK = STOP")
print("PALAC NAPRED = + | PALAC NAZAD = -")
print("1-2 prsta=SPOR | 3-4 prsta=BRZO ")

while True:
    if arduino:
        line = arduino.readline()
        if line:
            print(line)

    success, img = cap.read()
    if not success:
        continue

    img = cv2.flip(img, 1)
    imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    results = hands.process(imgRGB)

    now = time.time()
    right_fingers = 0
    left_fingers = 0
    detected_right = False
    detected_left = False

    if results.multi_hand_landmarks:
        for idx, handLms in enumerate(results.multi_hand_landmarks):
            handedness = results.multi_handedness[idx].classification[0].label
            print(f"\n--- {handedness} RUKA ---")

            tipIds = [4, 8, 12, 16, 20]
            pipIds = [2, 6, 10, 14, 18]

            # NORMALIZOVANA PALAC DETEKCIJA
            thumb_tip_x = handLms.landmark[4].x
            thumb_base_x = handLms.landmark[2].x
            thumb_x_diff = thumb_tip_x - thumb_base_x

            # DESNA: NAPRED = palac LEVO (zbog flip-a)
            # LEVA: NAPRED = palac DESNO
            if handedness == 'Right':
                thumb_forward = thumb_x_diff < -0.02
            else:
                thumb_forward = thumb_x_diff > 0.02

            direction_multiplier = 1 if thumb_forward else -1

            print(f"PALAC X: x_tip={thumb_tip_x:.4f}, x_base={thumb_base_x:.4f}, diff={thumb_x_diff:.4f}")
            print(f"PALAC ({handedness}): {'NAPRED (+)' if thumb_forward else 'NAZAD (-)'}")

            # === OSTALI PRSTI ===
            other_fingers = 0
            for i in range(1, 5):
                tip_y = handLms.landmark[tipIds[i]].y
                pip_y = handLms.landmark[pipIds[i]].y
                finger_up = tip_y < pip_y
                other_fingers += 1 if finger_up else 0
                print(f"Prst {i + 1}: {'GORE' if finger_up else 'DOLE'}")

            # UKUPNO + STOP LOGIKA
            total_up_fingers = other_fingers + (1 if thumb_forward else 0)
            fingers = total_up_fingers

            print(f"UKUPNO: {other_fingers}/4 + palac = {fingers}/5")
            print(f"SMER: {'NAPRED (+)' if direction_multiplier > 0 else 'NAZAD (-)'}")
            speed_factor = 1 if other_fingers <= 2 else 2
            print(f"BRZINA: {'SPOR (x1)' if speed_factor == 1 else 'BRZ (x2)'}")

            # === START ===
            if fingers == 5 and not system_active:
                system_active = True
                print("START!")

            # GLOBAL STOP SA OK ZNAKOM
            thumb_tip = handLms.landmark[4]
            index_tip = handLms.landmark[8]
            ok_distance = ((thumb_tip.x - index_tip.x) ** 2 + (thumb_tip.y - index_tip.y) ** 2) ** 0.5
            print(f"OK dist: {ok_distance:.4f}")

            # STOP KOD SVAKE RUKE (globalno!)
            if ok_distance < 0.05 and system_active:
                send_cmd('STOP1')
                send_cmd('STOP2')
                system_active = False  # GLOBAL STOP
                print("OK STOP--SISTEM ISKLJUČEN!")
                break


            if not system_active:
                continue

            if handedness == 'Right':
                right_fingers = fingers
                right_direction_multiplier = direction_multiplier
                right_speed_factor = speed_factor
                detected_right = True
            elif handedness == 'Left':
                left_fingers = fingers
                left_direction_multiplier = direction_multiplier
                left_speed_factor = speed_factor
                detected_left = True

            mp_drawing.draw_landmarks(img, handLms, mp_hands.HAND_CONNECTIONS)

    # KONTROLA MOTORA
    if system_active:
        # DESNA RUKA → Motor 2
        if detected_right and right_fingers > 0:
            if (now - last_right_send) > SEND_INTERVAL:
                speed = right_fingers * SPEED_PER_FINGER * right_speed_factor
                steps = int(STEPS_CHUNK * right_direction_multiplier)
                send_cmd(f'SPEED2 {int(speed)}')
                send_cmd(f'MOVE2 {steps}')
                send_cmd(f'SPEED1 {int(speed/4)}') #ako vam se previse vraca ovaj drugi motor obrisite za svaki taster ovu i sledecu liniju
                send_cmd(f'MOVE1 {-(steps/4)}')  #vracamo se drugim motorom za duplo manje stepova
                print(f"RIGHT → {right_fingers}/5 | SMER:{'+' if steps > 0 else '-'} | SPD:{int(speed)}")
                last_right_send = now
        elif detected_right and right_fingers == 0:
            send_cmd('STOP2')

        # LEVA RUKA → Motor 1
        if detected_left and left_fingers > 0:
            if (now - last_left_send) > SEND_INTERVAL:
                speed = left_fingers * SPEED_PER_FINGER * left_speed_factor
                steps = int(STEPS_CHUNK * left_direction_multiplier)
                send_cmd(f'SPEED1 {int(speed)}')
                send_cmd(f'MOVE1 {steps}')
                send_cmd(f'SPEED2 {int(speed/4)}') #ako vam se previse vraca ovaj drugi motor obrisite za svaki taster ovu i sledecu liniju
                send_cmd(f'MOVE2 {-(steps/4)}')  #vracamo se drugim motorom za duplo manje stepova
                print(f"LEFT  → {left_fingers}/5 | SMER:{'+' if steps > 0 else '-'} | SPD:{int(speed)}")
                last_left_send = now
        elif detected_left and left_fingers == 0:
            send_cmd('STOP1')

    # === PRIKAZ ===
    status_text = "AKTIVAN" if system_active else "CEKAM START (5 prstiju)"
    cv2.putText(img, f"STATUS: {status_text}", (20, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                (0, 255, 0) if system_active else (0, 100, 255), 2)

    cv2.putText(img, f"DESNA M2: {right_fingers}/5", (20, 70),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 150, 255), 2)
    cv2.putText(img, f"LEVA M1:  {left_fingers}/5", (20, 110),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 150, 0), 2)

    cv2.putText(img, "PALAC NAPRED=+ | NAZAD=-", (20, 450),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
    cv2.putText(img, "DLAN=STOP | 1-2=SPOR | 3-4=BRZO", (20, 470),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

    cv2.imshow('GEST KONTROLA 4.0 - FIX', img)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

send_cmd('STOP1')
send_cmd('STOP2')
cap.release()
cv2.destroyAllWindows()
if arduino:
    arduino.close()
print("GOTOVO!")
