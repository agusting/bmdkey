import hid
import struct
import time
import enum
from typing import List
from pynput.keyboard import Controller as KeyboardController, Key
from pynput.mouse import Controller as MouseController, Button

# ==================================================================================
# STEP 1: VERIFY YOUR PRODUCT ID
#
# Find your Product ID using the steps above and enter it here.
# The value must be an integer. 'BD3D' becomes 0xBD3D.
#
# ==================================================================================
# Common Speed Editor PID. Change this if your device is different.
YOUR_PRODUCT_ID = 0xBD3D


# ==================================================================================
# STEP 2: DEFINE YOUR CUSTOM KEY MAP
#
# This is where you define what each button on the Speed Editor should do.
# ==================================================================================

KEY_MAP = {
    # --- Example Mappings ---
    'SMART_INSRT': {'type': 'key', 'action': Key.f5},
    'APPND':       {'type': 'string', 'action': 'This is my custom text!'},
    'RIPL_OWR':    {'type': 'mouse_click', 'action': Button.right},
    'CLOSE_UP':    {'type': 'combo', 'action': [Key.ctrl, 'c']},
    'PLACE_ON_TOP':{'type': 'combo', 'action': [Key.ctrl, 'v']},

    # --- Add Your Own Mappings Below ---
    'CAM1':        {'type': 'key', 'action': '1'},
    'CAM2':        {'type': 'key', 'action': '2'},
    'CAM3':        {'type': 'key', 'action': '3'},
    'SPLIT':       {'type': 'string', 'action': 'Split command executed.'},
    'SNAP':        {'type': 'key', 'action': Key.enter},
}

# ==================================================================================
#
#       (No need to modify anything below this line)
#
# ==================================================================================

# --- Enums from provided code ---
class SpeedEditorKey(enum.IntEnum):
    NONE=0x00;SMART_INSRT=0x01;APPND=0x02;RIPL_OWR=0x03;CLOSE_UP=0x04;PLACE_ON_TOP=0x05;SRC_OWR=0x06;IN=0x07;OUT=0x08;TRIM_IN=0x09;TRIM_OUT=0x0a;ROLL=0x0b;SLIP_SRC=0x0c;SLIP_DEST=0x0d;TRANS_DUR=0x0e;CUT=0x0f;DIS=0x10;SMTH_CUT=0x11;SOURCE=0x1a;TIMELINE=0x1b;SHTL=0x1c;JOG=0x1d;SCRL=0x1e;ESC=0x31;SYNC_BIN=0x1f;AUDIO_LEVEL=0x2c;FULL_VIEW=0x2d;TRANS=0x22;SPLIT=0x2f;SNAP=0x2e;RIPL_DEL=0x2b;CAM1=0x33;CAM2=0x34;CAM3=0x35;CAM4=0x36;CAM5=0x37;CAM6=0x38;CAM7=0x39;CAM8=0x3a;CAM9=0x3b;LIVE_OWR=0x30;VIDEO_ONLY=0x25;AUDIO_ONLY=0x26;STOP_PLAY=0x3c

# --- Authentication logic from provided code ---
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

# --- Device communication class ---
class SpeedEditor:
    USB_VID=0x1edb

    def __init__(self, pid):
        self.dev = hid.Device(self.USB_VID, pid) # This will raise HIDException if it fails

    def authenticate(self):
        self.dev.send_feature_report(b'\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00')
        data=self.dev.get_feature_report(6,10)
        if data[0:2]!=b'\x06\x00':raise RuntimeError('Failed auth get_kbd_challenge')
        challenge=int.from_bytes(data[2:],'little')
        self.dev.send_feature_report(b'\x06\x01\x00\x00\x00\x00\x00\x00\x00\x00')
        data=self.dev.get_feature_report(6,10)
        if data[0:2]!=b'\x06\x02':raise RuntimeError('Failed auth get_kbd_response')
        response=bmd_kbd_auth(challenge)
        self.dev.send_feature_report(b'\x06\x03'+response.to_bytes(8,'little'))
        data=self.dev.get_feature_report(6,10)
        if data[0:2]!=b'\x06\x04':raise RuntimeError('Failed auth get_kbd_status')
        return int.from_bytes(data[2:4],'little')

    def read_keys(self):
        report = self.dev.read(64, timeout=50)
        if not report or report[0] != 4: return []
        keys = [SpeedEditorKey(k) for k in struct.unpack('<6H', report[1:13]) if k != 0]
        return keys

# --- Main application logic ---
def main():
    keyboard = KeyboardController()
    mouse = MouseController()
    
    try:
        print(f"Attempting to connect to Speed Editor (PID: {hex(YOUR_PRODUCT_ID)})...")
        se = SpeedEditor(pid=YOUR_PRODUCT_ID)
        
        print("Device found. Authenticating...")
        se.authenticate()
        
        print("Authentication successful! Listening for key presses...")
        print("(Press Ctrl+C in this window to exit the script)")

        last_keys = []
        while True:
            current_keys = se.read_keys()
            pressed_keys = [k for k in current_keys if k not in last_keys]

            for key in pressed_keys:
                key_name = key.name
                if key_name in KEY_MAP:
                    mapping = KEY_MAP[key_name]
                    action_type = mapping.get('type')
                    action = mapping.get('action')
                    print(f"Key: {key_name:<12} -> Action: {mapping}")
                    if action_type == 'key': keyboard.press(action); keyboard.release(action)
                    elif action_type == 'string': keyboard.type(action)
                    elif action_type == 'mouse_click': mouse.click(action)
                    elif action_type == 'combo':
                        with keyboard.pressed(*action[:-1]):
                            keyboard.press(action[-1]); keyboard.release(action[-1])
            last_keys = current_keys
            time.sleep(0.01)

    except hid.HIDException:
        print("\nERROR: FAILED TO CONNECT TO SPEED EDITOR.")
        print("Please check the following:")
        print("  1. Is the Product ID in the script correct? Use the diagnostic script to check.")
        print("  2. Is DaVinci Resolve or other Blackmagic software completely closed?")
        print("  3. Is the device securely plugged in?")
        print("  4. Try running this script from a Command Prompt with 'Run as administrator'.")
    except RuntimeError as e:
        print(f"\nERROR: An error occurred during authentication: {e}")
    except KeyboardInterrupt:
        print("\nExiting script. Goodbye!")

if __name__ == "__main__":
    main()