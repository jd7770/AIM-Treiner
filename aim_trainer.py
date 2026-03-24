import sys
import os
import math
import random
import json
from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
from panda3d.core import loadPrcFileData

# Optimización para i3
loadPrcFileData("", "load-display pandagl")
loadPrcFileData("", "notify-level-glgsg fatal")

app = Ursina()

# --- ESTÉTICA Y VENTANA ---
window.title = "AIM TREINER BETA 1.2 - GOLD EDITION"
window.fullscreen = True
window.exit_button.visible = False
window.fps_counter.enabled = False # Desactivamos el de fábrica para usar el nuestro
window.color = color.black

# --- VARIABLES DE ESTADO ---
speed_val = 5
time_limit = 60
is_playing = False
current_level = 'easy'
map_index = 1
map_selected = False 
time_on_target = 0
total_time_passed = 0
direction_x = 1
direction_z = 1
menu_state = 'main'
pause_timer = 0
is_paused = False
current_random_speed = 10
target_y = 3
target_z = 20 

# --- RANKING ---
def cargar_ranking():
    archivo = "ranking_aim.json"
    if os.path.exists(archivo):
        try:
            with open(archivo, "r") as f:
                return sorted([int(x) for x in json.load(f)], reverse=True)[:3]
        except: return [0, 0, 0]
    return [0, 0, 0]

def guardar_record(acc):
    archivo = "ranking_aim.json"
    actuales = cargar_ranking()
    actuales.append(int(acc))
    actuales = sorted(actuales, reverse=True)[:3]
    try:
        with open(archivo, "w") as f: json.dump(actuales, f)
    except: pass

# --- ESCENARIO ---
ground = Entity(model='plane', scale=60, y=-2, color=color.dark_gray, texture='white_cube', texture_scale=(15,15), collider='box')
ceiling = Entity(model='plane', scale=60, y=15, rotation_x=180, color=color.dark_gray, texture='white_cube', texture_scale=(15,15))
wall_f = Entity(model='cube', scale=(60, 40, 1), z=25, color=color.black, collider='box')
wall_b = Entity(model='cube', scale=(60, 40, 1), z=-15, color=color.black, collider='box')
wall_l = Entity(model='cube', scale=(1, 40, 60), x=-25, color=color.black, collider='box')
wall_r = Entity(model='cube', scale=(1, 40, 60), x=25, color=color.black, collider='box')

target = Entity(model='cube', color=color.red, collider='box', position=(0, 3, 20), enabled=False)

# --- JUGADOR ---
player = FirstPersonController(y=1.5, z=-5, enabled=False)
player.speed = 0 
player.cursor.model, player.cursor.scale, player.cursor.color = 'quad', 0.01, color.lime

# --- INTERFAZ (UI) ---
main_menu = Entity(parent=camera.ui)
levels_menu = Entity(parent=camera.ui, enabled=False)
settings_menu = Entity(parent=camera.ui, enabled=False)
ranking_menu = Entity(parent=camera.ui, enabled=False)

# 1) LOGO EN EL MENÚ (Usando el PNG de las letras estilizadas)
# INSTRUCCIONES: Verifica que el archivo se llame 'logo.png' y esté en la misma carpeta.
# He optimizado la escala (1.1, 0.45) para que las letras no se estiren.
logo_img = Entity(
    parent=main_menu,
    model='quad',
    texture='logo.png', # <--- Ursina buscará este archivo
    y=0.25,
    scale=(1.1, 0.45), # Escala ancha para que las letras se vean nítidas
    color=color.white # Usamos blanco para que respete los colores originales de la textura
)

start_txt = Text("", parent=main_menu, y=-0.1, color=color.yellow, origin=(0,0))

# 2) MEDIDOR DE FPS PERSONALIZADO
fps_display = Text(
    text='FPS: 0', 
    position=window.top_left + Vec2(0.02, -0.02), 
    origin=(-0.5, 0.5), 
    color=color.lime, 
    scale=1, 
    parent=camera.ui
)

r_labels = [Text('', parent=ranking_menu, y=0.1 - (j*0.15), scale=2, origin=(0,0), color=color.cyan) for j in range(3)]

def set_menu_state(state):
    global menu_state
    menu_state = state
    main_menu.enabled = (state == 'main')
    levels_menu.enabled = (state == 'levels')
    settings_menu.enabled = (state == 'settings')
    ranking_menu.enabled = (state == 'ranking')
    
    if state == 'main' and map_selected:
        start_txt.text = "Presiona 'ENTER' para continuar"
    
    if state == 'ranking':
        recs = cargar_ranking()
        for i, t in enumerate(r_labels):
            t.text = f"TOP {i+1}: {recs[i] if i < len(recs) else 0}%"

btn_s = {'x': -0.7, 'scale': (0.2, 0.05), 'origin': (-0.5, 0)}
Button('MAPAS', parent=main_menu, y=-0.2, on_click=lambda: set_menu_state('levels'), **btn_s)
Button('AJUSTES', parent=main_menu, y=-0.27, on_click=lambda: set_menu_state('settings'), **btn_s)
Button('RANKING', parent=main_menu, y=-0.34, on_click=lambda: set_menu_state('ranking'), **btn_s)

# SELECCIÓN DE MAPAS
for i, lvl in enumerate(['easy', 'medium', 'hard']):
    Text(lvl.upper(), parent=levels_menu, x=-0.2, y=0.2 - (i*0.15), scale=1.5)
    for idx in range(1, 4):
        def select(l=lvl, n=idx):
            global current_level, map_index, map_selected
            current_level, map_index = l, n
            map_selected = True
            set_menu_state('main')
        Button(str(idx), parent=levels_menu, x=0 + (idx*0.1), y=0.2 - (i*0.15), scale=0.05, on_click=select)

