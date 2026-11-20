import bpy
import os
import time
import traceback
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WATCH_FILE = os.path.join(BASE_DIR, "live_command.py")
STATUS_FILE = os.path.join(BASE_DIR, "live_status.json")
PREVIEW_IMG = os.path.join(BASE_DIR, "preview.png")

last_mtime = 0

def check_for_updates():
    global last_mtime
    try:
        if os.path.exists(WATCH_FILE):
            mtime = os.path.getmtime(WATCH_FILE)
            if mtime > last_mtime:
                last_mtime = mtime
                time.sleep(0.05)  # Ensure file is completely written
                with open(WATCH_FILE, "r", encoding="utf-8") as f:
                    code = f.read()

                print(f"[LiveSync] Executing update from {WATCH_FILE}...")
                success = True
                error_msg = ""
                try:
                    ctx_globals = {
                        "bpy": bpy,
                        "__name__": "__main__",
                        "__file__": WATCH_FILE,
                    }
                    exec(code, ctx_globals)

                    # Redraw all 3D Viewports
                    for window in bpy.context.window_manager.windows:
                        for area in window.screen.areas:
                            if area.type == 'VIEW_3D':
                                area.tag_redraw()

                    # Render a quick preview image if a camera exists
                    if bpy.context.scene.camera:
                        bpy.context.scene.render.image_settings.file_format = 'PNG'
                        bpy.context.scene.render.filepath = PREVIEW_IMG
                        bpy.context.scene.render.resolution_x = 960
                        bpy.context.scene.render.resolution_y = 540
                        bpy.context.scene.render.resolution_percentage = 100
                        # Fast rendering using current engine
                        bpy.ops.render.render(write_still=True)
                        print(f"[LiveSync] Rendered live preview to: {PREVIEW_IMG}")

                except Exception:
                    success = False
                    error_msg = traceback.format_exc()
                    print(f"[LiveSync Error]\n{error_msg}")

                status = {
                    "last_run": time.time(),
                    "success": success,
                    "error": error_msg,
                    "preview_image": PREVIEW_IMG if os.path.exists(PREVIEW_IMG) else None
                }
                with open(STATUS_FILE, "w", encoding="utf-8") as f:
                    json.dump(status, f, indent=2)

    except Exception as e:
        print(f"[LiveSync Loop Error]: {e}")

    return 0.1  # Check every 100ms

# Register timer in Blender
if not bpy.app.timers.is_registered(check_for_updates):
    bpy.app.timers.register(check_for_updates)

print("=" * 60)
print("[LiveSync] Blender Live Preview Sync is ACTIVE!")
print(f"[LiveSync] Watching file: {WATCH_FILE}")
print("=" * 60)
