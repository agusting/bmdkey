import hid
import time
import sys
import os
from Crypto.Cipher import AES

# Blackmagic Design Speed Editor Vendor and Product IDs
VENDOR_ID = 0x1edb
PRODUCT_ID = 0xda0e
# The shared secret key for the AES handshake
AES_KEY = b'CHANGEME'

# Mappings for the key/button report (Report ID 1).
KEY_MAPPINGS = {
    (1, 0x01): "SMART IN",   (1, 0x02): "SMART OUT",  (1, 0x04): "TRANS",
    (1, 0x08): "BLACK",      (1, 0x10): "FREEZE",     (1, 0x20): "JOG",
    (1, 0x40): "SHTL",       (1, 0x80): "SCRL",
    (2, 0x01): "ESC",        (2, 0x02): "SYNC BIN",   (2, 0x04): "AUDIO LEVEL",
    (2, 0x08): "FULL VIEW",  (2, 0x10): "TRANS DUR",  (2, 0x20): "CUT",
    (2, 0x40): "DIS",        (2, 0x80): "SMTH CUT",
    (3, 0x01): "INS",        (3, 0x02): "APPND",      (3, 0x04): "RIP O/WR",
    (3, 0x08): "PLACE ON TOP",(3, 0x10): "SRC O/WR",
    (4, 0x01): "CAM 1",      (4, 0x02): "CAM 2",      (4, 0x04): "CAM 3",
    (4, 0x08): "CAM 4",      (4, 0x10): "CAM 5",      (4, 0x20): "CAM 6",
    (4, 0x40): "CAM 7",      (4, 0x80): "CAM 8",
    (5, 0x01): "CAM 9",      (5, 0x02): "LIVE O/WR",  (5, 0x04): "VIDEO ONLY",
    (5, 0x08): "AUDIO ONLY", (5, 0x10): "STOP/PLAY",
    (6, 0x01): "IN",         (6, 0x02): "OUT",        (6, 0x04): "TRIM IN",
    (6, 0x08): "TRIM OUT",   (6, 0x10): "ROLL",       (6, 0x20): "SLIP SRC",
    (6, 0x40): "SLIP DEST",  (6, 0x80): "TRANS DISS",
    (7, 0x01): "SNAP",       (7, 0x02): "RIPL DEL",
}
JOG_MODE_MAPPINGS = {0: "JOG", 1: "SHTL", 2: "SCRL"}

def process_report(report, prev_key_report):
    report_id = report[0]
    if report_id == 1:
        for byte_index in range(1, 9):
            if byte_index < len(report) and report[byte_index] != prev_key_report[byte_index]:
                for bit in range(8):
                    bit_mask = 1 << bit
                    if (byte_index, bit_mask) in KEY_MAPPINGS:
                        key_name = KEY_MAPPINGS[(byte_index, bit_mask)]
                        if (report[byte_index] & bit_mask) and not (prev_key_report[byte_index] & bit_mask):
                            print(f"[KEY DOWN] {key_name}")
                        elif not (report[byte_index] & bit_mask) and (prev_key_report[byte_index] & bit_mask):
                            print(f"[KEY UP]   {key_name}")
        return report
    elif report_id == 2:
        value = report[1] | (report[2] << 8)
        if value >= 32768: value -= 65536
        mode_id = report[4]
        mode_name = JOG_MODE_MAPPINGS.get(mode_id, f"Unknown Mode {mode_id}")
        if value != 0: print(f"[{mode_name}] Value: {value}")
        return prev_key_report
    return prev_key_report

def main():
    print("--- Blackmagic Speed Editor Controller (Full Handshake) ---")
    device_handle = None

    try:
        devices_info = hid.enumerate(VENDOR_ID, PRODUCT_ID)
        if not devices_info:
            print("\n[FATAL] Speed Editor not found.", file=sys.stderr)
            return

        target_device_info = None
        for device_info in devices_info:
            if device_info['interface_number'] == 2:
                target_device_info = device_info
                break
        
        if not target_device_info:
            print("\n[FATAL] Could not find the required data interface (interface #2).", file=sys.stderr)
            return

        print(f"[INFO] Found target data interface at path: {target_device_info['path'].decode()}")

        device_handle = hid.device()
        device_handle.open_path(target_device_info['path'])
        
        # --- Step 1: Send the initial challenge ---
        print("[AUTH] Step 1: Sending challenge...")
        challenge = [0x06, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                     0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                     0x00, 0x00, 0x00, 0x00]
        device_handle.send_feature_report(bytes(challenge))
        
        # --- Step 2: Receive the keyboard's encrypted response ---
        print("[AUTH] Step 2: Receiving encrypted response from keyboard...")
        response = device_handle.get_feature_report(0x06, 20)
        
        iv = bytes(response[0:16])
        encrypted_token = bytes(response[16:20])
        print(f"  - IV received: {iv.hex()}")
        print(f"  - Encrypted token: {encrypted_token.hex()}")

        # --- Step 3: Decrypt the token ---
        print("[AUTH] Step 3: Decrypting token with shared secret key...")
        cipher = AES.new(AES_KEY, AES.MODE_CBC, iv=iv)
        decrypted_token = cipher.decrypt(encrypted_token)
        print(f"  - Decrypted token: {decrypted_token.hex()}")

        # --- Step 4: Send the decrypted token back to unlock the device ---
        print("[AUTH] Step 4: Sending decrypted token back to keyboard...")
        unlock_report = [0x07, 0x00, 0x00, 0x00, 0x00]
        unlock_report[1:5] = decrypted_token
        device_handle.send_feature_report(bytes(unlock_report))
        print("[SUCCESS] Device unlocked!")
        
        # --- Step 5: Begin listening for events ---
        print("\n--- Listening for Events ---")
        device_handle.set_nonblocking(0) # Use robust blocking reads
        previous_key_report = [0] * 64
        while True:
            report = device_handle.read(64)
            if report:
                previous_key_report = process_report(report, previous_key_report)

    except OSError as e:
        print(f"\n[FATAL] OS Error: {e}", file=sys.stderr)
        if "Permission" in str(e):
             print("[INFO] On Linux, ensure you are running with 'sudo' or have a correct udev rule.", file=sys.stderr)
        else:
             print("[INFO] This can happen if another program (DaVinci Resolve) has a lock on the device.", file=sys.stderr)
    except KeyboardInterrupt:
        print("\n\nExiting.")
    except Exception as e:
        print(f"\n[FATAL] An unexpected error occurred: {e}", file=sys.stderr)
    finally:
        if device_handle:
            device_handle.close()
            print("\n[INFO] Device connection closed.")

if __name__ == "__main__":
    main()