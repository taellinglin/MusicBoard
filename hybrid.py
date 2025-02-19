import random
import numpy as np
from panda3d.core import Vec4, Point3, NodePath, AmbientLight
from panda3d.core import Geom, GeomNode, GeomVertexFormat, GeomVertexData, GeomVertexWriter, Material, GeomTriangles
from direct.showbase.ShowBase import ShowBase
import pygame
import pygame.sndarray

# Configuration
GRID_WIDTH = 32
GRID_HEIGHT = 32
CELL_SIZE = 1  # Adjusted to fit screen resolution
FPS = 60
PENTATONIC_SCALE = [
    261.63, 293.66, 329.63, 392.00, 440.00, 523.25, 587.33, 659.26, 698.46, 783.99, 880.00, 987.77,
    1046.50, 1174.66, 1318.51, 1396.91, 1479.98, 1567.98, 1760.00, 1975.53, 2093.00, 2349.32, 2637.02,
    2793.83, 3135.96, 3520.00, 3951.07, 4186.01, 5232.04, 5874.66, 6271.93, 7040.00, 7902.13, 8372.02,
    9877.94, 10465.04, 11749.31, 12543.85, 14080.00, 15804.26, 16744.04, 19755.88, 20930.08, 23498.61,
    25087.70, 28160.00, 31608.52, 33488.09, 39511.75, 41860.16, 46997.22, 50175.40, 56320.00, 63217.04,
    66976.19, 79023.50, 83720.31, 93994.44, 100350.81, 112640.00, 126434.08, 133952.38, 158046.99,
    167440.63, 187988.89, 200701.62, 225280.00, 252868.16, 267904.77, 316092.99, 334881.25, 375977.77,
    401403.24, 450560.00, 505736.33, 535809.53, 632185.98, 669762.51, 751955.55, 802806.48, 901120.00,
    1011472.66, 1071619.07, 1264371.96, 1339525.02, 1503911.11, 1605612.96, 1802240.00, 2022945.32,
    2143619.06, 2528743.93, 2679050.04, 3011822.21, 3201225.93, 3604480.00, 4045890.63, 4287238.13,
    5057487.87, 5358100.09, 6023644.42, 6402451.86, 7208960.00, 8091781.26, 8574476.26, 10114975.74,
    10716100.18, 12047288.84, 12804903.72
]

ROYGBIV = [
    (255, 0, 0),      # Red
    (255, 127, 0),    # Orange
    (255, 255, 0),    # Yellow
    (0, 255, 0),      # Green
    (0, 0, 255),      # Blue
    (75, 0, 130),     # Indigo
    (148, 0, 211)     # Violet
]

