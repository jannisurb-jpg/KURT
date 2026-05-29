import time
import tkinter as tk

import psutil
import GPUtil

import threading

devMode = True
text_main_color  = "#00ccff"
gpu_graph_color = "#ff000d"
ram_graph_color = "#00ff1a"
cpu_graph_color = "#1a00ff"

root = tk.Tk()
root.title("Jarvis")
if not devMode:
    root.attributes("-fullscreen", True)
    root.resizable(False, False)

canvas        = tk.Canvas(root, bg="#141414", highlightthickness=0)
canvas.pack(fill="both", expand=True)

screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()

hovered = False
item_id = 0
is_holding = False
diffX = 0
diffY = 0
last_x = 0
last_y = 0
graph_size = 150

def on_hover(e):
    global hovered, item_id
    item_id = canvas.find_withtag("current")[0]
    print(f"[DEBUG] Hovering over item with id: {item_id}")
    hovered = True

def on_press(e):
    global is_holding, diffX, diffY, last_x, last_y
    is_holding = True
    last_x = root.winfo_pointerx()
    last_y = root.winfo_pointery()

    x = root.winfo_pointerx()
    y = root.winfo_pointery()

    item_type = canvas.type(item_id)

    if "music_overlay" in canvas.gettags(item_id):
        bbox = canvas.bbox(overlay_label)
        diffX = x - (bbox[0] + bbox[2]) / 2
        diffY = y - (bbox[1] + bbox[3]) / 2
    else:
        # For lines/groups, diff from mouse position directly
        diffX = 0
        diffY = 0

def on_release(e):
    global is_holding
    is_holding = False

def CreateBackground():
    howManyBackgroundLines = 30

    for i in range(howManyBackgroundLines):
        y = i * (screen_height / howManyBackgroundLines)
        x1 = 0
        y1 = y
        x2 = screen_width
        y2 = y
        bgLine = canvas.create_line(x1, y1, x2, y2, fill="#202020", width=2, tags="bg_line")

    for i in range(howManyBackgroundLines):
        x = i * (screen_width / howManyBackgroundLines)
        x1 = x
        y1 = 0
        x2 = x
        y2 = screen_height
        bgLine = canvas.create_line(x1, y1, x2, y2, fill="#202020", width=2, tags="bg_line")

overlay_label = canvas.create_text(screen_width/2, 50, text="", fill=text_main_color, font=("Arial", 15, "bold"), tags="music_overlay")
musicBox_outline = canvas.create_rectangle(screen_width/2 - 200, 20, screen_width/2 + 200, 80, outline=text_main_color, width=1)
def ShowMusicOverlay(title, artist):
    global overlay_label
    overlay_text = f"🎵 {title} - {artist}"
    canvas.itemconfig(overlay_label, text=overlay_text)

    canvas.tag_bind(overlay_label, "<Enter>", on_hover)
    canvas.tag_bind(overlay_label, "<Leave>", lambda e: globals().update(hovered=False))
    canvas.tag_bind(overlay_label, "<Button-1>", on_press)
    canvas.tag_bind(overlay_label, "<ButtonRelease-1>", on_release)

info_y_axis = canvas.create_line(screen_width - 300, 400, screen_width - 300, 400 - graph_size, fill=text_main_color, width=2, tags="info_axis")
info_x_axis = canvas.create_line(screen_width - 300, 400, screen_width - 300 + graph_size, 400, fill=text_main_color, width=2, tags="info_axis")

gpu_graph_points = []
gpu_graph_lines = []
for i in range(graph_size):
    gpu_graph_points.append([screen_width - 300 + graph_size - i, 400])

for i in range(graph_size - 1):
    gpu_graph_lines.append(canvas.create_line(gpu_graph_points[i][0], gpu_graph_points[i][1], gpu_graph_points[i + 1][0], gpu_graph_points[i + 1][1], fill=gpu_graph_color, width=1, tags="info_axis"))

ram_graph_points = []
ram_graph_lines = []
for i in range(graph_size):
    ram_graph_points.append([screen_width - 300 + graph_size - i, 400])

for i in range(graph_size - 1):
    ram_graph_lines.append(canvas.create_line(ram_graph_points[i][0], ram_graph_points[i][1], ram_graph_points[i + 1][0], ram_graph_points[i + 1][1], fill=ram_graph_color, width=1, tags="info_axis"))

cpu_graph_points = []
cpu_graph_lines = []
for i in range(graph_size):
    cpu_graph_points.append([screen_width - 300 + graph_size - i, 400])

for i in range(graph_size - 1):
    cpu_graph_lines.append(canvas.create_line(cpu_graph_points[i][0], cpu_graph_points[i][1], cpu_graph_points[i + 1][0], cpu_graph_points[i + 1][1], fill=cpu_graph_color, width=1, tags="info_axis"))

