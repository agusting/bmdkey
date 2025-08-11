import hid
import time

def rol8(value):
    return ((value << 8) & 0xFFFFFFFFFFFFFFFF) | (value >> (64 - 8))

def rol8n(value, n):
    shift = (n * 8) % 64
    return ((value << shift) & 0xFFFFFFFFFFFFFFFF) | (value >> (64 - shift))

def calculateKeyboardResponse(challenge):
    auth_even_tbl = [
        0x3ae1206f97c10bc8,
        0x2a9ab32bebf244c6,
        0x20a6f8b8df9adf0a,
        0xaf80ece52cfc1719,
        0xec2ee2f7414fd151,
        0xb055adfd73344a15,
        0xa63d2e3059001187,
        0x751bf623f42e0dde
    ]
    auth_odd_tbl = [
        0x3e22b34f502e7fde,
        0x24656b981875ab1c,
        0xa17f3456df7bf8c3,
        0x6df72e1941aef698,
        0x72226f011e66ab94,
        0x3831a3c606296b42,
        0xfd7ff81881332c89,
        0x61a3f6474ff236c6
    ]
    mask = 0xa79a63f585d37bf0

    n = challenge & 0b111
    v = rol8n(challenge, n)

    if (v & 1) == ((0x78 >> n) & 1):
        k = auth_even_tbl[n]
    else:
        v = v ^ rol8(v)
        k = auth_odd_tbl[n]

    rotated_v = rol8(v)
    response = v ^ (rotated_v & mask) ^ k
    return response

def find_speed_editor_interface():
    """Find the Speed Editor device with usage_page=0xff01 (control interface)."""
    devices = hid.enumerate()
    for d in devices:
        product = d.get("product_string") or ""
        usage_page = d.get("usage_page", 0)
        vendor_id = d.get("vendor_id")
        product_id = d.get("product_id")
        interface_number = d.get("interface_number", -1)
        if "speed editor" in product.lower() and usage_page == 0xff01:
            print(f"Found Speed Editor control interface: VID={vendor_id:04X} PID={product_id:04X} Interface={interface_number}")
            return vendor_id, product_id, interface_number
    raise RuntimeError("Speed Editor control interface not found")

def connect_and_authenticate():
    vid, pid, interface = find_speed_editor_interface()

    dev = hid.device()
    dev.open(vid, pid, interface)
    dev.set_nonblocking(True)

    # Send handshake initiation as feature report (report ID 0x02)
    req_packet = [0x02, 0x10] + [0] * 62
    print("Sending handshake initiation (feature report)...")
    dev.send_feature_report(req_packet)

    # Wait for challenge with timeout
    print("Waiting for challenge (up to 5 seconds)...")
    challenge_data = None
    for _ in range(50):  # 50 x 0.1s = 5 seconds timeout
        data = dev.read(64)
        if data:
            challenge_data = data
            break
        time.sleep(0.1)

    if not challenge_data:
        raise RuntimeError("No challenge received from device within timeout")

    challenge_bytes = bytes(challenge_data[:8])
    challenge = int.from_bytes(challenge_bytes, "little")
    print(f"Received challenge bytes: {challenge_bytes.hex()}")
    print(f"Challenge value: {challenge:016X}")

    # Calculate response
    response = calculateKeyboardResponse(challenge)
    response_bytes = response.to_bytes(8, "little")

    # Send response as feature report
    response_packet = [0x02, 0x10] + list(response_bytes) + [0] * (64 - 10)
    print(f"Sending response: {response_bytes.hex()}")
    dev.send_feature_report(response_packet)

    print("Authentication sent. Listening for events...")

    try:
        while True:
            event = dev.read(64)
            if event:
                print("Event:", event)
            else:
                time.sleep(0.05)
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        dev.close()

if __name__ == "__main__":
    connect_and_authenticate()
