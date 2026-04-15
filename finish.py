# =====================================================
# Isaac Sim - Warehouse Zones & A -> B Transport
# Zone A = RED, Zone B = GREEN
# =====================================================

# -----------------------------------------------------
# 1️⃣ 啟動 SimulationApp（一定要最先）
# -----------------------------------------------------
from isaacsim import SimulationApp
simulation_app = SimulationApp({"headless": False})

# -----------------------------------------------------
# 2️⃣ SimulationApp 後才能 import
# -----------------------------------------------------
from isaacsim.core.utils.stage import add_reference_to_stage, is_stage_loading
import omni.usd
from pxr import Usd, UsdGeom, UsdLux, UsdShade, Gf, Sdf
import time
import math
import requests  # 用來把位姿送到本機 dashboard_server

# -----------------------------------------------------
# 3️⃣ 取得 Stage
# -----------------------------------------------------
stage = omni.usd.get_context().get_stage()


# -----------------------------------------------------
# 工具：在重新執行時清除上次留下的物件
# -----------------------------------------------------
def remove_if_exists(path: str):
    prim = stage.GetPrimAtPath(path)
    if prim.IsValid():
        stage.RemovePrim(path)
        print(f"🧹 已移除上一輪的物件: {path}")

# -----------------------------------------------------
# 4️⃣ 載入倉庫 USD
# -----------------------------------------------------
warehouse_usd_path = r"D:\project_isaac\1.usd"   # 🔺請改成你的路徑
warehouse_prim_path = "/World/Warehouse"

# 清理上一輪跑出的物件，確保每次執行都是乾淨的
remove_if_exists("/World/Zones")
remove_if_exists("/World/CargoBox")
remove_if_exists("/World/DomeLight")

add_reference_to_stage(warehouse_usd_path, warehouse_prim_path)
print("Loading warehouse scene...")

while is_stage_loading():
    simulation_app.update()

print("✅ Warehouse scene loaded")

# -----------------------------------------------------
# 5️⃣ 環境光
# -----------------------------------------------------
light_path = "/World/DomeLight"
dome_light = UsdLux.DomeLight.Define(stage, light_path)
dome_light.GetIntensityAttr().Set(1200.0)
print("✅ DomeLight added")

# -----------------------------------------------------
# 6️⃣ 建立 Zones
# -----------------------------------------------------
UsdGeom.Xform.Define(stage, "/World/Zones")

# A 區
zone_a_path = "/World/Zones/Zone_A"
zone_a = UsdGeom.Xform.Define(stage, zone_a_path)
UsdGeom.Xformable(zone_a).AddTranslateOp().Set((0.0, 0.0, 0.0))

# B 區
zone_b_path = "/World/Zones/Zone_B"
zone_b = UsdGeom.Xform.Define(stage, zone_b_path)
UsdGeom.Xformable(zone_b).AddTranslateOp().Set((8.0, 4.0, 0.0))

# 4 區
zone_4_path = "/World/Zones/Zone_4"
zone_4 = UsdGeom.Xform.Define(stage, zone_4_path)
UsdGeom.Xformable(zone_4).AddTranslateOp().Set((0.0, 0.0, 0.0))

# 5 區
zone_5_path = "/World/Zones/Zone_5"
zone_5 = UsdGeom.Xform.Define(stage, zone_5_path)
UsdGeom.Xformable(zone_5).AddTranslateOp().Set((0.0, 0.0, 0.0))

# 6 區
zone_6_path = "/World/Zones/Zone_6"
zone_6 = UsdGeom.Xform.Define(stage, zone_6_path)
UsdGeom.Xformable(zone_6).AddTranslateOp().Set((0.0, 0.0, 0.0))

# 準備送出區
zone_prepare_path = "/World/Zones/Zone_Prepare"
zone_prepare = UsdGeom.Xform.Define(stage, zone_prepare_path)
UsdGeom.Xformable(zone_prepare).AddTranslateOp().Set((0.0, 0.0, 0.0))

print("✅ Zone A & Zone B & Zone 4 & Zone 5 & Zone 6 & Prepare Zone created")

# -----------------------------------------------------
# 7️⃣ 建立「有顏色的 Zone Marker」
# -----------------------------------------------------
def create_zone_marker_with_color(path, position, color, name):
    cube_path = f"{path}/{name}"
    cube = UsdGeom.Cube.Define(stage, cube_path)
    cube.CreateSizeAttr(0.3)

    # 位置
    xform = UsdGeom.Xformable(cube)
    xform.AddTranslateOp().Set(
        (position[0], position[1], position[2] + 0.5)
    )

    # Material
    material_path = f"{cube_path}_Material"
    material = UsdShade.Material.Define(stage, material_path)

    shader = UsdShade.Shader.Define(stage, material_path + "/Shader")
    shader.CreateIdAttr("UsdPreviewSurface")

    # ✅ 正確的 USD 型別指定
    shader.CreateInput(
        "diffuseColor",
        Sdf.ValueTypeNames.Color3f
    ).Set(Gf.Vec3f(color[0], color[1], color[2]))

    shader.CreateInput(
        "roughness",
        Sdf.ValueTypeNames.Float
    ).Set(0.4)

    material.CreateSurfaceOutput().ConnectToSource(
        shader.ConnectableAPI(), "surface"
    )

    UsdShade.MaterialBindingAPI(cube).Bind(material)

# 建立帶範圍的區域（用平面標示範圍）
def create_zone_with_range(path, min_pos, max_pos, color, name):
    """
    建立一個帶有範圍的區域
    min_pos: (x_min, y_min, z_min) - 範圍的最小座標
    max_pos: (x_max, y_max, z_max) - 範圍的最大座標
    """
    # 計算中心點和尺寸
    center_x = (min_pos[0] + max_pos[0]) / 2.0
    center_y = (min_pos[1] + max_pos[1]) / 2.0
    center_z = (min_pos[2] + max_pos[2]) / 2.0
    
    size_x = max_pos[0] - min_pos[0]
    size_y = max_pos[1] - min_pos[1]
    size_z = max_pos[2] - min_pos[2]
    
    # 確保最小尺寸，避免視覺化問題（如果某個維度為 0，給一個小的寬度）
    if size_x == 0:
        size_x = 0.2  # 給一個小的寬度，讓區域更接近指定位置
        # center_x 保持為 min_pos[0]（即指定的固定值）
    if size_z == 0:
        size_z = 0.02  # 保持厚度
    
    # 建立範圍標示平面（放在底部）
    # 確保路徑以字母開頭，符合 USD 命名規則
    if not name or not path:
        raise ValueError(f"Invalid path or name: path={path}, name={name}")
    
    # 如果名稱以數字開頭，在前面加上前綴
    plane_name = f"{name}_Range" if name and not name[0].isdigit() else f"Range_{name}"
    plane_path = f"{path}/{plane_name}"
    
    # 確保路徑有效
    if not plane_path or plane_path == "/" or not plane_path.startswith("/"):
        raise ValueError(f"Invalid plane path: {plane_path}")
    
    plane = UsdGeom.Cube.Define(stage, plane_path)
    plane.CreateSizeAttr(1.0)  # 基礎尺寸
    
    # 設定位置和縮放
    xform = UsdGeom.Xformable(plane)
    xform.AddTranslateOp().Set((center_x, center_y, min_pos[2] + 0.01))
    xform.AddScaleOp().Set((size_x, size_y, 0.02))
    
    # Material（半透明）
    material_path = f"{plane_path}_Material"
    material = UsdShade.Material.Define(stage, material_path)
    shader = UsdShade.Shader.Define(stage, material_path + "/Shader")
    shader.CreateIdAttr("UsdPreviewSurface")
    
    shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(
        Gf.Vec3f(color[0], color[1], color[2])
    )
    shader.CreateInput("opacity", Sdf.ValueTypeNames.Float).Set(0.3)  # 半透明
    shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.4)
    
    material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
    UsdShade.MaterialBindingAPI(plane).Bind(material)
    
    # 建立四個角落的標記
    corners = [
        (min_pos[0], min_pos[1], min_pos[2]),
        (max_pos[0], min_pos[1], min_pos[2]),
        (max_pos[0], max_pos[1], min_pos[2]),
        (min_pos[0], max_pos[1], min_pos[2])
    ]
    
    for i, corner_pos in enumerate(corners):
        # 確保角落路徑名稱以字母開頭
        if name and not name[0].isdigit():
            corner_name = f"{name}_Corner_{i+1}"
        else:
            corner_name = f"Corner_{name}_{i+1}" if name else f"Corner_{i+1}"
        corner_path = f"{path}/{corner_name}"
        corner = UsdGeom.Cube.Define(stage, corner_path)
        corner.CreateSizeAttr(0.2)
        corner_xform = UsdGeom.Xformable(corner)
        corner_xform.AddTranslateOp().Set((corner_pos[0], corner_pos[1], corner_pos[2] + 0.1))
        
        # 角落標記的材質
        corner_material_path = f"{corner_path}_Material"
        corner_material = UsdShade.Material.Define(stage, corner_material_path)
        corner_shader = UsdShade.Shader.Define(stage, corner_material_path + "/Shader")
        corner_shader.CreateIdAttr("UsdPreviewSurface")
        corner_shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(
            Gf.Vec3f(color[0], color[1], color[2])
        )
        corner_shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.4)
        corner_material.CreateSurfaceOutput().ConnectToSource(corner_shader.ConnectableAPI(), "surface")
        UsdShade.MaterialBindingAPI(corner).Bind(corner_material)
    
    return (center_x, center_y, center_z)

