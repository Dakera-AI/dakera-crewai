"""A CrewAI crew with persistent Dakera memory.

DakeraStorage backs CrewAI's ExternalMemory: after each task the crew stores the
agent's answer in Dakera, and before each task it recalls the memories relevant to
it into the agent's prompt. The memories live on the Dakera server, so the second
kickoff (or a new process) builds on the first.

CrewAI 0.193 – 1.9 (``pip install "crewai-dakera[crewai]"``); CrewAI 1.10 replaced
ExternalMemory with a unified Memory. With ``OPENAI_API_KEY`` set the agent uses
gpt-4o-mini; without it a scripted stand-in LLM answers, so the example runs
without a model provider and shows what the agent is prompted with.

Usage:
    export DAKERA_API_URL="http://localhost:3000"
    export DAKERA_API_KEY="dk-..."          # optional
    export OPENAI_API_KEY="sk-..."          # optional
    pip install "crewai-dakera[crewai]"
    python crew_memory.py
"""

import os
from typing import Any

from crewai import LLM, Agent, Crew, Task
from crewai.llms.base_llm import BaseLLM
from crewai.memory.external.external_memory import ExternalMemory

from crewai_dakera import DakeraStorage

api_url = os.environ.get("DAKERA_API_URL", "http://localhost:3000")
api_key = os.environ.get("DAKERA_API_KEY", "")


class ScriptedLLM(BaseLLM):
    """Stand-in LLM for running the example without a model provider."""

    def __init__(self, answers: list[str]) -> None:
        super().__init__(model="scripted")
        self.answers = answers
        self.last_prompt = ""

    def call(self, messages: Any, *args: Any, **kwargs: Any) -> str:
        self.last_prompt = messages if isinstance(messages, str) else messages[-1]["content"]
        return f"Thought: I can answer.\nFinal Answer: {self.answers.pop(0)}"

    def supports_function_calling(self) -> bool:
        return False

    def supports_stop_words(self) -> bool:
        return False

    def get_context_window_size(self) -> int:
        return 8192


if os.environ.get("OPENAI_API_KEY"):
    llm: BaseLLM | LLM = LLM(model="gpt-4o-mini")
else:
    llm = ScriptedLLM(
        [
            "Agents with persistent memory recall facts across sessions and repeat work less.",
            "Building on earlier research: persistent memory lets agents recall across sessions.",
        ]
    )

storage = DakeraStorage(api_url=api_url, api_key=api_key, agent_id="crewai-crew-demo")

researcher = Agent(
    role="Senior Researcher",
    goal="Uncover insights about {topic}",
    backstory="An expert researcher who builds on earlier findings.",
    llm=llm,
)
research_task = Task(
    description="Research {topic} and state the key finding in one sentence.",
    expected_output="One sentence",
    agent=researcher,
)


def run(topic: str) -> str:
    crew = Crew(
        agents=[researcher],
        tasks=[research_task],
        external_memory=ExternalMemory(storage=storage),
    )
    return crew.kickoff(inputs={"topic": topic}).raw


print(f"First run:  {run('AI agent memory')}")
print(f"Second run: {run('long-term memory for AI agents')}")

if isinstance(llm, ScriptedLLM):
    start = llm.last_prompt.find("External memories")
    print("\nWhat the second run recalled into the prompt:")
    print(llm.last_prompt[start:].split("\n\n")[0] if start >= 0 else "(nothing)")

print("\nStored in Dakera:")
for memory in storage.search("AI agent memory", limit=5):
    text = " ".join(memory["content"].split())  # CrewAI stores the agent's whole final step
    print(f"  [{memory['score']:.3f}] {text[:100]}")

# Forget everything this demo stored, so a rerun starts from scratch.
storage.reset()
