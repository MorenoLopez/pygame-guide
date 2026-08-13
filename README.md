# Pygame Platformer - Learning Project

A complete Mario-like platformer built with Pygame, created as a learning project to teach Pygame fundamentals.

## What's Included

- **index.html** — A comprehensive dark-mode HTML guide that teaches Pygame from scratch
- **src/game.py** — The complete working game (3 levels, player, enemies, coins, camera, UI)
- **assets/images/** — 16 game sprites generated for the project

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the game
cd src
python game.py
```

## Controls

| Action | Key |
|--------|-----|
| Move Left | ← or A |
| Move Right | → or D |
| Jump | Space or ↑ or W |
| Pause | Esc |
| Restart Level | R |

## Project Structure

```
pygame-platformer/
├── assets/
│   └── images/          # All game sprites
├── src/
│   └── game.py          # Complete game code
├── index.html           # Learning guide (open in browser)
└── requirements.txt
```

## Learning Path

1. Open `index.html` in your browser
2. Read through Chapters 1–10 to learn Pygame concepts
3. Study `src/game.py` to see how everything connects
4. Modify the game and experiment!

## Features

- Smooth camera with interpolation
- Gravity and platform collision
- Mario-style enemy stomping
- Animated coins with sine-wave floating
- 3 levels with tilemap-based design
- Game states: Menu, Playing, Paused, Game Over, Victory
- HUD with lives and coin counter


*This project is for educational purposes. Feel free to use, modify, and learn from it.*
