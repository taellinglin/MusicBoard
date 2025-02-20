import os
import pygame
import mido
import random
import sys
import math
import numpy as np
import argparse
import colorsys

# ---------------------------
# Configuration and Constants
# ---------------------------
CELL_SIZE = 10              # Cell size in pixels for clarity
GRID_COLS = 96 * 2          # 96 * 20 = 1920 width
GRID_ROWS = 54 * 2          # Grid height will be ~935 px; we'll center vertically
FPS = 60
TRANSITION_DURATION = 0.5    # Seconds to interpolate between grid updates
TRANSITION_FRAMES = int(FPS * TRANSITION_DURATION)

# Base ROYGBIV colors (RGB tuples)
ROYGBIV = [
    (255, 64, 64),    # Red
    (255, 165, 64),   # Orange
    (255, 255, 64),   # Yellow
    (64, 255, 64),    # Green
    (64, 64, 255),    # Blue
    (138, 43, 226),   # Indigo
    (186, 85, 211)    # Violet
]

# Period (in ms) for the rapid color cycle
COLOR_CYCLE_PERIOD = 500

# War rule parameters: if a neighbor's phase offset exceeds the cell's by this threshold,
# then with probability WAR_PROBABILITY the cell adopts that neighbor’s attributes.
WAR_THRESHOLD = 0.2
WAR_PROBABILITY = 0.5

# Calculate triangle height for equilateral triangles
TRI_HEIGHT = CELL_SIZE * math.sqrt(3) / 2
GRID_WIDTH = GRID_COLS * CELL_SIZE
GRID_HEIGHT = int(GRID_ROWS * TRI_HEIGHT)

# ---------------------------
# Helper Functions for Color & Geometry
# ---------------------------
def shift_hue(color, new_hue):
    """
    Given an RGBA color (with RGB in 0-255), convert to HSV,
    set the hue to new_hue (in [0,1]), then convert back.
    The alpha channel is preserved.
    """
    r, g, b, a = color
    r_f, g_f, b_f = r / 255.0, g / 255.0, b / 255.0
    h, s, v = colorsys.rgb_to_hsv(r_f, g_f, b_f)
    new_r, new_g, new_b = colorsys.hsv_to_rgb(new_hue, s, v)
    return (int(new_r * 255), int(new_g * 255), int(new_b * 255), a)

def scale_polygon(points, scale):
    """
    Scale a polygon (list of (x,y) points) about its centroid by 'scale'.
    """
    cx = sum(p[0] for p in points) / len(points)
    cy = sum(p[1] for p in points) / len(points)
    new_points = []
    for x, y in points:
        new_points.append((cx + (x - cx) * scale, cy + (y - cy) * scale))
    return new_points

def lerp_color(c1, c2, t):
    """
    Linear interpolation between two RGBA colors.
    """
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(4))

def lerp_cell(cell1, cell2, t):
    """
    Interpolate between two cell dictionaries.
    For simplicity, we linearly interpolate only the base color.
    Offset and scale are taken from cell1.
    """
    if cell1 is None and cell2 is None:
        return None
    if cell1 is None:
        return cell2
    if cell2 is None:
        return cell1
    interp_color = lerp_color(cell1["color"], cell2["color"], t)
    return {"color": interp_color, "offset": cell1["offset"], "scale": cell1["scale"]}

# ---------------------------
# MIDI File Loading & Parsing
# ---------------------------
def get_sorted_midi_files():
    """Return a sorted list of all MIDI files (.mid) in the current directory."""
    files = sorted([f for f in os.listdir('.') if f.endswith('.mid')])
    if not files:
        raise FileNotFoundError("No .mid files found in the current directory.")
    return files

def extract_midi_events(midi_filename):
    """
    Parse the MIDI file and extract note_on events (with velocity > 0)
    along with their absolute times in ms.
    Returns a sorted list of tuples: (abs_time_ms, msg)
    """
    try:
        mid = mido.MidiFile(midi_filename)
    except Exception as e:
        print(f"Error loading MIDI file: {e}")
        sys.exit(1)
    
    abs_time = 0
    events = []
    for msg in mid:
        abs_time += msg.time * 1000  # convert seconds to milliseconds
        if msg.type == 'note_on' and msg.velocity > 0:
            events.append((abs_time, msg))
    events.sort(key=lambda x: x[0])
    return events