# AJUSTES
speed_label = Text('', parent=settings_menu, y=0.25, origin=(0,0))
def adjust_speed(v):
    global speed_val
    speed_val = max(1, min(20, speed_val + v))
    speed_label.text = f'VELOCIDAD (Nivel 1): {speed_val}'
adjust_speed(0)

Button('-', parent=settings_menu, x=-0.1, y=0.18, scale=0.05, on_click=lambda: adjust_speed(-1))
Button('+', parent=settings_menu, x=0.1, y=0.18, scale=0.05, on_click=lambda: adjust_speed(1))
t_label = Text(f'TIEMPO: {time_limit}s', parent=settings_menu, y=-0.1, origin=(0,0))
for i, secs in enumerate([30, 60, 120, 300]):
    def set_t(s=secs): 
        global time_limit
        time_limit = s
        t_label.text = f'TIEMPO: {time_limit}s'
    Button(f'{secs}s', parent=settings_menu, x=-0.2 + (i*0.13), y=-0.18, scale=(0.1, 0.04), on_click=set_t)

Button('VOLVER', parent=levels_menu, y=-0.4, scale=(0.15, 0.05), on_click=lambda: set_menu_state('main'))
Button('VOLVER', parent=settings_menu, y=-0.35, scale=(0.2, 0.05), on_click=lambda: set_menu_state('main'))
Button('VOLVER', parent=ranking_menu, y=-0.35, scale=(0.2, 0.05), on_click=lambda: set_menu_state('main'))

precision_hud = Text('', origin=(0,0), y=-0.2, scale=2, color=color.cyan, enabled=False)
timer_hud = Text('', position=(0, 0.4), origin=(0,0), scale=1.5, enabled=False)

# --- UPDATE ---
def update():
    global is_playing, total_time_passed, direction_x, direction_z, is_paused, pause_timer, time_on_target, current_random_speed, target_y, target_z

    # Actualizar medidor de FPS personalizado
    if time.dt > 0:
        fps_display.text = f'FPS: {int(1/time.dt)}'

    if not is_playing:
        if menu_state == 'main' and map_selected and held_keys['enter']:
            start_game()
        return

    total_time_passed += time.dt
    if is_paused:
        pause_timer -= time.dt
        if pause_timer <= 0: is_paused = False
        return

    # Lógica de movimientos (sin cambios)
    if current_level == 'easy':
        if map_index == 1: target.x += direction_x * speed_val * time.dt
        elif map_index == 2:
            target.x += direction_x * 8 * time.dt
            target.z += direction_z * 10 * time.dt
            if target.z > 23 or target.z < 5: direction_z *= -1
        elif map_index == 3:
            target.x += direction_x * 9 * time.dt
            target.y = 4 + math.sin(total_time_passed * 4) * 5

    elif current_level == 'medium':
        if map_index == 1:
            if int(total_time_passed) % 2 == 0: current_random_speed = random.uniform(8, 22)
            target.x += direction_x * current_random_speed * time.dt
        elif map_index == 2:
            target.x += direction_x * 12 * time.dt
            if random.random() < 0.02: target_z = random.uniform(5, 22)
            target.z = lerp(target.z, target_z, time.dt * 4)
        elif map_index == 3: target.x += direction_x * 15 * time.dt

    elif current_level == 'hard':
        if map_index == 1:
            target.x += direction_x * 16 * time.dt
            if random.random() < 0.015: is_paused, pause_timer, direction_x = True, 1.2, direction_x * -1
        elif map_index == 2 or map_index == 3:
            target.x += direction_x * (20 if map_index == 2 else 25) * time.dt
            if random.random() < 0.03: target_y = random.choice([1, 8, 4])
            target.y = lerp(target.y, target_y, time.dt * 5)
            if map_index == 3 and random.random() < 0.02: 
                is_paused, pause_timer, direction_x = True, 0.4, direction_x * -1

    if target.x > 23: direction_x = -1
    elif target.x < -23: direction_x = 1

    if mouse.hovered_entity == target: time_on_target += time.dt
    acc = (time_on_target / total_time_passed) * 100 if total_time_passed > 0 else 100
    precision_hud.text = f'{int(acc)}%'
    timer_hud.text = f'TIEMPO: {int(max(0, time_limit - total_time_passed))}s'
    if total_time_passed >= time_limit: end_game(acc)

def start_game():
    global is_playing, total_time_passed, time_on_target, target_y, target_z
    is_playing, total_time_passed, time_on_target, target_y, target_z = True, 0, 0, 3, 20
    set_menu_state('playing')
    start_txt.text = "" 
    target.enabled = True
    target.position = (0, 3, 20)
    target.model = 'cube'
    target.scale = (2, 4, 0.5)
    
    if current_level == 'easy':
        if map_index == 2: target.scale = (1.5, 4, 1.5)
        if map_index == 3: target.model, target.scale = 'sphere', (2, 2, 2)
    elif current_level == 'medium' and map_index == 2:
        target.scale = (1.5, 4, 1.5)
    elif current_level == 'hard':
        target.scale = (1.2, 1.2, 0.5)

    player.enabled, mouse.locked, precision_hud.enabled, timer_hud.enabled = True, True, True, True

def end_game(acc):
    global is_playing
    is_playing = False
    guardar_record(acc)
    target.enabled = player.enabled = mouse.locked = precision_hud.enabled = timer_hud.enabled = False
    set_menu_state('main')

app.run()