# 🟢 B 區（綠）
create_zone_marker_with_color(
    zone_b_path,
    (8.0, 4.0, 0.0),
    color=(0.0, 1.0, 0.0),
    name="marker_B"
)

# 🔵 4 區（藍色，帶範圍）
# 設定 4 區的範圍：(-5.5, 8~16, 0)
zone_4_min = (-5.5, 8.0, 0.0)   # 最小座標 (x_min, y_min, z_min)
zone_4_max = (-5.5, 16.0, 0.0)  # 最大座標 (x_max, y_max, z_max)

zone_4_center = create_zone_with_range(
    zone_4_path,
    zone_4_min,
    zone_4_max,
    color=(0.0, 0.5, 1.0),  # 藍色
    name="Range_4"
)

# 4 區的中心標記
create_zone_marker_with_color(
    zone_4_path,
    zone_4_center,
    color=(0.0, 0.5, 1.0),
    name="marker_4"
)

# 🟡 5 區（黃色，帶範圍）
# 設定 5 區的範圍：(-0.5, 8~16, 0)
zone_5_min = (-0.5, 8.0, 0.0)
zone_5_max = (-0.5, 16.0, 0.0)

zone_5_center = create_zone_with_range(
    zone_5_path,
    zone_5_min,
    zone_5_max,
    color=(1.0, 1.0, 0.0),  # 黃色
    name="Range_5"
)

# 5 區的中心標記
create_zone_marker_with_color(
    zone_5_path,
    zone_5_center,
    color=(1.0, 1.0, 0.0),
    name="marker_5"
)

# 🟣 6 區（紫色，帶範圍）
# 設定 6 區的範圍：(4.5, 8~16, 0)
zone_6_min = (4.5, 8.0, 0.0)
zone_6_max = (4.5, 16.0, 0.0)

zone_6_center = create_zone_with_range(
    zone_6_path,
    zone_6_min,
    zone_6_max,
    color=(1.0, 0.0, 1.0),  # 紫色
    name="Range_6"
)

# 6 區的中心標記
create_zone_marker_with_color(
    zone_6_path,
    zone_6_center,
    color=(1.0, 0.0, 1.0),
    name="marker_6"
)

# 🟠 準備送出區（橙色，帶範圍）
# 設定準備送出區的範圍：(-9, -4~8, 0)
zone_prepare_min = (-9.0, -4.0, 0.0)
zone_prepare_max = (-9.0, 8.0, 0.0)

zone_prepare_center = create_zone_with_range(
    zone_prepare_path,
    zone_prepare_min,
    zone_prepare_max,
    color=(1.0, 0.5, 0.0),  # 橙色
    name="Range_Prepare"
)

# 準備送出區的中心標記（已移除）
# create_zone_marker_with_color(
#     zone_prepare_path,
#     zone_prepare_center,
#     color=(1.0, 0.5, 0.0),
#     name="marker_Prepare"
# )

print("✅ Zone markers added (Red / Green / Blue 4 / Yellow 5 / Purple 6 / Orange Prepare)")

# -----------------------------------------------------
# 8️⃣ 找到 Forklift（機器）
# -----------------------------------------------------
def traverse_stage_tree(prim, depth=0, max_depth=10, keyword=None):
    """
    遞迴遍歷 USD Stage 樹狀結構，列出所有物件路徑
    
    Args:
        prim: 要遍歷的 Prim 物件
        depth: 當前深度（用於縮排顯示）
        max_depth: 最大遍歷深度（避免無限遞迴）
        keyword: 關鍵字篩選（例如 "fork", "lift" 等）
    
    Returns:
        list: 找到的所有符合條件的路徑列表
    """
    found_paths = []
    
    if depth > max_depth:
        return found_paths
    
    if not prim.IsValid():
        return found_paths
    
    prim_path = str(prim.GetPath())
    prim_name = str(prim.GetName()).lower()
    
    # 如果沒有關鍵字，或者名稱包含關鍵字，則記錄
    if keyword is None or keyword.lower() in prim_name:
        found_paths.append(prim_path)
        indent = "  " * depth
        print(f"{indent}📦 {prim_path} (類型: {prim.GetTypeName()})")
    
    # 遞迴遍歷子節點
    for child in prim.GetChildren():
        child_paths = traverse_stage_tree(child, depth + 1, max_depth, keyword)
        found_paths.extend(child_paths)
    
    return found_paths

# 往上尋找含關鍵字的較高層節點，避免只抓到零件而非整台車
# 但不要往上找到 Warehouse 或 World 層級
def ascend_to_keyword_root(prim, keywords=None, stop_paths=None, max_levels=5):
    """
    往上尋找車子的根節點，但嚴格限制不要找到場景層級
    
    Args:
        prim: 起始 Prim 物件
        keywords: 關鍵字列表
        stop_paths: 停止路徑（遇到這些路徑就停止）
        max_levels: 最多往上找幾層（避免無限往上）
    
    Returns:
        找到的根節點，如果找不到合適的就返回原始節點
    """
    if keywords is None:
        keywords = ["fork", "lift", "vehicle", "agv"]
    if stop_paths is None:
        stop_paths = ["/World", "/World/Warehouse"]

    cur = prim
    best_match = prim  # 記錄最好的匹配
    level = 0
    
    while cur and cur.IsValid() and level < max_levels:
        name = str(cur.GetName()).lower()
        path_str = str(cur.GetPath())
        parent = cur.GetParent()
        
        # 如果到達停止路徑，立即停止
        if path_str in stop_paths or name in ["world", "warehouse"]:
            break
        
        # 檢查當前節點是否符合關鍵字
        match = any(k in name for k in keywords)
        
        # 如果符合關鍵字，記錄為最佳匹配
        if match:
            best_match = cur
        
        # 如果沒有父節點，停止
        if not parent or not parent.IsValid():
            break
        
        # 檢查父節點是否為停止路徑
        parent_path = str(parent.GetPath())
        parent_name = str(parent.GetName()).lower()
        if parent_path in stop_paths or parent_name in ["world", "warehouse"]:
            # 如果當前節點符合關鍵字，返回當前節點
            if match:
                return cur
            # 否則返回最佳匹配
            break
        
        cur = parent
        level += 1
    
    # 返回最佳匹配（如果找到），否則返回原始節點
    return best_match if best_match != prim or any(k in str(prim.GetName()).lower() for k in keywords) else prim
# 獲取物件的世界座標位置
def get_world_position(prim):
    """
    獲取 Prim 的世界座標位置
    返回 (x, y, z) 或 None
    """
    if not prim.IsValid():
        return None
    
    xform = UsdGeom.Xformable(prim)
    if not xform:
        return None
    
    # 獲取世界變換矩陣
    world_transform = xform.ComputeLocalToWorldTransform(Usd.TimeCode.Default())
    translation = world_transform.ExtractTranslation()
    
    return (translation[0], translation[1], translation[2])

# 判斷物件是否為障礙物
def is_obstacle(prim, name, position):
    """
    判斷物件是否為障礙物
    障礙物特徵：
    1. 散落在地上（z座標接近0，通常在 -0.5 到 1.0 之間）
    2. 不是牆壁、柱子、櫃子/料架等固定結構
    3. 不是車輛本身

    🔧 備註：
    - B 區的「櫃子 / 料架」通常應視為場景固定結構（環境的一部分），
      不應被當成需要繞行的「臨時障礙物」，否則車子會在櫃子周圍一直繞圈。
    """
    if not position:
        return False
    
    name_lower = name.lower()
    x, y, z = position
    
    # 排除場景結構（牆壁、柱子等）
    structure_keywords = [
        "wall", "column", "pillar", "floor", "ceiling", "roof",
        "warehouse", "building", "structure", "foundation"
    ]
    if any(kw in name_lower for kw in structure_keywords):
        return False

    # ✅ 排除倉儲櫃 / 料架（固定貨架，不當成「臨時障礙物」）
    #   如果你的 USD 中櫃子的名稱不同（例如含有 "rack_b", "shelf01" 等），
    #   可以把實際名稱關鍵字加到下方這個列表裡。
    rack_keywords = ["rack", "shelf", "shelves", "cabinet", "storage"]
    if any(kw in name_lower for kw in rack_keywords):
        return False
    
    # 排除車輛
    vehicle_keywords = ["fork", "lift", "vehicle", "agv", "car", "truck"]
    if any(kw in name_lower for kw in vehicle_keywords):
        return False
    
    # 排除區域標記
    if "zone" in name_lower or "marker" in name_lower or "range" in name_lower:
        return False
    
    # 障礙物特徵：z座標接近地面（散落在地上的物件）
    # 通常障礙物的 z 座標在 -0.5 到 1.5 之間
    if -0.5 <= z <= 1.5:
        # 檢查是否有幾何形狀（有幾何形狀的才可能是障礙物）
        if prim.IsA(UsdGeom.Imageable):
            return True
    
    return False

# 判斷物件是否為箱子
def is_box(prim, name, position):
    """
    判斷物件是否為箱子
    箱子特徵：
    1. 名稱包含 box, crate, cargo, container 等
    2. 有幾何形狀
    """
    if not position:
        return False
    
    name_lower = name.lower()
    box_keywords = ["box", "crate", "cargo", "container", "pallet", "package"]
    
    if any(kw in name_lower for kw in box_keywords):
        if prim.IsA(UsdGeom.Imageable):
            return True
    
    return False

