import bpy
import socket
import threading
import queue
import io
import sys
import traceback
import json

HOST = '127.0.0.1'
PORT = 9876

# Thread-safe queue for commands to be executed on Blender's main thread
task_queue = queue.Queue()

def main_thread_timer():
    try:
        while not task_queue.empty():
            client_sock, code_str = task_queue.get_nowait()
            old_stdout = sys.stdout
            redirected_output = io.StringIO()
            sys.stdout = redirected_output
            success = True
            err_msg = ""
            try:
                exec_globals = {
                    "bpy": bpy,
                    "__name__": "__main__",
                }
                exec(code_str, exec_globals)
                
                # Tag all 3D Viewport areas to redraw immediately
                for window in bpy.context.window_manager.windows:
                    for area in window.screen.areas:
                        if area.type == 'VIEW_3D':
                            area.tag_redraw()
            except Exception:
                success = False
                err_msg = traceback.format_exc()
            finally:
                sys.stdout = old_stdout

            output_text = redirected_output.getvalue()
            response = {
                "success": success,
                "output": output_text,
                "error": err_msg
            }
            try:
                msg = json.dumps(response).encode('utf-8') + b"\n<<<END>>>\n"
                client_sock.sendall(msg)
                client_sock.close()
            except Exception as e:
                print(f"[LiveBridge] Error sending response: {e}")
    except Exception as e:
        print(f"[LiveBridge] Timer loop error: {e}")
    return 0.05  # Check queue every 50ms

def socket_server_thread():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server.bind((HOST, PORT))
        server.listen(5)
        print(f"[LiveBridge] Server running on {HOST}:{PORT}")
    except Exception as e:
        print(f"[LiveBridge] Error binding port {PORT}: {e}")
        return

    while True:
        try:
            client, _ = server.accept()
            chunks = []
            while True:
                data = client.recv(4096)
                if not data:
                    break
                chunks.append(data)
                if b"\n<<<END>>>\n" in data:
                    break
            full_data = b"".join(chunks)
            code_str = full_data.replace(b"\n<<<END>>>\n", b"").decode('utf-8')
            task_queue.put((client, code_str))
        except Exception as e:
            print(f"[LiveBridge] Accept loop error: {e}")
            break

# Ensure timer is registered
if not bpy.app.timers.is_registered(main_thread_timer):
    bpy.app.timers.register(main_thread_timer)

# Start background socket server
t = threading.Thread(target=socket_server_thread, daemon=True)
t.start()

print("==================================================")
print(f"[LiveBridge] Blender Live Bridge is ACTIVE on {HOST}:{PORT}")
print("==================================================")
