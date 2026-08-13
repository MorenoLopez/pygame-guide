#!/usr/bin/env python3
"""
Pygame Platformer - A Mario-like game built with Pygame..

Controls:
    LEFT/RIGHT ARROWS or A/D  - Move
    SPACE or UP ARROW or W    - Jump
    ESC                       - Pause/Menu
    R                         - Restart level
"""

import pygame
import sys
import os
import math
import random
from enum import Enum

# =============================================================================
# CONSTANTS
# =============================================================================
SCREEN_WIDTH = 960
SCREEN_HEIGHT = 640
FPS = 60
TILE_SIZE = 32
GRAVITY = 0.6
JUMP_STRENGTH = -12
PLAYER_SPEED = 5
MAX_FALL_SPEED = 12

# Colors
SKY_BLUE = (135, 206, 235)
DARK_BLUE = (25, 25, 40)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GOLD = (255, 215, 0)
RED = (220, 50, 50)
GREEN = (50, 200, 50)

# =============================================================================
# ASSET LOADING
# =============================================================================
def load_image(name, scale=None):
    """Load and optionally scale an image from the ./assets/images folder."""
    path = os.path.join("assets", "images", f"{name}.png")
    if not os.path.exists(path):
        # Fallback: create a colored surface
        surf = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
        surf.fill((200, 50, 50, 180))
        return surf
    img = pygame.image.load(path).convert_alpha()
    if scale:
        img = pygame.transform.scale(img, scale)
    return img

# =============================================================================
# GAME STATES
# =============================================================================
class GameState(Enum):
    MENU = 0
    PLAYING = 1
    PAUSED = 2
    GAME_OVER = 3
    LEVEL_COMPLETE = 4
    VICTORY = 5

# =============================================================================
# CAMERA
# =============================================================================
class Camera:
    """A simple camera that follows the player with smooth interpolation."""
    def __init__(self, width, height):
        self.camera = pygame.Rect(0, 0, width, height)
        self.width = width
        self.height = height
        self.smoothness = 0.1

    def apply(self, entity):
        """Apply camera offset to an entity rect."""
        return entity.rect.move(self.camera.topleft)

    def apply_rect(self, rect):
        """Apply camera offset to a raw rect."""
        return rect.move(self.camera.topleft)

    def update(self, target):
        """Smoothly follow the target."""
        x = -target.rect.centerx + int(SCREEN_WIDTH / 2)
        y = -target.rect.centery + int(SCREEN_HEIGHT / 2)

        # Clamp to level bounds
        x = min(0, x)
        y = min(0, y)
        if hasattr(target, 'level_width') and target.level_width > 0:
            x = max(-(target.level_width - SCREEN_WIDTH), x)
        if hasattr(target, 'level_height') and target.level_height > 0:
            y = max(-(target.level_height - SCREEN_HEIGHT), y)
        else:
            y = max(-(20 * TILE_SIZE - SCREEN_HEIGHT), y)

        # Smooth interpolation
        self.camera.x += int((x - self.camera.x) * self.smoothness)
        self.camera.y += int((y - self.camera.y) * self.smoothness)

