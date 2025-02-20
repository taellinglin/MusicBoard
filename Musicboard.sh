#!/bin/bash
echo -e "Setting up the environment..."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Function to print text with ROYGBIV colors
print_roygbiv() {
    local text="$1"
    local colors=(196 208 226 46 21 93 129) # ROYGBIV ANSI color codes

    for ((i=0; i<${#text}; i++)); do
        color=${colors[i % ${#colors[@]}]}
        echo -ne "\e[38;5;${color}m${text:$i:1}"
    done
    echo -e "\e[0m" # Reset color
}

# Print "Running main.py" in ROYGBIV colors
print_roygbiv "Running main.py"

# Run the script
python main.py

# Deactivate virtual environment
deactivate
