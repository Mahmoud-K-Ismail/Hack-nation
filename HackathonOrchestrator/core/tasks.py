from crewai import Task


class OrchestratorTasks:
    def source_experts_task(self, agent, topic: str) -> Task:
        return Task(
            description=(
                f"Find 3 potential high-profile speakers or jurors with expertise in '{topic}'."
            ),
            expected_output=(
                "A list of the candidates found, including their name, email, and expertise."
            ),
            agent=agent,
        )

    def outreach_and_schedule_task(self, agent, context) -> Task:
        return Task(
            description=(
                "For each candidate identified in the previous step, send a personalized outreach "
                "email. If they express interest (assume they do for this simulation), schedule an "
                "introductory meeting with them."
            ),
            expected_output=(
                "A confirmation report stating that all found candidates have been contacted and "
                "meetings have been scheduled."
            ),
            agent=agent,
            context=[context],
        )

    # In the future, we can add streaming callbacks here when CrewAI exposes hooks.