# Get sorted list of MIDI files and initialize with the first file.
midi_files = get_sorted_midi_files()
current_midi_index = 0
current_midi_file = midi_files[current_midi_index]
print(f"Now playing MIDI file: {current_midi_file}")
midi_events = extract_midi_events(current_midi_file)
print(f"Loaded MIDI file '{current_midi_file}' with {len(midi_events)} note events.")

# ---------------------------
# Pygame Initialization (Fullscreen)
# ---------------------------
pygame.init()
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
pygame.display.set_caption("Pyramidal Game of Life - MIDI Edition")
clock = pygame.time.Clock()
full_screen_size = screen.get_size()

# Create a surface for the grid with per-pixel alpha support
grid_surface = pygame.Surface((GRID_WIDTH, GRID_HEIGHT), pygame.SRCALPHA)

# ---------------------------
# Sound Setup
# ---------------------------
pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)
pygame.mixer.set_num_channels(128)

# Load percussion samples (ensure these files are in your working directory)
kick = pygame.mixer.Sound("kick.wav")
snare = pygame.mixer.Sound("snare.wav")
hihat = pygame.mixer.Sound("hihat.wav")

# Load note sample from note.wav (our base melodic sample)
base_note_sound = pygame.mixer.Sound("note.wav")
base_note_array = pygame.sndarray.array(base_note_sound)
BASE_NOTE_FREQ = 110.0

