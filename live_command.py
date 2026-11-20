import bpy
import bmesh
import math
import mathutils

def clear_scene():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for col_name in ("Cua_Nap_Mo_NegY_Sang_Y", "Cua_Nap_Mo_Y_Sang_NegY"):
        col = bpy.data.collections.get(col_name)
        if col is not None:
            bpy.data.collections.remove(col)
    for block in bpy.data.meshes:
        if block.users == 0:
            bpy.data.meshes.remove(block)
    for block in bpy.data.materials:
        if block.users == 0:
            bpy.data.materials.remove(block)

def default_collection():
    return bpy.data.collections.get("Collection") or bpy.context.scene.collection

def create_material(name, color, metallic=0.8, roughness=0.35):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Roughness"].default_value = roughness
    return mat

def add_box(bm, x0, x1, y0, y1, z0, z1):
    cx = (x0 + x1) / 2.0
    cy = (y0 + y1) / 2.0
    cz = (z0 + z1) / 2.0
    sx = abs(x1 - x0)
    sy = abs(y1 - y0)
    sz = abs(z1 - z0)
    mat_trans = (
        mathutils.Matrix.Translation((cx, cy, cz)) @
        mathutils.Matrix.Diagonal((sx, sy, sz, 1.0))
    )
    bmesh.ops.create_cube(bm, size=1.0, matrix=mat_trans)

