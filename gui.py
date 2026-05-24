import math
import tkinter as tk

import psutil
import GPUtil

devMode = True
text_main_color  = "#00ccff"

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

    if item_type == "text":
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
        bgLine = canvas.create_line(x1, y1, x2, y2, fill="#303030", width=2)

    for i in range(howManyBackgroundLines):
        x = i * (screen_width / howManyBackgroundLines)
        x1 = x
        y1 = 0
        x2 = x
        y2 = screen_height
        bgLine = canvas.create_line(x1, y1, x2, y2, fill="#303030", width=2)

overlay_label = canvas.create_text(screen_width/2, 50, text="", fill=text_main_color, font=("Arial", 15, "bold"))
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
for i in range(graph_size):
    gpu_graph_points.append([screen_width - 300 + i, 400])

def ShowSystemInfoGraph():
    # CPU
    cpu = psutil.cpu_percent(interval=1)
    print(f"CPU: {cpu}%")

    # RAM
    ram = psutil.virtual_memory()
    print(f"RAM: {ram.percent}%")

    # GPU
    gpus = GPUtil.getGPUs()
    for gpu in gpus:
        print(f"GPU: {gpu.load * 100:.1f}%")
        print(f"VRAM: {gpu.memoryUtil * 100:.1f}%")
        print(f"GPU Temp: {gpu.temperature}°C")

    canvas.tag_bind(info_y_axis, "<Enter>", on_hover)
    canvas.tag_bind(info_y_axis, "<Leave>", lambda e: globals().update(hovered=False))
    canvas.tag_bind(info_y_axis, "<Button-1>", on_press)
    canvas.tag_bind(info_y_axis, "<ButtonRelease-1>", on_release)

    canvas.tag_bind(info_x_axis, "<Enter>", on_hover)
    canvas.tag_bind(info_x_axis, "<Leave>", lambda e: globals().update(hovered=False))
    canvas.tag_bind(info_x_axis, "<Button-1>", on_press)
    canvas.tag_bind(info_x_axis, "<ButtonRelease-1>", on_release)

def UpdateSystemInfoGraph(gpu_percent):
    global gpu_graph_points

    pass
    
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

    if item_type == "text":
        canvas.itemconfig(self, fill="red")
        canvas.itemconfig(musicBox_outline, outline="red")
        canvas.coords(self, x - diffX, y - diffY)

        bbox = canvas.bbox(self)
        canvas.coords(musicBox_outline, bbox[0] - 10, bbox[1] - 10, bbox[2] + 10, bbox[3] + 10)

        canvas.tag_raise(self)
        canvas.tag_raise(musicBox_outline)

    elif item_type == "line":
        # Move all items with the same tag as a group
        item_tags = canvas.gettags(self)
        if item_tags:
            canvas.move(item_tags[0], dx, dy)

        last_x = x
        last_y = y
        canvas.tag_raise(self)

def StartGUILoop():
    HandleGUI()
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