# 先列出整個 Warehouse 場景樹結構（幫助用戶了解場景結構）
print("\n" + "="*60)
print("🔍 開始掃描 USD 場景結構...")
print("="*60)

warehouse_prim = stage.GetPrimAtPath("/World/Warehouse")
obstacles = []  # 障礙物集合
boxes = []      # 箱子集合

if warehouse_prim.IsValid():
    print("\n📋 完整場景樹結構：")
    all_paths = traverse_stage_tree(warehouse_prim, depth=0, max_depth=15, keyword=None)
    
    print("\n" + "="*60)
    print("🔍 分析場景物件：識別障礙物和箱子...")
    print("="*60)
    
    # 分析所有物件
    for path in all_paths:
        prim = stage.GetPrimAtPath(path)
        if prim.IsValid():
            name = str(prim.GetName())
            position = get_world_position(prim)
            
            # 判斷是否為箱子
            if is_box(prim, name, position):
                boxes.append({
                    "path": path,
                    "name": name,
                    "position": position
                })
                print(f"📦 箱子: {name} @ {position}")
            
            # 判斷是否為障礙物
            elif is_obstacle(prim, name, position):
                obstacles.append({
                    "path": path,
                    "name": name,
                    "position": position
                })
                print(f"🚫 障礙物: {name} @ {position}")
    
    print(f"\n✅ 找到 {len(obstacles)} 個障礙物")
    print(f"✅ 找到 {len(boxes)} 個箱子")
    
    print("\n" + "="*60)
    print("🔍 搜尋包含 'fork', 'lift', 'vehicle', 'agv' 的物件...")
    print("="*60)
    
    # 搜尋包含關鍵字的物件
    keywords = ["fork", "lift", "vehicle", "agv"]
    found_objects = []
    
    for keyword in keywords:
        print(f"\n🔎 搜尋關鍵字: '{keyword}'")
        keyword_paths = traverse_stage_tree(warehouse_prim, depth=0, max_depth=15, keyword=keyword)
        found_objects.extend(keyword_paths)
    
    # 去重
    found_objects = list(set(found_objects))
    
    if found_objects:
        print(f"\n✅ 找到 {len(found_objects)} 個可能相關的物件：")
        for i, path in enumerate(found_objects, 1):
            print(f"  {i}. {path}")
    else:
        print("\n⚠️ 未找到包含關鍵字的物件")
        print("📋 以下是所有物件的路徑，請手動查找：")
        for path in all_paths[:50]:  # 只顯示前50個，避免輸出過多
            print(f"  - {path}")
        if len(all_paths) > 50:
            print(f"  ... 還有 {len(all_paths) - 50} 個物件未顯示")
else:
    print("❌ 無法找到 /World/Warehouse，請確認 USD 場景已正確載入")

# 嘗試常見的 forklift 路徑
possible_forklift_paths = [
    "/World/Warehouse/forklift",
    "/World/Warehouse/Forklift",
    "/World/forklift",
    "/World/Forklift",
    "/World/Warehouse/vehicle",
    "/World/Warehouse/Vehicle",
]

forklift_path = None
forklift_prim = None

# 檢查路徑是否為場景層級（不應該移動這些）
def is_scene_level(path_str):
    """檢查路徑是否為場景層級（World, Warehouse 等）"""
    path_lower = path_str.lower()
    return path_str in ["/World", "/World/Warehouse"] or path_lower.endswith("/world") or path_lower.endswith("/warehouse")

# 如果有找到的物件，優先使用（往上抓到車的根節點）
if found_objects:
    # 優先選擇名稱最符合的
    for path in found_objects:
        prim = stage.GetPrimAtPath(path)
        if prim.IsValid():
            root_prim = ascend_to_keyword_root(prim, keywords=["fork", "lift", "vehicle", "agv"])
            root_path = str(root_prim.GetPath())
            
            # 如果根節點是場景層級，使用原始節點
            if is_scene_level(root_path):
                print(f"⚠️ 根節點 {root_path} 是場景層級，使用原始節點: {path}")
                forklift_path = path
                forklift_prim = prim
            else:
                forklift_path = root_path
                forklift_prim = root_prim
                print(f"\n✅ 自動選擇 Forklift 根節點: {forklift_path}")
            break

# 如果還沒找到，嘗試常見路徑（同樣往上抓根節點）
if forklift_path is None:
    for path in possible_forklift_paths:
        prim = stage.GetPrimAtPath(path)
        if prim.IsValid():
            root_prim = ascend_to_keyword_root(prim, keywords=["fork", "lift", "vehicle", "agv"])
            root_path = str(root_prim.GetPath())
            
            # 如果根節點是場景層級，使用原始節點
            if is_scene_level(root_path):
                print(f"⚠️ 根節點 {root_path} 是場景層級，使用原始節點: {path}")
                forklift_path = path
                forklift_prim = prim
            else:
                forklift_path = root_path
                forklift_prim = root_prim
                print(f"✅ 找到 Forklift 根節點: {forklift_path}")
            break

# 如果還是找不到，使用第一個找到的物件（如果有的話，並抓根節點）
if forklift_path is None and found_objects:
    prim = stage.GetPrimAtPath(found_objects[0])
    if prim.IsValid():
        root_prim = ascend_to_keyword_root(prim, keywords=["fork", "lift", "vehicle", "agv"])
        root_path = str(root_prim.GetPath())
        
        # 如果根節點是場景層級，使用原始節點
        if is_scene_level(root_path):
            print(f"⚠️ 根節點 {root_path} 是場景層級，使用原始節點: {found_objects[0]}")
            forklift_path = found_objects[0]
            forklift_prim = prim
        else:
            forklift_path = root_path
            forklift_prim = root_prim
            print(f"⚠️ 使用第一個找到的物件（根節點）: {forklift_path}")

if forklift_path is None:
    print("\n⚠️ 警告：找不到 Forklift 物件")
    print("請從上面的列表中選擇正確的路徑，並手動設定 forklift_path 變數")
    print("例如：forklift_path = \"/World/Warehouse/你的forklift路徑\"")
    # 如果找不到，使用一個預設路徑（用戶需要修改）
    forklift_path = "/World/Warehouse/forklift"  # 🔺 請改成實際路徑
    forklift_prim = stage.GetPrimAtPath(forklift_path)
    if not forklift_prim.IsValid():
        print(f"❌ 錯誤：預設路徑 {forklift_path} 不存在！")
        print("請檢查上面的列表並更新 forklift_path")

# 取得 Forklift 的 Xform
if forklift_prim and forklift_prim.IsValid():
    forklift_xform = UsdGeom.Xformable(forklift_prim)
    
    # 確保有 translate 和 rotate 操作
    # 檢查是否已有 translate 操作
    translate_op = None
    rotate_op = None
    
    xform_ops = forklift_xform.GetOrderedXformOps()
    for op in xform_ops:
        if op.GetOpType() == UsdGeom.XformOp.TypeTranslate:
            translate_op = op
        elif op.GetOpType() == UsdGeom.XformOp.TypeRotateZ:
            rotate_op = op
    
    # 如果沒有 translate 操作，創建一個
    if translate_op is None:
        translate_op = forklift_xform.AddTranslateOp()
    
    # 如果沒有 rotate 操作，創建一個（用於車輛朝向）
    if rotate_op is None:
        rotate_op = forklift_xform.AddRotateZOp()
    
    # 起點：機器當前位置
    start_pos = (2.61797, 9.66071, -0.04722)  # 使用實際的 z 座標（y-0.5）
    translate_op.Set(start_pos)
    rotate_op.Set(0.0)  # 初始朝向（0度 = 朝向 +X 方向）
    
    # 📦 找到需要跟著車子移動的貨物物件（這些物件不是車子的子物件，需要手動同步移動）
    cargo_objects = [
        "Box_40756", "Box_40782", "Box_40754", "Box_40784", 
        "Box_40810", "Box_40812", "SM_PaletteA_424"
    ]
    
    # 存儲貨物物件的資訊：路徑、Prim、Xform、TranslateOp、相對於車子的偏移量
    cargo_list = []  # 格式: [{"name": name, "path": path, "prim": prim, "xform": xform, "translate_op": op, "offset": (dx, dy, dz)}, ...]
    
    print(f"\n🔍 搜尋需要跟著車子移動的貨物物件...")
    # 獲取車子的初始世界位置和角度
    forklift_initial_world_pos = get_world_position(forklift_prim)
    forklift_initial_angle = rotate_op.Get() if rotate_op else 0.0  # 初始角度（度）
    
    if forklift_initial_world_pos:
        # 在整個 Warehouse 場景中搜索貨物物件
        all_paths = traverse_stage_tree(warehouse_prim, depth=0, max_depth=15, keyword=None)
        
        for obj_name in cargo_objects:
            found_path = None
            # 搜索物件路徑（可能包含這個名稱）
            for path in all_paths:
                if obj_name in path:
                    found_path = path
                    break
            
            if found_path:
                cargo_prim = stage.GetPrimAtPath(found_path)
                if cargo_prim.IsValid():
                    cargo_xform = UsdGeom.Xformable(cargo_prim)
                    if cargo_xform:
                        # 獲取貨物的初始世界位置
                        cargo_initial_world_pos = get_world_position(cargo_prim)
                        
                        if cargo_initial_world_pos:
                            # 計算相對於車子的世界座標偏移量
                            world_offset = (
                                cargo_initial_world_pos[0] - forklift_initial_world_pos[0],
                                cargo_initial_world_pos[1] - forklift_initial_world_pos[1],
                                cargo_initial_world_pos[2] - forklift_initial_world_pos[2]
                            )
                            
                            # ✅ 將世界座標偏移轉換為車子本地座標系偏移（考慮車子初始角度）
                            # 這樣當車子旋轉時，貨物也會跟著旋轉
                            initial_angle_rad = math.radians(-forklift_initial_angle)  # 負號因為是逆變換
                            local_offset_x = world_offset[0] * math.cos(initial_angle_rad) - world_offset[1] * math.sin(initial_angle_rad)
                            local_offset_y = world_offset[0] * math.sin(initial_angle_rad) + world_offset[1] * math.cos(initial_angle_rad)
                            local_offset = (local_offset_x, local_offset_y, world_offset[2])
                            
                            # 獲取或創建 translate 和 rotate 操作
                            cargo_translate_op = None
                            cargo_rotate_op = None
                            xform_ops = cargo_xform.GetOrderedXformOps()
                            for op in xform_ops:
                                if op.GetOpType() == UsdGeom.XformOp.TypeTranslate:
                                    cargo_translate_op = op
                                elif op.GetOpType() == UsdGeom.XformOp.TypeRotateZ:
                                    cargo_rotate_op = op
                            
                            if cargo_translate_op is None:
                                cargo_translate_op = cargo_xform.AddTranslateOp()
                            
                            # ✅ 為貨物添加旋轉操作，使其能跟隨車子旋轉
                            if cargo_rotate_op is None:
                                cargo_rotate_op = cargo_xform.AddRotateZOp()
                            
                            # 設置貨物的初始旋轉角度（與車子一致）
                            if cargo_rotate_op:
                                cargo_rotate_op.Set(forklift_initial_angle)
                            
                            cargo_list.append({
                                "name": obj_name,
                                "path": found_path,
                                "prim": cargo_prim,
                                "xform": cargo_xform,
                                "translate_op": cargo_translate_op,
                                "rotate_op": cargo_rotate_op,  # 添加旋轉操作
                                "local_offset": local_offset,  # 本地座標系偏移（會隨車子旋轉）
                                "initial_local_offset": local_offset,  # 保存初始偏移量，用於重置
                                "initial_world_pos": cargo_initial_world_pos,
                                "initial_angle": forklift_initial_angle  # 保存初始角度
                            })
                            print(f"  ✅ 找到 {obj_name} @ {found_path}，本地偏移: {local_offset}")
                else:
                    print(f"  ⚠️ {obj_name} @ {found_path} 不是有效的 Xformable")
            else:
                print(f"  ℹ️ 未找到 {obj_name}（可能不存在於場景中）")
        
        if cargo_list:
            print(f"✅ 找到 {len(cargo_list)} 個貨物物件，將在車子移動時同步移動它們")
        else:
            print(f"ℹ️ 未找到需要同步移動的貨物物件")
    else:
        print(f"⚠️ 無法獲取車子的初始世界位置，無法計算貨物偏移量")
    
    print(f"✅ Forklift 設置在起始位置: {start_pos}")
