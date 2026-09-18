"""build_agent: constructs a fresh Agent per answer_question call (Eng. Principle 4 —
no module-level global agent instance).

The system prompt is rendered by `capabilities.answer_question` (using that
question's actual selected briefing) and passed at run time as `instructions` to
`agent.run_sync`, since a fresh briefing is only known once dataset selection has
run — build_agent itself only needs the model/tool/output wiring, which is the same
for every question.
"""

from pydantic_ai import Agent

from qa_agent import tools
from qa_agent.deps import AgentDeps
from qa_agent.models import AgentAnswer
from qa_agent.settings import AgentSettings


def build_agent(settings: AgentSettings) -> Agent[AgentDeps, AgentAnswer]:
    agent: Agent[AgentDeps, AgentAnswer] = Agent(
        model=settings.model_name,
        deps_type=AgentDeps,
        output_type=AgentAnswer,
    )
    agent.instrument = settings.instrument
    agent.tool(retries=10)(tools.discover_data_sources)
    agent.tool(retries=10)(tools.inspect_schema)
    agent.tool(retries=10)(tools.query_rows)
    agent.tool(retries=10)(tools.aggregate_rows)
    return agent
