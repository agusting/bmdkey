import hid
import sys
import time

# --- Device IDs confirmed by you ---
BMD_VENDOR_ID = 0x1edb
SPEED_EDITOR_PRODUCT_ID = 0xda0e # Using the specific ID you provided

# --- Authentication logic (no changes needed here) ---
def bmd_kbd_auth(challenge):
    AUTH_EVEN_TBL=[0x3ae1206f97c10bc8,0x2a9ab32bebf244c6,0x20a6f8b8df9adf0a,0xaf80ece52cfc1719,0xec2ee2f7414fd151,0xb055adfd73344a15,0xa63d2e3059001187,0x751bf623f42e0dde];AUTH_ODD_TBL=[0x3e22b34f502e7fde,0x24656b981875ab1c,0xa17f3456df7bf8c3,0x6df72e1941aef698,0x72226f011e66ab94,0x3831a3c606296b42,0xfd7ff81881332c89,0x61a3f6474ff236c6];MASK=0xa79a63f585d37bf0
    def rol8(v): return ((v<<56)|(v>>8))&0xffffffffffffffff
    def rol8n(v,n):
        for _ in range(n): v=rol8(v)
        return v
    n=challenge&7;v=rol8n(challenge,n)
    if(v&1)==((0x78>>n)&1):k=AUTH_EVEN_TBL[n]
    else:v=v^rol8(v);k=AUTH_ODD_TBL[n]
    return v^(rol8(v)&MASK)^k

def main():
    """Main function to connect and authenticate."""
    device = None
    try:
        # --- 1. CONNECT TO THE DEVICE ---
        print(f"Searching for Speed Editor (VID={hex(BMD_VENDOR_ID)}, PID={hex(SPEED_EDITOR_PRODUCT_ID)})...")
        device = hid.Device(vid=BMD_VENDOR_ID, pid=SPEED_EDITOR_PRODUCT_ID)
        print("[SUCCESS] Device found and connection opened.")

        # --- 2. PERFORM AUTHENTICATION ---
        print("\nStarting authentication handshake...")

        print("   - Step 1: Sending reset command...")
        device.send_feature_report(b'\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00')

        print("   - Step 2: Reading challenge from device...")
        challenge_data = device.get_feature_report(6, 10)
        if challenge_data[0:2] != b'\x06\x00':
            raise RuntimeError(f"Failed to get challenge. Expected report 06 00, but got {challenge_data[:2].hex()}.")
        challenge = int.from_bytes(challenge_data[2:], 'little')
        print("        Challenge received.")

        print("   - Step 3: Sending dummy challenge to device...")
        device.send_feature_report(b'\x06\x01\x00\x00\x00\x00\x00\x00\x00\x00')
        
        print("   - Step 4: Reading (and ignoring) device response...")
        kbd_response = device.get_feature_report(6, 10)
        if kbd_response[0:2] != b'\x06\x02':
            raise RuntimeError(f"Device did not send expected response. Expected report 06 02, but got {kbd_response[:2].hex()}.")

        print("   - Step 5: Computing and sending our response...")
        response = bmd_kbd_auth(challenge)
        device.send_feature_report(b'\x06\x03' + response.to_bytes(8, 'little'))
        
        print("   - Step 6: Reading final authentication status...")
        status_data = device.get_feature_report(6, 10)
        if status_data[0:2] != b'\x06\x04':
            raise RuntimeError("Authentication sequence failed at the final step.")

        print("\n----------------------------------------------------")
        print(">>> [SUCCESS] Authentication complete! <<<")
        print("The Speed Editor is connected and authenticated.")
        print("----------------------------------------------------")

        # Keep the script alive for a few seconds to confirm connection
        print("\nThis script will close in 10 seconds...")
        time.sleep(10)

    except hid.HIDException:
        print("\n[ERROR] Could not connect to the Speed Editor.", file=sys.stderr)
        print("This means the hid.Device() function failed.", file=sys.stderr)
        print("Please check these things:", file=sys.stderr)
        print("  1. Is DaVinci Resolve or any other Blackmagic software completely closed?", file=sys.stderr)
        print("  2. Is the device securely plugged in?", file=sys.stderr)
        print("  3. Try running this script from a Command Prompt with 'Run as administrator'.", file=sys.stderr)

    except (RuntimeError, ValueError) as e:
        print(f"\n[ERROR] An error occurred during the authentication process: {e}", file=sys.stderr)
        print("This usually means the connection was made, but the handshake failed.", file=sys.stderr)

    finally:
        if device:
            device.close()
            print("\nDevice connection closed.")

if __name__ == "__main__":
    main()