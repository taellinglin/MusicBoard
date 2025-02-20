# MusicBoard 🎵🎨  

MusicBoard is an interactive MIDI-driven visualization inspired by cellular automata and color theory. It processes MIDI files to generate a dynamic, evolving grid of colorful pyramidal cells, responding to musical input with vibrant patterns.  

## Features  
- 🎹 **MIDI Integration**: Reads and visualizes note events from MIDI files.  
- 🎨 **Color Cycling**: Implements smooth hue transitions using the ROYGBIV color scheme.  
- 🔀 **Dynamic Cellular Automata**: Applies custom rules to update the grid, inspired by the "Game of Life."  
- 🎵 **Sound Interaction**: Triggers percussion samples and note-based audio events.  
- 🖥 **Fullscreen Pygame Interface**: Uses Pygame for rendering and interactivity.  

## Running the Program  
Simply run the appropriate script for your operating system:  

#### Windows  
Double-click **MusicBoard.bat** or run:  

```cmd
MusicBoard.bat
```

#### macOS/Linux
Run the shell script:

```bash
./MusicBoard.sh
```

## How It Works  

### 🎶 MIDI Processing  
- The program loads all `.mid` files in the directory.  
- Extracts `note_on` events and maps them to visual changes.  

### 🔄 Cellular Automata & Color Transitions  
- The grid consists of triangular cells that shift colors and interact based on MIDI input.  
- Cells blend hues over time, creating a smooth, evolving visualization.  

### 🥁 Sound Effects  
- Triggers percussion samples (`kick.wav`, `snare.wav`, `hihat.wav`).  
- Uses a base note sample (`note.wav`) for pitch-based synthesis.  

## Controls  
- **ESC**: Exit the program.  
- **Arrow Keys**: Navigate through MIDI files.  

## To-Do List 🚀  
- [ ] Add real-time MIDI input support.  
- [ ] Implement more complex audio-reactive behavior.  
- [ ] Optimize rendering for larger grid sizes.  

## License  
This project is licensed under the MIT License.  
