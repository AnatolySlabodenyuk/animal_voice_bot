#!/bin/bash
uvicorn web_dashboard:app --host 0.0.0.0 --port 3000 &
python main.py