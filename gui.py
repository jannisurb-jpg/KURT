#System
import psutil
import GPUtil
import threading

#Math
import random
import math
import time
from datetime import datetime

#Other
import tkinter as tk

#region Varaibles
#Colors
text_main_color  = "#00ccff"
gpu_graph_color = "#ff000d"
ram_graph_color = "#00ff1a"
cpu_graph_color = "#1a00ff"
outline_color = "#FFFFFF"

#Drag and Drop
hovered = False
item_id = 0
is_holding = False
diffX = 0
diffY = 0
last_x = 0
last_y = 0

#Graph Widget
graph_size = 150
cpu = None
ram = None
gpu = None

#KURT Widget
current_state = 0
inner_KURT_ring = 40
outer_KURT_ring = 80
max_range_for_connection = 20
neurons_size = 5
neurons_quantity = 150
neuron_color = "#00ccff"

breathing_speed = .02
max_radius = 100
min_radius = 30
rotation_speed = .05
neurons = [] #neuron, angle, radius

#Start
old_time_graphs = time.time()
old_time_breathing = time.time()
supposed_to_grow = True

devMode = False
#endregion

#region Creating window
root = tk.Tk()
root.title("Jarvis")
if not devMode:
    root.attributes("-fullscreen", True)
    root.resizable(False, False)

canvas        = tk.Canvas(root, bg="#141414", highlightthickness=0)
canvas.pack(fill="both", expand=True)

screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()

def CreateBackground(howManyBackgroundLines):
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
#endregion

#Drag and Drop functions
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
    elif "time_overlay" in canvas.gettags(item_id):
        bbox = canvas.bbox(time_label)
        diffX = x - (bbox[0] + bbox[2]) / 2
        diffY = y - (bbox[1] + bbox[3]) / 2
    else:
        # For lines/groups, diff from mouse position directly
        diffX = 0
        diffY = 0

def on_release(e):
    global is_holding
    is_holding = False

#Creating widgets
def CreateOutline(bottom_left, top_right, width, height, tag):
    visible_outline = .3

    y_length = height * visible_outline
    x_length = width * visible_outline

    x_btm_left = canvas.create_line(bottom_left[0], bottom_left[1], bottom_left[0] + x_length, bottom_left[1], fill=outline_color, tags=tag)
    y_btm_left = canvas.create_line(bottom_left[0], bottom_left[1], bottom_left[0], bottom_left[1] + y_length, fill=outline_color, tags=tag)

    x_top_right = canvas.create_line(top_right[0], top_right[1], top_right[0] - x_length, top_right[1], fill=outline_color, tags=tag)
    y_top_right = canvas.create_line(top_right[0], top_right[1], top_right[0], top_right[1] - y_length, fill=outline_color, tags=tag)

#Visualization of KURT
def CreateKURT():
    global cx,cy, neurons
    cx, cy = screen_width - outer_KURT_ring - 50, screen_height - outer_KURT_ring - 50
    for i in range(neurons_quantity): 
        angle = random.random() * 2 * math.pi
        radius = math.sqrt(random.random() * (outer_KURT_ring**2 - inner_KURT_ring**2) + inner_KURT_ring**2)

        x = cx + radius * math.cos(angle)
        y = cy + radius * math.sin(angle)

        neuron = canvas.create_oval(x - neurons_size/2, y - neurons_size/2, x + neurons_size/2, y + neurons_size/2, fill=neuron_color, tags="logo")
        neurons.append([neuron, angle, radius])

        canvas.tag_bind(neuron, "<Enter>", on_hover)
        canvas.tag_bind(neuron, "<Leave>", lambda e: globals().update(hovered=False))
        canvas.tag_bind(neuron, "<Button-1>", on_press)
        canvas.tag_bind(neuron, "<ButtonRelease-1>", on_release)

#Create time widget
def CreateTimeWidget():
    global time_label
    time_label = canvas.create_text(screen_width/2, 50, text="00:00", fill=text_main_color, font=("Arial", 15, "bold"), tags="time_overlay", width=350, justify="center")
    CreateOutline([screen_width/2 - 75, 80], [screen_width/2 + 75, 20], 150, -60, "time_outline")

    canvas.tag_bind(time_label, "<Enter>", on_hover)
    canvas.tag_bind(time_label, "<Leave>", lambda e: globals().update(hovered=False))
    canvas.tag_bind(time_label, "<Button-1>", on_press)
    canvas.tag_bind(time_label, "<ButtonRelease-1>", on_release)

