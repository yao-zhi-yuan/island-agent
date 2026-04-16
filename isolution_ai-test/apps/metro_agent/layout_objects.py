import math

def layout_objects_inline(length, spacing=8, y=0, z=0):
    """Generate inline layout of objects along the length with given spacing.
    左右对称排列物体, 间距spacing, 总长度length，返回物体位置列表
    关于线的中心点 (length/2) 对称排列
    """
    positions = []
    num_objects = int(length // spacing)
    center = length / 2
    # 计算总宽度（所有物体占据的空间）
    total_width = num_objects * spacing
    # 起始位置（关于中心对称）
    start_x = center - total_width / 2
    
    for i in range(num_objects):
        x_pos = start_x + (i + 0.5) * spacing
        positions.append({"x": x_pos, "y": y, "z": z})
    return positions


def layout_pillar_pos_in_y(y_min, y_max, spacing=8)->list[float]:
    """Generate pillar positions along the width with given spacing.
    关于宽度的中心点 (width/2) 对称排列
    """
    positions = []
    distance = y_max - y_min
    num_pillars = int(distance // spacing)
    center = (y_max + y_min) / 2
    # 计算总宽度（所有物体占据的空间）
    total_width = num_pillars * spacing
    # 起始位置（关于中心对称）
    start_y = center - total_width / 2
    
    for i in range(num_pillars):
        y_pos = start_y + (i + 0.5) * spacing
        positions.append(y_pos)
    return positions

def layout_grid_objects(x_min, x_max, y_min, y_max, spacing_x=8, spacing_y=8, z=0, as_matrix=False):
    """Generate grid layout of objects within given rectangular area with specified spacings.
    在指定的矩形区域内对称排列物体
    关于矩形区域的中心点对称排列
    
    Args:
        x_min: 矩形区域x方向最小值
        x_max: 矩形区域x方向最大值
        y_min: 矩形区域y方向最小值
        y_max: 矩形区域y方向最大值
        spacing_x: x方向间距
        spacing_y: y方向间距
        z: z坐标
        as_matrix: 是否返回二维矩阵格式
            - False: 返回一维列表 [{"x": ..., "y": ..., "z": ...}, ...]
            - True: 返回二维矩阵 [[row1_positions], [row2_positions], ...]
    
    Returns:
        一维列表或二维矩阵，取决于as_matrix参数
    """
    length = x_max - x_min
    width = y_max - y_min
    
    num_x = int(length // spacing_x)
    num_y = int(width // spacing_y)
    
    center_x = (x_min + x_max) / 2
    center_y = (y_min + y_max) / 2
    
    # 计算总宽度（所有物体占据的空间）
    total_width_x = num_x * spacing_x
    total_width_y = num_y * spacing_y
    
    # 起始位置（关于中心对称）
    start_x = center_x - total_width_x / 2
    start_y = center_y - total_width_y / 2
    
    if as_matrix:
        # 返回二维矩阵: grid[i][j] 表示第i行第j列的位置
        grid = []
        for i in range(num_x):
            x_pos = start_x + (i + 0.5) * spacing_x
            row = []
            for j in range(num_y):
                y_pos = start_y + (j + 0.5) * spacing_y
                row.append({"x": x_pos, "y": y_pos, "z": z})
            grid.append(row)
        return grid
    else:
        # 返回一维列表（扁平化）
        positions = []
        for i in range(num_x):
            x_pos = start_x + (i + 0.5) * spacing_x
            for j in range(num_y):
                y_pos = start_y + (j + 0.5) * spacing_y
                positions.append({"x": x_pos, "y": y_pos, "z": z})
        return positions
def layout_grid_simple(x_min, x_max, y_min, y_max, spacing_x=8, spacing_y=8, z=0):
    """Generate simple grid layout of objects within given rectangular area.
    Ensures at least 1x1 placement if the area exists (x_max >= x_min and y_max >= y_min).
    Always returns a flat list of positions.
    """
    length = x_max - x_min
    width = y_max - y_min
    
    # If the area is negative, return empty list
    if length < 0 or width < 0:
        return []

    # Calculate number of objects, ensuring at least 1
    # Adding a small epsilon 1e-6 to handle floating point precision issues
    num_x = int((length + 1e-6) // spacing_x) + 1
    num_y = int((width + 1e-6) // spacing_y) + 1
    
    center_x = (x_min + x_max) / 2
    center_y = (y_min + y_max) / 2
    
    # Total span covered by objects
    total_spread_x = (num_x - 1) * spacing_x
    total_spread_y = (num_y - 1) * spacing_y
    
    # Starting position for symmetric layout
    start_x = center_x - total_spread_x / 2
    start_y = center_y - total_spread_y / 2
    
    positions = []
    for i in range(num_x):
        x_pos = start_x + i * spacing_x
        for j in range(num_y):
            y_pos = start_y + j * spacing_y
            positions.append({"x": x_pos, "y": y_pos, "z": z})
            
    return positions

def layout_pillars_grid(x_min, x_max, y_min, y_max, spacing=8, margin=None, min_rows=2, spacing_x=None):
    """Generate pillar grid inside given rectangle with smarter automatic margin.

    Behavior when margin is None (自动计算):
    - Start with num_rows = min_rows (default 2).
    - Compute margin = (width - spacing*(num_rows-1)) / 2 so that rows are spacing apart and centered.
    - If computed margin > 8, add two extra rows (one near each side) i.e. num_rows += 2 and recompute margin.
      Repeat until margin <= 8 or num_rows becomes too large.
    - Ensure margin is non-negative; if negative, set margin = 0 and distribute rows evenly.

    If margin is provided (float), use it as-is and fall back to previous logic for computing row/col counts.

    Args:
        x_min, x_max, y_min, y_max: rectangle bounds
        spacing: desired spacing between rows (y direction)
        margin: if float, use as side margin; if None, compute automatically
        min_rows: minimal number of rows (default 2)
        spacing_x: spacing in x direction for columns; if None use spacing

    Returns:
        list of {"x": float, "y": float, "z": 0}
    """
    if spacing_x is None:
        spacing_x = spacing

    width = y_max - y_min
    length = x_max - x_min

    # Automatic margin calculation when margin is None
    if margin is None:
        num_rows = max(min_rows, 2)
        # compute margin so that rows are (num_rows-1)*spacing apart and centered
        # margin = (width - total_span) / 2, where total_span = (num_rows-1) * spacing
        while True:
            total_span = (num_rows - 1) * spacing
            computed_margin = (width - total_span) / 2
            # if computed_margin is negative, break and handle later (will set margin=0)
            if computed_margin <= 8 or num_rows > 50:
                margin = max(0.0, computed_margin)
                break
            # computed_margin > 8 -> add two side rows (one near each side)
            num_rows += 2
        # ensure at least min_rows
        num_rows = max(num_rows, min_rows)
    else:
        # explicit margin given
        margin = float(margin)
        # compute num_rows from available width similarly to previous logic
        available_width = max(0.0, width - 2 * margin)
        if available_width <= 0:
            return []
        num_rows = max(min_rows, int(available_width // spacing) + 1)
        if num_rows <= 1:
            num_rows = max(2, min_rows)

    # Now we have num_rows and margin (margin may be 0)
    available_width = max(0.0, width - 2 * margin)
    if available_width <= 0:
        # degenerate: place rows centered within width
        y_positions = [y_min + width * 0.5]
    else:
        if num_rows > 1:
            actual_spacing_y = available_width / (num_rows - 1)
        else:
            actual_spacing_y = 0
        y_start = y_min + margin
        y_positions = [y_start + i * actual_spacing_y for i in range(num_rows)]

    # x direction columns (reuse previous logic)
    available_length = max(0.0, length - 2 * margin)
    if available_length <= 0:
        x_positions = [x_min + length / 2]
    else:
        num_cols = max(1, int(available_length // spacing_x) + 1)
        if num_cols > 1:
            actual_spacing_x = available_length / (num_cols - 1)
            x_start = x_min + margin
            x_positions = [x_start + i * actual_spacing_x for i in range(num_cols)]
        else:
            x_positions = [x_min + length / 2]
    # 如果列数是奇数，所有柱子在x方向上偏移spacing_x上偏移spacing_x/2,同时删除最后一列柱子
    if num_cols % 2 == 1 :
        offset = spacing_x / 2
        x_positions = [x + offset for x in x_positions]
        x_positions = x_positions[:-1]

    # build pillars
    pillars = []
    for x in x_positions:
        for y in y_positions:
            pillars.append({"x": x, "y": y, "z": 0})

    return pillars


def fill_area_with_plane(
    x_min, x_max, y_min, y_max,
    plane_size=(0.6, 0.6),
    spacing=(0.0, 0.0),
    fill_edges: bool = True,
    align_lights: dict | None = None,
):
    """Tile ceiling with rectangular cells and optionally compute aligned lights.

    New behavior (strict alignment):
    - Cells are tiled with a pitch = plane_size + spacing.
      If fill_edges=True the tiling uses ceil to cover the area (cells
      may extend beyond the bounds) and is symmetric about the area center.
    - If `align_lights` is provided, the function first computes a lights
      grid that is constrained so every light rectangle (considering its
      half-size) fully lies inside the area bounds. Lights are placed with
      the provided center-to-center spacing. Then the cell tiling origin
      is shifted so that every light center coincides exactly with a cell
      center. This guarantees lights and cells are aligned and symmetric.

    Args:
        x_min, x_max, y_min, y_max: rectangle bounds (meters)
        plane_size: (length_x, length_y) of each cell (meters)
        spacing: extra gap between cells (meters) added to plane_size to
                 form the cell pitch (center-to-center)
        fill_edges: if True use ceil to cover area; if False use floor
                    so cells are fully inside the area
        align_lights: optional dict with keys:
            - "light_size": (lx, ly) light footprint size in meters
            - "light_spacing": (sx, sy) desired center-to-center spacing
              between lights in meters

    Returns:
        - If align_lights is None: list of cell centers [{'x','y','z'},...]
        - If align_lights provided: (cells_list, lights_list)
    """
    # cell pitch (center-to-center)
    cell_x, cell_y = plane_size
    gap_x, gap_y = spacing
    pitch_x = cell_x + gap_x
    pitch_y = cell_y + gap_y

    length = x_max - x_min
    width = y_max - y_min

    # compute number of cells along each axis
    if fill_edges:
        num_cells_x = int(math.ceil(length / pitch_x))
        num_cells_y = int(math.ceil(width / pitch_y))
    else:
        num_cells_x = int(length // pitch_x)
        num_cells_y = int(width // pitch_y)
    num_cells_x = max(1, num_cells_x)
    num_cells_y = max(1, num_cells_y)

    # center-based symmetric start for cells (initial)
    center_x = (x_min + x_max) / 2.0
    center_y = (y_min + y_max) / 2.0
    total_cells_w_x = num_cells_x * pitch_x
    total_cells_w_y = num_cells_y * pitch_y
    start_cell_x = center_x - total_cells_w_x / 2.0 + cell_x / 2.0
    start_cell_y = center_y - total_cells_w_y / 2.0 + cell_y / 2.0

    # optionally compute lights first to enforce they stay within bounds
    lights = None
    if align_lights is not None:
        # parse inputs
        light_size = align_lights.get("light_size")
        light_spacing = align_lights.get("light_spacing")
        if light_size is None or light_spacing is None:
            raise ValueError("align_lights requires 'light_size' and 'light_spacing'")
        lx, ly = light_size
        sx, sy = light_spacing

        half_lx = lx / 2.0
        half_ly = ly / 2.0

        # available range for light centers so lights fully inside bounds
        min_cx = x_min + half_lx
        max_cx = x_max - half_lx
        min_cy = y_min + half_ly
        max_cy = y_max - half_ly

        # if no space for a single light center, produce empty lights
        if min_cx > max_cx or min_cy > max_cy:
            lights = []
        else:
            # compute number of lights (floor logic for spacing)
            available_len_x = max_cx - min_cx
            available_len_y = max_cy - min_cy

            # if spacing is zero, place as many as possible with step equal 0 -> fallback to 1 center
            if sx <= 0:
                num_lx = 1
            else:
                num_lx = int(math.floor(available_len_x / sx)) + 1
            if sy <= 0:
                num_ly = 1
            else:
                num_ly = int(math.floor(available_len_y / sy)) + 1

            num_lx = max(1, num_lx)
            num_ly = max(1, num_ly)

            # compute centered start for lights
            total_lights_span_x = (num_lx - 1) * sx if num_lx > 1 else 0.0
            total_lights_span_y = (num_ly - 1) * sy if num_ly > 1 else 0.0
            start_light_x = (min_cx + max_cx) / 2.0 - total_lights_span_x / 2.0
            start_light_y = (min_cy + max_cy) / 2.0 - total_lights_span_y / 2.0

            # clamp start to valid interval (should already be inside but be safe)
            min_start_x = min_cx
            max_start_x = max_cx - total_lights_span_x
            start_light_x = min(max(start_light_x, min_start_x), max_start_x)
            min_start_y = min_cy
            max_start_y = max_cy - total_lights_span_y
            start_light_y = min(max(start_light_y, min_start_y), max_start_y)

            # build lights centers
            lights = []
            for i in range(num_lx):
                cx = start_light_x + i * sx
                for j in range(num_ly):
                    cy = start_light_y + j * sy
                    lights.append({"x": cx, "y": cy, "z": 0})

        # Now shift cell start so lights align with some cell centers
        if lights:
            # use first light center to compute index offset
            # compute ideal index offset (may be non-integer) then round
            # i0 such that start_light_x = start_cell_x + i0 * pitch_x
            first_light = lights[0]
            raw_i0 = (first_light["x"] - start_cell_x) / pitch_x
            raw_j0 = (first_light["y"] - start_cell_y) / pitch_y
            i0 = int(round(raw_i0))
            j0 = int(round(raw_j0))
            # adjust start_cell so that light[0] sits exactly on cell index i0,j0
            start_cell_x = first_light["x"] - i0 * pitch_x
            start_cell_y = first_light["y"] - j0 * pitch_y
            # This ensures every light (at integer k steps of sx,sy) will map onto
            # cell centers if sx is integer multiple of pitch_x and likewise for y.

    # Generate final cells using (possibly adjusted) start_cell_x/start_cell_y
    cells = []
    for i in range(num_cells_x):
        cx = start_cell_x + i * pitch_x
        for j in range(num_cells_y):
            cy = start_cell_y + j * pitch_y
            cells.append({"x": cx, "y": cy, "z": 0})

    if align_lights is not None:
        return cells, lights
    return cells


def generate_cells_and_aligned_lights(
    x_min, x_max, y_min, y_max,
    cell_size=(0.6, 0.6),
    light_spacing=(2.4, 2.4),
    fill_cells_edges=True,
):
    """Generate a tiled cell grid and an aligned lights grid.

    Behavior and guarantees:
    - Cells tile the ceiling using cell_size. If fill_cells_edges is True
      the tiling uses ceil(...) so cells cover the whole area (may extend
      slightly beyond bounds) and remain symmetric about the area center.
    - Lights are chosen as a centered subset of cell centers so every
      light center coincides exactly with some cell center (guarantees
      alignment and symmetry). Lights are placed in a matrix with a
      step derived from light_spacing / cell_size (rounded to integer).

    Returns: (cells, lights) where each is a list of {"x", "y", "z"}.

    Typical presets to use with this function:
    - cell_size=(0.6, 0.6), light_spacing=(2.4, 2.4)
    - cell_size=(0.6, 1.2), light_spacing=(3.6, 3.6)
    """
    cell_x, cell_y = cell_size
    lsx, lsy = (
        light_spacing
        if isinstance(light_spacing, tuple)
        else (light_spacing, light_spacing)
    )

    length = x_max - x_min
    width = y_max - y_min

    if fill_cells_edges:
        num_x = int(math.ceil(length / cell_x))
        num_y = int(math.ceil(width / cell_y))
    else:
        num_x = int(length // cell_x)
        num_y = int(width // cell_y)

    # center-based symmetric start so the tiling is symmetric
    center_x = (x_min + x_max) / 2.0
    center_y = (y_min + y_max) / 2.0

    total_w_x = num_x * cell_x
    total_w_y = num_y * cell_y

    # first cell center position
    start_x = center_x - total_w_x / 2.0 + cell_x / 2.0
    start_y = center_y - total_w_y / 2.0 + cell_y / 2.0

    cells = []
    for i in range(num_x):
        x = start_x + i * cell_x
        for j in range(num_y):
            y = start_y + j * cell_y
            cells.append({"x": x, "y": y, "z": 0})

    # derive integer step from desired light spacing so lights snap to cells
    step_x = max(1, int(round(lsx / cell_x)))
    step_y = max(1, int(round(lsy / cell_y)))

    # choose offsets so lights are centered (include the center cell)
    center_idx_x = (num_x - 1) / 2.0
    center_idx_y = (num_y - 1) / 2.0
    offset_x = int(round(center_idx_x)) % step_x
    offset_y = int(round(center_idx_y)) % step_y

    lights = []
    for i in range(offset_x, num_x, step_x):
        x = start_x + i * cell_x
        for j in range(offset_y, num_y, step_y):
            y = start_y + j * cell_y
            lights.append({"x": x, "y": y, "z": 0})

    return cells, lights


def preset_cells_600_600_lights_2_4(x_min, x_max, y_min, y_max, fill_cells_edges=True):
    """Convenience preset: cells 0.6x0.6, lights spacing 2.4m."""
    return generate_cells_and_aligned_lights(
        x_min, x_max, y_min, y_max,
        cell_size=(0.6, 0.6),
        light_spacing=(2.4, 2.4),
        fill_cells_edges=fill_cells_edges,
    )


def preset_cells_600_1200_lights_3_6(x_min, x_max, y_min, y_max, fill_cells_edges=True):
    """Convenience preset: cells 0.6x1.2, lights spacing 3.6m."""
    return generate_cells_and_aligned_lights(
        x_min, x_max, y_min, y_max,
        cell_size=(0.6, 0.6),
        light_spacing=(3.6, 3.6),
        fill_cells_edges=fill_cells_edges,
    )


def layout_aligned_lights_and_cells(
    x_min, x_max, y_min, y_max,
    light_size=(0.6, 1.2),
    spacing=(3.6, 3.6),
    cell_size=(0.6, 0.6),
    height=0.0,
    remove_colliding_cells=False,
):
    """
    根据指定逻辑在区域内放置灯具，并生成与灯具对齐的单元格。

    该函数严格遵循 "放灯逻辑.md" 中的说明。

    Args:
        x_min, x_max (float): 区域的x坐标范围。
        y_min, y_max (float): 区域的y坐标范围。
        light_size (tuple): 灯具的尺寸 (长, 宽)。
        spacing (tuple): 灯具之间的中心间距 (x间距, y间距)。
        cell_size (tuple): 布局单元格的尺寸 (x单元格, y单元格)。

    Returns:
        tuple: 包含两个列表 (lights, cells)。
            - lights: 对齐的灯具中心位置列表。
            - cells: 覆盖区域的单元格中心位置列表。
    """
    auto_rotation = [0, 0, 0]  # 暂未使用
    if light_size[0] < light_size[1]:
        auto_rotation = [0, 0, 90]
    lx, ly = light_size
    sx, sy = spacing
    cx, cy = cell_size

    half_lx = lx / 2.0
    half_ly = ly / 2.0

    # 1. 计算灯具布局
    # 可用区域的边界，确保灯具实体完全在区域内
    min_light_cx = x_min + half_lx
    max_light_cx = x_max - half_lx
    min_light_cy = y_min + half_ly
    max_light_cy = y_max - half_ly

    lights = []
    if min_light_cx <= max_light_cx and min_light_cy <= max_light_cy:
        avail_x = max_light_cx - min_light_cx
        avail_y = max_light_cy - min_light_cy

        # 计算x, y方向可以放置的灯具数量
        num_lx = int(avail_x / sx) + 1 if sx > 0 else 1
        num_ly = int(avail_y / sy) + 1 if sy > 0 else 1

        # 为了中心对称，计算灯具阵列的总宽度和高度
        total_span_x = (num_lx - 1) * sx
        total_span_y = (num_ly - 1) * sy

        # 计算灯具阵列的起始位置（使其在可用区域内居中）
        start_light_x = (min_light_cx + max_light_cx) / 2.0 - total_span_x / 2.0
        start_light_y = (min_light_cy + max_light_cy) / 2.0 - total_span_y / 2.0

        # 生成灯具位置列表
        for i in range(num_lx):
            for j in range(num_ly):
                lights.append({
                    "x": start_light_x + i * sx,
                    "y": start_light_y + j * sy,
                    "z": height,
                    "w": light_size[0],
                    "h": light_size[1],
                    "l": 0,
                    "rotation": auto_rotation,
                })

    # 2. 计算单元格布局
    length = x_max - x_min
    width = y_max - y_min
    num_cells_x = int(math.ceil(length / cx)) if cx > 0 else 1
    num_cells_y = int(math.ceil(width / cy)) if cy > 0 else 1

    # 确定单元格网格的起始位置
    if lights:
        # 根据第一个灯具的位置进行对齐
        first_light = lights[0]

        # --- X方向对齐 ---
        multiple_x = round(lx / cx) if cx > 0 else 1
        if multiple_x % 2 == 0:  # Even multiple
            # Target is the edge between cells
            target_x = first_light["x"] + cx / 2.0
        else:  # Odd multiple
            # Target is the center of a cell
            target_x = first_light["x"]

        # Temporarily calculate a centered grid to find the nearest cell
        center_x = (x_min + x_max) / 2.0
        num_x = int(math.ceil((x_max - x_min) / cx)) if cx > 0 else 1
        total_w_x = num_x * cx
        start_x_initial = center_x - total_w_x / 2.0 + (cx / 2.0)

        # Find the index of the cell closest to our target and align the grid
        k0 = round((target_x - start_x_initial) / cx)
        start_cell_cx = target_x - k0 * cx

        # --- Y方向对齐 ---
        multiple_y = round(ly / cy) if cy > 0 else 1
        if multiple_y % 2 == 0:  # Even multiple
            target_y = first_light["y"] + cy / 2.0
        else:  # Odd multiple
            target_y = first_light["y"]

        center_y = (y_min + y_max) / 2.0
        num_y = int(math.ceil((y_max - y_min) / cy)) if cy > 0 else 1
        total_w_y = num_y * cy
        start_y_initial = center_y - total_w_y / 2.0 + (cy / 2.0)

        j0 = round((target_y - start_y_initial) / cy)
        start_cell_cy = target_y - j0 * cy

    else:
        # 如果没有灯具，则将单元格网格在区域内居中
        length = x_max - x_min
        width = y_max - y_min
        num_cells_x = int(math.ceil(length / cx)) if cx > 0 else 1
        num_cells_y = int(math.ceil(width / cy)) if cy > 0 else 1
        total_cells_w_x = num_cells_x * cx
        total_cells_w_y = num_cells_y * cy
        center_x = (x_min + x_max) / 2.0
        center_y = (y_min + y_max) / 2.0
        start_cell_cx = center_x - total_cells_w_x / 2.0 + (cx / 2.0)
        start_cell_cy = center_y - total_cells_w_y / 2.0 + (cy / 2.0)

    # 3. 铺放单元格以覆盖整个区域
    # Find k_min, k_max, j_min, j_max to cover the area
    k_min = math.floor((x_min - start_cell_cx) / cx)
    k_max = math.ceil((x_max - start_cell_cx) / cx)
    j_min = math.floor((y_min - start_cell_cy) / cy)
    j_max = math.ceil((y_max - start_cell_cy) / cy)

    cells = []
    for k in range(int(k_min), int(k_max) + 1):
        for j in range(int(j_min), int(j_max) + 1):
            cells.append({
                "x": start_cell_cx + k * cx,
                "y": start_cell_cy + j * cy,
                "z": height,
                "w": cell_size[0],
                "h": cell_size[1],
                "l": 0,
                "rotation": [0, 0, 0],
            })
    
    # remove colliding cells (optional, depending on use case)'
    # if x,y in light box, remove that cell
    if remove_colliding_cells and lights:
        for light in lights:
            lx_min = light["x"] - half_lx
            lx_max = light["x"] + half_lx
            ly_min = light["y"] - half_ly
            ly_max = light["y"] + half_ly
            cells = [
                cell for cell in cells
                if not (lx_min <= cell["x"] <= lx_max and ly_min <= cell["y"] <= ly_max)
            ]

    return lights, cells


def main():
    """Main function for testing layout functions."""
    print("=" * 60)
    print("测试 layout_grid_objects 的两种返回格式")
    print("=" * 60)

    # 定义矩形区域: x从0到20, y从5到15
    x_min, x_max = 3, 20
    y_min, y_max = 5, 15
    spacing_x = 8
    spacing_y = 5

    print(f"\n矩形区域: x=[{x_min}, {x_max}], y=[{y_min}, {y_max}]")
    print(f"间距: spacing_x={spacing_x}, spacing_y={spacing_y}")

    # 一维列表格式
    print("\n【一维列表格式】- as_matrix=False")
    print("场景：当你只需要遍历所有位置，不关心行列关系时")
    positions_flat = layout_grid_objects(
        x_min, x_max, y_min, y_max, spacing_x, spacing_y, as_matrix=False
    )
    print(f"返回类型: list, 长度: {len(positions_flat)}")
    print("示例使用:")
    print("  for pos in positions:")
    print("      place_light(pos)")
    print(f"\n所有位置: {positions_flat}")

    # 二维矩阵格式
    print(f"\n{'='*60}")
    print("【二维矩阵格式】- as_matrix=True")
    print("场景：当你需要按行处理、或需要访问特定行列的灯具时")
    positions_matrix = layout_grid_objects(
        x_min, x_max, y_min, y_max, spacing_x, spacing_y, as_matrix=True
    )
    if positions_matrix:
        shape = f"{len(positions_matrix)}x{len(positions_matrix[0])}"
    else:
        shape = "0x0"
    print(f"返回类型: list[list], 形状: {shape}")
    print("示例使用:")
    print("  # 按行处理")
    print("  for row in grid:")
    print("      process_row(row)")
    print("  # 访问特定位置")
    print("  center_light = grid[1][0]")
    if positions_matrix:
        print(f"\n第一行: {positions_matrix[0]}")
        if len(positions_matrix) > 1:
            print(f"第二行: {positions_matrix[1]}")

    # 使用场景对比
    print(f"\n{'='*60}")
    print("【推荐使用场景】")
    print("\n一维列表 (as_matrix=False) ✅ 适用于:")
    print("  • 简单遍历所有灯具位置")
    print("  • 不需要区分行列")
    print("  • 统计总数量")
    print("  • 计算总功率等")

    print("\n二维矩阵 (as_matrix=True) ✅ 适用于:")
    print("  • 需要按行/列分组处理")
    print("  • 需要访问特定行列的灯具")
    print("  • 需要计算每行的功率")
    print("  • 需要做行列相关的逻辑判断")
    print("  • 可视化网格布局")


if __name__ == "__main__":
    main()
