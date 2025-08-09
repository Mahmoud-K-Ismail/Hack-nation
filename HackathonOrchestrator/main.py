import os
from dotenv import load_dotenv


load_dotenv()


# --- Main Execution ---

def run_orchestrator(topic: str = "AI in FinTech") -> None:
    print(f"--- Launching Orchestrator for topic: {topic} ---")

    # Offline simulation mode to avoid external LLM calls
    dummy_run = os.getenv("DUMMY_RUN", "0") == "1" or not os.getenv("OPENAI_API_KEY")
    if dummy_run:
        print("Running in DUMMY mode (no external LLM calls).\n")
        print("[SourcingAgent] Found 3 potential candidates:")
        mock_results = [
            {"name": "Dr. Evelyn Reed", "email": "e.reed@example.com", "expertise": "Quantum Computing"},
            {"name": "Marco Jin", "email": "m.jin@example.com", "expertise": "AI in FinTech"},
            {"name": "Anya Sharma", "email": "a.sharma@example.com", "expertise": "Decentralized Science"},
        ]
        for idx, c in enumerate(mock_results, 1):
            print(f"  {idx}. {c['name']} - {c['expertise']} ({c['email']})")
        print("\n[SchedulingAgent] Contacting candidates and scheduling intro meetings...")
        for c in mock_results:
            print(f"  Email sent to {c['name']} - meeting scheduled.")
        print("\n--- Crew Run Complete (Simulated) ---")
        return

    # Import CrewAI-dependent modules only when needed
    from crewai import Crew, Process
    from agents import OrchestratorAgents
    from tasks import OrchestratorTasks

    agents = OrchestratorAgents()
    tasks = OrchestratorTasks()

    # Instantiate Agents
    sourcing_agent = agents.sourcing_agent()
    scheduling_agent = agents.scheduling_agent()

    # Instantiate Tasks
    source_task = tasks.source_experts_task(sourcing_agent, topic)
    outreach_task = tasks.outreach_and_schedule_task(scheduling_agent, source_task)

    # Form the Crew
    crew = Crew(
        agents=[sourcing_agent, scheduling_agent],
        tasks=[source_task, outreach_task],
        process=Process.sequential,
        verbose=2,
    )

    result = crew.kickoff()
    print("\n--- Crew Run Complete ---")
    print(result)


if __name__ == "__main__":
    run_orchestrator()
