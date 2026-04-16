"""Visualize metro station layout and lighting design from a JSON file.

Usage:
    python scripts/visualize_metro_lighting.py <input_json_file>

Example:
    python scripts/visualize_metro_lighting.py metro_station_hall_design_demo_output.json
"""
import json
import os
import math
import argparse
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib
from matplotlib import transforms

# Configure fonts to support Chinese characters
matplotlib.rcParams['font.sans-serif'] = [
    'PingFang SC', 'Heiti SC', 'STHeiti', 'Songti SC',
    'Microsoft YaHei', 'SimHei', 'Arial Unicode MS'
]
matplotlib.rcParams['axes.unicode_minus'] = False  # Use normal minus sign

# Fixture color palette (centralized, similar to room_colors)
FIXTURE_PALETTE = {
    'line': "#a01692",       # 线形灯 - teal
    'downlight': '#2c82c9',  # 筒灯 - blue
    'module': '#8e44ad',     # 模组 - purple
    'default': '#7f8c8d'     # 默认 - gray
}
CONFLICT_COLOR = "#ff1900"  # 冲突时使用的红色
EDGE_COLOR = "#F8F8F800"

def draw_layout(ax, rooms_data):
    """Draws the station layout (rooms and objects) on the given axes."""
    min_x, max_x, min_y, max_y = math.inf, -math.inf, math.inf, -math.inf

    # Room colors for different types
    room_colors = {
        '站厅外通道1': '#c6e2ff',
        '站厅外通道2': '#c6e2ff',
        '站厅内通道': '#fff2b2',
        '客服中心': '#d5f5e3'
    }

    for room in rooms_data:
        rect = room.get('rectangle', {})
        if not all(k in rect for k in ['x_min', 'x_max', 'y_min', 'y_max']):
            continue

        x_min, y_min = rect['x_min'], rect['y_min']
        x_max, y_max = rect['x_max'], rect['y_max']
        w, h = x_max - x_min, y_max - y_min

        min_x = min(min_x, x_min)
        max_x = max(max_x, x_max)
        min_y = min(min_y, y_min)
        max_y = max(max_y, y_max)

        color = room_colors.get(room.get('name', ''), '#e6e6e6')
        patch = patches.Rectangle((x_min, y_min), w, h, linewidth=1, edgecolor='k', facecolor=color, alpha=0.8)
        ax.add_patch(patch)
        ax.text(x_min + w / 2, y_min + h / 2, room.get('name', ''), ha='center', va='center', fontsize=10)

        # Draw objects inside the room
        for obj in room.get('objects', []):
            locations = obj.get('locations', [])
            for loc in locations:
                ox, oy = loc.get('x'), loc.get('y')
                if ox is None or oy is None:
                    continue
                ow, oh = loc.get('w', 0.6), loc.get('h', 0.6)
                obj_patch = patches.Rectangle((ox - ow / 2, oy - oh / 2), ow, oh, linewidth=1, edgecolor='black', facecolor='#444', alpha=0.9)
                ax.add_patch(obj_patch)
                ax.text(ox, oy, obj.get('type', 'obj')[:2], color='white', ha='center', va='center', fontsize=8)

    return min_x, max_x, min_y, max_y

