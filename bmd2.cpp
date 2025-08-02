// --- Preprocessor-based includes ---
#ifdef _WIN32
#include <windows.h>
#else // For Linux
#include <unistd.h>
#include <fakekey/fakekey.h>
#include <X11/Xlib.h>
#include <X11/Xatom.h>
#include <X11/extensions/XTest.h> // Needed for XTestFakeButtonEvent
#endif

// --- Common includes ---
#include <stdlib.h>
#include <stdio.h>
#include <exception>
#include <vector>
#include <set>
#include <algorithm>
#include <ranges>
#include <map>
#include <chrono>
#include <hidapi.h>
#include <fmt/format.h>

// --- Constants ---
#define TIMEOUT_MS (60 * 1000)

// --- Global State ---
static std::set<uint16_t> currentKeyboardState;

// --- Platform-Specific Definitions ---
#ifdef _WIN32 // WINDOWS
// --- Windows Virtual-Key Code Mappings ---
static const std::vector<WORD> MODIFIERS = {VK_LMENU, VK_LWIN}; // Left Alt, Left Windows Key
static const std::map<int, std::pair<WORD, bool>> KEYMAP = {
    // ... (Windows KEYMAP from the previous answer) ...
    {0x01, {VK_F1, false}}, {0x02, {VK_F2, false}}, {0x03, {VK_F3, false}},
    {0x04, {VK_F4, false}}, {0x05, {VK_F5, false}}, {0x06, {VK_F6, false}},
    {0x07, {VK_F7, false}}, {0x08, {VK_F8, false}}, {0x09, {VK_F9, false}},
    {0x0a, {VK_UP, false}}, {0x0b, {VK_F11, false}}, {0x0c, {VK_LEFT, true}},
    {0x0d, {VK_DOWN, false}}, {0x0e, {VK_RIGHT, true}}, {0x0f, {VK_F15, false}},
    {0x10, {VK_F16, false}}, {0x11, {VK_F17, false}}, {0x1a, {VK_F18, false}},
    {0x1b, {VK_F19, false}}, {0x1c, {VK_F20, false}}, {0x1d, {VK_F21, false}},
    {0x1e, {VK_F22, false}}, {0x31, {VK_F1, true}}, {0x1f, {VK_F2, true}},
    {0x2c, {VK_F3, true}}, {0x2d, {VK_F4, true}}, {0x22, {VK_F5, true}},
    {0x2f, {VK_F6, true}}, {0x2e, {VK_F7, true}}, {0x2b, {VK_F8, true}},
    {0x33, {VK_F10, true}}, {0x34, {VK_F11, true}}, {0x35, {VK_F12, true}},
    {0x36, {VK_F13, true}}, {0x37, {VK_F14, true}}, {0x38, {VK_F15, true}},
    {0x39, {VK_F16, true}}, {0x3a, {VK_F17, true}}, {0x3b, {VK_F18, true}},
    {0x25, {VK_F20, true}}, {0x26, {VK_F21, true}}, {0x3c, {VK_F22, true}},
};
#else // LINUX / X11
// --- Linux X11 Global Variables ---
static Display *display;
static FakeKey *fakekey;
static int minKeycode;
static int maxKeycode;
// --- X11 KeySym Mappings ---
static const std::vector<KeySym> MODIFIERS = {XK_Alt_L, XK_Meta_L, XK_Super_L};
static const std::map<int, std::pair<KeySym, bool>> KEYMAP = {
    // ... (Original X11 KEYMAP from your code) ...
    {0x01, {XK_F1, false}}, {0x02, {XK_F2, false}}, {0x03, {XK_F3, false}},
    {0x04, {XK_F4, false}}, {0x05, {XK_F5, false}}, {0x06, {XK_F6, false}},
    {0x07, {XK_F7, false}}, {0x08, {XK_F8, false}}, {0x09, {XK_F9, false}},
    {0x0a, {XK_Up, false}}, {0x0b, {XK_F11, false}}, {0x0c, {XK_Left, true}},
    {0x0d, {XK_Down, false}}, {0x0e, {XK_Right, true}}, {0x0f, {XK_F15, false}},
    {0x10, {XK_F16, false}}, {0x11, {XK_F17, false}}, {0x1a, {XK_F18, false}},
    {0x1b, {XK_F19, false}}, {0x1c, {XK_F20, false}}, {0x1d, {VK_F21, false}},
    {0x1e, {VK_F22, false}}, {0x31, {VK_F1, true}}, {0x1f, {VK_F2, true}},
    {0x2c, {VK_F3, true}}, {0x2d, {VK_F4, true}}, {0x22, {VK_F5, true}},
    {0x2f, {VK_F6, true}}, {0x2e, {VK_F7, true}}, {0x2b, {VK_F8, true}},
    {0x33, {VK_F10, true}}, {0x34, {VK_F11, true}}, {0x35, {VK_F12, true}},
    {0x36, {VK_F13, true}}, {0x37, {VK_F14, true}}, {0x38, {VK_F15, true}},
    {0x39, {VK_F16, true}}, {0x3a, {VK_F17, true}}, {0x3b, {VK_F18, true}},
    {0x25, {VK_F20, true}}, {0x26, {VK_F21, true}}, {0x3c, {VK_F22, true}},
};
#endif

