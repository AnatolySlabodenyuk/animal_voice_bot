#!/bin/bash
uvicorn sound_game:app --host 0.0.0.0 --port 3000 &
python main.py