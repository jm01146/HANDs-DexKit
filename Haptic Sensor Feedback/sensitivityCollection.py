import time
import math
import threading
from datetime import datetime

import serial
from serial import SerialException

from openpyxl import Workbook
from openpyxl.utils import get_column_letter

# USER CONFIG
SERIAL_PORT = "COM4"          # change this (e.g., "COM3" on Windows, "/dev/ttyACM0" on Linux)
BAUD_RATE = 115200            # must match your microcontroller serial baud
READ_TIMEOUT_S = 1.0

OUTPUT_XLSX = "distanceRecording_someAxisChange_numberTrials.xlsx"

# How often to save the workbook (seconds)
SAVE_EVERY_S = 10

# Your allowed labels (mm). You can add more if needed.
ALLOWED_DISTANCE_MM = [0, 1, 2, 5, 10, 15, 20, 25, 50, 75, 100, 125, 150]

# GLOBAL STATE (current label)
label_lock = threading.Lock()
current_distance_mm = 0
current_note = "standard"

def set_label(distance_mm: int, note: str = ""):
    global current_distance_mm, current_note
    with label_lock:
        current_distance_mm = distance_mm
        current_note = note if note else current_note


def get_label():
    with label_lock:
        return current_distance_mm, current_note
    

def try_parse_bxyz(line: str):
    """
    Expects a line like:
        "12.3,-45.6,78.9"
    OR with labels:
        "Bx:12.3,By:-45.6,Bz:78.9"
    We will extract the first 3 numbers we find.
    """
    # Keep digits, minus, dot, comma, and spaces. Replace other stuff with space.
    cleaned = []
    for ch in line:
        if ch.isdigit() or ch in "-., ":
            cleaned.append(ch)
        else:
            cleaned.append(" ")
    cleaned = "".join(cleaned)

    # Split by commas first; fallback to whitespace
    parts = [p.strip() for p in cleaned.split(",") if p.strip()]
    if len(parts) < 3:
        parts = cleaned.split()

    nums = []
    for p in parts:
        try:
            nums.append(float(p))
        except ValueError:
            continue
        if len(nums) == 3:
            break

    if len(nums) != 3:
        return None

    bx, by, bz = nums
    return bx, by, bz


def make_workbook():
    wb = Workbook()
    ws = wb.active
    ws.title = "raw_log"

    headers = [
        "timestamp_iso",
        "epoch_s",
        "distance_mm",
        "note",
        "Bx_uT",
        "By_uT",
        "Bz_uT",
        "Bmag_uT",
        "raw_line",
    ]
    ws.append(headers)

    # Make columns a bit wider (optional)
    widths = [24, 12, 10, 10, 16, 10, 10, 10, 10, 40]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w

    return wb, ws


def label_input_thread(stop_event: threading.Event):
    """
    Console thread: lets you change current label while logging.
    Commands:
      - type a mass in grams: 0,10,100,200,500,1000
      - "note something" to set a note
      - "help" to reprint
      - "q" to quit
    """
    print("\nLabel control ready.")
    print("Type one of these masses (g) to label data:", ALLOWED_DISTANCE_MM)
    print('Optional: type "note baseline", or "note loading", etc.')
    print('Type "q" then Enter to stop.\n')

    while not stop_event.is_set():
        try:
            cmd = input().strip()
        except EOFError:
            stop_event.set()
            break
        except KeyboardInterrupt:
            stop_event.set()
            break

        if not cmd:
            continue

        if cmd.lower() in ("q", "quit", "exit"):
            stop_event.set()
            break

        if cmd.lower() == "help":
            print("Commands:")
            print("  0 | 1 | 2 | 5 | 10 | ... |   (set weight label in mm)")
            print('  note <text>                  (set note text)')
            print("  q                            (quit)")
            continue

        if cmd.lower().startswith("note "):
            note = cmd[5:].strip()
            if note:
                with label_lock:
                    global current_note
                    current_note = note
                print(f"Note set to: {note}")
            continue

        # Try interpret as mass label
        try:
            distance_mm = int(cmd)
        except ValueError:
            print("Didn’t understand. Type 'help' for commands.")
            continue

        if distance_mm not in ALLOWED_DISTANCE_MM:
            print(f"Mass must be one of: {ALLOWED_DISTANCE_MM}")
            continue

        set_label(distance_mm)
        d, note = get_label()
        print(f"Label set: distance_mm={d}, note={note}")


def main():
    print("Starting magnet force data logger...")
    print(f"Port: {SERIAL_PORT}  Baud: {BAUD_RATE}")
    print(f"Output: {OUTPUT_XLSX}")
    print("IMPORTANT: Your serial device must output Bx,By,Bz each line.\n")

    wb, ws = make_workbook()

    stop_event = threading.Event()
    t = threading.Thread(target=label_input_thread, args=(stop_event,), daemon=True)
    t.start()

    last_save = time.time()
    row_count = 0

    try:
        with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=READ_TIMEOUT_S) as ser:
            # Give serial a second to settle (especially on Arduino reset)
            time.sleep(1.5)
            ser.reset_input_buffer()

            print("Logging... (change labels by typing in console; 'q' to quit)\n")

            while not stop_event.is_set():
                try:
                    raw = ser.readline()
                except SerialException as e:
                    print(f"Serial error: {e}")
                    break

                if not raw:
                    continue

                try:
                    line = raw.decode("utf-8", errors="replace").strip()
                except Exception:
                    continue

                parsed = try_parse_bxyz(line)
                if parsed is None:
                    # Still log it if you want to debug format issues:
                    # comment this out if you only want valid numeric rows.
                    ts = datetime.now().isoformat(timespec="milliseconds")
                    epoch = time.time()
                    d, note = get_label()
                    ws.append([ts, epoch, d, note, None, None, None, None, line])
                    row_count += 1
                    continue

                bx, by, bz = parsed
                bmag = math.sqrt(bx * bx + by * by + bz * bz)

                ts = datetime.now().isoformat(timespec="milliseconds")
                epoch = time.time()
                d, note = get_label()

                ws.append([ts, epoch, d, note, bx, by, bz, bmag, line])
                row_count += 1

                # Periodic save
                now = time.time()
                if (now - last_save) >= SAVE_EVERY_S:
                    wb.save(OUTPUT_XLSX)
                    last_save = now
                    print(f"Saved {row_count} rows... current label: {d} mm, note='{note}'")

    except KeyboardInterrupt:
        stop_event.set()
    except SerialException as e:
        print(f"Could not open serial port: {e}")

    # Final save
    try:
        wb.save(OUTPUT_XLSX)
        print(f"\nFinal save complete. Total rows: {row_count}")
        print(f"File written: {OUTPUT_XLSX}")
    except Exception as e:
        print(f"Failed to save workbook: {e}")


if __name__ == "__main__":
    main()