// --- HIDAPI and Authentication Code (Unchanged and Common to Both Platforms) ---
// ... (The HidDevice class, authentication logic, getInt helpers, etc. are all here)
// [This section of your code remains the same]


// --- Platform-Specific Input Simulation Functions ---
#ifdef _WIN32 // WINDOWS
static void send_key_event(WORD vk, bool pressed) {
    INPUT input = {0};
    input.type = INPUT_KEYBOARD;
    input.ki.wVk = vk;
    if (!pressed) input.ki.dwFlags = KEYEVENTF_KEYUP;
    SendInput(1, &input, sizeof(INPUT));
}
static void send_mouse_wheel(bool down) {
    INPUT input = {0};
    input.type = INPUT_MOUSE;
    input.mi.dwFlags = MOUSEEVENTF_WHEEL;
    input.mi.mouseData = down ? -WHEEL_DELTA : WHEEL_DELTA;
    SendInput(1, &input, sizeof(INPUT));
}
static void press_release_modifiers(bool pressed) {
    for (WORD vk : MODIFIERS) send_key_event(vk, pressed);
}
static void handle_key_event(int keynum, bool pressed) {
    auto it = KEYMAP.find(keynum);
    if (it == KEYMAP.end()) return;
    WORD vk_code = it->second.first;
    bool needs_shift = it->second.second;
    if (pressed) {
        if (needs_shift) send_key_event(VK_SHIFT, true);
        send_key_event(vk_code, true);
    } else {
        send_key_event(vk_code, false);
        if (needs_shift) send_key_event(VK_SHIFT, false);
    }
}
#else // LINUX / X11
static void send_mouse_wheel(bool down) {
    int button = down ? 5 : 4; // Button 4 is scroll up, 5 is scroll down
    XTestFakeButtonEvent(display, button, True, 0);
    XTestFakeButtonEvent(display, button, False, 0);
    XFlush(display);
}
static void press_release_modifiers(bool pressed) {
    for (KeySym keysym : MODIFIERS) {
        fakekey_send_keyevent(fakekey, XKeysymToKeycode(display, keysym), pressed, 0);
    }
    XFlush(display);
}
static void handle_key_event(int keynum, bool pressed) {
    auto it = KEYMAP.find(keynum);
    if (it == KEYMAP.end()) return;
    KeySym keysym = it->second.first;
    KeySym keysyms[] = {keysym, keysym};
    KeyCode code = XKeysymToKeycode(display, keysym);
    if (!code) {
        XChangeKeyboardMapping(display, maxKeycode - 1, 2, keysyms, 1);
        XSync(display, False);
        code = maxKeycode - 1;
    }
    fakekey_send_keyevent(fakekey, code, pressed, it->second.second ? FAKEKEYMOD_SHIFT : 0);
}
#endif