else:
    print("❌ 無法取得 Forklift 物件，請檢查路徑")
    forklift_xform = None
    translate_op = None
    rotate_op = None
    cargo_list = []  # 初始化為空列表

# 確保場景更新
simulation_app.update()

# -----------------------------------------------------
# 避障相關函數
# -----------------------------------------------------
def check_obstacle_ahead(current_pos, direction_angle, obstacles, look_ahead_distance=1.5, safety_radius=0.8):
    """
    檢查前方是否有障礙物
    
    Args:
        current_pos: 當前位置 (x, y, z)
        direction_angle: 朝向角度（度）
        obstacles: 障礙物列表
        look_ahead_distance: 向前看的距離（米）
        safety_radius: 安全半徑（米）
    
    Returns:
        最近的障礙物距離，如果沒有則返回 None
    """
    x, y, z = current_pos
    angle_rad = math.radians(direction_angle)
    
    # 計算前方檢查點
    check_x = x + look_ahead_distance * math.cos(angle_rad)
    check_y = y + look_ahead_distance * math.sin(angle_rad)
    
    min_distance = None
    closest_obstacle = None
    
    for obstacle in obstacles:
        if not obstacle.get("position"):
            continue
        
        obs_x, obs_y, obs_z = obstacle["position"]
        
        # 只檢查 z 座標相近的障礙物（同一層）
        if abs(obs_z - z) > 1.0:
            continue
        
        # 計算障礙物到檢查點的距離
        dist_to_check = math.hypot(obs_x - check_x, obs_y - check_y)
        
        # 如果障礙物在安全半徑內
        if dist_to_check < safety_radius:
            # 計算障礙物到車輛的距離
            dist_to_vehicle = math.hypot(obs_x - x, obs_y - y)
            
            if min_distance is None or dist_to_vehicle < min_distance:
                min_distance = dist_to_vehicle
                closest_obstacle = obstacle
    
    return min_distance, closest_obstacle

def calculate_avoidance_waypoint(current_pos, target_pos, obstacle_pos, avoidance_distance=2.0):
    """
    計算繞過障礙物的路徑點（waypoint）
    
    Args:
        current_pos: 當前位置 (x, y, z)
        target_pos: 目標位置 (x, y, z)
        obstacle_pos: 障礙物位置 (x, y, z)
        avoidance_distance: 繞行距離（米）
    
    Returns:
        繞行路徑點 (x, y, z) 或 None（如果不需要繞行）
    """
    x, y, _ = current_pos
    obs_x, obs_y, _ = obstacle_pos
    target_x, target_y, _ = target_pos
    
    # 計算從當前位置到目標的向量
    to_target_dx = target_x - x
    to_target_dy = target_y - y
    to_target_dist = math.hypot(to_target_dx, to_target_dy)
    
    if to_target_dist < 0.01:
        return None
    
    # 計算從當前位置到障礙物的向量
    to_obstacle_dx = obs_x - x
    to_obstacle_dy = obs_y - y
    to_obstacle_dist = math.hypot(to_obstacle_dx, to_obstacle_dy)
    
    # 計算障礙物在路徑上的投影點
    # 使用點積計算投影
    dot_product = to_obstacle_dx * to_target_dx + to_obstacle_dy * to_target_dy
    projection_t = dot_product / (to_target_dist * to_target_dist)
    
    # 如果投影點不在路徑上，不需要繞行
    if projection_t < 0 or projection_t > 1:
        return None
    
    # 計算投影點位置
    proj_x = x + projection_t * to_target_dx
    proj_y = y + projection_t * to_target_dy
    
    # 計算從投影點到障礙物的距離
    dist_to_obstacle = math.hypot(obs_x - proj_x, obs_y - proj_y)
    
    # 如果障礙物不在路徑上（距離太遠），不需要繞行
    if dist_to_obstacle > avoidance_distance:
        return None
    
    # 計算垂直於路徑的方向（用於繞行）
    # 路徑方向的垂直向量
    perp_dx = -to_target_dy / to_target_dist
    perp_dy = to_target_dx / to_target_dist
    
    # 決定向左還是向右繞
    # 使用叉積判斷障礙物在路徑的左側還是右側
    cross_product = to_obstacle_dx * to_target_dy - to_obstacle_dy * to_target_dx
    
    # 如果障礙物在左側，向右繞（使用正方向）
    # 如果障礙物在右側，向左繞（使用負方向）
    if cross_product > 0:
        # 障礙物在左側，向右繞
        waypoint_x = obs_x + avoidance_distance * perp_dx
        waypoint_y = obs_y + avoidance_distance * perp_dy
    else:
        # 障礙物在右側，向左繞
        waypoint_x = obs_x - avoidance_distance * perp_dx
        waypoint_y = obs_y - avoidance_distance * perp_dy
    
    return (waypoint_x, waypoint_y, current_pos[2])

def find_path_around_obstacles(current_pos, target_pos, obstacles, avoidance_distance=2.0, detection_distance=3.0):
    """
    尋找繞過障礙物的路徑
    
    Args:
        current_pos: 當前位置
        target_pos: 目標位置
        obstacles: 障礙物列表
        avoidance_distance: 繞行距離（米）
        detection_distance: 檢測距離（米）- 3公尺
    
    Returns:
        路徑點列表（包括中間點和最終目標）
    """
    path = [target_pos]  # 默認直接到目標
    
    # 檢查路徑上是否有障礙物（在3公尺以內）
    blocking_obstacles = []
    
    for obstacle in obstacles:
        if not obstacle.get("position"):
            continue
        
        obstacle_pos = obstacle["position"]
        
        # 計算障礙物到車輛的距離
        x, y, _ = current_pos
        obs_x, obs_y, _ = obstacle_pos
        dist_to_obstacle = math.hypot(obs_x - x, obs_y - y)
        
        # 只考慮3公尺以內的障礙物
        if dist_to_obstacle > detection_distance:
            continue
        
        # 計算障礙物到路徑的距離
        target_x, target_y, _ = target_pos
        
        # 計算路徑向量
        path_dx = target_x - x
        path_dy = target_y - y
        path_dist = math.hypot(path_dx, path_dy)
        
        if path_dist < 0.01:
            continue
        
        # 計算障礙物到起點的向量
        to_obstacle_dx = obs_x - x
        to_obstacle_dy = obs_y - y
        
        # 計算投影
        dot_product = to_obstacle_dx * path_dx + to_obstacle_dy * path_dy
        projection_t = dot_product / (path_dist * path_dist)
        
        # 如果障礙物在路徑上或路徑附近
        if 0 <= projection_t <= 1:
            proj_x = x + projection_t * path_dx
            proj_y = y + projection_t * path_dy
            dist_to_path = math.hypot(obs_x - proj_x, obs_y - proj_y)
            
            # 如果障礙物距離路徑小於繞行距離，需要繞行
            if dist_to_path < avoidance_distance:
                blocking_obstacles.append((dist_to_obstacle, obstacle))
    
    # 按距離排序，處理最近的障礙物
    blocking_obstacles.sort(key=lambda x: x[0])
    
    # 為最近的障礙物計算繞行點
    if blocking_obstacles:
        _, closest_obstacle = blocking_obstacles[0]
        waypoint = calculate_avoidance_waypoint(
            current_pos, target_pos, closest_obstacle["position"], avoidance_distance
        )
        if waypoint:
            # 插入繞行點（在目標之前）
            path.insert(0, waypoint)
            print(f"🚫 檢測到障礙物 '{closest_obstacle['name']}'，計算繞行路徑點: ({waypoint[0]:.2f}, {waypoint[1]:.2f})")
    
    return path

