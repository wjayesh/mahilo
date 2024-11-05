# Multi-Agent Story Weavers Game

This is a multi-agent system designed to create an interactive storytelling experience where multiple users can craft their own stories that occasionally intersect in unexpected and entertaining ways. Each user gets their own StoryWeaver agent that helps guide their narrative while secretly weaving in elements from other participants' stories.

## System Overview

The system consists of multiple StoryWeaver agents, one for each participant. Each agent:
1. Helps their assigned user develop a unique story
2. Asks engaging questions to push the narrative in unexpected directions
3. Occasionally weaves in elements from other participants' stories
4. Maintains the mystery by never explicitly revealing other ongoing stories

## Getting Started

### Installation and Running the Server

1. Clone the repository:
```
git clone https://github.com/wjayesh/multi-agent.git
```

2. Install the required packages:
```
pip install -r requirements.txt
```

3. Run the server with default players (jayesh, arunjoy, ritvi):
```
cd examples/story_weavers
python run_server.py
```

Or specify custom player names:
```
python run_server.py alice bob charlie
```

### Code Explanation

1. The StoryWeaver agent code is defined in `mahilo/templates/story_weavers/story_weaver_agent.py`

2. The `run_server.py` file is the entry point that:
   - Creates a StoryWeaver agent for each participant
   - Registers the agents with the agent manager
   - Activates all agents to begin the storytelling session

### How to Play

1. Each participant connects to their designated StoryWeaver agent
2. The agent provides a story starter prompt or accepts the user's own beginning
3. Through questions and responses, users develop their unique narratives
4. When users request updates, their stories may unexpectedly intersect with elements from other participants' stories
5. The game continues until participants are ready to see their final, complete stories

## Story Elements

- **Story Starters**: Engaging prompts to begin each narrative
- **Guided Questions**: Agents ask specific questions to develop the story
- **Story Mixing**: Unexpected intersections between different participants' narratives
- **Final Stories**: Complete narratives that coherently incorporate all story elements 