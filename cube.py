import pygame
import random
import sys
import math
import numpy as np

# Preinitialize the mixer (we aim for mono, but if it defaults to stereo, we'll reshape)
pygame.mixer.pre_init(44100, -16, 1, 512)
pygame.init()

# Grid dimensions (x, y are ground plane, z is vertical height)
GRID_WIDTH = 16
GRID_DEPTH = 16
GRID_HEIGHT = 16  # number of vertical layers

# Isometric drawing parameters
TILE_WIDTH = 40    # width of the diamond (top face)
TILE_HEIGHT = 20   # height of the diamond (top face)
CUBE_HEIGHT = TILE_HEIGHT  # vertical height of the cube

# Simulation parameters
FPS = 5
# 3D rules: using B6/S567 (dead cell becomes alive if exactly 6 neighbors, live cell survives if 5-7 neighbors)
BIRTH_COUNT = 6
SURVIVE_COUNTS = {5, 6, 7}

# ROYGBIV colors
ROYGBIV = [
    (255, 0, 0),      # Red
    (255, 127, 0),    # Orange
    (255, 255, 0),    # Yellow
    (0, 255, 0),      # Green
    (0, 0, 255),      # Blue
    (75, 0, 130),     # Indigo
    (148, 0, 211)     # Violet
]

# Screen dimensions (adjust as needed)
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("3D Isometric ROYGBIV Life with Pentatonic Sound")
clock = pygame.time.Clock()

def darken(color, factor):
    """Darken a color by a given factor (0 < factor < 1)."""
    return tuple(max(0, int(c * factor)) for c in color)

# Create a 3D grid. Each cell is either None (dead) or a color tuple (alive).
def create_grid(w, d, h):
    return [[[None for _ in range(h)] for _ in range(d)] for _ in range(w)]

grid = create_grid(GRID_WIDTH, GRID_DEPTH, GRID_HEIGHT)

# Seed the grid randomly (~20% alive)
for x in range(GRID_WIDTH):
    for y in range(GRID_DEPTH):
        for z in range(GRID_HEIGHT):
            if random.random() < 0.2:
                grid[x][y][z] = random.choice(ROYGBIV)

# Setup pentatonic scale notes.
# We'll use a pentatonic major scale: intervals in semitones: 0, 2, 4, 7, 9
base_frequency = 220.0  # Base frequency (A3)
pentatonic_intervals = [0, 2, 4, 7, 9]
pentatonic_frequencies = [base_frequency * (2 ** (i/12)) for i in pentatonic_intervals]

def generate_tone(frequency, duration=0.3, volume=0.5, sample_rate=44100):
    """Generate a pygame Sound object for a sine wave of a given frequency."""
    n_samples = int(sample_rate * duration)
    t = np.linspace(0, duration, n_samples, False)
    wave = np.sin(2 * np.pi * frequency * t)
    # Scale to 16-bit signed integers
    wave = (wave * 32767 * volume).astype(np.int16)
    # Reshape to 2D array if needed (for stereo: shape = (n_samples, channels))
    if pygame.mixer.get_init()[2] == 1:
        # Mono expected, but if it complains, force shape (n_samples, 1)
        wave = wave.reshape(-1, 1)
    else:
        # For stereo, duplicate channels
        wave = np.column_stack((wave, wave))
    sound = pygame.sndarray.make_sound(wave)
    return sound

# Pre-generate sound objects for our pentatonic frequencies.
pentatonic_sounds = [generate_tone(freq) for freq in pentatonic_frequencies]

def play_random_pentatonic():
    """Play a random note from the pentatonic scale."""
    sound = random.choice(pentatonic_sounds)
    sound.play()

def count_neighbors(x, y, z, grid):
    count = 0
    for dx in [-1, 0, 1]:
        for dy in [-1, 0, 1]:
            for dz in [-1, 0, 1]:
                if dx == 0 and dy == 0 and dz == 0:
                    continue
                nx, ny, nz = x + dx, y + dy, z + dz
                if 0 <= nx < GRID_WIDTH and 0 <= ny < GRID_DEPTH and 0 <= nz < GRID_HEIGHT:
                    if grid[nx][ny][nz] is not None:
                        count += 1
    return count