cpu = None
ram = None
gpu = None
def ShowSystemInfoGraph():
    canvas.tag_bind(info_y_axis, "<Enter>", on_hover)
    canvas.tag_bind(info_y_axis, "<Leave>", lambda e: globals().update(hovered=False))
    canvas.tag_bind(info_y_axis, "<Button-1>", on_press)
    canvas.tag_bind(info_y_axis, "<ButtonRelease-1>", on_release)

    canvas.tag_bind(info_x_axis, "<Enter>", on_hover)
    canvas.tag_bind(info_x_axis, "<Leave>", lambda e: globals().update(hovered=False))
    canvas.tag_bind(info_x_axis, "<Button-1>", on_press)
    canvas.tag_bind(info_x_axis, "<ButtonRelease-1>", on_release)

def update_stats_thread():
    global cpu, ram, gpu
    while True:
        cpu = psutil.cpu_percent(interval=1)  # blocking is fine in a thread
        ram = psutil.virtual_memory()
        gpus = GPUtil.getGPUs()
        gpu = gpus[0].load if gpus else 0
        time.sleep(0.5)

threading.Thread(target=update_stats_thread, daemon=True).start()

def UpdateSystemInfoGraph():
    global gpu_graph_points, cpu, ram, gpu

    if cpu is None or ram is None or gpu is None:
        return

    #CPU
    # Use the current x-axis y position as the baseline instead of hardcoded 400
    baseline_y = canvas.coords(info_x_axis)[1]  # y1 of the x-axis line

    new_y = baseline_y - (cpu / 100 * graph_size)

    for i in range(len(cpu_graph_points) - 1, 0, -1):
        cpu_graph_points[i][1] = cpu_graph_points[i - 1][1]
    cpu_graph_points[0][1] = new_y

    for i in range(len(cpu_graph_lines)):
        canvas.coords(cpu_graph_lines[i],
                  cpu_graph_points[i][0], cpu_graph_points[i][1],
                  cpu_graph_points[i+1][0], cpu_graph_points[i+1][1])
    #RAM
    # Use the current x-axis y position as the baseline instead of hardcoded 400
    baseline_y = canvas.coords(info_x_axis)[1]  # y1 of the x-axis line

    new_y = baseline_y - (ram.percent / 100 * graph_size)

    for i in range(len(ram_graph_points) - 1, 0, -1):
        ram_graph_points[i][1] = ram_graph_points[i - 1][1]
    ram_graph_points[0][1] = new_y

    for i in range(len(ram_graph_lines)):
        canvas.coords(ram_graph_lines[i],
                  ram_graph_points[i][0], ram_graph_points[i][1],
                  ram_graph_points[i+1][0], ram_graph_points[i+1][1])

    # GPU
    # Use the current x-axis y position as the baseline instead of hardcoded 400
    baseline_y = canvas.coords(info_x_axis)[1]  # y1 of the x-axis line

    new_y = baseline_y - (gpu * graph_size)

    for i in range(len(gpu_graph_points) - 1, 0, -1):
        gpu_graph_points[i][1] = gpu_graph_points[i - 1][1]
    gpu_graph_points[0][1] = new_y

    for i in range(len(gpu_graph_lines)):
        canvas.coords(gpu_graph_lines[i],
                  gpu_graph_points[i][0], gpu_graph_points[i][1],
                  gpu_graph_points[i+1][0], gpu_graph_points[i+1][1])

todo_list = canvas.create_text(screen_width/2, 100, text="", fill=text_main_color, font=("Arial", 15, "bold"), tags="todo_list")
def UpdateTodoList(list):
    canvas.itemconfig(todo_list, text=list)
    
canvas.tag_bind(todo_list, "<Enter>", on_hover)
canvas.tag_bind(todo_list, "<Leave>", lambda e: globals().update(hovered=False))
canvas.tag_bind(todo_list, "<Button-1>", on_press)
canvas.tag_bind(todo_list, "<ButtonRelease-1>", on_release)

def HandleGUI():
    global overlay_label, info_x_axis, info_y_axis
    
    if is_holding:
        MoveOverlay(item_id)
    else:
        canvas.itemconfig(overlay_label, fill=text_main_color)
        canvas.itemconfig(musicBox_outline, outline=text_main_color)

