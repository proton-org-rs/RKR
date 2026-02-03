import time
import serial
import serial.tools.list_ports
BAUD = 115200


def list_ports():
    ports = list(serial.tools.list_ports.comports())
    if not ports:
        print("Nema portova")
        return []
    print("Portovi:")
    for i, p in enumerate(ports):
        print(f"  [{i}] {p.device}-{p.description}")
    return ports


def pick_port():
    ports = list_ports()
    if not ports:
        raise SystemExit(1)

    if len(ports) == 1:
        return ports[0].device

    s = input("Izaberi port:").strip()
    ind = int(s) if s else 0
    return ports[ind].device


def send_cmd(ser: serial.Serial, cmd: str, wait_reply: bool = True) -> str:
    cmd = cmd.strip()
    if not cmd:
        return ""

    ser.write((cmd + "\n").encode("utf-8"))
    ser.flush()

    if not wait_reply:
        return ""

    reply = ser.readline().decode("utf-8", errors="replace").strip()
    return reply


def demo_plus_minus(ser: serial.Serial, steps: int = 2000, pause_s: float = 0.3):
    r = send_cmd(ser, f"MOVE1 {steps}")
    r1 = send_cmd(ser, f"MOVE2 {steps}")
    print(f"> MOVE1 {steps}\n< {r}")
    print(f"> MOVE2 {steps}\n< {r1}")
    time.sleep(pause_s)

    r = send_cmd(ser, f"MOVE1 {-steps}")
    r1 = send_cmd(ser, f"MOVE2 {-steps}")
    print(f"> MOVE {-steps}\n< {r}")
    print(f"> MOVE {-steps}\n< {r1}")
    time.sleep(pause_s)


def main():
    port = pick_port()
    print(f"Koristim port: {port}")

    with serial.Serial(port, BAUD, timeout=1) as ser:
        time.sleep(2.0)
        ser.reset_input_buffer()

        for cmd in ["EN 1", "SPEED 300", "ACCEL 200"]:
            reply = send_cmd(ser, cmd)
            print(f"> {cmd}\n< {reply}")

        print("\nPrikaz:\n")
        for _ in range(3):
            demo_plus_minus(ser, steps=2000, pause_s=1.0)

        print("\nKRAJ.")
 

if __name__ == "__main__":
    main()