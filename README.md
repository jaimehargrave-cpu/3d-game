from ursina import *
from random import uniform

app = Ursina()
window.title = 'Neon Siege'
window.color = color.rgb(8, 10, 20)
window.fps_counter.enabled = True
window.exit_button.visible = False

# HUD
health_text = Text(text='Health: 100', position=(-0.85, 0.45), scale=1.5, origin=(0, 0), color=color.white)
score_text = Text(text='Score: 0', position=(0.6, 0.45), scale=1.5, origin=(0, 0), color=color.cyan)

# World
Entity(model='plane', scale=(50, 1, 50), texture='grass', texture_scale=(50, 50), color=color.rgb(20, 28, 38))
for x in (-18, 18):
    for z in (-18, 18):
        pillar = Entity(model='cube', position=(x, 2.5, z), scale=(2, 5, 2), color=color.rgb(30, 40, 55), collider='box')
        pillar.y = 2.5

class Player(Entity):
    def __init__(self):
        super().__init__(model='cube', color=color.azure, scale=(1, 1.8, 1), position=(0, 0.9, 0), collider='box')
        self.speed = 8
        self.health = 100
        self.score = 0
        self.fire_cooldown = 0
        self.rotation_y = 0

    def update(self):
        self.fire_cooldown = max(0, self.fire_cooldown - time.dt)

        move = Vec3(0, 0, 0)
        if held_keys['w']:
            move += Vec3(0, 0, 1)
        if held_keys['s']:
            move += Vec3(0, 0, -1)
        if held_keys['a']:
            move += Vec3(-1, 0, 0)
        if held_keys['d']:
            move += Vec3(1, 0, 0)

        if move.length() > 0:
            move = move.normalized() * self.speed * time.dt
            self.position += move.rotated_y(self.rotation_y)

        self.position.x = clamp(self.position.x, -18, 18)
        self.position.z = clamp(self.position.z, -18, 18)

        # mouse look
        self.rotation_y += mouse.velocity[0] * 0.2
        camera.position = lerp(camera.position, self.position + Vec3(0, 4.5, -8).rotated_y(self.rotation_y), 6 * time.dt)
        camera.look_at(self.position + Vec3(0, 1, 0))

        if mouse.left and self.fire_cooldown <= 0:
            shoot()
            self.fire_cooldown = 0.12

        health_text.text = f'Health: {int(self.health)}'
        score_text.text = f'Score: {self.score}'

player = Player()


enemies = []

def spawn_enemy():
    while True:
        pos = Vec3(uniform(-15, 15), 0.9, uniform(-15, 15))
        if distance(pos, player.position) > 8:
            enemy = Entity(model='cube', color=color.red, scale=(1, 2, 1), position=pos, collider='box')
            enemy.health = 2
            enemy.speed = 3.2
            enemies.append(enemy)
            return

for _ in range(8):
    spawn_enemy()


class Bullet(Entity):
    def __init__(self, start, direction):
        super().__init__(model='sphere', color=color.cyan, scale=0.2, position=start)
        self.direction = direction.normalized()
        self.speed = 28
        self.life = 2

    def update(self):
        self.position += self.direction * self.speed * time.dt
        self.life -= time.dt

        if self.life <= 0:
            destroy(self)
            return

        for enemy in enemies:
            if enemy.enabled and distance(self.position, enemy.position) < 1.0:
                enemy.health -= 1
                destroy(self)
                if enemy.health <= 0:
                    destroy(enemy)
                    enemies.remove(enemy)
                    player.score += 10
                    spawn_enemy()
                return


def shoot():
    muzzle = player.position + Vec3(0, 0.7, 0) + camera.forward * 1.5
    Bullet(muzzle, camera.forward)


def update_enemies():
    for enemy in enemies:
        if not enemy.enabled:
            continue
        direction = player.position - enemy.position
        direction.y = 0
        if direction.length() > 0:
            direction = direction.normalized()
            enemy.position += direction * enemy.speed * time.dt
        enemy.look_at(player.position + Vec3(0, 0.5, 0), 'y')

        if distance(enemy.position, player.position) < 1.5:
            player.health -= 22 * time.dt
            if player.health <= 0:
                destroy(player)
                Text('Mission Failed', origin=(0, 0), position=(0, 0), scale=3, color=color.red)
                mouse.locked = False
                invoke(setattr, window, 'exit_button', None, delay=0.1)


def update():
    update_enemies()
    if player.health <= 0:
        return

    # keep mouse locked to the window for aim
    mouse.locked = True
    player.update()

    # win condition in a basic way
    if player.score >= 200:
        Text('Victory!', origin=(0, 0), position=(0, 0), scale=3, color=color.green)
        mouse.locked = False

# prevent accidental window exit
window.exit_button.visible = False

app.run()
