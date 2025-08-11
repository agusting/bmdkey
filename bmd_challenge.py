import hid

def rol8(value):
    """Rotate 64-bit integer left by 8 bits (1 byte)."""
    return ((value << 8) & 0xFFFFFFFFFFFFFFFF) | (value >> (64 - 8))

def rol8n(value, n):
    """Rotate 64-bit integer left by n bytes (n*8 bits)."""
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

    print(f"\n--- Calculating response for challenge: {challenge:016X} ---")

    n = challenge & 0b111
    print(f"n (low 3 bits)  : {n}")

    v = rol8n(challenge, n)
    print(f"v after rol8n   : {v:016X}")

    if (v & 1) == ((0x78 >> n) & 1):
        print("Path: EVEN")
        k = auth_even_tbl[n]
    else:
        print("Path: ODD")
        v = v ^ rol8(v)
        print(f"v after XOR rol8: {v:016X}")
        k = auth_odd_tbl[n]

    print(f"k (table value) : {k:016X}")
    rotated_v = rol8(v)
    print(f"rol8(v)         : {rotated_v:016X}")
    masked = rotated_v & mask
    print(f"masked rol8(v)  : {masked:016X}")

    response = v ^ masked ^ k
    print(f"Final response  : {response:016X}")
    return response


def connect_and_authenticate():
    # Vendor/Product ID for the Blackmagic Speed Editor
    VID = 0x1edb
    PID = 0xda0e

    print("Opening HID device...")
    dev = hid.device()
    dev.open(VID, PID)

    # This should match the report size used by bmd.py (usually 64 bytes)
    dev.set_nonblocking(True)

    print("Reading challenge...")
    data = dev.read(64)
    if not data:
        raise RuntimeError("No data received from device")

    # Challenge is usually in the first 8 bytes (little-endian)
    challenge_bytes = data[:8]
    challenge = int.from_bytes(challenge_bytes, "little")
    print(f"Challenge bytes : {challenge_bytes.hex()}")
    print(f"Challenge value : {challenge:016X}")

    # Calculate response
    response_value = calculateKeyboardResponse(challenge)
    response_bytes = response_value.to_bytes(8, "little")

    # Build the response packet (from bmd.py handshake)
    # Usually: [0x02, 0x10, <8-byte response>, zeros...]
    # This may vary, so check your reference script
    packet = bytearray(64)
    packet[0] = 0x02
    packet[1] = 0x10
    packet[2:10] = response_bytes

    print(f"Sending response: {response_bytes.hex()}")
    dev.write(packet)

    print("Authentication sent. Device should now start sending events.")

    dev.close()


if __name__ == "__main__":
    connect_and_authenticate()
