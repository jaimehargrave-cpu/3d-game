from pathlib import Path
import math
import random
import struct
import tempfile
import wave

from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController

app = Ursina()
window.title = 'Neon Strike FPS'
window.color = color.rgb(8, 10, 20)
window.fps_counter.enabled = True
window.exit_button.visible = False
mouse.visible = True

MAP_SIZE = 120
MAP_HALF = MAP_SIZE / 2

# Small synthesized sounds keep the project self-contained; no sound assets required.
def make_tone(path, frequency, duration, volume=0.25, noise=False):
    sample_rate = 22050
    count = int(sample_rate * duration)
    with wave.open(str(path), 'wb') as audio_file:
        audio_file.setparams((1, 2, sample_rate, count, 'NONE', 'not compressed'))
        samples = bytearray()
        for index in range(count):
            t = index / sample_rate
            envelope = max(0.0, 1.0 - t / duration) ** 2
            sample = random.uniform(-1, 1) if noise else math.sin(2 * math.pi * frequency * t)
            samples.extend(struct.pack('<h', int(32767 * volume * envelope * sample)))
        audio_file.writeframes(samples)

_sound_dir = Path(tempfile.gettempdir()) / 'neon_strike_sounds'
_sound_dir.mkdir(exist_ok=True)
for _name, _freq, _duration, _noise in (
    ('shot.wav', 110, 0.12, True),
    ('hit.wav', 620, 0.09, False),
    ('reload.wav', 240, 0.22, False),
    ('hurt.wav', 85, 0.18, False),
    ('empty.wav', 360, 0.06, False),
):
    _path = _sound_dir / _name
    if not _path.exists():
        make_tone(_path, _freq, _duration, noise=_noise)

sounds = {name: Audio(str(_sound_dir / f'{name}.wav'), autoplay=False) for name in ('shot', 'hit', 'reload', 'hurt', 'empty')}

# Game state
player_health = 100
score = 0
wave = 1
game_state = 'menu'  # menu, playing, paused, game_over
current_weapon = 'Rifle'
reload_timer = 0.0
fire_timer = 0.0
damage_timer = 0.0
enemies = []
world_entities = []
weapons = {
    'Pistol': {'mag_size': 12, 'ammo': 12, 'reserve': 60, 'damage': 1, 'rate': 0.28, 'range': 55},
    'Rifle': {'mag_size': 30, 'ammo': 30, 'reserve': 120, 'damage': 1, 'rate': 0.095, 'range': 85},
}

# HUD and menu
hud = Text(text='', position=(-0.86, 0.46), scale=1.05, color=color.white, background=True, enabled=False)
status_text = Text(text='', position=(-0.86, 0.39), scale=0.9, color=color.azure, background=True, enabled=False)
menu_backdrop = Entity(parent=camera.ui, model='quad', scale=(2, 2), color=color.rgba(4, 8, 18, 230), enabled=True)
menu_title = Text(parent=camera.ui, text='NEON STRIKE', origin=(0, 0), y=0.24, scale=3, color=color.azure, enabled=True)
menu_subtitle = Text(parent=camera.ui, text='SURVIVE THE SWARM', origin=(0, 0), y=0.12, scale=1.1, color=color.white, enabled=True)
menu_hint = Text(parent=camera.ui, text='WASD move  |  Mouse aim  |  Left click fire\n1 / 2 switch weapon  |  R reload  |  Space jump  |  Esc pause', origin=(0, 0), y=-0.08, scale=0.9, color=color.light_gray, enabled=True)
start_button = Button(parent=camera.ui, text='START GAME', scale=(0.28, 0.08), y=-0.25, color=color.azure, highlight_color=color.cyan, enabled=True)
start_button.on_click = lambda: start_game()

# Player and first-person weapon model
player = FirstPersonController(position=(0, 2, 0), speed=9, jump_height=1.5, gravity=1.8)
player.cursor.visible = False
player.mouse_sensitivity = Vec2(40, 40)
player.height = 2
player.camera_pivot.y = 1.7
player.enabled = False