def update_grid(old_grid):
    new_grid = create_grid(GRID_WIDTH, GRID_DEPTH, GRID_HEIGHT)
    # Track birth events to trigger sound
    for x in range(GRID_WIDTH):
        for y in range(GRID_DEPTH):
            for z in range(GRID_HEIGHT):
                neighbors = count_neighbors(x, y, z, old_grid)
                if old_grid[x][y][z] is not None:
                    # Live cell survival rule
                    if neighbors in SURVIVE_COUNTS:
                        new_grid[x][y][z] = old_grid[x][y][z]
                    else:
                        new_grid[x][y][z] = None
                else:
                    # Birth rule
                    if neighbors == BIRTH_COUNT:
                        new_grid[x][y][z] = random.choice(ROYGBIV)
                        play_random_pentatonic()  # Play a note when a cell is born
                    else:
                        new_grid[x][y][z] = None
    return new_grid

def iso_projection(x, y, z):
    """
    Convert 3D grid coordinates (x, y, z) to 2D isometric screen coordinates.
    x and y are the ground plane; z is vertical.
    """
    screen_x = (x - y) * (TILE_WIDTH // 2)
    screen_y = (x + y) * (TILE_HEIGHT // 2)
    screen_y -= z * CUBE_HEIGHT  # account for vertical height
    offset_x = SCREEN_WIDTH // 2
    offset_y = SCREEN_HEIGHT // 2
    return int(screen_x + offset_x), int(screen_y + offset_y)

def draw_cube(surface, pos, color):
    """
    Draw an isometric cube at screen position pos.
    pos corresponds to the top center of the cube's top face.
    """
    x, y = pos
    # Top face diamond (clockwise order)
    top = [
        (x, y),  # top center
        (x + TILE_WIDTH // 2, y + TILE_HEIGHT // 2),
        (x, y + TILE_HEIGHT),
        (x - TILE_WIDTH // 2, y + TILE_HEIGHT // 2)
    ]
    
    # Left face
    left = [
        top[3],
        top[2],
        (top[2][0], top[2][1] + CUBE_HEIGHT),
        (top[3][0], top[3][1] + CUBE_HEIGHT)
    ]
    
    # Right face
    right = [
        top[1],
        top[2],
        (top[2][0], top[2][1] + CUBE_HEIGHT),
        (top[1][0], top[1][1] + CUBE_HEIGHT)
    ]
    
    left_color = darken(color, 0.8)
    right_color = darken(color, 0.6)
    
    pygame.draw.polygon(surface, left_color, left)
    pygame.draw.polygon(surface, right_color, right)
    pygame.draw.polygon(surface, color, top)
    # Optional outlines
    pygame.draw.polygon(surface, (50, 50, 50), top, 1)
    pygame.draw.polygon(surface, (50, 50, 50), left, 1)
    pygame.draw.polygon(surface, (50, 50, 50), right, 1)

def draw_grid(surface, grid):
    surface.fill((10, 10, 10))
    # For proper overlapping, sort cells by depth (x + y + z)
    cells = []
    for x in range(GRID_WIDTH):
        for y in range(GRID_DEPTH):
            for z in range(GRID_HEIGHT):
                if grid[x][y][z] is not None:
                    depth = x + y + z
                    cells.append((depth, x, y, z, grid[x][y][z]))
    cells.sort(key=lambda t: t[0])
    
    for _, x, y, z, color in cells:
        screen_pos = iso_projection(x, y, z)
        draw_cube(surface, screen_pos, color)

def main():
    global grid
    running = True
    paused = False

    while running:
        clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            # Toggle pause/resume with the spacebar.
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    paused = not paused

        if not paused:
            grid = update_grid(grid)
        draw_grid(screen, grid)
        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
