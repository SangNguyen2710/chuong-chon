import bpy
import csv
import math
import os

OUTPUT_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vat_tu_bom.csv")

def analyze_and_export_bom():
    # Gather counts directly from Blender scene objects
    cages = [o for o in bpy.data.objects if o.name.startswith("Khoi_Khung_Luoi_Fence_")]
    con_duc = bpy.data.objects.get("khoi_khung_luoi_con_duc")
    slide_gates = [o for o in bpy.data.objects if o.name.startswith("Cua_Luoi_Truot_Truc_Z_")]
    top_doors = [o for o in bpy.data.objects if o.name.startswith("Cua_Nap_Fence_")]
    con_duc_door = bpy.data.objects.get("Cua_Nap_Con_Duc")
    legs = bpy.data.objects.get("Chan_Chong_Sat_4_Goc")
    roof_pillars = bpy.data.objects.get("Cot_Mai_Ton_4_Goc")
    roof = bpy.data.objects.get("Mai_Ton")

    n_cages = len(cages)
    # Base dimensions from actual cage object (cm)
    sx, sy, sz = (130.0, 60.0, 60.0)
    if cages:
        sx, sy, sz = [round(d, 2) for d in cages[0].dimensions]

    t = 2.0  # frame bar 2x2 cm

    # 1. Sat tru 4x4 cm (chan chong duoi + cot mai tren)
    leg_len_m = (4 * 50.0) / 100.0 if legs else 0.0
    pillar_high_m = (2 * 40.0) / 100.0 if roof_pillars else 0.0
    pillar_low_m = (2 * 20.0) / 100.0 if roof_pillars else 0.0
    total_4x4_m = leg_len_m + pillar_high_m + pillar_low_m

    # 2. Sat hop 2x2 cm (khung chinh 4 chuong + khung con duc)
    # 1 chuong: 4*130 (X) + 4*56 (Z) + 2*56 (+X) + 2*56 (-X) = 968 cm = 9.68 m
    per_cage_2x2_m = (4 * sx + 4 * (sz - 2 * t) + 4 * (sy - 2 * t)) / 100.0
    cages_2x2_m = n_cages * per_cage_2x2_m

    # Con duc (60 x 240 x 60): 4*60 (-Y/+Y) + 4*232 (-X/+X lot long) + 7*56 (tru dung) = 1560 cm = 15.60 m
    cd_x, cd_y, cd_z = (60.0, 240.0, 60.0)
    if con_duc:
        cd_x, cd_y, cd_z = [round(d, 2) for d in con_duc.dimensions]
    con_duc_2x2_m = (4 * cd_x + 4 * (cd_y - 4 * t) + 7 * (cd_z - 2 * t)) / 100.0 if con_duc else 0.0
    total_2x2_m = cages_2x2_m + con_duc_2x2_m

    # Ray truot chu U (nep dan huong cua -X): 4 chuong * 2 ben * 59.2 cm
    rail_len_m = n_cages * 2 * (sz - 0.8) / 100.0

    # 3. Sat khung cua nho (~1.5x1.5 cm hoac 1.6x1.6 cm)
    # 4 cua truot -X: 2*59.2 + 2*54.0 = 226.4 cm/cua + tay nam ~26cm
    slide_frame_m = len(slide_gates) * (2 * (sz - 0.8) + 2 * (sy - 2 * t - 2.0) + 26.0) / 100.0
    # 4 cua nap tren chuong: 2*125.5 + 4*52.8 = 462.2 cm/cua + tay nam ~27cm
    top_door_frame_m = len(top_doors) * (2 * (sx - 4.5) + 4 * (sy - 2 * t - 3.2) + 27.0) / 100.0
    # 1 cua nap con duc: 2*236 + 5*54.5 = 744.5 cm + tay nam ~27cm
    cd_door_frame_m = (2 * (cd_y - 2 * t) + 5 * (cd_x - t * 1.15 - 3.2) + 27.0) / 100.0 if con_duc_door else 0.0
    total_door_frame_m = slide_frame_m + top_door_frame_m + cd_door_frame_m

    # 4. Luoi thep fence (m2)
    # 1 chuong: day (128x58) + 2 ben (2*128x58) + +X (58x58) + cua truot (54x56) + cua nap (122.3x52.8)
    in_x, in_y, in_z = sx - t, sy - t, sz - t
    cage_fence_m2 = (
        3 * (in_x * in_y) + (in_y * in_z) + (54.0 * 56.0) + ((sx - 4.5 - 3.2) * (sy - 2 * t - 3.2))
    ) / 10000.0
    cages_fence_m2 = n_cages * cage_fence_m2

    # Con duc: -X (238x58) + 2 dau (2*58x58) + day (238x58) + cua nap (54.5x232.8)
    cd_in_x, cd_in_y, cd_in_z = cd_x - t, cd_y - t, cd_z - t
    cd_fence_m2 = (
        2 * (cd_in_y * cd_in_z) + 2 * (cd_in_x * cd_in_z) + ((cd_x - t * 1.15 - 3.2) * (cd_y - 2 * t - 3.2))
    ) / 10000.0 if con_duc else 0.0
    total_fence_m2 = cages_fence_m2 + cd_fence_m2

    # 5. Mai ton lop (m2)
    roof_slope_x_cm = math.sqrt(230.0 ** 2 + (230.0 * 20.0 / 186.0) ** 2)
    roof_y_cm = 280.0
    roof_area_m2 = (roof_slope_x_cm * roof_y_cm) / 10000.0 if roof else 0.0

    # 6. Phu kien
    hinges_count = len(top_doors) * 2 + (4 if con_duc_door else 0)
    latches_count = len(top_doors) * 2 + (2 if con_duc_door else 0)
    baseplates_count = 4 if legs else 0

    rows = [
        ("Hạng mục", "Quy cách vật liệu", "Khối lượng tịnh", "Đơn vị", "Quy đổi / Ghi chú"),
        ("Sắt hộp trụ chịu lực (chân dưới + cột mái)", "Sắt hộp vuông 4×4 cm", f"{total_4x4_m:.2f}", "m", f"{math.ceil(total_4x4_m / 6.0)} cây 6m (4 chân 50cm + 2 cột cao 40cm + 2 cột thấp 20cm)"),
        ("Sắt hộp khung 4 chuồng chính (130×60×60)", "Sắt hộp vuông 2×2 cm", f"{cages_2x2_m:.2f}", "m", f"{n_cages} chuồng × {per_cage_2x2_m:.2f} m"),
        ("Sắt hộp khung khối ngang phía trước (60×240×60)", "Sắt hộp vuông 2×2 cm", f"{con_duc_2x2_m:.2f}", "m", "Khung chính + 3 trụ đứng mặt trước"),
        ("Tổng sắt hộp khung 2×2 cm", "Sắt hộp vuông 2×2 cm", f"{total_2x2_m:.2f}", "m", f"Cần mua ~{math.ceil(total_2x2_m / 6.0)} cây 6m (chưa tính hao hụt cắt)"),
        ("Thanh ray trượt cửa đứng", "Thép chữ V / U dẫn hướng", f"{rail_len_m:.2f}", "m", "4 chuồng × 2 ray đứng (mỗi ray ~0.59 m)"),
        ("Sắt khung các loại cửa (cửa trượt + cửa nắp)", "Sắt hộp nhỏ 1.5×1.5 cm", f"{total_door_frame_m:.2f}", "m", f"Cần mua ~{math.ceil(total_door_frame_m / 6.0)} cây 6m (4 cửa trượt + 5 cửa nắp)"),
        ("Lưới fence mắt cáo 4 chuồng chính", "Lưới thép mạ kẽm", f"{cages_fence_m2:.2f}", "m²", "Đáy, 3 vách, cửa trượt đứng và cửa nắp trên"),
        ("Lưới fence mắt cáo khối ngang phía trước", "Lưới thép mạ kẽm", f"{cd_fence_m2:.2f}", "m²", "Mặt trước, 2 đầu hông, đáy và cửa nắp trên"),
        ("Tổng lưới fence (tịnh / dự phòng 10%)", "Lưới thép mạ kẽm", f"{total_fence_m2:.2f}", "m²", f"Dự phòng hao hụt 10%: ~{total_fence_m2 * 1.10:.2f} m²"),
        ("Mái tôn sóng 3D (231.3 × 280 cm)", "Tôn lợp mạ kẽm / tôn lạnh", f"{roof_area_m2:.2f}", "m²", "Khổ 1.07m × dài 2.35m: cần ~3 tấm chồng sóng"),
        ("Bản lề cửa nắp", "Bản lề sắt hàn", f"{hinges_count}", "cái", "4 chuồng × 2 + khối ngang trước × 4"),
        ("Chốt gài cửa nắp", "Chốt gài / then cài", f"{latches_count}", "bộ", "4 chuồng × 2 + khối ngang trước × 2"),
        ("Bản đế chân chống", "Thép tấm 6.4×6.4×0.8 cm", f"{baseplates_count}", "tấm", "Hàn dưới 4 chân góc tiếp đất"),
    ]

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerows(rows)

    print("=== BẢNG BÓC TÁCH VẬT TƯ (BOM) ===")
    for r in rows:
        print(" | ".join(r))
    print(f"Đã lưu file BOM CSV tại: {OUTPUT_CSV}")

if __name__ == "__main__":
    analyze_and_export_bom()
