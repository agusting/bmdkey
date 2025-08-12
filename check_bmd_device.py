# File: check_bmd_device.py
import hid

# Blackmagic Design's Vendor ID
BMD_VID = 0x1edb

print("Searching for connected Blackmagic Design HID devices...")

found_device = False
for device_dict in hid.enumerate():
    if device_dict['vendor_id'] == BMD_VID:
        found_device = True
        print(f"\n--- Found Blackmagic Device ---")
        print(f"  Vendor ID:  {hex(device_dict['vendor_id'])}")
        print(f"  Product ID: {hex(device_dict['product_id'])}") # <-- This is the value you need!
        print(f"  Product:    {device_dict['product_string']}")
        print(f"---------------------------------")

if not found_device:
    print("\nNo Blackmagic devices found.")
    print("Please check the following:")
    print("1. Is the Speed Editor plugged in?")
    print("2. Is DaVinci Resolve or other BMD software completely closed?")
else:
    print("\nIf you see your device listed, use its 'Product ID' in the main script.")