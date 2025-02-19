import os
import pygame
import mido
import random
import sys
import math
import numpy as np
import argparse


# ---------------------------
# Configuration and Constants
# ---------------------------
# For a 1920x1080 display:
CELL_SIZE = 10              # Cell size in pixels for clarity
GRID_COLS = 96*2              # 96 * 20 = 1920 width
GRID_ROWS = 54*2              # Grid height will be ~935 px; we'll center vertically
FPS = 60
TRANSITION_DURATION = 0.5   # Seconds to interpolate between grid updates
TRANSITION_FRAMES = int(FPS * TRANSITION_DURATION)

# ROYGBIV colors with enhanced brightness (for the board)
ROYGBIV = [
    (255, 64, 64),    # Brighter Red
    (255, 165, 64),   # Brighter Orange
    (255, 255, 64),   # Brighter Yellow
    (64, 255, 64),    # Brighter Green
    (64, 64, 255),    # Brighter Blue
    (138, 43, 226),   # Brighter Indigo
    (186, 85, 211)    # Brighter Violet
]

# Calculate triangle height for equilateral triangles
TRI_HEIGHT = CELL_SIZE * math.sqrt(3) / 2
GRID_WIDTH = GRID_COLS * CELL_SIZE
GRID_HEIGHT = int(GRID_ROWS * TRI_HEIGHT)

# ---------------------------
# MIDI File Loading & Parsing
# ---------------------------
def choose_random_midi():
    # List all files in the current working directory
    files = [f for f in os.listdir('.') if f.endswith('.mid')]

    # Check if there are any .mid files
    if not files:
        raise FileNotFoundError("No .mid files found in the current directory.")
    
    # Choose a random .mid file from the list
    chosen_file = random.choice(files)
    return chosen_file

# Usage
try:
    midi_file = choose_random_midi()
    print(f"Chosen MIDI file: {midi_file}")
    # Load or process the MIDI file as needed
except FileNotFoundError as e:
    print(e)

