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
# Brzina motora po prstu (steps/sec)
MOVE_PER_FINGER = 150  # 1 prst = 150, 5 prstiju = 750 steps/sec
# Koliko koraka šaljemo svaki interval dok su prsti gore
STEPS_CHUNK = 2000  # Relativni koraci koji se šalju u loop-u
SEND_INTERVAL = 0.3  # Svake 150ms šalji nove korake (dok su prsti gore)
SPEED_PER_FINGER = 400

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

print("LEVA RUKA = Motor 1 | DESNA RUKA = Motor 2")
print("START: SVI PRSTI GORE (5/5) | STOP: DLAN (0/5) | Q=QUIT")

while True:
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

            tipIds = [4, 8, 12, 16, 20]
            pipIds = [2, 6, 10, 14, 18]
            fingers = 0

            # Palac
            if handLms.landmark[4].z < handLms.landmark[2].z + 0.05:
                fingers += 1
            # Ostali prsti
            for i in range(1, 5):
                if handLms.landmark[tipIds[i]].y < handLms.landmark[pipIds[i]].y:
                    fingers += 1

            # Sistem start/stop
            if fingers == 5 and not system_active:
                system_active = True
                print("SISTEM START!")
            elif fingers == 0 and system_active:
                system_active = False
                send_cmd('STOP1')
                send_cmd('STOP2')
                print("SISTEM STOP!")

            if handedness == 'Right':
                right_fingers = fingers
                detected_right = True
            elif handedness == 'Left':
                left_fingers = fingers
                detected_left = True

            mp_drawing.draw_landmarks(img, handLms, mp_hands.HAND_CONNECTIONS)

    # === KONTINUALNO SLANJE DOK SU PRSTI GORE ===
    # Motor se okreće sve dok ima prstiju gore, brzina zavisi od broja prstiju
    if system_active:
        # DESNA RUKA → Motor 2
        if detected_right and right_fingers > 0:
            if (now - last_right_send) > SEND_INTERVAL:
                speed = right_fingers * SPEED_PER_FINGER
                send_cmd(f'SPEED2 {int(speed)}')
                print(f'SPEED2 {speed}')
                send_cmd(f'MOVE2 {STEPS_CHUNK}')
                print(f"RIGHT {right_fingers}/5 → brzina {speed}")
                last_right_send = now
        elif detected_right and right_fingers == 0:
            send_cmd('STOP2')

        # LEVA RUKA → Motor 1
        if detected_left and left_fingers > 0:
            if (now - last_left_send) > SEND_INTERVAL:
                speed = left_fingers * SPEED_PER_FINGER
                send_cmd(f'SPEED1 {speed}')
                send_cmd(f'MOVE1 {STEPS_CHUNK}')
                print(f"LEFT  {left_fingers}/5 → brzina {speed}")
                last_left_send = now
        elif detected_left and left_fingers == 0:
            send_cmd('STOP1')

    # Prikaz
    status_text = "AKTIVAN" if system_active else "CEKAM START (5 prstiju)"
    cv2.putText(img, f"STATUS: {status_text}", (20, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                (0, 255, 0) if system_active else (0, 100, 255), 2)
    cv2.putText(img, f"DESNA (M2): {right_fingers}/5",
                (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 150, 255), 3)
    cv2.putText(img, f"LEVA  (M1): {left_fingers}/5",
                (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 150, 0), 3)
    cv2.putText(img, "SVI PRSTI=START | DLAN=STOP | Q=QUIT",
                (20, 450), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)

    cv2.imshow('GEST KONTROLA', img)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

send_cmd('STOP1')
send_cmd('STOP2')
cap.release()
cv2.destroyAllWindows()
if arduino:
    arduino.close()
print("GOTOVO!")