weapon_model = Entity(parent=camera.ui, model='cube', color=color.gray, scale=(0.16, 0.14, 0.62), position=(0.55, -0.42, 0.8), rotation=(8, 0, 0), enabled=False)
weapon_grip = Entity(parent=weapon_model, model='cube', color=color.dark_gray, scale=(0.65, 1.2, 0.35), position=(0, -0.75, -0.1))

# Map: broad arena, perimeter walls, cover, and landmarks.
ground = Entity(model='plane', scale=(MAP_SIZE, 1, MAP_SIZE), texture='grass', texture_scale=(60, 60), color=color.rgb(35, 44, 49), collider='box')
world_entities.append(ground)
for side in (-1, 1):
    for pos in (Vec3(side * MAP_HALF, 5, 0), Vec3(0, 5, side * MAP_HALF)):
        wall = Entity(model='cube', position=pos, scale=(2, 10, MAP_SIZE), color=color.rgb(24, 35, 48), collider='box') if pos.x else Entity(model='cube', position=pos, scale=(MAP_SIZE, 10, 2), color=color.rgb(24, 35, 48), collider='box')
        world_entities.append(wall)

cover_positions = []
for x in range(-45, 46, 15):
    for z in range(-45, 46, 15):
        if abs(x) < 12 and abs(z) < 12:
            continue
        if random.random() < 0.58:
            cover_positions.append((x + random.uniform(-3, 3), z + random.uniform(-3, 3)))
for index, (x, z) in enumerate(cover_positions):
    size_x = random.choice((3, 4, 6))
    size_z = random.choice((3, 4, 6))
    height = random.choice((2.5, 3.5, 5))
    block = Entity(model='cube', position=(x, height / 2, z), scale=(size_x, height, size_z), color=color.rgb(35 + index % 20, 50, 70), collider='box')
    world_entities.append(block)

# Colorful beacons help orient the player in the expanded arena.
for x, z, tint in ((-48, -48, color.cyan), (48, -48, color.orange), (-48, 48, color.lime), (48, 48, color.violet)):
    beacon = Entity(model='cube', position=(x, 2, z), scale=(1, 4, 1), color=tint, collider='box')
    world_entities.append(beacon)


def play_sound(name):
    sound = sounds[name]
    sound.stop()
    sound.play()


def update_hud():
    weapon = weapons[current_weapon]
    reload_label = '  RELOADING' if reload_timer > 0 else ''
    hud.text = f'HEALTH {max(0, int(player_health))}    SCORE {score}    WAVE {wave}\n{current_weapon}  {weapon["ammo"]}/{weapon["reserve"]}{reload_label}'


def set_menu(title, subtitle, button_label, show_button=True):
    menu_backdrop.enabled = True
    menu_title.enabled = True
    menu_title.text = title
    menu_subtitle.enabled = True
    menu_subtitle.text = subtitle
    menu_hint.enabled = title == 'NEON STRIKE'
    start_button.enabled = show_button
    start_button.text = button_label
    mouse.locked = False
    mouse.visible = True


def clear_enemies():
    for enemy in enemies[:]:
        destroy(enemy)
    enemies.clear()


def start_game():
    global player_health, score, wave, game_state, current_weapon, reload_timer
    clear_enemies()
    player_health, score, wave = 100, 0, 1
    current_weapon = 'Rifle'
    reload_timer = 0
    for data in weapons.values():
        data['ammo'] = data['mag_size']
    player.position = Vec3(0, 2, 0)
    player.rotation = Vec3(0, 0, 0)
    player.enabled = True
    weapon_model.enabled = True
    hud.enabled = True
    status_text.enabled = False
    menu_hint.enabled = False
    menu_backdrop.enabled = False
    menu_title.enabled = False
    menu_subtitle.enabled = False
    start_button.enabled = False
    game_state = 'playing'
    mouse.locked = True
    mouse.visible = False
    spawn_wave()
    update_hud()