def MoveOverlay(self):
    global last_x, last_y

    x = root.winfo_pointerx()
    y = root.winfo_pointery()

    dx = x - last_x
    dy = y - last_y

    # Check if it's a line or text
    item_type = canvas.type(self)

    if "music_overlay" in canvas.gettags(self):
        canvas.itemconfig(self, fill="red")
        canvas.itemconfig(musicBox_outline, outline="red")
        canvas.coords(self, x - diffX, y - diffY)

        bbox = canvas.bbox(self)
        canvas.coords(musicBox_outline, bbox[0] - 10, bbox[1] - 10, bbox[2] + 10, bbox[3] + 10)

        canvas.tag_raise(self)
        canvas.tag_raise(musicBox_outline)

    elif "todo_list" in canvas.gettags(self):
        canvas.itemconfig(self, fill="red")
        canvas.coords(self, x - diffX, y - diffY)

        bbox = canvas.bbox(self)

        canvas.tag_raise(self)

    elif item_type == "line":
        # Move all items with the same tag as a group
        item_tags = canvas.gettags(self)
        if item_tags:
            canvas.move(item_tags[0], dx, dy)

            # Keep gpu_graph_points in sync with the visual position
            for point in gpu_graph_points:
                point[0] += dx
                point[1] += dy

            # Keep cpu_graph_points in sync with the visual position
            for point in cpu_graph_points:
                point[0] += dx
                point[1] += dy

            # Keep ram_graph_points in sync with the visual position
            for point in ram_graph_points:
                point[0] += dx
                point[1] += dy

        last_x = x
        last_y = y
        canvas.tag_raise(self)

old_time_graphs = time.time()
def StartGUILoop():
    global old_time_graphs
    canvas.tag_lower("bg_line")  # Ensure background lines are always at the back
    HandleGUI()
    if time.time() - old_time_graphs >= .5:  # Update every second
        UpdateSystemInfoGraph()
        old_time_graphs = time.time()
    root.after(30, StartGUILoop)

"""canvas        = tk.Canvas(root, bg="black", highlightthickness=0)
canvas.pack(fill="both", expand=True)
#overlay_label = canvas.create_text(960, 50, text=f"{name} hört zu...", fill="white", font=("Arial", 28, "bold"))

screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()

capsule_radius = 100

first_ring_radius = 130
second_ring_radius = 195
cx = screen_width - 35 - first_ring_radius / 2
cy = 35 + first_ring_radius / 2

first_ring_indicator_inner_radius = 75
first_ring_indicator_outer_radius = 85
num_lines = 20
center_of_jarvis_x = screen_width - 50 - (.5 * capsule_radius)
center_of_jarvis_y = 50 + capsule_radius/2

dot_radius = 10

#capsule = canvas.create_rectangle(screen_width/2 - capsule_width/2, 50, screen_width/2 + capsule_width/2, capsule_radius, outline="blue", width=3)
capsule = canvas.create_oval(screen_width - 50 - capsule_radius, 50, screen_width - 50, 50 + capsule_radius, fill="#0088ff")
first_ring = canvas.create_arc(
    cx - first_ring_radius / 2, cy - first_ring_radius / 2,
    cx + first_ring_radius / 2, cy + first_ring_radius / 2,
    start=0, extent=180, style=tk.ARC, outline="#0088ff", width=3
)

second_ring = canvas.create_arc(
    cx - second_ring_radius / 2, cy - second_ring_radius / 2,
    cx + second_ring_radius / 2, cy + second_ring_radius / 2,
    start=0, extent=300, style=tk.ARC, outline="#00ccff", width=3
)

first_ring_indicators = []

for i in range(num_lines):
    angle = math.radians(i * (360 / num_lines))
    x1 = center_of_jarvis_x + first_ring_indicator_inner_radius * math.cos(angle)
    y1 = center_of_jarvis_y + first_ring_indicator_inner_radius * math.sin(angle)
    x2 = center_of_jarvis_x + first_ring_indicator_outer_radius * math.cos(angle)
    y2 = center_of_jarvis_y + first_ring_indicator_outer_radius * math.sin(angle)
    if i == num_lines * .25 or i == num_lines *.5 or i == num_lines *.75 or i == num_lines:
        first_ring_indicator = canvas.create_line(x1, y1, x2, y2, fill="#00ccff", width=5)
    else:
        first_ring_indicator = canvas.create_line(x1, y1, x2, y2, fill="#00aaff", width=2)
    first_ring_indicators.append(first_ring_indicator)


center_dot = canvas.create_oval(
    center_of_jarvis_x - dot_radius,
    center_of_jarvis_y - dot_radius,
    center_of_jarvis_x + dot_radius,
    center_of_jarvis_y + dot_radius,
    fill="white"
)

center_outline = canvas.create_oval(
    center_of_jarvis_x - capsule_radius/2,
    center_of_jarvis_y - capsule_radius/2,
    center_of_jarvis_x + capsule_radius/2,
    center_of_jarvis_y + capsule_radius/2,
    outline="#00ccff",
    width=3
)

reset_pending = False
reset_time    = 0"""