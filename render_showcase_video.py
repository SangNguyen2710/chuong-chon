import bpy
import math
import mathutils
import os

OUTPUT_VIDEO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gioi_thieu_chuong_fence.mp4")

def keyframe_cam_track(cam, target_empty, frame, cam_pos, target_pos):
    cam.location = cam_pos
    cam.keyframe_insert(data_path="location", frame=frame)
    target_empty.location = target_pos
    target_empty.keyframe_insert(data_path="location", frame=frame)

def set_smooth_beziers(obj):
    if obj.animation_data and obj.animation_data.action:
        action = obj.animation_data.action
        fcurves = getattr(action, "fcurves", None)
        if fcurves is None and hasattr(action, "layers"):
            for layer in action.layers:
                for strip in getattr(layer, "strips", []):
                    for bag in getattr(strip, "channelbags", []):
                        for fc in getattr(bag, "fcurves", []):
                            for kp in fc.keyframe_points:
                                kp.interpolation = 'BEZIER'
        elif fcurves:
            for fc in fcurves:
                for kp in fc.keyframe_points:
                    kp.interpolation = 'BEZIER'

def make_unique_materials_for_fade(obj):
    """Clone materials on an object so its Alpha can fade out independently without affecting others."""
    unique_mats = []
    for idx, mat in enumerate(obj.data.materials):
        if mat is not None:
            m_copy = mat.copy()
            m_copy.name = f"{obj.name}_FadeMat_{idx}"
            obj.data.materials[idx] = m_copy
            unique_mats.append(m_copy)
    return unique_mats

def keyframe_materials_alpha(mats, alpha_val, frame):
    for m in mats:
        bsdf = m.node_tree.nodes.get("Principled BSDF") if m.node_tree else None
        if bsdf and "Alpha" in bsdf.inputs:
            inp = bsdf.inputs["Alpha"]
            inp.default_value = alpha_val
            inp.keyframe_insert("default_value", frame=frame)

def create_hud_overlay(cam):
    """Create a crisp Vietnamese HUD title/note attached to the top of the camera view."""
    vn_font = None
    for font_path in (r"C:\Windows\Fonts\arialbd.ttf", r"C:\Windows\Fonts\segoeuib.ttf", r"C:\Windows\Fonts\arial.ttf"):
        try:
            vn_font = bpy.data.fonts.load(font_path, check_existing=True)
            break
        except Exception:
            pass

    mat_hud_text = bpy.data.materials.new("HUD_Text_Mat")
    mat_hud_text.use_nodes = True
    bsdf = mat_hud_text.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (1.0, 0.94, 0.25, 1.0)
        if "Emission Color" in bsdf.inputs:
            bsdf.inputs["Emission Color"].default_value = (1.0, 0.94, 0.25, 1.0)
            bsdf.inputs["Emission Strength"].default_value = 2.0

    mat_hud_bg = bpy.data.materials.new("HUD_Bg_Mat")
    mat_hud_bg.use_nodes = True
    bsdf_bg = mat_hud_bg.node_tree.nodes.get("Principled BSDF")
    if bsdf_bg:
        bsdf_bg.inputs["Base Color"].default_value = (0.04, 0.06, 0.09, 1.0)
        bsdf_bg.inputs["Roughness"].default_value = 1.0
        if "Alpha" in bsdf_bg.inputs:
            bsdf_bg.inputs["Alpha"].default_value = 0.72

    bpy.ops.mesh.primitive_plane_add(size=1.0)
    bg_obj = bpy.context.active_object
    bg_obj.name = "HUD_Backdrop"
    bg_obj.parent = cam
    bg_obj.location = (0.0, 1.76, -10.0)
    bg_obj.scale = (7.3, 0.50, 1.0)
    bg_obj.visible_shadow = False
    bg_obj.data.materials.append(mat_hud_bg)

    f_data = bpy.data.curves.new(type="FONT", name="HUD_Banner_Curve")
    f_data.body = "1. Toàn cảnh 360° & Số liệu kích thước (Tất cả cửa đóng hoàn toàn)"
    if vn_font is not None:
        f_data.font = vn_font
    f_data.align_x = 'CENTER'
    f_data.align_y = 'CENTER'
    f_data.size = 0.160
    f_data.space_line = 1.25
    f_data.extrude = 0.004

    hud_obj = bpy.data.objects.new("HUD_Banner", f_data)
    bpy.context.scene.collection.objects.link(hud_obj)
    hud_obj.parent = cam
    hud_obj.location = (0.0, 1.76, -9.9)
    hud_obj.visible_shadow = False
    hud_obj.data.materials.append(mat_hud_text)

    return hud_obj

