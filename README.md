# Agentic-Hackathon-Project
Repo for Hackathon Project

## Getting started
Before running the project make sure ffmpeg is installed in your system:
'brew install ffmpeg'

Clone this repo and create a virtual environment using the following commands:
```
mkdir .venv && python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Then, create a `.env` file in this folder and make sure you set `OPENAI_API_KEY="sk-..."`.

## Running the agent workflow
Before running the agent, you may want to start the Phoenix observability application with the following command:
```
python -m phoenix.server.main serve
```

You can also run `nohup python -m phoenix.server.main serve > tracing.log &` to run this in the background.

This will start up a dashboard which can be viewed at http://0.0.0.0:6006/projects.

To run the agent, run `python src/agent.py`