"""Visualize station layout from station_hall_rooms.json and save an image.

Usage:
    source .venv/bin/activate && python scripts/visualize_station.py

Generates: station_hall_diagram.png in repository root.
"""
import json
import os
import math

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib

# Configure fonts to support Chinese characters on macOS/Windows/Linux.
# Try common Chinese-capable fonts; matplotlib will pick the first available.
matplotlib.rcParams['font.sans-serif'] = [
    'PingFang SC', 'Heiti SC', 'STHeiti', 'Songti SC',
    'Microsoft YaHei', 'SimHei', 'Arial Unicode MS'
]
matplotlib.rcParams['axes.unicode_minus'] = False  # use normal minus sign

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
INPUT = os.path.join(ROOT, 'station_hall_rooms.json')
OUTPUT = os.path.join(ROOT, 'station_hall_diagram.png')

if not os.path.exists(INPUT):
    print('Input JSON not found:', INPUT)
    raise SystemExit(1)

with open(INPUT, 'r', encoding='utf-8') as f:
    rooms = json.load(f)

# Determine bounds
min_x = math.inf
max_x = -math.inf
min_y = math.inf
max_y = -math.inf
for room in rooms:
    rect = room.get('rectangle', {})
    if 'x_min' in rect:
        min_x = min(min_x, rect.get('x_min', min_x))
        max_x = max(max_x, rect.get('x_max', max_x))
        min_y = min(min_y, rect.get('y_min', min_y))
        max_y = max(max_y, rect.get('y_max', max_y))

if min_x == math.inf:
    print('No rectangle data found in JSON')
    raise SystemExit(1)

fig_w = max(10, (max_x - min_x) / 5)
fig_h = max(5, (max_y - min_y) / 5)

fig, ax = plt.subplots(figsize=(fig_w, fig_h))

# Draw rooms
colors = {
    '站厅外通道1': '#c6e2ff',
    '站厅外通道2': '#c6e2ff',
    '站厅内通道': '#fff2b2',
    '客服中心': '#d5f5e3'
}

for room in rooms:
    name = room.get('name', '')
    rect = room.get('rectangle', {})
    x_min = rect.get('x_min', 0)
    x_max = rect.get('x_max', 0)
    y_min = rect.get('y_min', 0)
    y_max = rect.get('y_max', 0)
    w = x_max - x_min
    h = y_max - y_min
    color = colors.get(name, '#e6e6e6')
    patch = patches.Rectangle((x_min, y_min), w, h, linewidth=1, edgecolor='k', facecolor=color, alpha=0.8)
    ax.add_patch(patch)
    ax.text(x_min + w/2, y_min + h/2, name, ha='center', va='center', fontsize=10)

    # draw objects inside room
    for obj in room.get('objects', []):
        locs = obj.get('locations') or obj.get('location') or []
        for loc in locs:
            ox = loc.get('x')
            oy = loc.get('y')
            ow = loc.get('w', 0.6)
            oh = loc.get('h', 0.6)
            # If location x,y are relative to room, try to handle both absolute and relative
            if ox is None or oy is None:
                continue
            # Draw object as smaller rectangle
            obj_patch = patches.Rectangle((ox - ow/2, oy - oh/2), ow, oh, linewidth=1, edgecolor='black', facecolor='#444', alpha=0.9)
            ax.add_patch(obj_patch)
            ax.text(ox, oy, obj.get('type', 'obj')[0:2], color='white', ha='center', va='center', fontsize=8)

ax.set_xlim(min_x - 1, max_x + 1)
ax.set_ylim(min_y - 1, max_y + 1)
ax.set_aspect('equal', adjustable='box')
ax.set_xlabel('X (m)')
ax.set_ylabel('Y (m)')
ax.set_title('Station Hall Layout')
plt.tight_layout()
# y 从 0 开始，从下到上（matplotlib 默认原点为左下），因此不反转 Y 轴以保持与数据坐标一致
# plt.gca().invert_yaxis()  # removed to keep y increasing upwards
plt.savefig(OUTPUT, dpi=200)
print('Saved diagram to', OUTPUT)