# ---------------------------
# Precompute Triangle Points (for the pyramidal grid)
# ---------------------------
cell_points = [[None for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
for r in range(GRID_ROWS):
    for c in range(GRID_COLS):
        x = c * CELL_SIZE
        y = r * TRI_HEIGHT
        if (r + c) % 2 == 0:
            pts = [(x + CELL_SIZE / 2, y),
                   (x, y + TRI_HEIGHT),
                   (x + CELL_SIZE, y + TRI_HEIGHT)]
        else:
            pts = [(x, y),
                   (x + CELL_SIZE, y),
                   (x + CELL_SIZE / 2, y + TRI_HEIGHT)]
        cell_points[r][c] = pts

# ---------------------------
# Cellular Automata Setup
# ---------------------------
def create_grid(rows, cols):
    return [[None for _ in range(cols)] for _ in range(rows)]

# Global grids for the cellular automata.
current_grid = create_grid(GRID_ROWS, GRID_COLS)
target_grid = [row.copy() for row in current_grid]

# Function to clear the board.
def clear_board():
    global current_grid, target_grid
    current_grid = [[None for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
    target_grid = [[None for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]

# Initialize current_grid with random cells (each cell is a dict)
for r in range(GRID_ROWS):
    for c in range(GRID_COLS):
        if random.random() < 0.2:
            base_color = random.choice(ROYGBIV) + (255,)
            current_grid[r][c] = {
                "color": base_color,
                "offset": random.random(),  # phase offset in [0,1)
                "scale": random.uniform(0.5, 1.5)
            }
target_grid = [row.copy() for row in current_grid]

def count_neighbors(r, c, grid):
    count = 0
    for dr in [-1, 0, 1]:
        for dc in [-1, 0, 1]:
            if dr == 0 and dc == 0:
                continue
            rr, cc = r + dr, c + dc
            if 0 <= rr < GRID_ROWS and 0 <= cc < GRID_COLS and grid[rr][cc] is not None:
                count += 1
    return count

def update_logic(grid):
    """
    Standard Game-of-Life update on our grid of cells.
    For cells born (neighbors==3) assign a new cell with random attributes.
    Then apply the war rules.
    """
    new_grid = create_grid(GRID_ROWS, GRID_COLS)
    for r in range(GRID_ROWS):
        for c in range(GRID_COLS):
            neighbors = count_neighbors(r, c, grid)
            if grid[r][c] is not None:
                # Survival rule: live cell survives with 2 or 3 neighbors.
                new_grid[r][c] = grid[r][c] if neighbors in [2, 3] else None
            else:
                if neighbors == 3:
                    new_grid[r][c] = {
                        "color": random.choice(ROYGBIV) + (255,),
                        "offset": random.random(),
                        "scale": random.uniform(0.5, 1.5)
                    }
                else:
                    new_grid[r][c] = None
    # Apply war rules to simulate color/offset conflicts.
    new_grid = apply_war_rules(new_grid)
    return new_grid

def apply_war_rules(grid):
    """
    For each live cell, check neighbors. If a neighbor’s offset exceeds
    the cell’s offset by at least WAR_THRESHOLD, then with probability WAR_PROBABILITY
    the cell adopts that neighbor’s attributes.
    """
    new_grid = [row.copy() for row in grid]
    for r in range(GRID_ROWS):
        for c in range(GRID_COLS):
            cell = grid[r][c]
            if cell is not None:
                for dr in [-1, 0, 1]:
                    for dc in [-1, 0, 1]:
                        if dr == 0 and dc == 0:
                            continue
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < GRID_ROWS and 0 <= cc < GRID_COLS:
                            neighbor = grid[rr][cc]
                            if neighbor is not None:
                                if (neighbor["offset"] - cell["offset"]) > WAR_THRESHOLD:
                                    if random.random() < WAR_PROBABILITY:
                                        new_grid[r][c] = neighbor.copy()
    return new_grid

# ---------------------------
# Pitch Shifting Function (Covering All Octaves)
# ---------------------------
def pitch_shift(sound_array, factor):
    num_samples = int(len(sound_array) / factor)
    indices = np.arange(num_samples) * factor
    new_array = np.zeros((num_samples, sound_array.shape[1]), dtype=sound_array.dtype)
    for channel in range(sound_array.shape[1]):
        new_array[:, channel] = np.interp(indices, np.arange(len(sound_array)), sound_array[:, channel])
    return new_array

# ---------------------------
# Sound Playback Functions
# ---------------------------
def play_pitch_shifted_note(target_freq, velocity, col):
    factor = target_freq / BASE_NOTE_FREQ
    shifted_array = pitch_shift(base_note_array, factor)
    pan = col / GRID_COLS  # 0.0 (left) to 1.0 (right)
    volume = velocity / 127.0
    shifted_array = shifted_array.astype(np.float32)
    shifted_array[:, 0] *= volume * (1 - pan)
    shifted_array[:, 1] *= volume * pan
    shifted_array = np.clip(shifted_array, -32768, 32767).astype(np.int16)
    new_sound = pygame.sndarray.make_sound(shifted_array)
    new_sound.play()

def play_drum(note):
    if note in [35, 36]:
        kick.play()
    elif note in [38, 40]:
        snare.play()
    elif note in [42, 44, 46]:
        hihat.play()
    else:
        hihat.play()  # Default

# ---------------------------
# Add a Piece to the Board from a MIDI Note
# ---------------------------
def add_piece_to_board(note, velocity):
    """
    Adds a 3x3 block to the board:
      - Map the note (roughly 21-108) to a horizontal position.
      - Map velocity (0-127) to a vertical position.
      - Create a new cell with a base color from ROYGBIV,
        a random phase offset, and a scale determined by velocity.
    """
    min_note = 21
    max_note = 108
    clamped_note = max(min_note, min(note, max_note))
    col = int(((clamped_note - min_note) / (max_note - min_note)) * (GRID_COLS - 3))
    row = int((velocity / 127) * (GRID_ROWS - 3))
    base_color = random.choice(ROYGBIV) + (255,)
    new_cell = {
        "color": base_color,
        "offset": random.random(),
        "scale": 0.5 + (velocity / 127.0)  # scale in [0.5, 1.5]
    }
    for dr in range(3):
        for dc in range(3):
            r = row + dr
            c = col + dc
            if 0 <= r < GRID_ROWS and 0 <= c < GRID_COLS:
                current_grid[r][c] = new_cell

# ---------------------------
# Grid Drawing Function (with Rapid Color Cycling, War Offset, and Scaling)
# ---------------------------
def draw_interpolated_grid(surface, current_grid, target_grid, t):
    # Clear the grid surface.
    surface.fill((20, 20, 20, 0))
    time_ms = pygame.time.get_ticks()
    for r in range(GRID_ROWS):
        for c in range(GRID_COLS):
            cell_current = current_grid[r][c]
            cell_target = target_grid[r][c]
            # Interpolate cells if both exist; otherwise pick one.
            if cell_current is not None and cell_target is not None:
                effective_cell = lerp_cell(cell_current, cell_target, t)
            else:
                effective_cell = cell_current if cell_current is not None else cell_target

            if effective_cell is not None:
                # Compute effective hue based on global time and the cell's phase offset.
                phase = ((time_ms / COLOR_CYCLE_PERIOD) + effective_cell["offset"]) % 1.0
                effective_color = shift_hue(effective_cell["color"], phase)
                # Scale the cell's triangle polygon.
                poly = scale_polygon(cell_points[r][c], effective_cell["scale"])
                pygame.draw.polygon(surface, effective_color, poly)
            # Draw cell borders with full opacity.
            pygame.draw.polygon(surface, (80, 80, 80, 255), cell_points[r][c], 2)

# ---------------------------
# Global Variables for Interpolation and MIDI Scheduling
# ---------------------------
transition_counter = 0
start_time = pygame.time.get_ticks()

# ---------------------------
# Main Loop
# ---------------------------
def main():
    global current_grid, target_grid, transition_counter
    global current_midi_index, current_midi_file, midi_events, start_time, pending_midi_events

    running = True
    paused = False

    # Clear and seed initial grid.
    clear_board()
    for r in range(GRID_ROWS):
        for c in range(GRID_COLS):
            if random.random() < 0.2:
                base_color = random.choice(ROYGBIV) + (255,)
                current_grid[r][c] = {
                    "color": base_color,
                    "offset": random.random(),
                    "scale": random.uniform(0.5, 1.5)
                }
    target_grid[:] = [row.copy() for row in current_grid]
    transition_counter = 0

    # Initialize pending MIDI events based on current playback time.
    current_play_time = pygame.time.get_ticks() - start_time
    pending_midi_events = [(t, msg) for (t, msg) in midi_events if t >= current_play_time]

    # Dictionary to track whether an arrow key is already pressed (for debouncing)
    arrow_key_pressed = {pygame.K_LEFT: False, pygame.K_RIGHT: False}

    while running:
        dt = clock.tick(FPS)
        current_play_time = pygame.time.get_ticks() - start_time

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                # Debounce arrow keys so holding one doesn't skip multiple songs.
                if event.key in arrow_key_pressed and not arrow_key_pressed[event.key]:
                    arrow_key_pressed[event.key] = True
                    if event.key == pygame.K_SPACE:
                        paused = not paused
                    elif event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_RIGHT:
                        # Song skipper: clear board and load next MIDI file.
                        clear_board()
                        current_midi_index = (current_midi_index + 1) % len(midi_files)
                        current_midi_file = midi_files[current_midi_index]
                        print(f"Now playing MIDI file: {current_midi_file}")
                        midi_events = extract_midi_events(current_midi_file)
                        start_time = pygame.time.get_ticks()
                        pending_midi_events = [(t, msg) for (t, msg) in midi_events]
                    elif event.key == pygame.K_LEFT:
                        # Song backker: clear board and load previous MIDI file.
                        clear_board()
                        current_midi_index = (current_midi_index - 1) % len(midi_files)
                        current_midi_file = midi_files[current_midi_index]
                        print(f"Now playing MIDI file: {current_midi_file}")
                        midi_events = extract_midi_events(current_midi_file)
                        start_time = pygame.time.get_ticks()
                        pending_midi_events = [(t, msg) for (t, msg) in midi_events]
                elif event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key == pygame.K_ESCAPE:
                    running = False

            elif event.type == pygame.KEYUP:
                if event.key in arrow_key_pressed:
                    arrow_key_pressed[event.key] = False

        # Process pending MIDI events.
        while pending_midi_events and pending_midi_events[0][0] <= current_play_time:
            sched_time, msg = pending_midi_events.pop(0)
            if msg.channel == 9:
                play_drum(msg.note)
            else:
                target_freq = 440 * (2 ** ((msg.note - 69) / 12))
                col = random.randint(0, GRID_COLS - 1)
                play_pitch_shifted_note(target_freq, msg.velocity, col)
                add_piece_to_board(msg.note, msg.velocity)

        # Auto-advance to next song if finished.
        if not pending_midi_events:
            clear_board()
            current_midi_index = (current_midi_index + 1) % len(midi_files)
            current_midi_file = midi_files[current_midi_index]
            print(f"Now playing MIDI file: {current_midi_file}")
            midi_events = extract_midi_events(current_midi_file)
            start_time = pygame.time.get_ticks()
            pending_midi_events = [(t, msg) for (t, msg) in midi_events]

        if not paused:
            transition_counter += 1
            if transition_counter >= TRANSITION_FRAMES:
                new_grid = update_logic(current_grid)
                current_grid = new_grid
                target_grid = update_logic(current_grid)
                transition_counter = 0
            t = transition_counter / TRANSITION_FRAMES
        else:
            t = 0

        draw_interpolated_grid(grid_surface, current_grid, target_grid, t)
        # Center the grid_surface on the fullscreen display.
        x_pos = (full_screen_size[0] - GRID_WIDTH) // 2
        y_pos = (full_screen_size[1] - GRID_HEIGHT) // 2
        screen.fill((0, 0, 0))
        screen.blit(grid_surface, (x_pos, y_pos))
        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
