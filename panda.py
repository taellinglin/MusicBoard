from direct.showbase.ShowBase import ShowBase
from panda3d.core import LPoint3f, LVector3f, NodePath
from panda3d.core import AmbientLight, DirectionalLight
from panda3d.core import LColor
from panda3d.core import ClockObject
from direct.task import Task
import mido
import os

class MidiVisualizer(ShowBase):
    def __init__(self, midi_file):
        super().__init__()

        # Load the MIDI file
        self.midi = mido.MidiFile(midi_file)

        # Set up the scene
        self.set_background_color(0, 0, 0)
        self.camera.set_pos(0, -50, 25)
        self.camera.look_at(0, 0, 0)

        # Add lighting
        self.setup_lights()

        # Dictionary to keep track of active notes and their corresponding cubes
        self.active_notes = {}

        # Preprocess MIDI events
        self.midi_events = self.process_midi()
        self.event_index = 0
        self.start_time = ClockObject.get_global_clock().get_real_time()

        # Schedule the update task
        self.taskMgr.add(self.update_scene, "update_scene")

    def setup_lights(self):
        ambient_light = AmbientLight("ambient_light")
        ambient_light.set_color(LColor(0.2, 0.2, 0.2, 1))
        ambient_light_np = self.render.attach_new_node(ambient_light)
        self.render.set_light(ambient_light_np)

        directional_light = DirectionalLight("directional_light")
        directional_light.set_color(LColor(0.8, 0.8, 0.8, 1))
        directional_light_np = self.render.attach_new_node(directional_light)
        directional_light_np.set_hpr(0, -60, 0)
        self.render.set_light(directional_light_np)

    def create_cube(self, note):
        # Create a cube model
        cube = self.loader.load_model("models/box")
        cube.set_scale(0.5, 0.5, 0.5)

        # Position the cube based on the MIDI note
        x = (note % 12) - 6  # Horizontal position based on pitch class
        y = (note // 12) - 5  # Vertical position based on octave
        cube.set_pos(x * 2, y * 2, 0)

        # Color the cube based on the note
        color = self.note_to_color(note)
        cube.set_color(color)

        # Attach the cube to the render tree
        cube.reparent_to(self.render)

        return cube

    def note_to_color(self, note):
        # Map MIDI notes to ROYGBIV colors
        colors = [
            LColor(1, 0, 0, 1),    # Red
            LColor(1, 0.5, 0, 1),  # Orange
            LColor(1, 1, 0, 1),    # Yellow
            LColor(0, 1, 0, 1),    # Green
            LColor(0, 0, 1, 1),    # Blue
            LColor(0.3, 0, 0.5, 1),# Indigo
            LColor(0.5, 0, 0.5, 1) # Violet
        ]
        return colors[note % len(colors)]

    def process_midi(self):
        """Preloads MIDI events with timestamps."""
        events = []
        current_time = 0

        for msg in self.midi:
            current_time += msg.time
            if msg.type in ('note_on', 'note_off'):
                events.append((current_time, msg))

        return events

    def update_scene(self, task):
        """Handles MIDI events dynamically based on real-time progression."""
        current_time = ClockObject.get_global_clock().get_real_time() - self.start_time

        while self.event_index < len(self.midi_events):
            event_time, msg = self.midi_events[self.event_index]
            if event_time > current_time:
                break  # Wait until it's time to process this event

            if msg.type == 'note_on' and msg.velocity > 0:
                if msg.note not in self.active_notes:
                    cube = self.create_cube(msg.note)
                    self.active_notes[msg.note] = cube
            elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                if msg.note in self.active_notes:
                    self.active_notes[msg.note].remove_node()
                    del self.active_notes[msg.note]

            self.event_index += 1  # Move to next event

        return Task.cont

if __name__ == "__main__":
    # Find the first MIDI file in the current working directory
    midi_files = [f for f in os.listdir('.') if f.lower().endswith('.mid')]
    if not midi_files:
        print("No MIDI files found in the current directory.")
    else:
        app = MidiVisualizer(midi_files[0])
        app.run()
def main():
    global grid
    running = True
    paused = False

    while running:
        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    paused = not paused  # Toggle pause

        if not paused:
            grid = update_grid(grid)  # Update the simulation

        draw_grid(screen, grid)  # Render the grid
        pygame.display.flip()  # Refresh the screen

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