#Create music widget
def CreateMusicWidget():
    global overlay_label
    overlay_label = canvas.create_text(200, 50, text="", fill=text_main_color, font=("Arial", 15, "bold"), tags="music_overlay", width=350)
    CreateOutline([25, 10], [375, 90], 350, 80, "music_outline")

def ShowSystemInfoGraph():
    global info_x_axis, info_y_axis, gpu_graph_points, gpu_graph_lines, cpu_graph_points, cpu_graph_lines, ram_graph_points, ram_graph_lines
    origin_x, origin_y = 50, screen_height - 50

    info_y_axis = canvas.create_line(origin_x, origin_y, origin_x, origin_y - graph_size, fill=text_main_color, width=2, tags="info_axis")
    info_x_axis = canvas.create_line(origin_x, origin_y, origin_x + graph_size, origin_y, fill=text_main_color, width=2, tags="info_axis")

    CreateOutline([origin_x - 25, origin_y + 25], [origin_x + 25 + graph_size, origin_y - 25 - graph_size], graph_size, -graph_size, "graph_outline")

    gpu_graph_points = []
    gpu_graph_lines = []
    for i in range(graph_size):
        gpu_graph_points.append([origin_x + graph_size - i, origin_y])

    for i in range(graph_size - 1):
        gpu_graph_lines.append(canvas.create_line(gpu_graph_points[i][0], gpu_graph_points[i][1], gpu_graph_points[i + 1][0], gpu_graph_points[i + 1][1], fill=gpu_graph_color, width=1, tags="info_axis"))

    ram_graph_points = []
    ram_graph_lines = []
    for i in range(graph_size):
        ram_graph_points.append([origin_x + graph_size - i, origin_y])

    for i in range(graph_size - 1):
        ram_graph_lines.append(canvas.create_line(ram_graph_points[i][0], ram_graph_points[i][1], ram_graph_points[i + 1][0], ram_graph_points[i + 1][1], fill=ram_graph_color, width=1, tags="info_axis"))

    cpu_graph_points = []
    cpu_graph_lines = []
    for i in range(graph_size):
        cpu_graph_points.append([origin_x + graph_size - i, origin_y])

    for i in range(graph_size - 1):
        cpu_graph_lines.append(canvas.create_line(cpu_graph_points[i][0], cpu_graph_points[i][1], cpu_graph_points[i + 1][0], cpu_graph_points[i + 1][1], fill=cpu_graph_color, width=1, tags="info_axis"))
    
    canvas.tag_bind(info_y_axis, "<Enter>", on_hover)
    canvas.tag_bind(info_y_axis, "<Leave>", lambda e: globals().update(hovered=False))
    canvas.tag_bind(info_y_axis, "<Button-1>", on_press)
    canvas.tag_bind(info_y_axis, "<ButtonRelease-1>", on_release)

    canvas.tag_bind(info_x_axis, "<Enter>", on_hover)
    canvas.tag_bind(info_x_axis, "<Leave>", lambda e: globals().update(hovered=False))
    canvas.tag_bind(info_x_axis, "<Button-1>", on_press)
    canvas.tag_bind(info_x_axis, "<ButtonRelease-1>", on_release)

def CreateTodoListWidget():
    global todo_list
    todo_list = canvas.create_text(screen_width/2, 100, text="", fill=text_main_color, font=("Arial", 15, "bold"), tags="todo_list")

    canvas.tag_bind(todo_list, "<Enter>", on_hover)
    canvas.tag_bind(todo_list, "<Leave>", lambda e: globals().update(hovered=False))
    canvas.tag_bind(todo_list, "<Button-1>", on_press)
    canvas.tag_bind(todo_list, "<ButtonRelease-1>", on_release)

#Refresh Widgets
def ShowMusicOverlay(title, artist):
    global overlay_label
    overlay_text = f"🎵 {title} - {artist}"
    canvas.itemconfig(overlay_label, text=overlay_text)

    canvas.tag_bind(overlay_label, "<Enter>", on_hover)
    canvas.tag_bind(overlay_label, "<Leave>", lambda e: globals().update(hovered=False))
    canvas.tag_bind(overlay_label, "<Button-1>", on_press)
    canvas.tag_bind(overlay_label, "<ButtonRelease-1>", on_release)