// --- Main Application Logic (with platform-specific setup) ---
int main()
{
#ifdef _WIN32
    // Windows atexit handler
    atexit([]() {
        for (uint16_t k : currentKeyboardState) handle_key_event(k, false);
        press_release_modifiers(false);
    });
#else
    // Linux/X11 setup
    display = XOpenDisplay(nullptr);
    if (!display) {
        fmt::print(stderr, "Cannot open X11 display.\n");
        return 1;
    }
    fakekey = fakekey_init(display);
    XDisplayKeycodes(display, &minKeycode, &maxKeycode);
    // Linux/X11 atexit handler
    atexit([]() {
        for (uint16_t k : currentKeyboardState) handle_key_event(k, false);
        press_release_modifiers(false);
        if (fakekey) fakekey_destroy(fakekey);
        if (display) XCloseDisplay(display);
    });
#endif

    hid_init();
    {
        HidDevice device(0x1edb, 0xda0e);
        authenticate(device);
        device.send({3, 0, 0, 0, 0, 0, 0});
        device.send({2, 0xff, 0xff, 0xff, 0xff});

        int32_t wheel_accumulator = 0;
        int msTimeout = TIMEOUT_MS;

        for (;;) {
            try {
                auto beforeTime = std::chrono::steady_clock::now();
                auto data = device.recv(msTimeout);
                auto afterTime = std::chrono::steady_clock::now();
                msTimeout -= std::chrono::duration_cast<std::chrono::milliseconds>(afterTime - beforeTime).count();

                switch (data[0]) {
                    case 3: { // Wheel packet
                        int32_t delta = getInt32(&data[2]);
                        wheel_accumulator += delta;
                        const int WHEEL_STEP_THRESHOLD = 30000;
                        while (abs(wheel_accumulator) >= WHEEL_STEP_THRESHOLD) {
                            if (wheel_accumulator > 0) {
                                send_mouse_wheel(false); // Scroll Up
                                wheel_accumulator -= WHEEL_STEP_THRESHOLD;
                            } else {
                                send_mouse_wheel(true); // Scroll Down
                                wheel_accumulator += WHEEL_STEP_THRESHOLD;
                            }
                        }
                        break;
                    }
                    case 4: { // Keyboard packet
                        std::set<uint16_t> newKeyboardState;
                        for (int i = 0; i < 6; i++) {
                            uint16_t keycode = getInt16(&data[1 + i * 2]);
                            if (keycode) newKeyboardState.insert(keycode);
                        }
                        std::set<uint16_t> keysPressed;
                        std::ranges::set_difference(newKeyboardState, currentKeyboardState, std::inserter(keysPressed, keysPressed.begin()));
                        std::set<uint16_t> keysReleased;
                        std::ranges::set_difference(currentKeyboardState, newKeyboardState, std::inserter(keysReleased, keysReleased.begin()));

                        if (currentKeyboardState.empty() && !newKeyboardState.empty()) {
                            press_release_modifiers(true);
                        }
                        for (uint16_t k : keysPressed) handle_key_event(k, true);
                        for (uint16_t k : keysReleased) handle_key_event(k, false);
                        if (!currentKeyboardState.empty() && newKeyboardState.empty()) {
                            press_release_modifiers(false);
                        }
                        currentKeyboardState = newKeyboardState;
                        break;
                    }
                    default:
                        fmt::print("Unhandled packet: ");
                        for (uint8_t c : data) fmt::print("{:02x} ", c);
                        fmt::print("\n");
                }
            }
            catch (const TimeoutException &e) {
                msTimeout = 0;
            }
            if (msTimeout <= 0) {
                msTimeout = TIMEOUT_MS;
                authenticate(device);
            }
        }
    }
    hid_exit();
    return 0;
}