# -----------------------------------------------------
# 將當前叉車位姿送到本機的 dashboard_server（前端會輪詢 /api/pose 即時顯示）
# -----------------------------------------------------
def send_pose_to_dashboard(current_pos, current_yaw_deg):
    """
    將目前叉車的位置與朝向 POST 到 http://127.0.0.1:8000/api/pose
    - 這個呼叫是「盡力而為」，若前端後端沒開，不會讓 Isaac Sim 腳本當掉。
    """
    if not current_pos:
        return

    x, y, _ = current_pos
    payload = {"x": float(x), "y": float(y), "yaw": float(current_yaw_deg)}

    try:
        requests.post("http://127.0.0.1:8000/api/pose", json=payload, timeout=0.1)
    except Exception:
        # 如果後端沒啟動或連線失敗，忽略即可
        pass

# -----------------------------------------------------
# 9️⃣ Forklift 移動至準備送出區前方（考慮車輛實際移動和避障）
# -----------------------------------------------------
if forklift_xform is None or translate_op is None:
    print("❌ Forklift 未正確初始化，無法移動")
else:
    # 👉 從後端讀取指令
    command_destination = ""
    command_raw = ""
    try:
        response = requests.get("http://127.0.0.1:8000/api/command", timeout=0.5)
        if response.status_code == 200:
            cmd_data = response.json()
            command_destination = cmd_data.get("destination", "")
            command_raw = cmd_data.get("raw", "")
            print(f"📋 收到指令：目的地 = {command_destination}, 原始指令 = {command_raw}")
    except Exception:
        pass  # 如果後端還沒啟動或沒有指令，使用預設路線
    
    # 👉 目標位置設定
    # 以「準備送出區中心」為基準，往 +X 方向 0.55037 公尺（1.05037 - 0.5），Y 方向 -0.2 公尺
    # 你之後如果要微調，只要改這個偏移量就好（例如 0.8、1.5 等）。
    target_pos = (
        zone_prepare_center[0] + 0.55037 - 0.5,  # x-0.5
        zone_prepare_center[1] - 0.2,
        start_pos[2]
    )
    # 最終希望車頭朝向的角度（度），可依實際需求調整
    target_final_yaw = 180.0
    
    dx = target_pos[0] - start_pos[0]
    dy = target_pos[1] - start_pos[1]
    distance = math.hypot(dx, dy)
    
    # 車輛移動參數
    max_speed = 1.5  # 最大速度 (m/s)
    max_angular_velocity = 90.0  # 最大角速度 (度/秒)
    obstacle_detection_distance = 4.0  # 檢測障礙物的距離（4公尺，增加檢測範圍確保安全）
    avoidance_distance = 2.5  # 繞行距離（米，增加繞行距離讓路線更安全）
    safety_radius = 1.2  # 安全半徑（增加安全邊距）

    # ✅ 到目標附近就停車的條件（不再一直為了調整角度繞圈）
    #    你可以把這個數值調大一點，讓車子在離 B 區 / 目標區「更遠一點」就停下來，
    #    例如改成 1.0 或 1.5，避免靠太近時把櫃子當成障礙物一直閃避。
    stop_distance = 1.0          # 與目標距離小於 1.0 m 就視為到達
    max_run_time = 180.0         # 最長行駛時間（秒），避免極端情況一直跑
    
    print(f"起點位置: {start_pos}")
    print(f"目標位置（B 區最終停車位置）: {target_pos}")
    print(f"距離: {distance:.2f} m")
    print(f"最大速度: {max_speed} m/s")
    print(f"障礙物數量: {len(obstacles)}")
    print(f"障礙物檢測距離: {obstacle_detection_distance} m")
    
    # ✅ 等待收到 API 開始信號才開始移動
    print("\n" + "="*60)
    print("⏸️  等待網頁端發送開始指令...")
    print("="*60)
    
    # 等待場景穩定
    for _ in range(10):
        simulation_app.update()
    
    # 等待開始信號（輪詢後端 API），同時讀取指令
    backend_connected = False  # 追蹤後端是否已連接
    poll_interval = 2.0  # 初始輪詢間隔（秒）- 後端未啟動時使用較長間隔
    last_poll_time = time.time()  # 上次輪詢時間
    
    while simulation_app.is_running():
        current_time = time.time()
        
        # 使用計時器控制輪詢頻率，而不是阻塞主線程
        if current_time - last_poll_time >= poll_interval:
            last_poll_time = current_time
            
            try:
                # 讀取指令
                cmd_response = requests.get("http://127.0.0.1:8000/api/command", timeout=0.5)
                if cmd_response.status_code == 200:
                    # 後端已連接，使用較短的輪詢間隔
                    if not backend_connected:
                        backend_connected = True
                        poll_interval = 0.5  # 後端已連接，改為 0.5 秒檢查一次
                        print("✅ 後端伺服器已連接")
                    
                    cmd_data = cmd_response.json()
                    new_dest = cmd_data.get("destination", "")
                    new_raw = cmd_data.get("raw", "")
                    if new_dest != command_destination or new_raw != command_raw:
                        command_destination = new_dest
                        command_raw = new_raw
                        print(f"📋 更新指令：目的地 = {command_destination}, 原始指令 = {command_raw}")
                
                # 檢查開始信號
                response = requests.get("http://127.0.0.1:8000/api/start", timeout=0.5)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("started", False):
                        print("✅ 收到 API 開始指令，開始執行...")
                        break
            except Exception:
                # 如果後端還沒啟動，使用較長的輪詢間隔，減少不必要的請求
                if backend_connected:
                    backend_connected = False
                    poll_interval = 2.0  # 後端斷線，改回較長間隔
                    print("⚠️  後端伺服器未連接，等待中...")
        
        # 每幀都更新，確保視角可以正常響應
        simulation_app.update()
    
    # 裝載參數
    load_forward_distance = 0.5  # 往前移動的距離（米）
    load_backward_extra_distance = 1  # 回到起始位置後再往後移動的距離（米），可以是整數或浮點數
    load_speed = 1.0  # 裝載時的速度（較慢，更精確）
    load_target_pos = (
        start_pos[0] + load_forward_distance,
        start_pos[1],
        start_pos[2]
    )
    
    # 最終起始位置（回到起始位置後再往後移動，-X方向）
    final_start_pos = (
        start_pos[0] - load_backward_extra_distance,  # 往後移動（-X方向）
        start_pos[1],
        start_pos[2]
    )
    
    # 計算初始路徑（保存用於重置，使用最終起始位置作為起點）
    initial_path_waypoints = find_path_around_obstacles(
        final_start_pos, target_pos, obstacles, avoidance_distance, obstacle_detection_distance
    )
    
    # ============================================================
    # ✅ 主循環：包含裝載階段和主要移動階段
    # ============================================================
    # 狀態：'loading_forward', 'loading_backward', 'main_moving'
    current_state = 'loading_forward'
    
    # 裝載階段變數
    load_start_time = None
    load_current_pos = None
    cargo_offset_recalculated = False
    
    # 倒退階段變數
    backup_start_time = None
    reached_start_pos = False  # 標記是否已到達起始位置
    
    # 主要移動階段變數
    main_start_time = None
    has_arrived = False
    current_angle = 0.0
    last_pos = start_pos
    last_frame_time = None
    last_path_update_time = None
    path_waypoints = None
    current_waypoint_index = 0
    current_waypoint = None
    
    # 初始化裝載階段
    print("\n" + "="*60)
    print("📦 開始裝載貨物階段：車子往前移動...")
    print("="*60)
    print(f"  起始位置: {start_pos}")
    print(f"  裝載目標位置: {load_target_pos}")
    print(f"  往前移動距離: {load_forward_distance} m")
    load_start_time = time.time()
    load_current_pos = start_pos
    cargo_offset_recalculated = False
    
    while simulation_app.is_running():
        current_frame_time = time.time()
        
        # ============================================================
        # 狀態：裝載階段 - 車子往前移動
        # ============================================================
        if current_state == 'loading_forward':
            if load_start_time is None:
                load_start_time = time.time()
                load_current_pos = start_pos
            
            delta_time = min(current_frame_time - load_start_time, 0.1)
            load_start_time = current_frame_time
            
            # 獲取當前位置
            load_current_pos = translate_op.Get()
            if not load_current_pos:
                load_current_pos = start_pos
            else:
                load_current_pos = tuple(load_current_pos)
            
            # 計算到目標的距離
            load_dx = load_target_pos[0] - load_current_pos[0]
            load_dy = load_target_pos[1] - load_current_pos[1]
            load_distance = math.hypot(load_dx, load_dy)
            
            # 如果到達目標，轉換到倒退階段
            if load_distance < 0.1:
                translate_op.Set(load_target_pos)
                print(f"  ✅ 到達裝載位置")
                
                # 等待一下，確保車子位置穩定
                for _ in range(10):
                    simulation_app.update()
                
                # 重新計算貨物相對於車子的偏移量
                if cargo_list and not cargo_offset_recalculated:
                    forklift_at_load_pos = load_target_pos
                    print(f"\n📦 重新計算貨物相對於車子的偏移量（車子位置: {forklift_at_load_pos}）...")
                    for cargo in cargo_list:
                        cargo_prim = cargo["prim"]
                        if cargo_prim.IsValid():
                            cargo_current_world_pos = get_world_position(cargo_prim)
                            if cargo_current_world_pos:
                                # 在第一次計算裝載偏移量時，initial_local_offset 已在初始化時保存
                                # 這裡不需要再次保存，直接使用即可
                                world_offset = (
                                    cargo_current_world_pos[0] - forklift_at_load_pos[0],
                                    cargo_current_world_pos[1] - forklift_at_load_pos[1],
                                    cargo_current_world_pos[2] - forklift_at_load_pos[2]
                                )
                                local_offset = (world_offset[0], world_offset[1], world_offset[2])
                                cargo["local_offset"] = local_offset
                                print(f"  ✅ {cargo['name']} 的相對偏移已更新: {local_offset}")
                    cargo_offset_recalculated = True
                
                # 轉換到倒退階段
                current_state = 'loading_backward'
                print("\n" + "="*60)
                print("🔙 開始倒退階段：車子回到起始位置...")
                print("="*60)
                backup_start_time = time.time()
                continue
            
            # 計算移動距離
            move_distance = min(load_speed * delta_time, load_distance)
            
            # 往前移動
            load_current_angle = 0.0
            angle_rad = math.radians(load_current_angle)
            new_x = load_current_pos[0] + move_distance * math.cos(angle_rad)
            new_y = load_current_pos[1] + move_distance * math.sin(angle_rad)
            new_pos = (new_x, new_y, start_pos[2])
            
            # 更新車子位置
            translate_op.Set(new_pos)
            if rotate_op:
                rotate_op.Set(load_current_angle)
            
            # 將目前位姿送到前端儀表板
            send_pose_to_dashboard(new_pos, load_current_angle)
            
            # ✅ 裝載階段：貨物不移動，保持在原地
            simulation_app.update()
            continue
        
        # ============================================================
        # 狀態：倒退階段 - 車子倒退回到起始位置
        # ============================================================
        elif current_state == 'loading_backward':
            if backup_start_time is None:
                backup_start_time = time.time()
            
            delta_time = min(current_frame_time - backup_start_time, 0.1)
            backup_start_time = current_frame_time
            
            # 獲取當前位置
            backup_current_pos = translate_op.Get()
            if not backup_current_pos:
                backup_current_pos = load_target_pos
            else:
                backup_current_pos = tuple(backup_current_pos)
            
            # 計算到起始位置的距離
            backup_dx = start_pos[0] - backup_current_pos[0]
            backup_dy = start_pos[1] - backup_current_pos[1]
            backup_distance = math.hypot(backup_dx, backup_dy)
            
            # 計算到最終起始位置的距離（如果已經在起始位置或之後）
            final_backup_dx = final_start_pos[0] - backup_current_pos[0]
            final_backup_dy = final_start_pos[1] - backup_current_pos[1]
            final_backup_distance = math.hypot(final_backup_dx, final_backup_dy)
            
            # 如果到達起始位置，先設置到起始位置，然後繼續往後移動
            if backup_distance < 0.1 and not reached_start_pos:
                translate_op.Set(start_pos)
                if rotate_op:
                    rotate_op.Set(0.0)
                
                # 確保貨物在起始位置
                if cargo_list:
                    for cargo in cargo_list:
                        cargo_prim = cargo["prim"]
                        cargo_translate_op = cargo["translate_op"]
                        cargo_rotate_op = cargo.get("rotate_op")
                        if cargo_prim.IsValid() and cargo_translate_op:
                            local_offset = cargo["local_offset"]
                            initial_cargo_world_pos = (
                                start_pos[0] + local_offset[0],
                                start_pos[1] + local_offset[1],
                                start_pos[2] + local_offset[2]
                            )
                            cargo_xform = cargo["xform"]
                            parent_prim = cargo_prim.GetParent()
                            if parent_prim and parent_prim.IsValid() and parent_prim != stage.GetPseudoRoot():
                                parent_xform = UsdGeom.Xformable(parent_prim)
                                if parent_xform:
                                    parent_world_transform = parent_xform.ComputeLocalToWorldTransform(Usd.TimeCode.Default())
                                    parent_inv_transform = parent_world_transform.GetInverse()
                                    world_point = Gf.Vec3d(initial_cargo_world_pos[0], initial_cargo_world_pos[1], initial_cargo_world_pos[2])
                                    local_point = parent_inv_transform.Transform(world_point)
                                    cargo_translate_op.Set((local_point[0], local_point[1], local_point[2]))
                            else:
                                cargo_translate_op.Set(initial_cargo_world_pos)
                            
                            # ✅ 同步更新貨物的旋轉角度，使其與車子一致（0度）
                            if cargo_rotate_op:
                                cargo_rotate_op.Set(0.0)
                
                print(f"  ✅ 已回到起始位置，繼續往後移動 {load_backward_extra_distance}m")
                reached_start_pos = True
                backup_current_pos = start_pos
                continue
            
            # 如果到達最終起始位置，轉換到主要移動階段
            # 檢查是否已經超過最終位置（X座標小於等於最終位置）
            if reached_start_pos and backup_current_pos[0] <= final_start_pos[0]:
                translate_op.Set(final_start_pos)
                if rotate_op:
                    rotate_op.Set(0.0)  # 確保角度是0度
                
                # 確保貨物在最終起始位置（初始角度0度）
                if cargo_list:
                    for cargo in cargo_list:
                        cargo_prim = cargo["prim"]
                        cargo_translate_op = cargo["translate_op"]
                        cargo_rotate_op = cargo.get("rotate_op")
                        if cargo_prim.IsValid() and cargo_translate_op:
                            local_offset = cargo["local_offset"]
                            # 初始時角度為0度
                            initial_cargo_world_pos = (
                                final_start_pos[0] + local_offset[0],
                                final_start_pos[1] + local_offset[1],
                                final_start_pos[2] + local_offset[2]
                            )
                            cargo_xform = cargo["xform"]
                            parent_prim = cargo_prim.GetParent()
                            if parent_prim and parent_prim.IsValid() and parent_prim != stage.GetPseudoRoot():
                                parent_xform = UsdGeom.Xformable(parent_prim)
                                if parent_xform:
                                    parent_world_transform = parent_xform.ComputeLocalToWorldTransform(Usd.TimeCode.Default())
                                    parent_inv_transform = parent_world_transform.GetInverse()
                                    world_point = Gf.Vec3d(initial_cargo_world_pos[0], initial_cargo_world_pos[1], initial_cargo_world_pos[2])
                                    local_point = parent_inv_transform.Transform(world_point)
                                    cargo_translate_op.Set((local_point[0], local_point[1], local_point[2]))
                            else:
                                cargo_translate_op.Set(initial_cargo_world_pos)
                            
                            # ✅ 同步更新貨物的旋轉角度，使其與車子一致（0度）
                            if cargo_rotate_op:
                                cargo_rotate_op.Set(0.0)
                
                print(f"  ✅ 已到達最終起始位置（往後 {load_backward_extra_distance}m），開始主要移動任務")
                
                # 等待一下，確保位置穩定
                for _ in range(10):
                    simulation_app.update()
                
                # 轉換到主要移動階段
                current_state = 'main_moving'
                print("\n" + "="*60)
                print("✅ 裝載完成，開始主要移動任務...")
                print("="*60)
                
                if path_waypoints is None:
                    path_waypoints = initial_path_waypoints.copy() if initial_path_waypoints else [target_pos]
                    current_waypoint_index = 0
                    current_waypoint = path_waypoints[current_waypoint_index] if path_waypoints else target_pos
                    print(f"📋 初始路徑包含 {len(path_waypoints)} 個路徑點")
                    for i, wp in enumerate(path_waypoints):
                        print(f"  路徑點 {i+1}: ({wp[0]:.2f}, {wp[1]:.2f})")
                
                main_start_time = time.time()
                last_frame_time = main_start_time
                last_path_update_time = main_start_time
                has_arrived = False
                current_angle = 0.0
                last_pos = final_start_pos  # 使用最終起始位置
                continue
            
            # 根據當前階段決定移動目標和距離
            if reached_start_pos:
                # 已經到達起始位置，繼續往後移動到最終起始位置
                # 計算到最終位置的 X 方向距離（絕對值）
                distance_to_final = abs(backup_current_pos[0] - final_start_pos[0])
                move_distance = min(load_speed * delta_time, distance_to_final)
            else:
                # 還沒到達起始位置，繼續倒退到起始位置
                move_distance = min(load_speed * delta_time, backup_distance)
            
            # 如果已經到達最終起始位置，不需要移動
            if reached_start_pos and backup_current_pos[0] <= final_start_pos[0]:
                continue
            
            # 倒退移動
            backup_current_angle = 0.0
            
            # 根據是否已到達起始位置決定移動方向
            if reached_start_pos:
                # 已經在起始位置，往後移動是 -X 方向
                new_x = backup_current_pos[0] - move_distance  # -X 方向
                new_y = backup_current_pos[1]
            else:
                # 還沒到達起始位置，倒退是朝向 -X 方向（180度）
                angle_rad = math.radians(backup_current_angle + 180.0)
                new_x = backup_current_pos[0] + move_distance * math.cos(angle_rad)
                new_y = backup_current_pos[1] + move_distance * math.sin(angle_rad)
            
            new_pos = (new_x, new_y, start_pos[2])
            
            # 更新車子位置
            translate_op.Set(new_pos)
            if rotate_op:
                rotate_op.Set(backup_current_angle)
            
            # 將目前位姿送到前端儀表板
            send_pose_to_dashboard(new_pos, backup_current_angle)
            
            # ✅ 倒退階段：貨物要跟著車子一起移動和旋轉
            if cargo_list:
                for cargo in cargo_list:
                    cargo_prim = cargo["prim"]
                    cargo_translate_op = cargo["translate_op"]
                    cargo_rotate_op = cargo.get("rotate_op")
                    if cargo_prim.IsValid() and cargo_translate_op:
                        angle_rad = math.radians(backup_current_angle)
                        local_offset = cargo["local_offset"]
                        rotated_offset_x = local_offset[0] * math.cos(angle_rad) - local_offset[1] * math.sin(angle_rad)
                        rotated_offset_y = local_offset[0] * math.sin(angle_rad) + local_offset[1] * math.cos(angle_rad)
                        new_cargo_world_pos = (
                            new_pos[0] + rotated_offset_x,
                            new_pos[1] + rotated_offset_y,
                            new_pos[2] + local_offset[2]
                        )
                        cargo_xform = cargo["xform"]
                        parent_prim = cargo_prim.GetParent()
                        if parent_prim and parent_prim.IsValid() and parent_prim != stage.GetPseudoRoot():
                            parent_xform = UsdGeom.Xformable(parent_prim)
                            if parent_xform:
                                parent_world_transform = parent_xform.ComputeLocalToWorldTransform(Usd.TimeCode.Default())
                                parent_inv_transform = parent_world_transform.GetInverse()
                                world_point = Gf.Vec3d(new_cargo_world_pos[0], new_cargo_world_pos[1], new_cargo_world_pos[2])
                                local_point = parent_inv_transform.Transform(world_point)
                                cargo_translate_op.Set((local_point[0], local_point[1], local_point[2]))
                        else:
                            cargo_translate_op.Set(new_cargo_world_pos)
                        
                        # ✅ 同步更新貨物的旋轉角度，使其與車子一致
                        if cargo_rotate_op:
                            cargo_rotate_op.Set(backup_current_angle)
            
            simulation_app.update()
            continue
        
        # ============================================================
        # 狀態：主要移動階段
        # ============================================================
        elif current_state == 'main_moving':
            if main_start_time is None:
                main_start_time = time.time()
                last_frame_time = main_start_time
                last_path_update_time = main_start_time
                if path_waypoints is None:
                    path_waypoints = initial_path_waypoints.copy() if initial_path_waypoints else [target_pos]
                    current_waypoint_index = 0
                    current_waypoint = path_waypoints[current_waypoint_index] if path_waypoints else target_pos
            
            elapsed = current_frame_time - main_start_time
            delta_time = current_frame_time - last_frame_time
            last_frame_time = current_frame_time
            
            # 限制 delta_time
            delta_time = min(delta_time, 0.1)
            
            # 獲取當前位置
            current_pos = translate_op.Get()
            if not current_pos:
                current_pos = start_pos
            else:
                current_pos = tuple(current_pos)
            
            # 每0.5秒檢查一次是否需要重新規劃路徑（如果接近障礙物）
            if current_frame_time - last_path_update_time > 0.5:
                # 檢查3公尺內是否有障礙物
                obstacle_distance, closest_obstacle = check_obstacle_ahead(
                    current_pos, current_angle, obstacles, 
                    look_ahead_distance=obstacle_detection_distance, 
                    safety_radius=safety_radius
                )
                
                # 如果距離障礙物3公尺以內，重新計算路徑
                if obstacle_distance is not None and obstacle_distance <= obstacle_detection_distance:
                    print(f"🚫 檢測到障礙物（距離: {obstacle_distance:.2f}m），重新規劃路徑...")
                    path_waypoints = find_path_around_obstacles(
                        current_pos, target_pos, obstacles, avoidance_distance, obstacle_detection_distance
                    )
                    current_waypoint_index = 0
                    current_waypoint = path_waypoints[current_waypoint_index] if path_waypoints else target_pos
                    print(f"📋 新的路徑包含 {len(path_waypoints)} 個路徑點")
                    for i, wp in enumerate(path_waypoints):
                        print(f"  路徑點 {i+1}: ({wp[0]:.2f}, {wp[1]:.2f})")
                    last_path_update_time = current_frame_time
            
            # 檢查是否到達當前路徑點
            waypoint_dx = current_waypoint[0] - current_pos[0]
            waypoint_dy = current_waypoint[1] - current_pos[1]
            waypoint_distance = math.hypot(waypoint_dx, waypoint_dy)
            
            # 如果到達當前路徑點，切換到下一個
            if waypoint_distance < 0.5:  # 0.5米範圍內視為到達
                if current_waypoint_index < len(path_waypoints) - 1:
                    current_waypoint_index += 1
                    current_waypoint = path_waypoints[current_waypoint_index]
                    print(f"✅ 到達路徑點 {current_waypoint_index+1}/{len(path_waypoints)}")
                elif waypoint_distance < 0.3:
                    # 到達最終目標
                    has_arrived = True
            
            # 計算到目標的最終距離（用於判斷是否需要調整朝向）
            final_dx_for_angle = target_pos[0] - current_pos[0]
            final_dy_for_angle = target_pos[1] - current_pos[1]
            final_distance_for_angle = math.hypot(final_dx_for_angle, final_dy_for_angle)
            
            # 計算到當前路徑點的方向
            # 如果接近目標（距離 < 1.5 米），開始調整朝向為你指定的最終角度（target_final_yaw）
            if final_distance_for_angle < 1.5:
                # 接近目標位置，調整朝向為最終希望的角度
                desired_angle = target_final_yaw
            elif waypoint_distance > 0.01:
                desired_angle = math.degrees(math.atan2(waypoint_dy, waypoint_dx))
            else:
                desired_angle = current_angle
            
            # 平滑旋轉到目標角度
            angle_diff = desired_angle - current_angle
            # 將角度差正規化到 [-180, 180]
            while angle_diff > 180:
                angle_diff -= 360
            while angle_diff < -180:
                angle_diff += 360
            
            # 限制角速度（基於實際幀時間）
            max_angle_change = max_angular_velocity * delta_time
            angle_change = max(-max_angle_change, min(max_angle_change, angle_diff))
            current_angle += angle_change
            
            # 計算移動距離（基於速度和時間）
            move_distance = max_speed * delta_time
            
            # 檢查前方是否有障礙物，如果有則減速或停止
            obstacle_distance, closest_obstacle = check_obstacle_ahead(
                current_pos, current_angle, obstacles, 
                look_ahead_distance=obstacle_detection_distance, 
                safety_radius=safety_radius
            )
            
            if obstacle_distance is not None:
                # 如果障礙物非常近（小於安全半徑），停止移動
                if obstacle_distance <= safety_radius:
                    move_distance = 0.0
                    print(f"⚠️  障礙物太近（{obstacle_distance:.2f}m），停止移動")
                # 如果障礙物在檢測距離內，減速到原速度的 50%
                elif obstacle_distance <= obstacle_detection_distance:
                    move_distance *= 0.5
                    print(f"🚫 前方障礙物距離: {obstacle_distance:.2f}m，減速至50%")
            
            # 計算新位置（沿當前朝向移動）
            angle_rad = math.radians(current_angle)
            new_x = current_pos[0] + move_distance * math.cos(angle_rad)
            new_y = current_pos[1] + move_distance * math.sin(angle_rad)
            new_pos = (new_x, new_y, start_pos[2])
            
            # ============================
            # ✅ 到達最終目標的判斷（位置 + 朝向）
            # ============================
            # 計算當前位置到目標的距離
            final_dx = target_pos[0] - current_pos[0]
            final_dy = target_pos[1] - current_pos[1]
            final_distance = math.hypot(final_dx, final_dy)
            
            # 計算最終應該面向的角度（使用上面設定的 target_final_yaw，例如 270°）
            final_yaw = target_final_yaw

            angle_error = abs(final_yaw - current_angle)
            while angle_error > 180:
                angle_error -= 360
            angle_error = abs(angle_error)

            # 👉【核心停止條件】
            # 只要「夠接近目標點」就停車，不再要求一定要把角度調到很精準，
            # 這樣可以避免因為在目標附近修正角度而一直繞圈。
            if final_distance < stop_distance:
                # ✅ 修復：使用當前位置，而不是直接跳到 target_pos，避免瞬移
                translate_op.Set(current_pos)
                if rotate_op:
                    rotate_op.Set(final_yaw)
                
                # 📦 同步移動貨物到最終位置（考慮車子最終角度）
                if cargo_list:
                    for cargo in cargo_list:
                        cargo_prim = cargo["prim"]
                        cargo_translate_op = cargo["translate_op"]
                        cargo_rotate_op = cargo.get("rotate_op")
                        
                        if cargo_prim.IsValid() and cargo_translate_op:
                            final_angle_rad = math.radians(final_yaw)
                            local_offset = cargo["local_offset"]
                            
                            rotated_offset_x = local_offset[0] * math.cos(final_angle_rad) - local_offset[1] * math.sin(final_angle_rad)
                            rotated_offset_y = local_offset[0] * math.sin(final_angle_rad) + local_offset[1] * math.cos(final_angle_rad)
                            
                            final_cargo_world_pos = (
                                current_pos[0] + rotated_offset_x,
                                current_pos[1] + rotated_offset_y,
                                current_pos[2] + local_offset[2]
                            )
                            
                            cargo_xform = cargo["xform"]
                            parent_prim = cargo_prim.GetParent()
                            
                            if parent_prim and parent_prim.IsValid() and parent_prim != stage.GetPseudoRoot():
                                parent_xform = UsdGeom.Xformable(parent_prim)
                                if parent_xform:
                                    parent_world_transform = parent_xform.ComputeLocalToWorldTransform(Usd.TimeCode.Default())
                                    parent_inv_transform = parent_world_transform.GetInverse()
                                    world_point = Gf.Vec3d(final_cargo_world_pos[0], final_cargo_world_pos[1], final_cargo_world_pos[2])
                                    local_point = parent_inv_transform.Transform(world_point)
                                    cargo_translate_op.Set((local_point[0], local_point[1], local_point[2]))
                            else:
                                cargo_translate_op.Set(final_cargo_world_pos)
                            
                            # ✅ 同步更新貨物的旋轉角度，使其與車子一致
                            if cargo_rotate_op:
                                cargo_rotate_op.Set(final_yaw)

                # 確保最後一次發送精確的位置和角度到網頁
                send_pose_to_dashboard(current_pos, final_yaw)
                
                print(f"🛑 Forklift 已完成任務：到達位置 ({current_pos[0]:.2f}, {current_pos[1]:.2f}, {current_pos[2]:.2f})，距離目標 {final_distance:.2f}m，停止移動")
                
                # 重置開始標誌，允許下次重新執行
                try:
                    reset_response = requests.post("http://127.0.0.1:8000/api/reset", timeout=1.0)
                    if reset_response.status_code == 200:
                        print("✅ 已重置執行標誌，可以重新執行")
                    else:
                        print(f"⚠️ 重置標誌失敗，狀態碼: {reset_response.status_code}")
                except Exception as e:
                    print(f"⚠️ 重置標誌時發生錯誤: {e}")
                
                simulation_app.update()
                continue

            # ⏱️ 安全機制：若超過最長運行時間，強制停車，避免無限繞圈
            if elapsed > max_run_time:
                translate_op.Set(current_pos)
                if rotate_op:
                    rotate_op.Set(current_angle)
                
                # 📦 同步移動貨物到最終位置（超時時，考慮車子當前角度）
                if cargo_list:
                    for cargo in cargo_list:
                        cargo_prim = cargo["prim"]
                        cargo_translate_op = cargo["translate_op"]
                        cargo_rotate_op = cargo.get("rotate_op")
                        
                        if cargo_prim.IsValid() and cargo_translate_op:
                            current_angle_rad = math.radians(current_angle)
                            local_offset = cargo["local_offset"]
                            
                            rotated_offset_x = local_offset[0] * math.cos(current_angle_rad) - local_offset[1] * math.sin(current_angle_rad)
                            rotated_offset_y = local_offset[0] * math.sin(current_angle_rad) + local_offset[1] * math.cos(current_angle_rad)
                            
                            final_cargo_world_pos = (
                                current_pos[0] + rotated_offset_x,
                                current_pos[1] + rotated_offset_y,
                                current_pos[2] + local_offset[2]
                            )
                            
                            cargo_xform = cargo["xform"]
                            parent_prim = cargo_prim.GetParent()
                            
                            if parent_prim and parent_prim.IsValid() and parent_prim != stage.GetPseudoRoot():
                                parent_xform = UsdGeom.Xformable(parent_prim)
                                if parent_xform:
                                    parent_world_transform = parent_xform.ComputeLocalToWorldTransform(Usd.TimeCode.Default())
                                    parent_inv_transform = parent_world_transform.GetInverse()
                                    world_point = Gf.Vec3d(final_cargo_world_pos[0], final_cargo_world_pos[1], final_cargo_world_pos[2])
                                    local_point = parent_inv_transform.Transform(world_point)
                                    cargo_translate_op.Set((local_point[0], local_point[1], local_point[2]))
                            else:
                                cargo_translate_op.Set(final_cargo_world_pos)
                            
                            # ✅ 同步更新貨物的旋轉角度，使其與車子一致
                            if cargo_rotate_op:
                                cargo_rotate_op.Set(current_angle)
                
                # 確保最後一次發送位置和角度到網頁
                send_pose_to_dashboard(current_pos, current_angle)
                
                print("⚠️ 超過最大運行時間，為安全起見強制停止移動")
                
                # 重置開始標誌，允許下次重新執行
                try:
                    reset_response = requests.post("http://127.0.0.1:8000/api/reset", timeout=1.0)
                    if reset_response.status_code == 200:
                        print("✅ 已重置執行標誌（超時重置）")
                except Exception as e:
                    print(f"⚠️ 重置標誌時發生錯誤: {e}")
                
                simulation_app.update()
                continue
            
            # 更新 Forklift 位置和旋轉
            translate_op.Set(new_pos)
            if rotate_op:
                rotate_op.Set(current_angle)
            
            # 將目前位姿送到前端儀表板
            # 如果接近目標，使用目標角度而不是當前角度，確保網頁顯示的角度與 Isaac Sim 一致
            if final_distance < 1.5:
                send_pose_to_dashboard(new_pos, final_yaw)
            else:
                send_pose_to_dashboard(new_pos, current_angle)
            
            # 📦 同步移動貨物物件（讓它們跟著車子一起移動和旋轉）
            if cargo_list:
                for cargo in cargo_list:
                    cargo_prim = cargo["prim"]
                    cargo_translate_op = cargo["translate_op"]
                    cargo_rotate_op = cargo.get("rotate_op")
                    
                    if cargo_prim.IsValid() and cargo_translate_op:
                        angle_rad = math.radians(current_angle)
                        local_offset = cargo["local_offset"]
                        
                        rotated_offset_x = local_offset[0] * math.cos(angle_rad) - local_offset[1] * math.sin(angle_rad)
                        rotated_offset_y = local_offset[0] * math.sin(angle_rad) + local_offset[1] * math.cos(angle_rad)
                        
                        new_cargo_world_pos = (
                            new_pos[0] + rotated_offset_x,
                            new_pos[1] + rotated_offset_y,
                            new_pos[2] + local_offset[2]
                        )
                        
                        cargo_xform = cargo["xform"]
                        parent_prim = cargo_prim.GetParent()
                        
                        if parent_prim and parent_prim.IsValid() and parent_prim != stage.GetPseudoRoot():
                            parent_xform = UsdGeom.Xformable(parent_prim)
                            if parent_xform:
                                parent_world_transform = parent_xform.ComputeLocalToWorldTransform(Usd.TimeCode.Default())
                                parent_inv_transform = parent_world_transform.GetInverse()
                                world_point = Gf.Vec3d(new_cargo_world_pos[0], new_cargo_world_pos[1], new_cargo_world_pos[2])
                                local_point = parent_inv_transform.Transform(world_point)
                                cargo_translate_op.Set((local_point[0], local_point[1], local_point[2]))
                        else:
                            cargo_translate_op.Set(new_cargo_world_pos)
                        
                        # ✅ 同步更新貨物的旋轉角度，使其與車子一致（融為一體）
                        if cargo_rotate_op:
                            cargo_rotate_op.Set(current_angle)
            
            # 每 30 幀打印一次位置（約 1 秒）
            if int(elapsed * 30) % 30 == 0 and not has_arrived:
                obstacle_info = ""
                if obstacle_distance is not None and obstacle_distance <= obstacle_detection_distance:
                    obstacle_info = f", 🚫 前方障礙物距離: {obstacle_distance:.2f}m"
                waypoint_info = f", 路徑點: {current_waypoint_index+1}/{len(path_waypoints)}"
                print(f"Forklift 位置: ({new_x:.2f}, {new_y:.2f}, {start_pos[2]:.2f}), "
                      f"朝向: {current_angle:.1f}°, 距離目標: {final_distance:.2f}m{waypoint_info}{obstacle_info}")
            
            if has_arrived:
                print(f"✅ Forklift 已到達目標位置: ({new_x:.2f}, {new_y:.2f}, {start_pos[2]:.2f})")
                simulation_app.update()
                continue
            
            last_pos = new_pos
            simulation_app.update()
            continue

# -----------------------------------------------------
# 結束前讓視窗保持開啟，直到使用者自行關閉 Isaac Sim
# -----------------------------------------------------
print("\n✅ 任務結束，模擬仍在執行中。")
print("👉 如果要關閉，請手動關掉 Isaac Sim 視窗或在終端機按 Ctrl+C。")

# 持續更新畫面，直到使用者關閉視窗（simulation_app.is_running() 變為 False）
while simulation_app.is_running():
    simulation_app.update()

simulation_app.close()
print("Simulation closed")
