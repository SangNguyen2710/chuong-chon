import socket
import sys
import json
import os

HOST = '127.0.0.1'
PORT = 9876

def send_to_blender(code_str, timeout=20.0):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((HOST, PORT))
        payload = code_str.encode('utf-8') + b"\n<<<END>>>\n"
        s.sendall(payload)

        received_chunks = []
        while True:
            data = s.recv(4096)
            if not data:
                break
            received_chunks.append(data)
            if b"\n<<<END>>>\n" in data:
                break
        s.close()

        raw = b"".join(received_chunks).replace(b"\n<<<END>>>\n", b"").decode('utf-8')
        return json.loads(raw)
    except ConnectionRefusedError:
        return {
            "success": False,
            "error": "ConnectionRefused: Blender Live Bridge is not running or not listening on port 9876. Please start Blender with live_bridge.py."
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Error communicating with Blender: {e}"
        }

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python send_command.py <file.py | \"inline python code\">")
        sys.exit(1)

    arg = sys.argv[1]
    if os.path.exists(arg):
        with open(arg, 'r', encoding='utf-8') as f:
            code = f.read()
    else:
        code = arg

    res = send_to_blender(code)
    print(json.dumps(res, indent=2, ensure_ascii=False))
