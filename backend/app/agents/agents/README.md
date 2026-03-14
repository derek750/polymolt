# Agent definitions

One file per agent. Each module **must** define a single top-level variable:

```python
agent: AgentConfig
```

## Adding a new agent

1. Create a new file in this folder, e.g. `my_agent.py`.
2. Define and export `agent`:

```python
from app.agents.base import AgentConfig

agent = AgentConfig(
    id="my_agent",          # unique id (used in API and pipeline)
    name="My Agent",        # display name
    description="Short description for orchestrator and API.",
    system_prompt="Your system prompt for the LLM...",
    model=None,             # optional: e.g. "gemini-2.5-flash" or None for default
)
```

Make sure to have in the system prompt:
"You MUST end your reply with exactly one of these two lines (nothing after it): "
"Answer: Yes "
"Answer: No "

3. Restart the app. The registry discovers the new module automatically.

No need to edit a central list — add a file and you’re done.