def build_main_frame_with_tracks(name, size_x, size_y, size_z, bar_thick, mat_frame, mat_rail, mat_handle):
    """
    Build the hollow structural frame (Khung sườn rỗng) with exact outer dimensions:
    X = 130, Y = 60, Z = 60.
    The -X end features vertical U-channel guide rails and an offset top bracing beam
    so the -X gate can slide freely up and down along Z.
    """
    mesh = bpy.data.meshes.new(name + "_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    default_collection().objects.link(obj)
    obj.data.materials.append(mat_frame)   # 0
    obj.data.materials.append(mat_rail)    # 1
    obj.data.materials.append(mat_handle)  # 2

    bm = bmesh.new()
    half_x = size_x / 2.0
    half_y = size_y / 2.0
    t = bar_thick

    # 4 longitudinal beams along X (top & bottom, front & back)
    for y_sign in (-1, 1):
        y0 = y_sign * half_y - (t if y_sign > 0 else 0.0)
        y1 = y_sign * half_y + (0.0 if y_sign > 0 else t)
        add_box(bm, -half_x, half_x, y0, y1, 0.0, t)
        add_box(bm, -half_x, half_x, y0, y1, size_z - t, size_z)

    # 4 vertical corner posts along Z
    for x_sign in (-1, 1):
        x0 = x_sign * half_x - (t if x_sign > 0 else 0.0)
        x1 = x_sign * half_x + (0.0 if x_sign > 0 else t)
        for y_sign in (-1, 1):
            y0 = y_sign * half_y - (t if y_sign > 0 else 0.0)
            y1 = y_sign * half_y + (0.0 if y_sign > 0 else t)
            add_box(bm, x0, x1, y0, y1, t, size_z - t)

    # +X end transverse Y beams (fixed end)
    add_box(bm, half_x - t, half_x, -half_y + t, half_y - t, 0.0, t)
    add_box(bm, half_x - t, half_x, -half_y + t, half_y - t, size_z - t, size_z)

    # -X end bottom threshold sill & recessed top bracing beam (leaves vertical slot at X = [-64.8, -63.2])
    add_box(bm, -half_x, -half_x + t, -half_y + t, half_y - t, 0.0, 0.8)
    # Top bracing beam offset slightly inward along +X so gate slides cleanly up past Z=60
    brace_x0, brace_x1 = -half_x + t + 0.5, -half_x + 2 * t + 0.5
    add_box(bm, brace_x0, brace_x1, -half_y + t, half_y - t, size_z - t, size_z)

    # Hinge bases (+X top beam) & Latch catch loops (-X recessed bracing beam) for top hatch door
    accent_start = len(bm.faces)
    for y_hinge in (-18.0, 18.0):
        add_box(bm, half_x - t, half_x, y_hinge - 2.5, y_hinge + 2.5, size_z - 1.2, size_z)
    for y_latch in (-16.0, 16.0):
        add_box(bm, brace_x0 - 1.0, brace_x0, y_latch - 2.0, y_latch + 2.0, size_z - 2.0, size_z - 0.2)

    bm.faces.ensure_lookup_table()
    for i in range(accent_start, len(bm.faces)):
        bm.faces[i].material_index = 2

    bm.to_mesh(mesh)
    bm.free()

    # Add inner guide rail lips (C-channel tracks) along -X vertical posts (material index 1)
    bm_rail = bmesh.new()
    bm_rail.from_mesh(mesh)
    track_x_front_0, track_x_front_1 = -half_x, -half_x + 0.4
    track_x_back_0, track_x_back_1 = -half_x + 1.6, -half_x + 2.0

    start_face_count = len(bm_rail.faces)
    for y_sign in (-1, 1):
        # Lip extending 1.0 inward along Y to hold the sliding gate in place
        if y_sign < 0:
            y0, y1 = -half_y + t, -half_y + t + 1.0
        else:
            y0, y1 = half_y - t - 1.0, half_y - t
        add_box(bm_rail, track_x_front_0, track_x_front_1, y0, y1, 0.8, size_z)
        add_box(bm_rail, track_x_back_0, track_x_back_1, y0, y1, 0.8, size_z)

    bm_rail.faces.ensure_lookup_table()
    for i in range(start_face_count, len(bm_rail.faces)):
        bm_rail.faces[i].material_index = 1

    bm_rail.to_mesh(mesh)
    bm_rail.free()

    return obj

def create_fence_panel(name, width, height, cell_size, wire_thick, location, rotation, mat, diamond=True):
    nx = max(2, int(round(width / cell_size)))
    ny = max(2, int(round(height / cell_size)))

    mesh = bpy.data.meshes.new(name + "_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    default_collection().objects.link(obj)
    obj.location = location
    obj.rotation_euler = rotation
    obj.data.materials.append(mat)

    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=nx, y_segments=ny, size=1.0)
    for v in bm.verts:
        v.co.x *= (width / 2.0)
        v.co.y *= (height / 2.0)

    bm.to_mesh(mesh)
    bm.free()

    if diamond:
        dec = obj.modifiers.new(name="DiamondPattern", type='DECIMATE')
        dec.decimate_type = 'UNSUBDIV'
        dec.iterations = 1

    wf = obj.modifiers.new(name="FenceWire", type='WIREFRAME')
    wf.thickness = wire_thick
    wf.use_replace = True
    wf.use_boundary = True
    wf.use_even_offset = True

    return obj

def build_sliding_gate(name, size_y, size_z, bar_thick, cell_size, wire_thick, mat_gate_frame, mat_fence, mat_handle):
    """
    Build the movable -X vertical sliding gate (Cua_Luoi_Truot_Truc_Z) at X = -64.0
    Width along Y fits inside the guide channels; height along Z is 59.2 (from 0.8 to 60.0 when closed).
    """
    gate_x_center = -64.0
    gate_thick_x = 1.0
    half_gx = gate_thick_x / 2.0

    # Gate fits into guide tracks (Y from -28.6 to +28.6 -> width 57.2)
    gy_half = (size_y / 2.0) - bar_thick + 0.6
    gz_min = 0.8
    gz_max = size_z
    frame_w = 1.6

    mesh = bpy.data.meshes.new(name + "_Mesh")
    gate_obj = bpy.data.objects.new(name, mesh)
    default_collection().objects.link(gate_obj)
    gate_obj.data.materials.append(mat_gate_frame)  # 0
    gate_obj.data.materials.append(mat_handle)      # 1

    bm = bmesh.new()
    # Left & Right stiles
    add_box(bm, gate_x_center - half_gx, gate_x_center + half_gx, -gy_half, -gy_half + frame_w, gz_min, gz_max)
    add_box(bm, gate_x_center - half_gx, gate_x_center + half_gx, gy_half - frame_w, gy_half, gz_min, gz_max)
    # Bottom & Top rails of gate
    add_box(bm, gate_x_center - half_gx, gate_x_center + half_gx, -gy_half + frame_w, gy_half - frame_w, gz_min, gz_min + frame_w)
    add_box(bm, gate_x_center - half_gx, gate_x_center + half_gx, -gy_half + frame_w, gy_half - frame_w, gz_max - frame_w, gz_max)

    # Top U-shaped Pull Handle on the top edge (pointing upward along +Z)
    handle_start = len(bm.faces)
    handle_w_half = 8.0
    handle_leg_t = 1.4
    handle_h = 5.0
    # Two vertical legs rising along +Z from top rail (gz_max)
    add_box(bm, gate_x_center - half_gx, gate_x_center + half_gx, -handle_w_half, -handle_w_half + handle_leg_t, gz_max, gz_max + handle_h)
    add_box(bm, gate_x_center - half_gx, gate_x_center + half_gx, handle_w_half - handle_leg_t, handle_w_half, gz_max, gz_max + handle_h)
    # Horizontal top grip bar connecting the two legs
    add_box(bm, gate_x_center - half_gx - 0.2, gate_x_center + half_gx + 0.2, -handle_w_half, handle_w_half, gz_max + handle_h, gz_max + handle_h + handle_leg_t)

    bm.faces.ensure_lookup_table()
    for i in range(handle_start, len(bm.faces)):
        bm.faces[i].material_index = 1

    bm.to_mesh(mesh)
    bm.free()

    # Create fence infill panel inside the gate frame
    in_w = 2.0 * (gy_half - frame_w)
    in_h = (gz_max - gz_min) - 2.0 * frame_w
    center_z = (gz_min + gz_max) / 2.0
    gate_fence = create_fence_panel(
        name + "_Fence",
        in_w,
        in_h,
        cell_size,
        wire_thick,
        (gate_x_center, 0.0, center_z),
        (math.radians(90), 0.0, math.radians(90)),
        mat_fence
    )

    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = gate_fence
    for mod in list(gate_fence.modifiers):
        bpy.ops.object.modifier_apply(modifier=mod.name)

    # Join gate frame and gate fence into 1 sliding gate object
    bpy.ops.object.select_all(action='DESELECT')
    gate_obj.select_set(True)
    gate_fence.select_set(True)
    bpy.context.view_layer.objects.active = gate_obj
    bpy.ops.object.join()

    # Restrict movement strictly to vertical Z sliding (pull up / pull down)
    gate_obj.lock_location = (True, True, False)
    gate_obj.lock_rotation = (True, True, True)

    limit = gate_obj.constraints.new(type='LIMIT_LOCATION')
    limit.name = "Slide_Z_Limit"
    limit.use_min_x = limit.use_max_x = True
    limit.min_x = limit.max_x = 0.0
    limit.use_min_y = limit.use_max_y = True
    limit.min_y = limit.max_y = 0.0
    limit.use_min_z = True
    limit.min_z = 0.0
    limit.use_max_z = True
    limit.max_z = 58.0
    limit.owner_space = 'LOCAL'
    limit.use_transform_limit = True

    return gate_obj

def apply_and_join(base_obj, part_objs, final_name):
    """Apply all modifiers on part_objs and join them into base_obj."""
    bpy.ops.object.select_all(action='DESELECT')
    for p in part_objs:
        bpy.context.view_layer.objects.active = p
        for mod in list(p.modifiers):
            bpy.ops.object.modifier_apply(modifier=mod.name)

    bpy.ops.object.select_all(action='DESELECT')
    base_obj.select_set(True)
    for p in part_objs:
        p.select_set(True)
    bpy.context.view_layer.objects.active = base_obj
    bpy.ops.object.join()
    base_obj.name = final_name
    return base_obj

def create_hinged_hatch_door(
    name, parent_obj, pivot_local, span_x, span_y, cell_size, wire_thick,
    rib_xs, rib_ys, latch_offsets, open_deg, mat_gate_frame, mat_fence, mat_handle,
    hinge_side='+X', target_collection=None
):
    """
    Create a hinged top mesh door (with latches + top U-handle) that opens upward (+Z)
    and closes downward (-Z). Supports hinge_side in ('+X', '+Y', '-Y').
    """
    dfw = 1.6
    dtz = 0.6

    col = target_collection if target_collection is not None else default_collection()
    door_mesh = bpy.data.meshes.new(name + "_Mesh")
    door_obj = bpy.data.objects.new(name, door_mesh)
    col.objects.link(door_obj)
    door_obj.parent = parent_obj
    door_obj.location = pivot_local
    door_obj.data.materials.append(mat_gate_frame)  # 0
    door_obj.data.materials.append(mat_handle)      # 1

    # Local bounds depending on which edge holds the hinges
    if hinge_side == '+X':
        x0, x1 = -span_x, 0.0
        y0, y1 = -span_y / 2.0, span_y / 2.0
    elif hinge_side == '+Y':
        x0, x1 = -span_x / 2.0, span_x / 2.0
        y0, y1 = -span_y, 0.0
    elif hinge_side == '-Y':
        x0, x1 = -span_x / 2.0, span_x / 2.0
        y0, y1 = 0.0, span_y
    else:
        raise ValueError(f"Unsupported hinge_side: {hinge_side}")

    dbm = bmesh.new()
    # Perimeter frame bars
    add_box(dbm, x0, x1, y0, y0 + dfw, -dtz, dtz)
    add_box(dbm, x0, x1, y1 - dfw, y1, -dtz, dtz)
    add_box(dbm, x0, x0 + dfw, y0 + dfw, y1 - dfw, -dtz, dtz)
    add_box(dbm, x1 - dfw, x1, y0 + dfw, y1 - dfw, -dtz, dtz)

    for x_rib in rib_xs:
        add_box(dbm, x_rib - 0.7, x_rib + 0.7, y0 + dfw, y1 - dfw, -dtz, dtz)
    for y_rib in rib_ys:
        add_box(dbm, x0 + dfw, x1 - dfw, y_rib - 0.7, y_rib + 0.7, -dtz, dtz)

    # Latches (Chot cua) + Top U-handle along the opening lip opposite the hinge
    door_accent_start = len(dbm.faces)
    if hinge_side == '+X':
        for y_latch in latch_offsets:
            add_box(dbm, x0 - 0.8, x0 + 2.5, y_latch - 1.0, y_latch + 1.0, -dtz - 0.8, dtz + 0.6)
            add_box(dbm, x0 + 0.5, x0 + 2.0, y_latch - 3.5, y_latch + 3.5, dtz + 0.2, dtz + 1.4)
        add_box(dbm, x0 + 1.5, x0 + 2.9, -9.0, -7.6, dtz, dtz + 4.5)
        add_box(dbm, x0 + 1.5, x0 + 2.9, 7.6, 9.0, dtz, dtz + 4.5)
        add_box(dbm, x0 + 1.4, x0 + 3.0, -9.0, 9.0, dtz + 4.5, dtz + 5.9)
    else:
        # Lip is at y0 (for '+Y' hinge) or y1 (for '-Y' hinge)
        y_lip = y0 if hinge_side == '+Y' else y1
        inward_dir = 1.0 if hinge_side == '+Y' else -1.0
        for x_latch in latch_offsets:
            ly_a = min(y_lip - 0.8 * inward_dir, y_lip + 2.5 * inward_dir)
            ly_b = max(y_lip - 0.8 * inward_dir, y_lip + 2.5 * inward_dir)
            add_box(dbm, x_latch - 1.0, x_latch + 1.0, ly_a, ly_b, -dtz - 0.8, dtz + 0.6)
            py_a = min(y_lip + 0.5 * inward_dir, y_lip + 2.0 * inward_dir)
            py_b = max(y_lip + 0.5 * inward_dir, y_lip + 2.0 * inward_dir)
            add_box(dbm, x_latch - 3.5, x_latch + 3.5, py_a, py_b, dtz + 0.2, dtz + 1.4)

        hy_a = min(y_lip + 1.5 * inward_dir, y_lip + 2.9 * inward_dir)
        hy_b = max(y_lip + 1.5 * inward_dir, y_lip + 2.9 * inward_dir)
        add_box(dbm, -9.0, -7.6, hy_a, hy_b, dtz, dtz + 4.5)
        add_box(dbm, 7.6, 9.0, hy_a, hy_b, dtz, dtz + 4.5)
        hy_top_a = min(y_lip + 1.4 * inward_dir, y_lip + 3.0 * inward_dir)
        hy_top_b = max(y_lip + 1.4 * inward_dir, y_lip + 3.0 * inward_dir)
        add_box(dbm, -9.0, 9.0, hy_top_a, hy_top_b, dtz + 4.5, dtz + 5.9)

    dbm.faces.ensure_lookup_table()
    for i in range(door_accent_start, len(dbm.faces)):
        dbm.faces[i].material_index = 1

    dbm.to_mesh(door_mesh)
    dbm.free()

    bpy.context.view_layer.update()
    door_world_cx = parent_obj.location.x + pivot_local[0] + (x0 + x1) / 2.0
    door_world_cy = parent_obj.location.y + pivot_local[1] + (y0 + y1) / 2.0
    door_world_cz = parent_obj.location.z + pivot_local[2]

    door_fence = create_fence_panel(
        name + "_Fence",
        span_x - 2 * dfw,
        span_y - 2 * dfw,
        cell_size,
        wire_thick,
        (door_world_cx, door_world_cy, door_world_cz),
        (0.0, 0.0, 0.0),
        mat_fence
    )
    apply_and_join(door_obj, [door_fence], name)

    # Lock location & restrict rotation to the single hinge axis
    door_obj.lock_location = (True, True, True)
    rot_limit = door_obj.constraints.new(type='LIMIT_ROTATION')
    rot_limit.name = "Hatch_Open_Z_Limit"
    rot_limit.use_limit_x = True
    rot_limit.use_limit_y = True
    rot_limit.use_limit_z = True
    rot_limit.min_z = rot_limit.max_z = 0.0
    rot_limit.owner_space = 'LOCAL'
    rot_limit.use_transform_limit = True

    if hinge_side == '+X':
        door_obj.lock_rotation = (True, False, True)
        rot_limit.min_x = rot_limit.max_x = 0.0
        rot_limit.min_y = 0.0
        rot_limit.max_y = math.radians(85.0)
        door_obj.rotation_euler = (0.0, math.radians(open_deg), 0.0)
    elif hinge_side == '+Y':
        door_obj.lock_rotation = (False, True, True)
        rot_limit.min_x = math.radians(-85.0)
        rot_limit.max_x = 0.0
        rot_limit.min_y = rot_limit.max_y = 0.0
        door_obj.rotation_euler = (math.radians(open_deg), 0.0, 0.0)
    else:  # '-Y'
        door_obj.lock_rotation = (False, True, True)
        rot_limit.min_x = 0.0
        rot_limit.max_x = math.radians(85.0)
        rot_limit.min_y = rot_limit.max_y = 0.0
        door_obj.rotation_euler = (math.radians(open_deg), 0.0, 0.0)

    return door_obj

def build_con_duc_block(name, size_x, size_y, size_z, bar_thick, cell_size, wire_thick, mat_frame, mat_fence, mat_gate_frame, mat_handle):
    """
    Build 'khoi_khung_luoi_con_duc' (60 x 240 x 60) positioned horizontally across the -X door side
    of the 4 cages (global X in [-125, -65], Y in [-120, +120], Z in [0, 60]).
    Includes a hinged top fence door (Cua_Nap_Con_Duc) with latches (chot) opening upward (+Z) and closing (-Z).
    """
    half_x = size_x / 2.0  # 30.0
    half_y = size_y / 2.0  # 120.0
    t = bar_thick

    mesh = bpy.data.meshes.new(name + "_Mesh")
    body_obj = bpy.data.objects.new(name, mesh)
    default_collection().objects.link(body_obj)
    body_obj.location = (-65.0 - half_x, 0.0, 0.0)  # (-95, 0, 0) -> +X face sits at -65.0
    body_obj.data.materials.append(mat_frame)   # 0
    body_obj.data.materials.append(mat_handle)  # 1

    bm = bmesh.new()
    # Bottom perimeter frame (Z = [0, t])
    add_box(bm, -half_x, half_x, -half_y, -half_y + t, 0.0, t)
    add_box(bm, -half_x, half_x, half_y - t, half_y, 0.0, t)
    add_box(bm, -half_x, -half_x + t, -half_y + t, half_y - t, 0.0, t)
    add_box(bm, half_x - t, half_x, -half_y + t, half_y - t, 0.0, t)

    # Top perimeter frame (Z = [size_z - t, size_z])
    add_box(bm, -half_x, half_x, -half_y, -half_y + t, size_z - t, size_z)
    add_box(bm, -half_x, half_x, half_y - t, half_y, size_z - t, size_z)
    add_box(bm, -half_x, -half_x + t, -half_y + t, half_y - t, size_z - t, size_z)
    add_box(bm, half_x - t, half_x, -half_y + t, half_y - t, size_z - t, size_z)

    # 4 Corner posts + 3 intermediate support posts along -X face (every 60 units in Y)
    for x0, x1 in [(-half_x, -half_x + t), (half_x - t, half_x)]:
        for y0, y1 in [(-half_y, -half_y + t), (half_y - t, half_y)]:
            add_box(bm, x0, x1, y0, y1, t, size_z - t)
    for y_mid in (-60.0, 0.0, 60.0):
        add_box(bm, -half_x, -half_x + t, y_mid - t / 2.0, y_mid + t / 2.0, t, size_z - t)

    # Latch catch loops (Chot bat tren khung -X, flush within 60x240x60) and Hinge bases (+X)
    accent_start = len(bm.faces)
    for y_latch in (-60.0, 60.0):
        add_box(bm, -half_x, -half_x + 1.4, y_latch - 2.5, y_latch + 2.5, size_z - 2.2, size_z - 0.2)
    for y_hinge in (-90.0, -30.0, 30.0, 90.0):
        add_box(bm, half_x - t, half_x, y_hinge - 3.0, y_hinge + 3.0, size_z - 1.2, size_z)

    bm.faces.ensure_lookup_table()
    for i in range(accent_start, len(bm.faces)):
        bm.faces[i].material_index = 1

    bm.to_mesh(mesh)
    bm.free()

    # Fence panels for -X (240x60), -Y (60x60), +Y (60x60), Bottom -Z (60x240)
    inset = t / 2.0
    in_x = size_x - 2 * inset
    in_y = size_y - 2 * inset
    in_z = size_z - 2 * inset
    cz = size_z / 2.0
    bx = body_obj.location.x

    panels = [
        create_fence_panel("CD_Fence_Front_MinusX", in_y, in_z, cell_size, wire_thick, (bx - half_x + inset, 0.0, cz), (math.radians(90), 0.0, math.radians(90)), mat_fence),
        create_fence_panel("CD_Fence_Left_MinusY", in_x, in_z, cell_size, wire_thick, (bx, -half_y + inset, cz), (math.radians(90), 0.0, 0.0), mat_fence),
        create_fence_panel("CD_Fence_Right_PlusY", in_x, in_z, cell_size, wire_thick, (bx, half_y - inset, cz), (math.radians(90), 0.0, 0.0), mat_fence),
        create_fence_panel("CD_Fence_Bottom", in_x, in_y, cell_size, wire_thick, (bx, 0.0, inset), (0.0, 0.0, 0.0), mat_fence),
    ]
    apply_and_join(body_obj, panels, name)

    # Top Hinged Fence Hatch Door (Cua_Nap_Con_Duc)
    door_obj = create_hinged_hatch_door(
        "Cua_Nap_Con_Duc",
        body_obj,
        (half_x - t / 2.0, 0.0, size_z - 0.4),
        size_x - t * 1.15,
        size_y - 2 * t,
        cell_size,
        wire_thick,
        rib_xs=[],
        rib_ys=(-60.0, 0.0, 60.0),
        latch_offsets=(-60.0, 60.0),
        open_deg=48.0,
        mat_gate_frame=mat_gate_frame,
        mat_fence=mat_fence,
        mat_handle=mat_handle,
        hinge_side='+X',
    )

    return body_obj, door_obj

def main():
    clear_scene()

    SIZE_X = 130.0
    SIZE_Y = 60.0
    SIZE_Z = 60.0
    BAR_THICK = 2.0
    WIRE_THICK = 0.28
    CELL_SIZE = 3.5

    # Materials
    mat_frame = create_material("Steel_Frame_Mat", (0.14, 0.16, 0.19, 1.0), metallic=0.85, roughness=0.32)
    mat_rail = create_material("Guide_Rail_Mat", (0.28, 0.30, 0.34, 1.0), metallic=0.90, roughness=0.25)
    mat_fence = create_material("Galvanized_Fence_Mat", (0.58, 0.62, 0.66, 1.0), metallic=0.90, roughness=0.28)
    mat_gate_frame = create_material("Gate_Frame_Mat", (0.20, 0.24, 0.28, 1.0), metallic=0.85, roughness=0.30)
    mat_handle = create_material("Handle_Accent_Mat", (0.95, 0.50, 0.05, 1.0), metallic=0.40, roughness=0.35)

    # 1. Build main hollow frame with -X guide rails
    main_obj = build_main_frame_with_tracks("Khoi_Khung_Luoi_Fence", SIZE_X, SIZE_Y, SIZE_Z, BAR_THICK, mat_frame, mat_rail, mat_handle)

    # 2. Build 4 fixed fence panels (Bottom, Front, Back, +X Right) — Top is now a hinged openable hatch door
    inset = BAR_THICK / 2.0
    in_x = SIZE_X - 2 * inset
    in_y = SIZE_Y - 2 * inset
    in_z = SIZE_Z - 2 * inset
    cz = SIZE_Z / 2.0

    fixed_panels = [
        create_fence_panel("Fence_Bottom", in_x, in_y, CELL_SIZE, WIRE_THICK, (0.0, 0.0, inset), (0.0, 0.0, 0.0), mat_fence),
        create_fence_panel("Fence_Front", in_x, in_z, CELL_SIZE, WIRE_THICK, (0.0, -SIZE_Y / 2.0 + inset, cz), (math.radians(90), 0.0, 0.0), mat_fence),
        create_fence_panel("Fence_Back", in_x, in_z, CELL_SIZE, WIRE_THICK, (0.0, SIZE_Y / 2.0 - inset, cz), (math.radians(90), 0.0, 0.0), mat_fence),
        create_fence_panel("Fence_Right_PlusX", in_y, in_z, CELL_SIZE, WIRE_THICK, (SIZE_X / 2.0 - inset, 0.0, cz), (math.radians(90), 0.0, math.radians(90)), mat_fence),
    ]

    apply_and_join(main_obj, fixed_panels, "Khoi_Khung_Luoi_Fence")

    # 3a. Build the movable -X sliding gate (pull up / pull down along Z)
    gate_obj = build_sliding_gate(
        "Cua_Luoi_Truot_Truc_Z",
        SIZE_Y, SIZE_Z, BAR_THICK, CELL_SIZE, WIRE_THICK,
        mat_gate_frame, mat_fence, mat_handle
    )
    gate_obj.parent = main_obj
    gate_obj.location = (0.0, 0.0, 28.0)

    # 3b. Build the hinged top hatch door with latches (+Z open / -Z close)
    top_door_obj = create_hinged_hatch_door(
        "Cua_Nap_Fence",
        main_obj,
        (SIZE_X / 2.0 - BAR_THICK / 2.0, 0.0, SIZE_Z - 0.4),
        SIZE_X - 4.5,
        SIZE_Y - 2 * BAR_THICK,
        CELL_SIZE,
        WIRE_THICK,
        rib_xs=(-41.5, -83.0),
        rib_ys=[],
        latch_offsets=(-16.0, 16.0),
        open_deg=26.0,
        mat_gate_frame=mat_gate_frame,
        mat_fence=mat_fence,
        mat_handle=mat_handle,
        hinge_side='+X',
    )

    # 3c. Optional hidden hatch doors opening along Y, kept inside the exact same collection
    # and parented directly under each Khoi_Khung_Luoi_Fence_i object for clean Outliner nesting:
    # (1) -Y -> +Y (hinged at +Y, rotates around X from -85 to 0 deg)
    # (2) +Y -> -Y (hinged at -Y, rotates around X from 0 to +85 deg)
    hatch_span_x = SIZE_X - 4.5
    hatch_span_y = SIZE_Y - 2 * BAR_THICK
    hatch_center_x = 1.0  # spans [-61.5, +63.5]

    door_neg_y_to_pos_y = create_hinged_hatch_door(
        "Cua_Nap_NegY_Sang_Y",
        main_obj,
        (hatch_center_x, hatch_span_y / 2.0, SIZE_Z - 0.4),
        hatch_span_x,
        hatch_span_y,
        CELL_SIZE,
        WIRE_THICK,
        rib_xs=(-21.0, 21.0),
        rib_ys=[],
        latch_offsets=(-32.0, 32.0),
        open_deg=-28.0,
        mat_gate_frame=mat_gate_frame,
        mat_fence=mat_fence,
        mat_handle=mat_handle,
        hinge_side='+Y',
    )

    door_pos_y_to_neg_y = create_hinged_hatch_door(
        "Cua_Nap_Y_Sang_NegY",
        main_obj,
        (hatch_center_x, -hatch_span_y / 2.0, SIZE_Z - 0.4),
        hatch_span_x,
        hatch_span_y,
        CELL_SIZE,
        WIRE_THICK,
        rib_xs=(-21.0, 21.0),
        rib_ys=[],
        latch_offsets=(-32.0, 32.0),
        open_deg=28.0,
        mat_gate_frame=mat_gate_frame,
        mat_fence=mat_fence,
        mat_handle=mat_handle,
        hinge_side='-Y',
    )

    # 4. Duplicate into 4 flush units placed side-by-side along the Y axis
    NUM_UNITS = 4
    y_start = -((NUM_UNITS - 1) * SIZE_Y) / 2.0  # -90, -30, +30, +90 (touching at -60, 0, +60)

    main_obj.name = "Khoi_Khung_Luoi_Fence_1"
    main_obj.location = (0.0, y_start, 0.0)
    gate_obj.name = "Cua_Luoi_Truot_Truc_Z_1"
    top_door_obj.name = "Cua_Nap_Fence_1"
    door_neg_y_to_pos_y.name = "Cua_Nap_NegY_Sang_Y_1"
    door_pos_y_to_neg_y.name = "Cua_Nap_Y_Sang_NegY_1"

    hidden_doors = [door_neg_y_to_pos_y, door_pos_y_to_neg_y]
    cages = [main_obj]
    for idx in range(1, NUM_UNITS):
        y_pos = y_start + idx * SIZE_Y
        cage_copy = main_obj.copy()
        cage_copy.data = main_obj.data.copy()
        cage_copy.name = f"Khoi_Khung_Luoi_Fence_{idx + 1}"
        cage_copy.location = (0.0, y_pos, 0.0)
        default_collection().objects.link(cage_copy)

        gate_copy = gate_obj.copy()
        gate_copy.data = gate_obj.data.copy()
        gate_copy.name = f"Cua_Luoi_Truot_Truc_Z_{idx + 1}"
        gate_copy.parent = cage_copy
        gate_copy.location = (0.0, 0.0, 28.0)
        default_collection().objects.link(gate_copy)

        door_copy = top_door_obj.copy()
        door_copy.data = top_door_obj.data.copy()
        door_copy.name = f"Cua_Nap_Fence_{idx + 1}"
        door_copy.parent = cage_copy
        door_copy.location = top_door_obj.location.copy()
        door_copy.rotation_euler = top_door_obj.rotation_euler.copy()
        default_collection().objects.link(door_copy)

        for template, base_name in [
            (door_neg_y_to_pos_y, "Cua_Nap_NegY_Sang_Y"),
            (door_pos_y_to_neg_y, "Cua_Nap_Y_Sang_NegY"),
        ]:
            opt_copy = template.copy()
            opt_copy.data = template.data.copy()
            opt_copy.name = f"{base_name}_{idx + 1}"
            opt_copy.parent = cage_copy
            opt_copy.location = template.location.copy()
            opt_copy.rotation_euler = template.rotation_euler.copy()
            default_collection().objects.link(opt_copy)
            hidden_doors.append(opt_copy)

        cages.append(cage_copy)

    # Keep the -Y->Y and Y->-Y optional doors hidden until the user wants to show/use them
    for hd in hidden_doors:
        hd.hide_set(True)
        hd.hide_render = True

    # 5. Build horizontal connecting block 'khoi_khung_luoi_con_duc' (60 x 240 x 60) at -X
    con_duc_obj, con_duc_door = build_con_duc_block(
        "khoi_khung_luoi_con_duc",
        60.0, SIZE_Y * NUM_UNITS, SIZE_Z,
        BAR_THICK, CELL_SIZE, WIRE_THICK,
        mat_frame, mat_fence, mat_gate_frame, mat_handle
    )

    # Ground plane
    bpy.ops.mesh.primitive_plane_add(size=1500, location=(-30, 0, -0.05))
    ground = bpy.context.active_object
    ground.name = "Studio_Floor"
    mat_floor = create_material("Floor_Mat", (0.22, 0.23, 0.25, 1.0), metallic=0.0, roughness=0.85)
    ground.data.materials.append(mat_floor)

    # Camera positioned on the -X, -Y side (higher elevation) to clearly show all 5 openable top doors + latches
    bpy.ops.object.camera_add(location=(-345.0, -305.0, 300.0))
    cam = bpy.context.active_object
    cam.data.clip_end = 3000.0
    bpy.context.scene.camera = cam

    direction = mathutils.Vector((-25.0, 0.0, 48.0)) - cam.location
    cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

    # Lighting from -X front-top to illuminate both 'khoi_khung_luoi_con_duc' and the 4 cages
    bpy.ops.object.light_add(type='SUN', location=(-220.0, -180.0, 280.0))
    sun = bpy.context.active_object
    sun.data.energy = 3.5
    sun_dir = mathutils.Vector((-30.0, 0.0, 20.0)) - sun.location
    sun.rotation_euler = sun_dir.to_track_quat('-Z', 'Y').to_euler()

    bpy.ops.object.light_add(type='AREA', location=(200.0, 200.0, 220.0))
    fill = bpy.context.active_object
    fill.data.energy = 160000.0
    fill.data.size = 280.0
    fill_dir = mathutils.Vector((-20.0, 0.0, 30.0)) - fill.location
    fill.rotation_euler = fill_dir.to_track_quat('-Z', 'Y').to_euler()

    # Adjust viewport clip_end
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.clip_end = 5000.0

    print("Created 4 cages at Y:", [c.location.y for c in cages])
    print("khoi_khung_luoi_con_duc dimensions:", tuple(round(d, 2) for d in con_duc_obj.dimensions), "at", tuple(round(v, 2) for v in con_duc_obj.location))
    print("Cua_Nap_Con_Duc rotation Y (deg):", round(math.degrees(con_duc_door.rotation_euler.y), 1))

main()