def pause_game():
    global game_state
    if game_state != 'playing':
        return
    game_state = 'paused'
    set_menu('PAUSED', 'Take a breather. The arena is waiting.', 'RESUME')
    start_button.on_click = resume_game


def resume_game():
    global game_state
    if game_state != 'paused':
        return
    game_state = 'playing'
    menu_backdrop.enabled = False
    menu_title.enabled = False
    menu_subtitle.enabled = False
    menu_hint.enabled = False
    start_button.enabled = False
    mouse.locked = True
    mouse.visible = False


def finish_game():
    global game_state
    if game_state == 'game_over':
        return
    game_state = 'game_over'
    player.enabled = False
    weapon_model.enabled = False
    set_menu('MISSION FAILED', f'Final score: {score}   |   Wave reached: {wave}', 'PLAY AGAIN')
    start_button.on_click = start_game


def spawn_enemy():
    for _ in range(80):
        pos = Vec3(random.uniform(-MAP_HALF + 8, MAP_HALF - 8), 1, random.uniform(-MAP_HALF + 8, MAP_HALF - 8))
        if distance(pos, player.position) > 22:
            enemy = Entity(model='cube', position=pos, scale=(1.2, 2, 1.2), color=color.rgb(220, 55, 75), collider='box')
            enemy.health = 2 + wave // 4
            enemy.speed = random.uniform(2.5, 3.4) + min(wave * 0.08, 1.4)
            enemy.attack_cooldown = random.uniform(0.1, 0.8)
            enemy.strafe_sign = random.choice((-1, 1))
            enemy.strafe_timer = random.uniform(1.0, 3.0)
            enemy.state = 'approach'
            enemy.roam_target = pos
            enemies.append(enemy)
            return


def spawn_wave():
    count = min(5 + wave * 2, 30)
    for _ in range(count):
        spawn_enemy()
    status_text.text = f'WAVE {wave} INCOMING'
    status_text.enabled = True
    invoke(setattr, status_text, 'enabled', False, delay=2)


def reload_weapon():
    global reload_timer
    weapon = weapons[current_weapon]
    if reload_timer > 0 or weapon['ammo'] == weapon['mag_size'] or weapon['reserve'] <= 0:
        return
    reload_timer = 1.15 if current_weapon == 'Rifle' else 0.9
    play_sound('reload')
    update_hud()


def finish_reload():
    global reload_timer
    weapon = weapons[current_weapon]
    amount = min(weapon['mag_size'] - weapon['ammo'], weapon['reserve'])
    weapon['ammo'] += amount
    weapon['reserve'] -= amount
    reload_timer = 0
    update_hud()


def switch_weapon(name):
    global current_weapon, reload_timer
    if name not in weapons or current_weapon == name:
        return
    current_weapon = name
    reload_timer = 0
    weapon_model.color = color.gray if name == 'Rifle' else color.rgb(165, 175, 190)
    weapon_model.scale = (0.16, 0.14, 0.62) if name == 'Rifle' else (0.13, 0.12, 0.42)
    update_hud()


def shoot():
    global fire_timer
    if game_state != 'playing' or reload_timer > 0 or fire_timer > 0:
        return
    weapon = weapons[current_weapon]
    if weapon['ammo'] <= 0:
        play_sound('empty')
        status_text.text = 'OUT OF AMMO — PRESS R TO RELOAD'
        status_text.enabled = True
        invoke(setattr, status_text, 'enabled', False, delay=1.2)
        return
    weapon['ammo'] -= 1
    fire_timer = weapon['rate']
    play_sound('shot')
    weapon_model.position = Vec3(0.55, -0.42, 0.8) + Vec3(0, 0, -0.08)
    invoke(setattr, weapon_model, 'position', Vec3(0.55, -0.42, 0.8), delay=0.06)

    hit = raycast(camera.world_position + camera.forward * 0.5, camera.forward, distance=weapon['range'], ignore=[player, weapon_model])
    if hit.hit and hasattr(hit.entity, 'health'):
        hit.entity.health -= weapon['damage']
        play_sound('hit')
        hit_marker.enabled = True
        invoke(setattr, hit_marker, 'enabled', False, delay=0.12)
        if hit.entity.health <= 0:
            if hit.entity in enemies:
                enemies.remove(hit.entity)
            destroy(hit.entity)
            add_score(10)
    update_hud()


