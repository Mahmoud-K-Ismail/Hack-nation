from crewai import Agent
from tools.sourcing_tools import SearchForExpertsTool
from tools.communication_tools import SendEmailTool, ScheduleMeetingTool


class OrchestratorAgents:
    def sourcing_agent(self) -> Agent:
        return Agent(
            role="Expert Sourcing Specialist",
            goal=(
                "Identify and vet high-profile experts (speakers, jurors) based on specific criteria."
            ),
            backstory=(
                "An expert talent scout with a deep network in the tech industry, "
                "skilled at identifying true leaders."
            ),
            verbose=True,
            tools=[SearchForExpertsTool()],
        )

    def scheduling_agent(self) -> Agent:
        return Agent(
            role="Communication & Scheduling Coordinator",
            goal=(
                "Manage all outreach and scheduling with sourced candidates. Ensure a professional "
                "and efficient communication flow."
            ),
            backstory=(
                "A highly organized coordinator who excels at managing calendars and crafting "
                "compelling outreach messages."
            ),
            verbose=True,
            tools=[SendEmailTool(), ScheduleMeetingTool()],
        )