def ControlKURTState(state, should_grow):
        grow_instead = False
        shrink_instead = False
        
        # Store computed positions to reuse for lines
        positions = {}
        
        for i in range(len(neurons)):
            angle = neurons[i][1]
            radius = neurons[i][2]

            if not should_grow:
                new_radius = radius * (1 - breathing_speed)
            else:
                new_radius = radius * (1 + breathing_speed)

            if new_radius <= min_radius and not should_grow:
                grow_instead = True
            if new_radius >= max_radius and should_grow:
                shrink_instead = True

            neurons[i][2] = new_radius

            new_x = cx + new_radius * math.cos(angle)
            new_y = cy + new_radius * math.sin(angle)

            canvas.coords(neurons[i][0], new_x - neurons_size/2, new_y - neurons_size/2, new_x + neurons_size/2, new_y + neurons_size/2)

        if state == 1:
            for i in range(len(neurons)):
                angle = neurons[i][1]
                radius = neurons[i][2]

                new_angle = angle + rotation_speed

                neurons[i][1] = new_angle

                new_x = cx + radius * math.cos(new_angle)
                new_y = cy + radius * math.sin(new_angle)

                canvas.coords(neurons[i][0], new_x - neurons_size/2, new_y - neurons_size/2, new_x + neurons_size/2, new_y + neurons_size/2)
        
        return grow_instead or shrink_instead

def RefreshTimeWidget():
    text = time.strftime("%H:%M") + "\n" + datetime.now().strftime("%d/%m/%Y")

    canvas.itemconfig(time_label, text=text)

def update_stats_thread():
    global cpu, ram, gpu
    while True:
        cpu = psutil.cpu_percent(interval=1)  # blocking is fine in a thread
        ram = psutil.virtual_memory()
        gpus = GPUtil.getGPUs()
        gpu = gpus[0].load if gpus else 0
        time.sleep(0.5)

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

def UpdateTodoList(list):
    canvas.itemconfig(todo_list, text=list)

#Start and refresh global
threading.Thread(target=update_stats_thread, daemon=True).start()
CreateKURT()
CreateTimeWidget()
CreateMusicWidget()
ShowSystemInfoGraph()
CreateTodoListWidget()

def HandleGUI():
    global overlay_label, info_x_axis, info_y_axis
    
    if is_holding:
        MoveOverlay(item_id)
    else:
        canvas.itemconfig(overlay_label, fill=text_main_color)
        canvas.itemconfig("logo", fill=neuron_color)
        canvas.itemconfig("time_overlay", fill=neuron_color)

def MoveOverlay(self):
    global last_x, last_y, cx, cy

    x = root.winfo_pointerx()
    y = root.winfo_pointery()

    dx = x - last_x
    dy = y - last_y

    # Check if it's a line or text
    item_type = canvas.type(self)

    if "music_overlay" in canvas.gettags(self):
        canvas.itemconfig(self, fill="red")
        canvas.coords(self, x - diffX, y - diffY)
        canvas.move("music_outline", dx, dy)

        canvas.tag_raise(self)
        canvas.tag_raise("music_outline")

        last_x = x
        last_y = y

    elif "time_overlay" in canvas.gettags(self):
        canvas.itemconfig(self, fill="red")
        canvas.coords(self, x - diffX, y - diffY)
        canvas.move("time_outline", dx, dy)

        canvas.tag_raise(self)
        canvas.tag_raise("time_outline")

        last_x = x
        last_y = y

    elif "todo_list" in canvas.gettags(self):
        canvas.itemconfig(self, fill="red")
        canvas.coords(self, x - dx, y - dy)

        bbox = canvas.bbox(self)

        canvas.tag_raise(self)

    elif "logo" in canvas.gettags(self):
        canvas.move("logo", dx, dy)
        canvas.itemconfig("logo", fill="red")
        cx += dx
        cy += dy
        last_x = x
        last_y = y

    elif item_type == "line":
        # Move all items with the same tag as a group
        item_tags = canvas.gettags(self)
        if item_tags:
            canvas.move(item_tags[0], dx, dy)
            canvas.move("graph_outline", dx, dy)

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

    canvas.tag_lower("bg_line") 

def StartGUILoop():
    global old_time_graphs, supposed_to_grow, old_time_breathing # Ensure background lines are always at the back

    HandleGUI()

    if time.time() - old_time_breathing >= .05:
        if not is_holding:
            grow_state = ControlKURTState(current_state, supposed_to_grow)

            if grow_state is True:
                supposed_to_grow = not supposed_to_grow
        
        old_time_breathing = time.time()

    if time.time() - old_time_graphs >= .5:
        UpdateSystemInfoGraph()
        RefreshTimeWidget()

        old_time_graphs = time.time()
    root.after(30, StartGUILoop)