def extract_midi_events(midi_filename):
    """
    Parse the MIDI file and extract note_on events (with velocity > 0) along with their absolute times in ms.
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

midi_filename = choose_random_midi()
if not midi_filename:
    print("No MIDI (.mid) file found in the current directory.")
    sys.exit(1)

midi_events = extract_midi_events(midi_filename)
print(f"Loaded MIDI file '{midi_filename}' with {len(midi_events)} note events.")

# ---------------------------
# Pygame Initialization (Fullscreen)
# ---------------------------
pygame.init()
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
pygame.display.set_caption("Pyramidal Game of Life - MIDI Edition")
clock = pygame.time.Clock()
full_screen_size = screen.get_size()

# Create a surface for the grid (size of the grid)
grid_surface = pygame.Surface((GRID_WIDTH, GRID_HEIGHT))

# ---------------------------
# Sound Setup
# ---------------------------
pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)
pygame.mixer.set_num_channels(128)

# Load percussion samples (ensure these files are in your working directory)
kick = pygame.mixer.Sound("kick.wav")
snare = pygame.mixer.Sound("snare.wav")
hihat = pygame.mixer.Sound("hihat.wav")

# Load note sample from note.wav (this is our base melodic sample)
base_note_sound = pygame.mixer.Sound("note.wav")
# Convert note.wav to a numpy array for pitch shifting (assumed stereo, 16-bit)
base_note_array = pygame.sndarray.array(base_note_sound)
# Define the base frequency of note.wav.
# Adjust this if your note.wav sample's pitch is different.
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

current_grid = create_grid(GRID_ROWS, GRID_COLS)  # current state
target_grid = create_grid(GRID_ROWS, GRID_COLS)   # next state

# Randomly seed the initial grid (20% chance alive with a random ROYGBIV color)
for r in range(GRID_ROWS):
    for c in range(GRID_COLS):
        current_grid[r][c] = random.choice(ROYGBIV) if random.random() < 0.2 else None
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
    new_grid = create_grid(GRID_ROWS, GRID_COLS)
    for r in range(GRID_ROWS):
        for c in range(GRID_COLS):
            neighbors = count_neighbors(r, c, grid)
            if grid[r][c] is not None:
                new_grid[r][c] = grid[r][c] if neighbors in [2, 3] else None
            else:
                new_grid[r][c] = random.choice(ROYGBIV) if neighbors == 3 else None
    return new_grid

# ---------------------------
# Color Interpolation Function
# ---------------------------
def lerp_color(c1, c2, t):
    # Handle cases where c1 or c2 might be None
    if c1 is None:
        c1 = (0, 0, 0)  # Default to black if c1 is None
    if c2 is None:
        c2 = (0, 0, 0)  # Default to black if c2 is None
    
    # Perform linear interpolation between c1 and c2 for each color channel (RGB)
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


# ---------------------------
# Pitch Shifting Function (Covering All Octaves)
# ---------------------------
def pitch_shift(sound_array, factor):
    """
    Resamples the numpy array 'sound_array' by the given factor.
    Here, factor = target_freq / BASE_NOTE_FREQ and can be any positive number.
    """
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
    """
    Play note.wav pitch-shifted to target_freq.
    Volume is set based on MIDI velocity (0-127 mapped to 0.0-1.0).
    Panning is based on the provided column (0 to GRID_COLS-1).
    """
    factor = target_freq / BASE_NOTE_FREQ  # No clamping: cover all octaves!
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
    """
    Map common drum MIDI note numbers to our percussion samples.
    Typically:
      - Kick: MIDI note 35 or 36
      - Snare: MIDI note 38 or 40
      - Hi-hat: MIDI note 42, 44, or 46
    """
    if note in [35, 36]:
        kick.play()
    elif note in [38, 40]:
        snare.play()
    elif note in [42, 44, 46]:
        hihat.play()
    else:
        hihat.play()  # Default to hi-hat

# ---------------------------
# Add a Piece to the Board from a MIDI Note
# ---------------------------
def add_piece_to_board(note, velocity):
    """
    Adds a 3x3 block of cells to the board based on the MIDI note's pitch and velocity.
    - The note (range roughly 21-108) maps to a horizontal position.
    - The velocity (0-127) maps to a vertical position.
    - The color is chosen from ROYGBIV based on the note value.
    """
    # Define MIDI note range (typical piano range)
    min_note = 21
    max_note = 108
    clamped_note = max(min_note, min(note, max_note))
    # Map note to horizontal (column) position.
    col = int(((clamped_note - min_note) / (max_note - min_note)) * (GRID_COLS - 3))
    # Map velocity to vertical (row) position.
    row = int((velocity / 127) * (GRID_ROWS - 3))
    # Choose color based on note (cycle through ROYGBIV).
    color = ROYGBIV[clamped_note % len(ROYGBIV)]
    # Insert a 3x3 block into the current grid.
    for dr in range(3):
        for dc in range(3):
            r = row + dr
            c = col + dc
            if 0 <= r < GRID_ROWS and 0 <= c < GRID_COLS:
                current_grid[r][c] = color

# ---------------------------
# Grid Drawing Function (with Interpolation)
# ---------------------------
def draw_interpolated_grid(surface, current_grid, target_grid, t):
    surface.fill((20, 20, 20))
    for r in range(GRID_ROWS):
        for c in range(GRID_COLS):
            interp_color = lerp_color(current_grid[r][c], target_grid[r][c], t)
            if interp_color != (0, 0, 0):
                pygame.draw.polygon(surface, interp_color, cell_points[r][c])
            pygame.draw.polygon(surface, (80, 80, 80), cell_points[r][c], 2)

# ---------------------------
# Global Variables for Interpolation and MIDI Scheduling
# ---------------------------
transition_counter = 0  # Frames since last grid update
start_time = pygame.time.get_ticks()  # Start time for MIDI event scheduling

# ---------------------------
# Main Loop
# ---------------------------
def main():
    global current_grid, target_grid, transition_counter
    running = True
    paused = False

    # Initialize current_grid and target_grid as blank grids (filled with zeros)
# Initialize current_grid and target_grid as blank grids (filled with RGB tuples)
    current_grid = [[(0, 0, 0)] * GRID_COLS for _ in range(GRID_ROWS)]
    target_grid = [[(0, 0, 0)] * GRID_COLS for _ in range(GRID_ROWS)]

    transition_counter = 0

    # Copy the MIDI events so we can process them in order.
    pending_midi_events = midi_events.copy()

    while running:
        dt = clock.tick(FPS)
        current_ms = pygame.time.get_ticks() - start_time

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key == pygame.K_ESCAPE:
                    running = False

        # Process pending MIDI events whose scheduled time has passed.
        while pending_midi_events and pending_midi_events[0][0] <= current_ms:
            sched_time, msg = pending_midi_events.pop(0)
            # In mido, channels are 0-indexed. Channel 9 corresponds to MIDI channel 10 (drums).
            if msg.channel == 9:
                play_drum(msg.note)
            else:
                target_freq = 440 * (2 ** ((msg.note - 69) / 12))
                # Use a random column for panning (or map as desired).
                col = random.randint(0, GRID_COLS - 1)
                play_pitch_shifted_note(target_freq, msg.velocity, col)
                # Also add a piece to the board based on the note.
                add_piece_to_board(msg.note, msg.velocity)

        # Update the board if not paused.
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

