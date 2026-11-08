from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
import random

app = Ursina()
window.title = 'Neon Strike FPS'
window.color = color.rgba(8, 10, 20, 255)
window.fps_counter.enabled = True
window.exit_button.visible = False

# --- Game state ---
player_health = 100
score = 0
wave = 1
game_over = False
enemies = []

def reset_game():
    global player_health, score, wave, game_over
    player_health = 100
    score = 0
    wave = 1
    game_over = False
    for enemy in enemies:
        destroy(enemy)
    enemies.clear()
    spawn_wave()
    hud.text = 'Health: 100 | Score: 0 | Wave: 1'
    game_text.enabled = False
    restart_text.enabled = False
    mouse.locked = True
    player.position = Vec3(0, 2, 0)
    player.rotation_y = 0

# --- HUD ---
hud = Text(
    text='Health: 100 | Score: 0 | Wave: 1',
    position=(-0.8, 0.45),
    origin=(0, 0),
    scale=1.4,
    color=color.white,
    background=True,
)

game_text = Text(
    text='MISSION FAILED',
    origin=(0, 0),
    position=(0, 0.1),
    scale=2.2,
    color=color.red,
    enabled=False,
)

restart_text = Text(
    text='Press R to restart',
    origin=(0, 0),
    position=(0, -0.15),
    scale=1.2,
    color=color.white,
    enabled=False,
)

# --- World ---
Entity(model='plane', scale=(50, 1, 50), texture='grass', texture_scale=(50, 50), color=color.rgb(14, 20, 28))

for x in (-18, 18):
    for z in (-18, 18):
        if abs(x) < 10 and abs(z) < 10:
            continue
        wall = Entity(
            model='cube',
            position=(x, 2, z),
            scale=(2, 4, 2),
            color=color.rgb(27, 36, 48),
            collider='box',
        )

# --- Player ---
player = FirstPersonController(
    position=(0, 2, 0),
    speed=8,
    jump_height=0,
    gravity=2,
)
player.cursor.visible = False
player.mouse_sensitivity = Vec2(60, 60)
player.height = 2
player.camera_pivot.y = 1.7

# Add a simple gun model to the camera
weapon = Entity(parent=camera.ui, model='cube', color=color.gray, scale=(0.18, 0.18, 0.8), position=(0.55, -0.45, 1), rotation=(10, 0, 0))
weapon.texture = None

# --- Enemy logic ---
def spawn_enemy():
    valid = False
    while not valid:
        x = random.randint(-20, 20)
        z = random.randint(-20, 20)
        pos = Vec3(x, 1, z)
        valid = distance(pos, player.position) > 12

    enemy = Entity(
        model='cube',
        position=pos,
        scale=(1, 2, 1),
        color=color.red,
        collider='box',
    )
    enemy.health = 2
    enemy.speed = random.uniform(2.2, 3.8)
    enemies.append(enemy)


def spawn_wave():
    global wave
    for _ in range(5 + wave * 2):
        spawn_enemy()


def update_hud():
    hud.text = f'Health: {int(player_health)} | Score: {score} | Wave: {wave}'


def shoot():
    if game_over:
        return

    hit = raycast(camera.world_position + camera.forward * 1.5, camera.forward, distance=60, ignore=[player])
    if hit.hit:
        if hasattr(hit.entity, 'health'):
            hit.entity.health -= 1
            if hit.entity.health <= 0:
                destroy(hit.entity)
                enemies.remove(hit.entity)
                update_score(10)

    # hit marker flash
    weapon.rotation_x = 20
    invoke(setattr, weapon, 'rotation_x', 0, delay=0.08)


def update_score(points):
    global score
    score += points
    if not enemies:
        global wave
        wave += 1
        spawn_wave()


def update_enemies():
    global player_health, game_over

    for enemy in enemies[:]:
        if enemy not in enemies:
            continue

        direction = player.position - enemy.position
        direction.y = 0
        if direction.length() > 0:
            direction = direction.normalized()
            enemy.position += direction * enemy.speed * time.dt
            enemy.look_at(player.position + Vec3(0, 1, 0), 'y')

        pa = player.position
        pb = enemy.position
        if distance(pa, pb) < 1.7:
            player_health -= 24 * time.dt
            if player_health <= 0:
                player_health = 0
                game_over = True
                game_text.enabled = True
                restart_text.enabled = True
                mouse.locked = False
                game_text.text = 'MISSION FAILED'
                break

    update_hud()


def input(key):
    if game_over:
        if key == 'r':
            reset_game()
        return

    if key == 'left mouse down':
        shoot()
    elif key == 'space':
        player.jump()
    elif key == 'r':
        reset_game()


def update():
    if game_over:
        return

    update_enemies()
    if len(enemies) == 0:
        wave += 1
        spawn_wave()

    if player.position.y < -10:
        player.position = Vec3(0, 2, 0)

    update_hud()


# --- Start state ---
reset_game()

app.run()