def draw_lighting(ax, lighting_plan):
    """Draw fixtures exactly as placed in the design JSON.

    - Always honor each location's `w`, `h` and `rotation` values.
    - Do not skip products based on plan name; draw everything present in the data.
    """
    total_fixtures = 0
    legend_handles = []

    # Fixture color palette (similar style to room_colors)
    fixture_palette = FIXTURE_PALETTE
    conflict_color = CONFLICT_COLOR
    edge_color = EDGE_COLOR

    for i, product in enumerate(lighting_plan.get('products', [])):
        locations = product.get('location', [])
        if not locations:
            continue

        total_fixtures += len(locations)
        series = product.get('series', 'N/A')
        label = f"{series} ({len(locations)})"
        category = product.get('category1', '').lower()

        # Determine legend/base color for this product from palette
        # (used for the legend marker when needed)
        if '线' in category or 'line' in category:
            product_base_color = fixture_palette['line']
        elif '筒' in category or 'downlight' in category:
            product_base_color = fixture_palette['downlight']
        elif '模组' in category or 'module' in category:
            product_base_color = fixture_palette['module']
        else:
            product_base_color = fixture_palette['default']

        # Draw each location exactly according to its properties (per-location coloring)
        if '线' in category or 'line' in category:
            for loc in locations:
                x = loc.get('x')
                y = loc.get('y')
                w = loc.get('w', 0.15)
                h = loc.get('h', 1.2)
                rotation = loc.get('rotation', [0, 0, 0])[2]

                # per-location conflict
                fixture_conflict = loc.get('conflictWithPillar', False)
                fixture_color = conflict_color if fixture_conflict else product_base_color

                # Create rectangle centered at (x,y)
                rect = patches.Rectangle((x - w / 2, y - h / 2), w, h,
                                         linewidth=0.1, edgecolor=edge_color,
                                         facecolor=fixture_color, alpha=0.95, zorder=5)

                # Rotate around center if rotation != 0
                if rotation:
                    rot = transforms.Affine2D().rotate_deg_around(x, y, rotation)
                    rect.set_transform(rot + ax.transData)

                ax.add_patch(rect)

            # legend handle uses product base color (show conflict by a small red dot if any conflict)
            any_conflict = any(loc.get('conflictWithPillar', False) for loc in locations)
            legend_color = conflict_color if any_conflict else product_base_color
            handle = ax.scatter([locations[0]['x']], [locations[0]['y']],
                                color=legend_color, label=label, marker='s', s=50,
                                zorder=6, alpha=0.9)
            legend_handles.append(handle)

        elif '筒灯' in category or 'downlight' in category:
            xs = [loc['x'] for loc in locations]
            ys = [loc['y'] for loc in locations]
            colors_list = [conflict_color if loc.get('conflictWithPillar', False) else product_base_color for loc in locations]
            handle = ax.scatter(xs, ys, c=colors_list, label=label,
                                marker='o', s=10, zorder=5, alpha=0.95,
                                edgecolors=edge_color, linewidths=0.6)
            # legend handle uses aggregated color
            any_conflict = any(loc.get('conflictWithPillar', False) for loc in locations)
            legend_handles.append(ax.scatter([xs[0]], [ys[0]], color=(conflict_color if any_conflict else product_base_color), marker='o', s=40, zorder=6))

        elif '模组' in category or 'module' in category:
            xs = [loc['x'] for loc in locations]
            ys = [loc['y'] for loc in locations]
            colors_list = [conflict_color if loc.get('conflictWithPillar', False) else product_base_color for loc in locations]
            handle = ax.scatter(xs, ys, c=colors_list, label=label,
                                marker='s', s=24, zorder=5, alpha=0.95, edgecolors=edge_color, linewidths=0.6)
            any_conflict = any(loc.get('conflictWithPillar', False) for loc in locations)
            legend_handles.append(ax.scatter([xs[0]], [ys[0]], color=(conflict_color if any_conflict else product_base_color), marker='s', s=24, zorder=6))

        else:
            xs = [loc['x'] for loc in locations]
            ys = [loc['y'] for loc in locations]
            colors_list = [conflict_color if loc.get('conflictWithPillar', False) else product_base_color for loc in locations]
            handle = ax.scatter(xs, ys, c=colors_list, label=label,
                                marker='o', s=30, zorder=5, alpha=0.95, edgecolors=edge_color, linewidths=0.6)
            any_conflict = any(loc.get('conflictWithPillar', False) for loc in locations)
            legend_handles.append(ax.scatter([xs[0]], [ys[0]], color=(conflict_color if any_conflict else product_base_color), marker='o', s=30, zorder=6))

    return total_fixtures, legend_handles

def main():
    """Main function to generate the visualization."""
    parser = argparse.ArgumentParser(description="Visualize a metro station lighting design from a JSON file.")
    parser.add_argument("input_file", nargs='?', default="metro_station_hall_design_demo_output.json", help="Path to the input JSON file (default: metro_station_hall_design_demo_output.json).")
    args = parser.parse_args()

    input_path = os.path.abspath(args.input_file)
    if not os.path.exists(input_path):
        print(f"Error: Input file not found at '{input_path}'")
        return

    with open(input_path, 'r', encoding='utf-8') as f:
        design_data = json.load(f)

    rooms_data = design_data.get('roomInfo')
    lighting_plan = design_data.get('planList', [{}])[0]

    if not rooms_data:
        print("Error: 'roomInfo' not found in the JSON file.")
        return
    if not lighting_plan:
        print("Error: 'planList' not found or is empty in the JSON file.")
        return

    fig, ax = plt.subplots(figsize=(24, 15))

    # Draw station layout
    min_x, max_x, min_y, max_y = draw_layout(ax, rooms_data)

    # Draw lighting fixtures
    total_fixtures, legend_handles = draw_lighting(ax, lighting_plan)

    # Configure plot
    ax.set_xlim(min_x - 2, max_x + 2)
    ax.set_ylim(min_y - 5, max_y + 5)
    ax.set_aspect('equal', adjustable='box')
    ax.set_xlabel('X (meters)')
    ax.set_ylabel('Y (meters)')
    
    plan_name = lighting_plan.get('name', 'Lighting Design')
    ax.set_title(f'"{plan_name}" - Top-Down View (Total Fixtures: {total_fixtures})', fontsize=16)
    
    if legend_handles:
        ax.legend(handles=legend_handles, title="Lighting Products", bbox_to_anchor=(1.01, 1), loc='upper left', fontsize=10)

    plt.grid(True, which='both', linestyle='--', linewidth=0.5)
    plt.tight_layout(rect=[0, 0, 0.88, 1]) # Adjust layout to make space for legend
    
    # Save the output
    output_filename = os.path.splitext(os.path.basename(input_path))[0] + "_visualization.png"
    output_path = os.path.join(os.path.dirname(input_path), output_filename)
    
    try:
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Successfully saved visualization to: {output_path}")
    except Exception as e:
        print(f"Error saving the plot: {e}")

if __name__ == '__main__':
    main()
