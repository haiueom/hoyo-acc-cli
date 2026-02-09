install:
	uv sync

start:
	uv run main.py

lint:
	uv run ruff check .

format:
	uv run ruff format .

clean:
	rm -rf dist build __pycache__ *.spec

build:
	uv run pyinstaller --onefile --collect-all rich --name hoyo-cli main.py
