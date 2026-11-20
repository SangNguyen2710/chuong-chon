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
        elif f <= 450:
            hud_obj.data.body = (
                "2. Ẩn mái tôn — Mở & đóng cửa nắp chuồng đực\n"
                "Lưu ý: Chiều cao mái tôn (20–40 cm) sẽ ảnh hưởng đến độ mở cửa nắp"
            )
        elif f <= 615:
            hud_obj.data.body = (
                "3. Góc cận — Mở lần lượt 4 cửa thông sang chuồng đực rồi đóng lại\n"
                "Ẩn nắp chuồng đực sau khi đóng để thấy rõ 4 khoang thông nhau"
            )
        else:
            hud_obj.data.body = (
                "4. Mở lần lượt 4 cửa nắp trên chuồng chính rồi đóng lại\n"
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
    scene.frame_end = 792  # 33 seconds at 24 fps

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
        g.keyframe_insert(data_path="location", index=2, frame=453)

    for d in top_doors:
        d.rotation_euler.y = 0.0
        d.keyframe_insert(data_path="rotation_euler", index=1, frame=1)
        d.keyframe_insert(data_path="rotation_euler", index=1, frame=631)

    con_duc_door.rotation_euler.y = 0.0
    con_duc_door.keyframe_insert(data_path="rotation_euler", index=1, frame=1)
    con_duc_door.keyframe_insert(data_path="rotation_euler", index=1, frame=350)

    # --- 2. Phase 1 (Frames 1..340): Hold overview, then slow 360° orbit ---
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

    # --- 3. Phase 2 (Frames 341..450): Hide roof, OPEN & CLOSE Cua_Nap_Con_Duc, then fade it out ---
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

    for lbl_name in ("Label_Mái rộng 280 cm", "Label_Mái dài 230 cm"):
        lbl = bpy.data.objects.get(lbl_name)
        if lbl is not None:
            lbl.hide_render = False
            lbl.keyframe_insert("hide_render", frame=1)
            lbl.keyframe_insert("hide_render", frame=340)
            lbl.hide_render = True
            lbl.keyframe_insert("hide_render", frame=341)

    # Frame male cage cleanly while opening and closing Cua_Nap_Con_Duc
    keyframe_cam_track(cam, cam_target, 360, (-415.0, -320.0, 355.0), (-55.0, 0.0, 96.0))
    keyframe_cam_track(cam, cam_target, 426, (-415.0, -320.0, 355.0), (-55.0, 0.0, 96.0))

    # Open Cua_Nap_Con_Duc (350..378), hold open (378..402), close back down (402..426)
    con_duc_door.rotation_euler.y = math.radians(52.0)
    con_duc_door.keyframe_insert(data_path="rotation_euler", index=1, frame=378)
    con_duc_door.keyframe_insert(data_path="rotation_euler", index=1, frame=402)
    con_duc_door.rotation_euler.y = 0.0
    con_duc_door.keyframe_insert(data_path="rotation_euler", index=1, frame=426)
    con_duc_door.keyframe_insert(data_path="rotation_euler", index=1, frame=792)

    # Only AFTER closing Cua_Nap_Con_Duc, fade it out smoothly (426..450) and hide at 451
    con_duc_fade_mats = make_unique_materials_for_fade(con_duc_door)
    keyframe_materials_alpha(con_duc_fade_mats, 1.0, 1)
    keyframe_materials_alpha(con_duc_fade_mats, 1.0, 426)
    keyframe_materials_alpha(con_duc_fade_mats, 0.0, 450)
    keyframe_materials_alpha(con_duc_fade_mats, 0.0, 610)
    keyframe_materials_alpha(con_duc_fade_mats, 1.0, 628)
    keyframe_materials_alpha(con_duc_fade_mats, 1.0, 792)

    con_duc_door.hide_render = False
    con_duc_door.hide_viewport = False
    con_duc_door.keyframe_insert("hide_render", frame=1)
    con_duc_door.keyframe_insert("hide_viewport", frame=1)
    con_duc_door.keyframe_insert("hide_render", frame=450)
    con_duc_door.keyframe_insert("hide_viewport", frame=450)
    con_duc_door.hide_render = True
    con_duc_door.hide_viewport = True
    con_duc_door.keyframe_insert("hide_render", frame=451)
    con_duc_door.keyframe_insert("hide_viewport", frame=451)
    con_duc_door.keyframe_insert("hide_render", frame=609)
    con_duc_door.keyframe_insert("hide_viewport", frame=609)
    con_duc_door.hide_render = False
    con_duc_door.hide_viewport = False
    con_duc_door.keyframe_insert("hide_render", frame=610)
    con_duc_door.keyframe_insert("hide_viewport", frame=610)

    # --- 4. Phase 3 (Frames 451..615): Close-up — Open all 4 connecting sliding gates, hold, then close ---
    keyframe_cam_track(cam, cam_target, 454, (-310.0, -270.0, 285.0), (-45.0, -40.0, 88.0))
    keyframe_cam_track(cam, cam_target, 540, (-320.0, -170.0, 295.0), (-45.0, 15.0, 90.0))
    keyframe_cam_track(cam, cam_target, 564, (-375.0, -255.0, 320.0), (-45.0, 0.0, 88.0))
    keyframe_cam_track(cam, cam_target, 608, (-375.0, -255.0, 320.0), (-45.0, 0.0, 88.0))

    # Sequential opening (454..534), hold open (..562), then sequential closing (562..604)
    for idx, g in enumerate(slide_gates):
        f_open_s = 454 + idx * 20
        f_open_e = f_open_s + 20
        f_close_s = 562 + idx * 8
        f_close_e = f_close_s + 18

        g.location.z = 0.0
        g.keyframe_insert(data_path="location", index=2, frame=f_open_s)
        g.location.z = 58.0
        g.keyframe_insert(data_path="location", index=2, frame=f_open_e)
        g.keyframe_insert(data_path="location", index=2, frame=f_close_s)
        g.location.z = 0.0
        g.keyframe_insert(data_path="location", index=2, frame=f_close_e)
        g.keyframe_insert(data_path="location", index=2, frame=792)

    # --- 5. Phase 4 (Frames 616..792): Pull back, restore closed Cua_Nap_Con_Duc, open & close 4 top hatch doors ---
    keyframe_cam_track(cam, cam_target, 632, (-505.0, -385.0, 410.0), (-20.0, 0.0, 118.0))
    keyframe_cam_track(cam, cam_target, 792, (-505.0, -385.0, 410.0), (-20.0, 0.0, 118.0))

    for idx, d in enumerate(top_doors):
        f_open_s = 632 + idx * 18
        f_open_e = f_open_s + 20
        f_close_s = 732 + idx * 8
        f_close_e = f_close_s + 20

        d.rotation_euler.y = 0.0
        d.keyframe_insert(data_path="rotation_euler", index=1, frame=f_open_s)
        d.rotation_euler.y = math.radians(42.0)
        d.keyframe_insert(data_path="rotation_euler", index=1, frame=f_open_e)
        d.keyframe_insert(data_path="rotation_euler", index=1, frame=f_close_s)
        d.rotation_euler.y = 0.0
        d.keyframe_insert(data_path="rotation_euler", index=1, frame=f_close_e)
        d.keyframe_insert(data_path="rotation_euler", index=1, frame=792)

    for obj in [cam, cam_target, con_duc_door] + slide_gates + top_doors:
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
    print(f"[Showcase] Rendering 792-frame (33s) MP4 video to: {OUTPUT_VIDEO}")
    bpy.ops.render.render(animation=True)
    print(f"[Showcase] Finished rendering video: {OUTPUT_VIDEO}")