def add_score(points):
    global score, wave
    score += points
    if not enemies and game_state == 'playing':
        wave += 1
        spawn_wave()


def clear_path(origin, direction, length):
    obstacle = raycast(origin, direction, distance=length, ignore=[player])
    return not obstacle.hit


def update_enemies():
    global player_health, damage_timer
    for enemy in enemies[:]:
        to_player = player.position - enemy.position
        to_player.y = 0
        distance_to_player = to_player.length()
        if distance_to_player < 0.001:
            continue
        forward = to_player.normalized()
        enemy.look_at(player.position + Vec3(0, 1, 0), 'y')
        enemy.attack_cooldown = max(0, enemy.attack_cooldown - time.dt)
        enemy.strafe_timer -= time.dt
        if enemy.strafe_timer <= 0:
            enemy.strafe_sign *= -1
            enemy.strafe_timer = random.uniform(1.2, 2.8)

        # Pursue when far; circle and lunge at close range. Probe ahead and sidestep cover.
        side = Vec3(-forward.z, 0, forward.x) * enemy.strafe_sign
        if distance_to_player > 9:
            move_direction = forward
            enemy.state = 'approach'
        else:
            move_direction = (forward * 0.35 + side * 0.9).normalized()
            enemy.state = 'flank'
        if not clear_path(enemy.position + Vec3(0, 0.8, 0), move_direction, 2.0):
            alternate = Vec3(-move_direction.z, 0, move_direction.x)
            if not clear_path(enemy.position + Vec3(0, 0.8, 0), alternate, 2.5):
                alternate = -alternate
            move_direction = alternate
        enemy.position += move_direction * enemy.speed * time.dt

        if distance_to_player < 1.8 and enemy.attack_cooldown <= 0 and damage_timer <= 0:
            player_health -= 12
            damage_timer = 0.45
            enemy.attack_cooldown = 1.0
            play_sound('hurt')
            if player_health <= 0:
                player_health = 0
                update_hud()
                finish_game()
                return
    update_hud()


# Hit marker and minimal crosshair
crosshair = Text(parent=camera.ui, text='+', origin=(0, 0), scale=1.3, color=color.white, enabled=False)
hit_marker = Text(parent=camera.ui, text='×', origin=(0, 0), scale=1.5, color=color.orange, enabled=False)


def input(key):
    global game_state
    if key == 'escape':
        if game_state == 'playing':
            pause_game()
        elif game_state == 'paused':
            resume_game()
        return
    if game_state != 'playing':
        if key == 'enter' and game_state in ('menu', 'game_over'):
            start_game()
        return
    if key == 'left mouse down':
        shoot()
    elif key == 'r':
        reload_weapon()
    elif key == '1':
        switch_weapon('Pistol')
    elif key == '2':
        switch_weapon('Rifle')


def update():
    global fire_timer, reload_timer, damage_timer
    if game_state != 'playing':
        return
    fire_timer = max(0, fire_timer - time.dt)
    damage_timer = max(0, damage_timer - time.dt)
    if reload_timer > 0:
        reload_timer -= time.dt
        if reload_timer <= 0:
            finish_reload()
    update_enemies()
    if player.position.y < -10:
        player.position = Vec3(0, 2, 0)
    update_hud()


# Friendly start menu is the initial state; gameplay begins only after pressing Start.
set_menu('NEON STRIKE', 'SURVIVE THE SWARM', 'START GAME')
start_button.on_click = start_game
app.run()