# Setup for Panda3D
class LifeSimulation(ShowBase):
    def __init__(self):
        super().__init__()

        # Pygame for sound generation
        pygame.init()
        pygame.mixer.init()

        # Create a 2D array for grid
        self.grid = np.zeros((GRID_HEIGHT, GRID_WIDTH, 3), dtype=int)
        self.cycle_speeds = np.zeros((GRID_HEIGHT, GRID_WIDTH), dtype=int)
        # Initialize grid to hold NodePath objects for each cell
        self.grid_nodes = [[None for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]

        # Initialize grid and cubes
        self.init_grid()

        # Variables for cycling
        self.bar_counter = 0
        self.current_key = random.choice(PENTATONIC_SCALE)

        # Task to update every frame
        self.taskMgr.add(self.update, "update_task")

        # Set the background color to black
        self.setBackgroundColor(0, 0, 0)  # RGB black

        # Set the camera rotation speed
        self.camera_rotation_speed = 30  # Degrees per second
        self.enableMouse()

        # Create a node for ambient light
        ambient_light = AmbientLight('ambient_light')
        # Set the color of the ambient light (RGBA format, where A is alpha)
        ambient_light.setColor((0.5, 0.5, 0.5, 1))  # Light gray color
        # Attach the ambient light to the render
        ambient_light_node = self.render.attachNewNode(ambient_light)
        # Set the ambient light as a global light source in the scene
        self.render.setLight(ambient_light_node)

    def init_grid(self):
        """Initialize grid and cubes."""
        for _ in range(GRID_HEIGHT * 4):  # Starting with more pieces
            x, y = random.randint(0, GRID_HEIGHT - 1), random.randint(0, GRID_WIDTH - 1)
            self.grid[x, y] = random.choice(ROYGBIV)

        # Create a cube for each grid cell
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                self.create_cube(x, y)

    def create_cube(self, x, y):
        """Creates a 3D cube for a specific grid cell."""
        # Create the geometry for the cube
        vertex_format = GeomVertexFormat.get_v3n3()  # 3D vertices with normals
        vertex_data = GeomVertexData('cube_data', vertex_format, Geom.UHStatic)
        vertex_writer = GeomVertexWriter(vertex_data, 'vertex')
        
        # Define the cube vertices (8 points)
        size = CELL_SIZE
        vertices = [
            (-size / 2, -size / 2, -size / 2), (size / 2, -size / 2, -size / 2), 
            (size / 2, size / 2, -size / 2), (-size / 2, size / 2, -size / 2),
            (-size / 2, -size / 2, size / 2), (size / 2, -size / 2, size / 2),
            (size / 2, size / 2, size / 2), (-size / 2, size / 2, size / 2)
        ]

        # Add the vertices to the geometry
        for vertex in vertices:
            vertex_writer.add_data3f(*vertex)

        # Define the cube faces (6 faces, 2 triangles per face)
        faces = [
            (0, 1, 2), (0, 2, 3),  # Bottom
            (4, 5, 6), (4, 6, 7),  # Top
            (0, 1, 5), (0, 5, 4),  # Front
            (1, 2, 6), (1, 6, 5),  # Right
            (2, 3, 7), (2, 7, 6),  # Back
            (3, 0, 4), (3, 4, 7),  # Left
        ]
        
        # Create a GeomTriangles object and add each triangle
        geom = Geom(vertex_data)
        geom_tri = GeomTriangles(Geom.UHStatic)
        for face in faces:
            geom_tri.add_vertices(*face)
        geom.add_primitive(geom_tri)

        # Create a GeomNode for the cube and attach it
        geom_node = GeomNode('cube')
        geom_node.add_geom(geom)
        cube = NodePath(geom_node)

        # Position the cube in the grid
        cube.set_pos(x * CELL_SIZE - (GRID_WIDTH * CELL_SIZE) / 2, y * CELL_SIZE - (GRID_HEIGHT * CELL_SIZE) / 2, 0)
        
        # Assign a color (material) to the cube
        material = Material()
        cube.set_material(material)
        
        # Store the NodePath in grid_nodes
        self.grid_nodes[y][x] = cube



    def count_neighbors(self, x, y):
        """Counts the number of live neighbors with wrapping board."""
        neighbors = 0
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                nx, ny = (x + dx) % GRID_HEIGHT, (y + dy) % GRID_WIDTH
                if any(self.grid[nx, ny]):
                    neighbors += 1
        return neighbors

    def update_grid(self):
        """Applies the hyperdimensional rules to generate complex patterns."""
        new_grid = np.zeros((GRID_HEIGHT, GRID_WIDTH, 3), dtype=int)
        for x in range(GRID_HEIGHT):
            for y in range(GRID_WIDTH):
                neighbors = self.count_neighbors(x, y)
                if any(self.grid[x, y]):
                    if 2 <= neighbors <= 4:
                        new_grid[x, y] = self.grid[x, y]
                    elif neighbors == 5:
                        new_grid[(x + 1) % GRID_HEIGHT, (y + 1) % GRID_WIDTH] = self.grid[x, y]
                else:
                    if neighbors == 3 or neighbors == 6:
                        new_grid[x, y] = random.choice(ROYGBIV)
        self.grid = new_grid

    def generate_tone(self):
        """Plays a note based on grid activity."""
        active_cells = np.count_nonzero(self.grid)
        if active_cells == 0:
            return
        freq = random.choice(PENTATONIC_SCALE) * (1 + active_cells / (GRID_HEIGHT * GRID_WIDTH))
        sample_rate = 44100
        duration = 0.2
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        wave = (4096 * np.sin(2 * np.pi * freq * t)).astype(np.int16)

        # Ensure the array is C-contiguous by making a copy of the array
        wave = np.array([wave, wave]).T.copy()

        sound = pygame.sndarray.make_sound(wave)
        sound.set_volume(min(1, active_cells / (GRID_HEIGHT * GRID_WIDTH)))
        sound.play()

    def update(self, task):
        """Update function for grid simulation and audio."""
        self.bar_counter += 1
        if self.bar_counter % 16 == 0:  # Change key every 16 bars
            self.current_key = random.choice(PENTATONIC_SCALE)

        self.update_grid()
        self.generate_tone()

        # Update the emissive colors based on grid state
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                color = self.grid[x, y]
                if any(color):
                    # Access the NodePath directly from grid_nodes
                    node = self.grid_nodes[y][x]
                    material = node.get_material()  # Retrieve the material
                    
                    # Check if the material is None, if so, create a new one
                    if material is None:
                        material = Material()  # Create a new material if it's None
                        node.set_material(material)  # Assign the material to the NodePath

                    material.set_emission(Vec4(color[0]/255, color[1]/255, color[2]/255, 1))  # Set emissive color
                    node.set_material(material)  # Apply the material to the node

        # Rotate the camera around the center of the grid
        self.camera.set_hpr(self.camera.get_h() + self.camera_rotation_speed * task.dt, 0, 0)

        return task.cont


if __name__ == "__main__":
    app = LifeSimulation()

    # Set the initial camera position and frame the grid properly
    app.camera.set_pos(0, -30, 10)  # Move it farther back so the whole grid is in frame
    app.camera.look_at(0, 0, 0)  # Look at the center of the grid

    app.run()