def register_hud_handler(hud_obj):
    def update_hud_per_frame(scene, depsgraph=None):
        f = scene.frame_current
        if f <= 340:
            hud_obj.data.body = "1. Toàn cảnh 360° & Số liệu kích thước (Tất cả cửa đóng hoàn toàn)"
        elif f <= 480:
            hud_obj.data.body = (
                "2. Ẩn mái tôn & mờ dần nắp khối trước — Mở lần lượt cửa thông giữa 2 khối\n"
                "Lưu ý: Chiều cao mái tôn (20–40 cm) sẽ ảnh hưởng đến độ mở cửa nắp trên"
            )
        else:
            hud_obj.data.body = (
                "3. Mở lần lượt cửa nắp trên của 4 chuồng chính\n"
                "Lưu ý: Chiều cao mái tôn (20–40 cm) sẽ ảnh hưởng đến độ mở cửa nắp trên"
            )

    bpy.app.handlers.frame_change_pre[:] = [
        h for h in bpy.app.handlers.frame_change_pre if getattr(h, "__name__", "") != "update_hud_per_frame"
    ]
    bpy.app.handlers.frame_change_pre.append(update_hud_per_frame)
    update_hud_per_frame(bpy.context.scene)

def setup_showcase_animation():
    scene = bpy.context.scene
    scene.render.fps = 24
    scene.frame_start = 1
    scene.frame_end = 600  # 25 seconds at 24 fps

    cam = scene.camera
    cam_target = bpy.data.objects.new("Cam_Target", None)
    bpy.context.scene.collection.objects.link(cam_target)
    cam_target.location = (-35.0, 0.0, 68.0)

    track = cam.constraints.new(type='TRACK_TO')
    track.target = cam_target
    track.track_axis = 'TRACK_NEGATIVE_Z'
    track.up_axis = 'UP_Y'

    # Keep all 3D Vietnamese dimension labels facing the camera smoothly
    for obj in bpy.data.objects:
        if obj.name.startswith("Label_") and obj.type == 'FONT':
            lbl_track = obj.constraints.new(type='TRACK_TO')
            lbl_track.target = cam
            lbl_track.track_axis = 'TRACK_Z'
            lbl_track.up_axis = 'UP_Y'

    hud_obj = create_hud_overlay(cam)
    register_hud_handler(hud_obj)

    slide_gates = [bpy.data.objects[f"Cua_Luoi_Truot_Truc_Z_{i}"] for i in range(1, 5)]
    top_doors = [bpy.data.objects[f"Cua_Nap_Fence_{i}"] for i in range(1, 5)]
    con_duc_door = bpy.data.objects["Cua_Nap_Con_Duc"]
    roof_obj = bpy.data.objects["Mai_Ton"]

    # --- 1. Initialize ALL doors to COMPLETELY CLOSED at Frame 1 ---
    for g in slide_gates:
        g.location.z = 0.0
        g.keyframe_insert(data_path="location", index=2, frame=1)
        g.keyframe_insert(data_path="location", index=2, frame=372)

    for d in top_doors:
        d.rotation_euler.y = 0.0
        d.keyframe_insert(data_path="rotation_euler", index=1, frame=1)
        d.keyframe_insert(data_path="rotation_euler", index=1, frame=482)

    con_duc_door.rotation_euler.y = 0.0
    con_duc_door.keyframe_insert(data_path="rotation_euler", index=1, frame=1)

    # --- 2. Phase 1 (Frames 1..340): Hold overview, then 360° orbit slowed down by half (~12.6s) ---
    center_x, center_y = -35.0, 0.0
    orbit_radius = 740.0
    orbit_z = 405.0
    start_angle = math.atan2(-495.0 - center_y, -565.0 - center_x)

    init_pos = (
        center_x + orbit_radius * math.cos(start_angle),
        center_y + orbit_radius * math.sin(start_angle),
        orbit_z,
    )
    keyframe_cam_track(cam, cam_target, 1, init_pos, (center_x, center_y, 68.0))
    keyframe_cam_track(cam, cam_target, 36, init_pos, (center_x, center_y, 68.0))

    # 360-degree circular orbit across frames 37..340 (304 frames = 12.67s, half the previous speed)
    orbit_steps = 24
    for i in range(1, orbit_steps + 1):
        u = i / orbit_steps
        smooth_u = 0.5 - 0.5 * math.cos(math.pi * u)
        frame = int(round(36 + u * (340 - 36)))
        ang = start_angle + smooth_u * 2.0 * math.pi
        pos = (
            center_x + orbit_radius * math.cos(ang),
            center_y + orbit_radius * math.sin(ang),
            orbit_z,
        )
        keyframe_cam_track(cam, cam_target, frame, pos, (center_x, center_y, 68.0))

    # --- 3. Phase 2 (Frames 341..480): Hide roof, gradually fade out Cua_Nap_Con_Duc, zoom in close & open connecting gates ---
    roof_obj.hide_render = False
    roof_obj.hide_viewport = False
    roof_obj.keyframe_insert("hide_render", frame=1)
    roof_obj.keyframe_insert("hide_viewport", frame=1)
    roof_obj.keyframe_insert("hide_render", frame=340)
    roof_obj.keyframe_insert("hide_viewport", frame=340)

    roof_obj.hide_render = True
    roof_obj.hide_viewport = True
    roof_obj.keyframe_insert("hide_render", frame=341)
    roof_obj.keyframe_insert("hide_viewport", frame=341)

    # Hide roof dimension labels while Mai_Ton is hidden so they don't block the close-up
    for lbl_name in ("Label_Mái rộng 280 cm", "Label_Mái dài 230 cm"):
        lbl = bpy.data.objects.get(lbl_name)
        if lbl is not None:
            lbl.hide_render = False
            lbl.keyframe_insert("hide_render", frame=1)
            lbl.keyframe_insert("hide_render", frame=340)
            lbl.hide_render = True
            lbl.keyframe_insert("hide_render", frame=341)

    # Fade Cua_Nap_Con_Duc out smoothly from frame 342 -> 372, then hide completely
    con_duc_fade_mats = make_unique_materials_for_fade(con_duc_door)
    keyframe_materials_alpha(con_duc_fade_mats, 1.0, 1)
    keyframe_materials_alpha(con_duc_fade_mats, 1.0, 342)
    keyframe_materials_alpha(con_duc_fade_mats, 0.0, 372)

    con_duc_door.hide_render = False
    con_duc_door.hide_viewport = False
    con_duc_door.keyframe_insert("hide_render", frame=1)
    con_duc_door.keyframe_insert("hide_viewport", frame=1)
    con_duc_door.keyframe_insert("hide_render", frame=372)
    con_duc_door.keyframe_insert("hide_viewport", frame=372)
    con_duc_door.hide_render = True
    con_duc_door.hide_viewport = True
    con_duc_door.keyframe_insert("hide_render", frame=373)
    con_duc_door.keyframe_insert("hide_viewport", frame=373)

    # Zoom camera IN CLOSE to look straight down into khoi_khung_luoi_con_duc and the 4 connecting gates
    # Sweeps smoothly from the -Y end (Cage 1) across to Cage 4 so every open passage is clearly visible
    keyframe_cam_track(cam, cam_target, 370, (-290.0, -255.0, 265.0), (-45.0, -45.0, 80.0))
    keyframe_cam_track(cam, cam_target, 476, (-295.0, -140.0, 275.0), (-45.0, 20.0, 80.0))

    # Sequential full opening of the 4 connecting sliding gates (0 -> 58 cm)
    for idx, g in enumerate(slide_gates):
        f_s = 376 + idx * 24
        f_e = f_s + 22
        g.location.z = 0.0
        g.keyframe_insert(data_path="location", index=2, frame=f_s)
        g.location.z = 58.0
        g.keyframe_insert(data_path="location", index=2, frame=f_e)
        g.keyframe_insert(data_path="location", index=2, frame=600)

    # --- 4. Phase 3 (Frames 481..600): Pull back slightly & open the 4 cage top hatch doors sequentially ---
    keyframe_cam_track(cam, cam_target, 502, (-425.0, -325.0, 365.0), (-25.0, 0.0, 88.0))
    keyframe_cam_track(cam, cam_target, 600, (-425.0, -325.0, 365.0), (-25.0, 0.0, 88.0))

    for idx, d in enumerate(top_doors):
        f_s = 486 + idx * 22
        f_e = f_s + 22
        d.rotation_euler.y = 0.0
        d.keyframe_insert(data_path="rotation_euler", index=1, frame=f_s)
        d.rotation_euler.y = math.radians(42.0)
        d.keyframe_insert(data_path="rotation_euler", index=1, frame=f_e)
        d.keyframe_insert(data_path="rotation_euler", index=1, frame=600)

    for obj in [cam, cam_target] + slide_gates + top_doors:
        set_smooth_beziers(obj)

    # Configure MP4 H.264 output
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.media_type = 'VIDEO'
    scene.render.ffmpeg.format = 'MPEG4'
    scene.render.ffmpeg.codec = 'H264'
    scene.render.ffmpeg.constant_rate_factor = 'HIGH'
    scene.render.filepath = OUTPUT_VIDEO

if __name__ == "__main__":
    setup_showcase_animation()
    print(f"[Showcase] Rendering 600-frame (25s) MP4 video to: {OUTPUT_VIDEO}")
    bpy.ops.render.render(animation=True)
    print(f"[Showcase] Finished rendering video: {OUTPUT_VIDEO}")