# =============================================================================
# PLAYER
# =============================================================================
class Player(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.images = {
            'idle': load_image("player_idle"),
            'run1': load_image("player_run1"),
            'run2': load_image("player_run2"),
            'jump': load_image("player_jump"),
        }
        self.image = self.images['idle']
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y
        self.vel_x = 0
        self.vel_y = 0
        self.on_ground = False
        self.facing_right = True
        self.animation_timer = 0
        self.animation_frame = 0
        self.lives = 3
        self.coins = 0
        self.invincible = 0
        self.dead = False
        self.level_width = 0
        self.level_height = 0

    def update(self, platforms, enemies, spikes, coins_group, flags):
        if self.dead:
            self.vel_y += GRAVITY
            self.rect.y += self.vel_y
            return False

        # Invincibility frames
        if self.invincible > 0:
            self.invincible -= 1

        keys = pygame.key.get_pressed()
        self.vel_x = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.vel_x = -PLAYER_SPEED
            self.facing_right = False
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.vel_x = PLAYER_SPEED
            self.facing_right = True

        # Jump
        if (keys[pygame.K_SPACE] or keys[pygame.K_UP] or keys[pygame.K_w]) and self.on_ground:
            self.vel_y = JUMP_STRENGTH
            self.on_ground = False

        # Gravity
        self.vel_y += GRAVITY
        if self.vel_y > MAX_FALL_SPEED:
            self.vel_y = MAX_FALL_SPEED

        # Horizontal movement + collision
        self.rect.x += self.vel_x
        self._check_collision(platforms, 'x')

        # Vertical movement + collision
        self.rect.y += self.vel_y
        self.on_ground = False
        self._check_collision(platforms, 'y')

        # Level bounds
        if self.rect.left < 0:
            self.rect.left = 0
        if self.rect.right > self.level_width:
            self.rect.right = self.level_width
        if self.rect.top > self.level_height + 100:
            self.die()

        # Enemy collision
        if self.invincible == 0:
            for enemy in enemies:
                if self.rect.colliderect(enemy.rect):
                    # Mario-style stomp: if falling and hitting top of enemy
                    if self.vel_y > 0 and self.rect.bottom <= enemy.rect.centery + 8:
                        enemy.kill()
                        self.vel_y = -8
                        self.coins += 5
                    else:
                        self.take_damage()

        # Spike collision
        if self.invincible == 0:
            for spike in spikes:
                if self.rect.colliderect(spike.rect):
                    self.take_damage()

        # Coin collection
        for coin in coins_group:
            if self.rect.colliderect(coin.rect):
                coin.collect()
                self.coins += 1

        # Flag collision (level complete)
        for flag in flags:
            if self.rect.colliderect(flag.rect):
                return True  # Level complete

        # Animation
        self._animate()
        return False

    def _check_collision(self, platforms, direction):
        for platform in platforms:
            if self.rect.colliderect(platform.rect):
                if direction == 'x':
                    if self.vel_x > 0:
                        self.rect.right = platform.rect.left
                    elif self.vel_x < 0:
                        self.rect.left = platform.rect.right
                    self.vel_x = 0
                elif direction == 'y':
                    if self.vel_y > 0:
                        self.rect.bottom = platform.rect.top
                        self.vel_y = 0
                        self.on_ground = True
                    elif self.vel_y < 0:
                        self.rect.top = platform.rect.bottom
                        self.vel_y = 0
                        # Hit a question block from below
                        if hasattr(platform, 'on_hit'):
                            platform.on_hit()

    def _animate(self):
        if not self.on_ground:
            self.image = self.images['jump']
        elif self.vel_x != 0:
            self.animation_timer += 1
            if self.animation_timer > 8:
                self.animation_timer = 0
                self.animation_frame = 1 - self.animation_frame
            self.image = self.images[f'run{self.animation_frame + 1}']
        else:
            self.image = self.images['idle']

        if not self.facing_right:
            self.image = pygame.transform.flip(self.image, True, False)

        # Blink when invincible
        if self.invincible > 0 and self.invincible % 6 < 3:
            self.image = self.image.copy()
            self.image.fill((255, 255, 255, 128), special_flags=pygame.BLEND_RGBA_MULT)

    def take_damage(self):
        self.lives -= 1
        self.invincible = 90
        self.vel_y = -6
        if self.lives <= 0:
            self.die()

    def die(self):
        self.dead = True
        self.vel_y = -10

    def reset(self, x, y):
        self.rect.x = x
        self.rect.y = y
        self.vel_x = 0
        self.vel_y = 0
        self.dead = False
        self.invincible = 0

# =============================================================================
# PLATFORM / TILE
# =============================================================================
class Platform(pygame.sprite.Sprite):
    def __init__(self, x, y, tile_type='grass'):
        super().__init__()
        self.tile_type = tile_type
        self.image = load_image(f"tile_{tile_type}")
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y
        self.bumped = False

    def on_hit(self):
        if self.tile_type == 'question' and not self.bumped:
            self.bumped = True
            self.image = load_image("tile_brick")

# =============================================================================
# ENEMY
# =============================================================================
class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y, patrol_distance=100):
        super().__init__()
        self.image = load_image("enemy")
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y
        self.start_x = x
        self.patrol_distance = patrol_distance
        self.speed = 2
        self.direction = 1
        self.vel_y = 0

    def update(self, platforms):
        # Horizontal patrol
        self.rect.x += self.speed * self.direction
        if abs(self.rect.x - self.start_x) > self.patrol_distance:
            self.direction *= -1
            self.image = pygame.transform.flip(self.image, True, False)

        # Gravity
        self.vel_y += GRAVITY
        self.rect.y += self.vel_y

        # Platform collision (only for ground)
        for platform in platforms:
            if self.rect.colliderect(platform.rect):
                if self.vel_y > 0 and self.rect.bottom <= platform.rect.centery + 10:
                    self.rect.bottom = platform.rect.top
                    self.vel_y = 0

