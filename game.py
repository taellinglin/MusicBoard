import os
import random
import sys
import math
import mido
import numpy as np
from panda3d.core import Point3, LPoint3f, NodePath
from panda3d.core import ColorAttrib
from panda3d.core import Vec3
from panda3d.core import Material
from panda3d.core import AmbientLight, DirectionalLight
from panda3d.core import Shader
from direct.showbase.ShowBase import ShowBase
from panda3d.core import Texture, CardMaker, WindowProperties


# ---------------------------
# Configuration and Constants
# ---------------------------
# For a 1920x1080 display:
CELL_SIZE = 40              # Cell size in pixels for clarity
GRID_COLS = 96              # 96 * 20 = 1920 width
GRID_ROWS = 54              # Grid height will be ~935 px; we'll center vertically
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
    files = [f for f in os.listdir('.') if f.endswith('.mid')]

    if not files:
        raise FileNotFoundError("No .mid files found in the current directory.")
    
    chosen_file = random.choice(files)
    return chosen_file

def extract_midi_events(midi_filename):
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
# Panda3D Initialization (Fullscreen)
# ---------------------------
from panda3d.core import *
from panda3d.audio import AudioManager
from direct.showbase.ShowBase import ShowBase
import midi  # If using a MIDI parsing library

class GridGame(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)

        # Create new window properties and set fullscreen
        properties = WindowProperties()
        properties.setFullscreen(True)
        self.win.requestProperties(properties)  # Apply fullscreen mode

        # Set up the camera position to make sure we can see objects
        self.camera.set_pos(0, -10, 5)  # Position the camera to see the scene
        self.camera.look_at(0, 0, 0)  # Look at the origin

        # Create a simple visible object (like a cube)
        self.cube = self.loader.loadModel("models/box")  # Load a basic box model
        self.cube.set_scale(1, 1, 1)  # Scale the cube
        self.cube.reparent_to(self.render)  # Add the cube to the scene

        # Load the MIDI file for sound
        self.midi_file = "Festival.mid"  # Specify your MIDI file
        self.load_and_play_midi(self.midi_file)

        self.taskMgr.add(self.update, "update_task")

        self.grid = []
        self.create_grid()
        self.current_grid = self.create_empty_grid()
        self.target_grid = self.create_empty_grid()

        self.accept('escape', self.exit_game)

        # Setup lighting
        self.setup_lighting()

    def load_and_play_midi(self, midi_file):
        # Make sure the midi library and playback mechanism is working
        # Example with a basic MIDI handler (ensure you have a MIDI-to-sound mechanism)
        try:
            midi_data = midi.read_midifile(midi_file)  # Using a MIDI library to read the file
            print(f"Loaded MIDI file '{midi_file}' with {len(midi_data)} events.")
            # Now, you need to implement the sound playback mechanism, e.g., using an audio library.
            # For simplicity, let's pretend we're handling it here.
            # In a real scenario, you'd convert MIDI to audio or use a library to play it.
            print("MIDI playback would start here.")
        except Exception as e:
            print(f"Error loading MIDI: {e}")

    def update(self, task):
        # This method updates the game state each frame.
        # You can implement logic for game state updates here.
        return task.cont

    def exit_game(self):
        self.userExit()

    def setup_lighting(self):
        # Set up basic lighting for visibility
        light = DirectionalLight('light')
        light.set_color((1, 1, 1, 1))  # White light
        light_np = self.render.attach_new_node(light)
        light_np.set_pos(0, -10, 10)
        self.render.set_light(light_np)



    def create_grid(self):
        self.grid_node = NodePath("grid")
        
        # Create 3D pyramidal cells
        for r in range(GRID_ROWS):
            row = []
            for c in range(GRID_COLS):
                # Calculate base position for each triangle cell
                x = c * CELL_SIZE
                y = r * TRI_HEIGHT
                if (r + c) % 2 == 0:
                    pts = [Point3(x + CELL_SIZE / 2, y, 0),
                           Point3(x, y + TRI_HEIGHT, 0),
                           Point3(x + CELL_SIZE, y + TRI_HEIGHT, 0)]
                else:
                    pts = [Point3(x, y, 0),
                           Point3(x + CELL_SIZE, y, 0),
                           Point3(x + CELL_SIZE / 2, y + TRI_HEIGHT, 0)]

                # Create a mesh for each triangular cell
                mesh = self.create_triangle(pts)
                row.append(mesh)
                mesh.reparent_to(self.grid_node)
            self.grid.append(row)
        
        self.grid_node.reparent_to(self.render)

    def create_triangle(self, points):
        """ Create a 3D triangle using Panda3D """
        cm = CardMaker("triangle")
        cm.set_frame(-CELL_SIZE / 2, CELL_SIZE / 2, 0, TRI_HEIGHT)
        triangle = self.render.attach_new_node(cm.generate())
        
        # Apply color
        color = random.choice(ROYGBIV)
        triangle.set_color(color[0] / 255, color[1] / 255, color[2] / 255, 1)
        
        return triangle

    def setup_lighting(self):
        """ Set up ambient and directional lighting """
        ambient_light = AmbientLight('ambient_light')
        ambient_light.set_color((0.5, 0.5, 0.5, 1))
        ambient_node = self.render.attach_new_node(ambient_light)
        self.render.set_light(ambient_node)

        directional_light = DirectionalLight('directional_light')
        directional_light.set_color((1, 1, 1, 1))
        directional_light.set_direction(Vec3(-1, -1, -1))
        directional_node = self.render.attach_new_node(directional_light)
        self.render.set_light(directional_node)

    def exit_game(self):
        self.userExit()

    def update(self, task):
        """ Update logic for grid animation (Game of Life simulation) """
        # Example: Update grid based on MIDI event timing
        for event_time, msg in midi_events:
            if task.time * 1000 >= event_time:
                self.handle_midi_event(msg)
        
        return task.cont

    def handle_midi_event(self, msg):
        """ Handle incoming MIDI events and modify the grid """
        if msg.type == 'note_on' and msg.velocity > 0:
            row, col = random.randint(0, GRID_ROWS - 1), random.randint(0, GRID_COLS - 1)
            self.update_cell_color(row, col)

    def update_cell_color(self, row, col):
        """ Change the color of a grid cell """
        new_color = random.choice(ROYGBIV)
        self.grid[row][col].set_color(new_color[0] / 255, new_color[1] / 255, new_color[2] / 255, 1)

    def create_empty_grid(self):
        """ Create an empty grid with None entries """
        return [[None for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]


# Run the Panda3D application
game = GridGame()
game.run()
