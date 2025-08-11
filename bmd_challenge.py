def rol8(value):
    """Rotate 64-bit integer left by 8 bits (1 byte)."""
    return ((value << 8) & 0xFFFFFFFFFFFFFFFF) | (value >> (64 - 8))

def rol8n(value, n):
    """Rotate 64-bit integer left by n bytes (n*8 bits)."""
    shift = (n * 8) % 64
    return ((value << shift) & 0xFFFFFFFFFFFFFFFF) | (value >> (64 - shift))

def calculateKeyboardResponse(challenge):
    # Fixed lookup tables (secrets)
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

    # Step 1: Extract index from lowest 3 bits
    n = challenge & 0b111

    # Step 2: Rotate challenge by n bytes
    v = rol8n(challenge, n)

    # Step 3: Choose table and possibly modify v
    if (v & 1) == ((0x78 >> n) & 1):
        k = auth_even_tbl[n]
    else:
        v = v ^ rol8(v)
        k = auth_odd_tbl[n]

    # Step 4: Mix and return
    return v ^ (rol8(v) & mask) ^ k


# --- Example usage ---
if __name__ == "__main__":
    challenge = 0x123456789ABCDEF0
    response = calculateKeyboardResponse(challenge)
    print(f"Challenge : {challenge:016X}")
    print(f"Response  : {response:016X}")