# =============================================================================
# SPIKE
# =============================================================================
class Spike(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = load_image("spike")
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y

# =============================================================================
# COIN
# =============================================================================
class Coin(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = load_image("coin")
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y
        self.base_y = y
        self.float_offset = random.random() * 6.28
        self.collected = False

    def update(self):
        self.float_offset += 0.1
        self.rect.y = self.base_y + int(math.sin(self.float_offset) * 4)

    def collect(self):
        self.collected = True
        self.kill()

# =============================================================================
# FLAG (END OF LEVEL)
# =============================================================================
class Flag(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = load_image("flag")
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y - 32  # Adjust for flag height

# =============================================================================
# DECORATION (Clouds, bushes, mountains - non-collidable)
# =============================================================================
class Decoration(pygame.sprite.Sprite):
    def __init__(self, x, y, deco_type):
        super().__init__()
        self.image = load_image(deco_type)
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y

# =============================================================================
# PARTICLE
# =============================================================================
class Particle:
    def __init__(self, x, y, color, velocity, lifetime):
        self.x = x
        self.y = y
        self.color = color
        self.vx, self.vy = velocity
        self.lifetime = lifetime
        self.max_lifetime = lifetime
        self.size = 4

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.2
        self.lifetime -= 1
        self.size = max(1, int(4 * (self.lifetime / self.max_lifetime)))

    def draw(self, surface, camera):
        pos = (int(self.x + camera.camera.x), int(self.y + camera.camera.y))
        pygame.draw.circle(surface, self.color, pos, self.size)

# =============================================================================
# LEVEL
# =============================================================================
class Level:
    """Parses a level map and creates all game objects."""

    # Legend:
    # # = grass/dirt block
    # B = brick block
    # ? = question block
    # . = dirt (underground)
    # P = player start
    # E = enemy
    # S = spike
    # C = coin
    # F = flag (end)
    # ^ = cloud
    # * = bush
    # M = mountain
    #   = empty

    def __init__(self, level_data):
        self.platforms = pygame.sprite.Group()
        self.enemies = pygame.sprite.Group()
        self.spikes = pygame.sprite.Group()
        self.coins = pygame.sprite.Group()
        self.flags = pygame.sprite.Group()
        self.decorations = pygame.sprite.Group()
        self.particles = []
        self.player_start = (100, 300)
        self.width = 0
        self.height = 0
        self._parse(level_data)

    def _parse(self, level_data):
        lines = level_data.strip().split('\n')
        self.height = len(lines) * TILE_SIZE
        self.width = max(len(line) for line in lines) * TILE_SIZE

        for row_idx, line in enumerate(lines):
            for col_idx, char in enumerate(line):
                x = col_idx * TILE_SIZE
                y = row_idx * TILE_SIZE

                if char == '#':
                    self.platforms.add(Platform(x, y, 'grass'))
                elif char == '.':
                    self.platforms.add(Platform(x, y, 'dirt'))
                elif char == 'B':
                    self.platforms.add(Platform(x, y, 'brick'))
                elif char == '?':
                    self.platforms.add(Platform(x, y, 'question'))
                elif char == 'P':
                    self.player_start = (x, y)
                elif char == 'E':
                    self.enemies.add(Enemy(x, y, patrol_distance=80))
                elif char == 'S':
                    self.spikes.add(Spike(x, y))
                elif char == 'C':
                    self.coins.add(Coin(x, y))
                elif char == 'F':
                    self.flags.add(Flag(x, y))
                elif char == '^':
                    self.decorations.add(Decoration(x, y - 16, 'cloud'))
                elif char == '*':
                    self.decorations.add(Decoration(x, y, 'bush'))
                elif char == 'M':
                    self.decorations.add(Decoration(x, y - 32, 'mountain'))

    def update(self):
        self.enemies.update(self.platforms)
        self.coins.update()
        for p in self.particles[:]:
            p.update()
            if p.lifetime <= 0:
                self.particles.remove(p)

    def draw(self, surface, camera):
        # Draw decorations first (background)
        for deco in self.decorations:
            surface.blit(deco.image, camera.apply(deco))
        # Draw platforms
        for platform in self.platforms:
            surface.blit(platform.image, camera.apply(platform))
        # Draw spikes
        for spike in self.spikes:
            surface.blit(spike.image, camera.apply(spike))
        # Draw coins
        for coin in self.coins:
            surface.blit(coin.image, camera.apply(coin))
        # Draw enemies
        for enemy in self.enemies:
            surface.blit(enemy.image, camera.apply(enemy))
        # Draw flag
        for flag in self.flags:
            surface.blit(flag.image, camera.apply(flag))
        # Draw particles
        for p in self.particles:
            p.draw(surface, camera)

# =============================================================================
# LEVEL DATA
# =============================================================================
LEVELS = [
    # Level 1 - Tutorial
    """
M                          ^                 *                      M
M              ^                    ^        C   C                  M
M     *              *         B       B                            M
M                                                ^                  M
M          C   C   C       B     ?  B                    B          M
M                            B      B             *                 M
M            B          B          BB   B       B                   M
M      B   B                     BBB               B                M
M                B     BB  B                       B   B            M
M  P     B       B     BB  B      B       B       B              F  M
######  ###########   #################  #############   #   ########
......  ...........   .................  .............   .   ........
......  ...........   .................  .............   .   ........
""",
    # Level 2 - Enemies
    """
M                          ^                 *                      M
M              ^                  E  ^        C                     M
M     *              *         BBBBB   B                            M
M                                                ^                  M
M          C   C   C       B     ?  B                    B          M
M                            B      B             *                 M
M     E      B          B          BB   B       B                   M
M     BB   B               E     BBB               B                M
M                B     BB  B                       B B B            M
M  P     B       B     BB  B      B       B   E      B           F  M
######  ###########   #################  #############   #   ########
......  ...........   .................  .............   .   ........
......  ...........   .................  .............   .   ........
""",
    # Level 3 - Challenge
    """
M                          ^                 *                          M
M              ^                  E  ^        C   C                     M
M     *              *         BBBBB   B                                M
M                                                ^                      M
M              C           B     ?  B              B     B              M
M                            B      B             *B                    M
M     E      B          B          BB   B       B                       M
M     BB   B               E     BBB               B                    M
M            C   B     BB  B      C                B B B                M
M  P     B       B     BB  B      B       B   E      B                F M
######  ###########   #################  #############   #      #########
......  ...........   .................  .............   .      .........
......  ...........   .................  .............   .      .........
"""
]

# =============================================================================
# UI / HUD
# =============================================================================
class UI:
    def __init__(self):
        self.font_large = pygame.font.Font(None, 48)
        self.font_medium = pygame.font.Font(None, 36)
        self.font_small = pygame.font.Font(None, 28)
        self.heart_img = load_image("heart", (20, 20))
        self.coin_img = load_image("coin", (16, 16))

    def draw_hud(self, surface, player, level_num, total_levels):
        # Background bar
        bar = pygame.Surface((SCREEN_WIDTH, 40), pygame.SRCALPHA)
        bar.fill((20, 20, 30, 200))
        surface.blit(bar, (0, 0))
        pygame.draw.line(surface, (60, 60, 80), (0, 40), (SCREEN_WIDTH, 40), 2)

        # Lives
        for i in range(player.lives):
            surface.blit(self.heart_img, (10 + i * 26, 10))

        # Coins
        surface.blit(self.coin_img, (120, 12))
        coin_text = self.font_small.render(f"x {player.coins}", True, GOLD)
        surface.blit(coin_text, (140, 10))

        # Level
        level_text = self.font_small.render(f"Level {level_num + 1}/{total_levels}", True, WHITE)
        surface.blit(level_text, (SCREEN_WIDTH - 120, 10))

    def draw_menu(self, surface):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.fill(BLACK)
        overlay.set_alpha(180)
        surface.blit(overlay, (0, 0))

        title = self.font_large.render("PYGAME PLATFORMER", True, GOLD)
        surface.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 180))

        subtitle = self.font_medium.render("Press SPACE to Start", True, WHITE)
        surface.blit(subtitle, (SCREEN_WIDTH//2 - subtitle.get_width()//2, 280))

        controls = self.font_small.render("ARROWS/WASD to Move  |  SPACE to Jump  |  ESC to Pause", True, (180, 180, 180))
        surface.blit(controls, (SCREEN_WIDTH//2 - controls.get_width()//2, 340))

    def draw_pause(self, surface):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.fill(BLACK)
        overlay.set_alpha(160)
        surface.blit(overlay, (0, 0))

        title = self.font_large.render("PAUSED", True, WHITE)
        surface.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 250))

        subtitle = self.font_small.render("Press ESC to Resume  |  R to Restart  |  Q to Quit", True, (180, 180, 180))
        surface.blit(subtitle, (SCREEN_WIDTH//2 - subtitle.get_width()//2, 320))

    def draw_game_over(self, surface, won=False):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.fill(BLACK)
        overlay.set_alpha(200)
        surface.blit(overlay, (0, 0))

        if won:
            title = self.font_large.render("YOU WIN!", True, GREEN)
            msg = self.font_medium.render("Press R to Play Again  |  Q to Quit", True, GOLD)
        else:
            title = self.font_large.render("GAME OVER", True, RED)
            msg = self.font_medium.render("Press R to Retry  |  Q to Quit", True, WHITE)

        surface.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 240))
        surface.blit(msg, (SCREEN_WIDTH//2 - msg.get_width()//2, 310))

    def draw_level_complete(self, surface):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.fill(BLACK)
        overlay.set_alpha(160)
        surface.blit(overlay, (0, 0))

        title = self.font_large.render("LEVEL COMPLETE!", True, GREEN)
        surface.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 260))

        subtitle = self.font_small.render("Press SPACE to Continue", True, WHITE)
        surface.blit(subtitle, (SCREEN_WIDTH//2 - subtitle.get_width()//2, 330))

# =============================================================================
# GAME CLASS
# =============================================================================
class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Pygame Platformer - Learning Project")
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.ui = UI()
        self.state = GameState.MENU
        self.current_level = 0
        self.player = None
        self.level = None
        self.camera = None
        self.total_coins = 0

    def load_level(self, level_idx):
        if level_idx >= len(LEVELS):
            self.state = GameState.VICTORY
            return

        self.level = Level(LEVELS[level_idx])
        self.player = Player(*self.level.player_start)
        self.player.level_width = self.level.width
        self.player.level_height = self.level.height
        self.camera = Camera(self.level.width, self.level.height)
        self.state = GameState.PLAYING

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                self._handle_input(event)

            self._update()
            self._draw()
            pygame.display.flip()

        pygame.quit()
        sys.exit()

    def _handle_input(self, event):
        if event.type == pygame.KEYDOWN:
            if self.state == GameState.MENU:
                if event.key == pygame.K_SPACE:
                    self.load_level(0)
            elif self.state == GameState.PLAYING:
                if event.key == pygame.K_ESCAPE:
                    self.state = GameState.PAUSED
                elif event.key == pygame.K_r:
                    self.load_level(self.current_level)
            elif self.state == GameState.PAUSED:
                if event.key == pygame.K_ESCAPE:
                    self.state = GameState.PLAYING
                elif event.key == pygame.K_r:
                    self.load_level(self.current_level)
                elif event.key == pygame.K_q:
                    self.state = GameState.MENU
            elif self.state == GameState.LEVEL_COMPLETE:
                if event.key == pygame.K_SPACE:
                    self.current_level += 1
                    self.load_level(self.current_level)
            elif self.state in (GameState.GAME_OVER, GameState.VICTORY):
                if event.key == pygame.K_r:
                    self.current_level = 0
                    self.total_coins = 0
                    self.load_level(0)
                elif event.key == pygame.K_q:
                    self.state = GameState.MENU

    def _update(self):
        if self.state == GameState.PLAYING:
            self.level.update()
            level_done = self.player.update(
                self.level.platforms,
                self.level.enemies,
                self.level.spikes,
                self.level.coins,
                self.level.flags
            )
            self.camera.update(self.player)

            if self.player.dead and self.player.rect.top > SCREEN_HEIGHT + 100:
                if self.player.lives > 0:
                    self.player.reset(*self.level.player_start)
                else:
                    self.state = GameState.GAME_OVER

            if level_done:
                self.total_coins += self.player.coins
                self.state = GameState.LEVEL_COMPLETE

    def _draw(self):
        # Sky background
        self.screen.fill(SKY_BLUE)

        if self.state in (GameState.PLAYING, GameState.PAUSED):
            self.level.draw(self.screen, self.camera)
            self.screen.blit(self.player.image, self.camera.apply(self.player))
            self.ui.draw_hud(self.screen, self.player, self.current_level, len(LEVELS))

        if self.state == GameState.MENU:
            self.ui.draw_menu(self.screen)
        elif self.state == GameState.PAUSED:
            self.ui.draw_pause(self.screen)
        elif self.state == GameState.LEVEL_COMPLETE:
            self.ui.draw_level_complete(self.screen)
        elif self.state in (GameState.GAME_OVER, GameState.VICTORY):
            self.ui.draw_game_over(self.screen, won=(self.state == GameState.VICTORY))

# =============================================================================
# MAIN ENTRY POINT
# =============================================================================
if __name__ == "__main__":
    game = Game()
    game.run()
