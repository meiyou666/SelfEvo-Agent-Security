from __future__ import annotations

import json
import os
from typing import Any

from config import CONFIG
from agent.schemas import AgentTaskResult, parse_agent_task_result


def _load_crewai() -> dict[str, Any]:
    try:
        from crewai import Agent, Crew, LLM, Process, Task
        from crewai.project import CrewBase, agent, crew, task
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "CrewAI is required for this agent. Install dependencies with "
            "`pip install -r requirements.txt` and configure the LLM environment."
        ) from exc
    return {
        "Agent": Agent,
        "Crew": Crew,
        "LLM": LLM,
        "Process": Process,
        "Task": Task,
        "CrewBase": CrewBase,
        "agent": agent,
        "crew": crew,
        "task": task,
    }


_crewai = _load_crewai()
Agent = _crewai["Agent"]
Crew = _crewai["Crew"]
LLM = _crewai["LLM"]
Process = _crewai["Process"]
Task = _crewai["Task"]
CrewBase = _crewai["CrewBase"]
agent = _crewai["agent"]
crew = _crewai["crew"]
task = _crewai["task"]


def _build_llm():
    return LLM(
        model=CONFIG.llm_model,
        temperature=CONFIG.llm_temperature,
    )


@CrewBase
class SecurityExperimentCrew:
    """Standard CrewAI crew for the experiment agent."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def security_experiment_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["security_experiment_agent"],
            llm=_build_llm(),
            verbose=CONFIG.crewai_verbose,
        )

    @task
    def infection_analysis_task(self) -> Task:
        return Task(
            config=self.tasks_config["infection_analysis_task"],
            agent=self.security_experiment_agent(),
            output_pydantic=AgentTaskResult,
        )

    @task
    def trigger_response_task(self) -> Task:
        return Task(
            config=self.tasks_config["trigger_response_task"],
            agent=self.security_experiment_agent(),
            output_pydantic=AgentTaskResult,
        )

    @task
    def report_task(self) -> Task:
        return Task(
            config=self.tasks_config["report_task"],
            agent=self.security_experiment_agent(),
            output_pydantic=AgentTaskResult,
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=[self.security_experiment_agent()],
            tasks=[self.trigger_response_task()],
            process=Process.sequential,
            verbose=CONFIG.crewai_verbose,
        )

    def run_infection(self, inputs: dict[str, Any]) -> AgentTaskResult:
        output = Crew(
            agents=[self.security_experiment_agent()],
            tasks=[self.infection_analysis_task()],
            process=Process.sequential,
            verbose=CONFIG.crewai_verbose,
        ).kickoff(inputs=inputs)
        return parse_agent_task_result(output)

    def run_trigger(self, inputs: dict[str, Any]) -> AgentTaskResult:
        task_method = self.report_task if inputs.get("scenario") == "report" else self.trigger_response_task
        output = Crew(
            agents=[self.security_experiment_agent()],
            tasks=[task_method()],
            process=Process.sequential,
            verbose=CONFIG.crewai_verbose,
        ).kickoff(inputs=inputs)
        return parse_agent_task_result(output)


def run_agent_task(task: dict[str, Any], memories: list[dict[str, Any]]) -> AgentTaskResult:
    _validate_llm_environment()
    inputs = _build_inputs(task, memories)
    experiment_crew = SecurityExperimentCrew()
    if task.get("phase") == "infection":
        return experiment_crew.run_infection(inputs)
    return experiment_crew.run_trigger(inputs)


def _validate_llm_environment() -> None:
    if not CONFIG.llm_model:
        raise RuntimeError("MODEL must be configured before running the CrewAI agent.")
    if CONFIG.llm_model.startswith("openai/") and not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY is required for OpenAI CrewAI models. "
            "Set OPENAI_API_KEY or choose another MODEL provider."
        )


def _build_inputs(task: dict[str, Any], memories: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "task_id": task["task_id"],
        "phase": task["phase"],
        "scenario": task.get("scenario", ""),
        "user_instruction": task.get("user_instruction", ""),
        "external_content": task.get("external_content", ""),
        "source_type": task.get("source_type", ""),
        "trust_level": task.get("trust_level", ""),
        "risk_tags": json.dumps(task.get("risk_tags", []), ensure_ascii=False),
        "retrieved_memories_json": json.dumps(memories, ensure_ascii=False),
    }
