#!/usr/bin/env python3
"""
ZKTeco Device Diagnostic Tool
Helps troubleshoot connection issues with ZKTeco devices
"""

import socket
import sys
from zk import ZK

def check_port(ip, port, timeout=5):
    """Check if a TCP port is open"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip, port))
        sock.close()
        return result == 0
    except Exception as e:
        return False

def diagnose_device(ip, port=4370):
    """Run diagnostics on a ZKTeco device"""
    print(f"\n{'='*60}")
    print(f"  ZKTeco Device Diagnostics")
    print(f"  Target: {ip}:{port}")
    print(f"{'='*60}\n")

    # Step 1: Check if port is open
    print(f"[1/4] Checking if port {port} is open...")
    if check_port(ip, port):
        print(f"      ✓ Port {port} is OPEN")
    else:
        print(f"      ✗ Port {port} is CLOSED or filtered")
        print(f"\n      Possible causes:")
        print(f"      - Device firewall is blocking the port")
        print(f"      - Device is configured on a different port")
        print(f"      - Network firewall between you and the device")
        print(f"\n      Try these ports: 4370, 80, 8080")

        # Check alternative ports
        alt_ports = [80, 8080, 5005]
        for alt_port in alt_ports:
            if check_port(ip, alt_port, timeout=2):
                print(f"      → Port {alt_port} is open (device might use this port)")
        return False

    # Step 2: Try different timeouts
    print(f"\n[2/4] Testing connection with different timeouts...")

    for timeout in [5, 10, 20, 30]:
        print(f"      Trying timeout={timeout}s...", end=" ", flush=True)
        try:
            zk = ZK(ip, port=port, timeout=timeout)
            conn = zk.connect()
            if conn:
                print(f"✓ SUCCESS!")

                # Step 3: Get device info
                print(f"\n[3/4] Getting device information...")
                try:
                    device_name = conn.get_device_name() or "Unknown"
                    serial = conn.get_serialnumber() or "Unknown"
                    firmware = conn.get_firmware_version() or "Unknown"
                    platform = conn.get_platform() or "Unknown"

                    print(f"      Device Name: {device_name}")
                    print(f"      Serial: {serial}")
                    print(f"      Firmware: {firmware}")
                    print(f"      Platform: {platform}")
                except Exception as e:
                    print(f"      Warning: Could not get device info: {e}")

                # Step 4: Try to get users
                print(f"\n[4/4] Testing data retrieval...")
                try:
                    users = conn.get_users()
                    print(f"      Users: {len(users)} registered")

                    attendance = conn.get_attendance()
                    print(f"      Attendance logs: {len(attendance)} records")
                except Exception as e:
                    print(f"      Warning: Could not get data: {e}")

                conn.disconnect()
                print(f"\n{'='*60}")
                print(f"  DIAGNOSIS: Device is working correctly!")
                print(f"  Recommended timeout: {timeout} seconds")
                print(f"{'='*60}\n")
                return True
            else:
                print("✗ No connection")
        except Exception as e:
            error_msg = str(e)
            if "timed out" in error_msg.lower():
                print(f"✗ Timeout")
            elif "refused" in error_msg.lower():
                print(f"✗ Connection refused")
            else:
                print(f"✗ {error_msg[:50]}")

    print(f"\n{'='*60}")
    print(f"  DIAGNOSIS: Could not connect to device")
    print(f"{'='*60}")
    print(f"\nPossible solutions:")
    print(f"  1. Check if device is powered on and connected to network")
    print(f"  2. Check device's network settings (IP, subnet, gateway)")
    print(f"  3. Try restarting the device")
    print(f"  4. Check if another software is connected to the device")
    print(f"  5. Verify device allows connections (check device menu)")
    print(f"  6. Some devices need 'COMM' settings enabled in menu")
    print()
    return False


def compare_devices(ip1, ip2, port=4370):
    """Compare two devices to find configuration differences"""
    print(f"\n{'='*60}")
    print(f"  Comparing Devices")
    print(f"  Device 1: {ip1}:{port}")
    print(f"  Device 2: {ip2}:{port}")
    print(f"{'='*60}\n")

    results = {}

    for name, ip in [("Device 1", ip1), ("Device 2", ip2)]:
        print(f"\n--- {name} ({ip}) ---")
        results[name] = {'ip': ip}

        # Port check
        port_open = check_port(ip, port)
        results[name]['port_open'] = port_open
        print(f"Port {port}: {'OPEN' if port_open else 'CLOSED'}")

        if not port_open:
            continue

        # Connection test
        for timeout in [10, 20, 30]:
            try:
                zk = ZK(ip, port=port, timeout=timeout)
                conn = zk.connect()
                if conn:
                    results[name]['connected'] = True
                    results[name]['timeout_needed'] = timeout
                    results[name]['device_name'] = conn.get_device_name()
                    results[name]['serial'] = conn.get_serialnumber()
                    results[name]['firmware'] = conn.get_firmware_version()
                    conn.disconnect()
                    print(f"Connected: YES (timeout={timeout}s)")
                    print(f"Device: {results[name]['device_name']}")
                    print(f"Serial: {results[name]['serial']}")
                    print(f"Firmware: {results[name]['firmware']}")
                    break
            except:
                pass
        else:
            results[name]['connected'] = False
            print(f"Connected: NO (tried timeouts up to 30s)")

    # Analysis
    print(f"\n{'='*60}")
    print(f"  Analysis")
    print(f"{'='*60}")

    if results.get("Device 1", {}).get('connected') and not results.get("Device 2", {}).get('connected'):
        print(f"\nDevice 2 ({ip2}) has issues:")
        if not results.get("Device 2", {}).get('port_open'):
            print(f"  - Port 4370 is closed. Check device COMM settings.")
        else:
            print(f"  - Port is open but connection fails.")
            print(f"  - Try increasing timeout in the app settings.")
            print(f"  - Device may need restart or COMM password reset.")

    return results


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python diagnose_device.py <ip>              Diagnose single device")
        print("  python diagnose_device.py <ip1> <ip2>       Compare two devices")
        print()
        print("Examples:")
        print("  python diagnose_device.py 192.168.1.44")
        print("  python diagnose_device.py 192.168.1.43 192.168.1.44")
        sys.exit(1)

    if len(sys.argv) == 2:
        ip = sys.argv[1]
        diagnose_device(ip)
    elif len(sys.argv) >= 3:
        ip1 = sys.argv[1]
        ip2 = sys.argv[2]
        compare_devices(ip1, ip2)
