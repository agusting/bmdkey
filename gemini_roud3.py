import hid
import time
import sys
import pprint # For pretty printing device info

# Blackmagic Design Speed Editor Vendor and Product IDs
VENDOR_ID = 0x1edb
PRODUCT_ID = 0xda0e

def authenticate_speed_editor(device):
    """
    Performs the authentication handshake with the Speed Editor.
    """
    print("\n[DEBUG] Starting authentication handshake...")
    try:
        # The total buffer MUST be 21 bytes: 1 for the Report ID + 20 for the payload.
        challenge = [0x06] + ([0x00] * 20)
        print(f"[DEBUG] Sending {len(challenge)}-byte challenge to device (Report ID {challenge[0]})")
        device.send_feature_report(bytes(challenge))
        print("[DEBUG] Challenge sent successfully.")
        
        time.sleep(0.05) # Crucial delay

        print("[DEBUG] Attempting to read response...")
        response = device.get_feature_report(0x06, 20)
        print(f"[DEBUG] Received response: {list(response)}")
        print("[SUCCESS] Authentication handshake completed.")
        return True

    except OSError as e:
        print(f"[ERROR] An OS-level error occurred during authentication: {e}", file=sys.stderr)
        print("[INFO] This is the final step. A failure here after a successful pre-auth check points to a firmware/timing issue.", file=sys.stderr)
        return False

def main():
    """
    Main function to connect to the Speed Editor and read data.
    """
    print("--- Blackmagic Speed Editor Diagnostic Script ---")

    print("\n[STEP 1] Enumerating all HID devices to find the editor...")
    try:
        devices = hid.enumerate(VENDOR_ID, PRODUCT_ID)
        if not devices:
            print("\n[FATAL] Speed Editor not found. Please ensure it is plugged in.", file=sys.stderr)
            return
        
        print("[SUCCESS] Found the Speed Editor. Device details:")
        pprint.pprint(devices[0])
        
        # This is our target device path
        device_path = devices[0]['path']
        
        print(f"\n[STEP 2] Attempting to open the device for communication...")
        device = hid.device()
        device.open_path(device_path)
        print("[SUCCESS] Device is open.")
        print(f"  - Manufacturer: {device.get_manufacturer_string()}")
        print(f"  - Product: {device.get_product_string()}")

        # The authentication is the real test now
        if not authenticate_speed_editor(device):
            print("\n[FAILURE] Authentication failed. The device did not respond as expected.", file=sys.stderr)
            print("[ACTION] This still strongly suggests a software conflict. See instructions below.", file=sys.stderr)
            device.close()
            return

        print("\n[SUCCESS] Device is authenticated. Listening for input (Ctrl+C to exit)...")
        device.set_nonblocking(1)
        while True:
            try:
                report = device.read(64)
                if report:
                    print(f"[DATA] {list(report)}")
                time.sleep(0.01)
            except KeyboardInterrupt:
                break

    except OSError as ex:
        print(f"\n[FATAL] An OS-level error occurred: {ex}", file=sys.stderr)
        print("[INFO] This typically means the device is locked or was disconnected.", file=sys.stderr)
    except Exception as ex:
        print(f"\n[FATAL] An unexpected Python error occurred: {ex}", file=sys.stderr)
    finally:
        if 'device' in locals() and 'device' in dir() and device.is_open():
            device.close()
            print("\n[INFO] Device connection closed.")

if __name__ == "__main__":
    main()
    #comment