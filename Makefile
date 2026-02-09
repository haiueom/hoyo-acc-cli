install:
    uv sync

start:
	uv run main.py

lint:
	uv run ruff check .

build:
	uv run pyinstaller --onefile --collect-all rich --name hoyo-cli main.py
