import os
import time
from typing import Callable, List, Optional
from dotenv import load_dotenv


load_dotenv()


# --- Main Execution ---

def run_orchestrator(
    topic: str = "AI in FinTech",
    on_log: Optional[Callable[[str], None]] = None,
    on_candidates_found: Optional[Callable[[List[dict]], None]] = None,
    on_candidate_status: Optional[Callable[[int, str], None]] = None,
    simulate_timing: bool = False,
) -> None:
    def log(message: str) -> None:
        print(message)
        if on_log:
            try:
                on_log(message)
            except Exception:
                pass

    log(f"--- Launching Orchestrator for topic: {topic} ---")

    # Offline simulation mode to avoid external LLM calls
    dummy_run = os.getenv("DUMMY_RUN", "0") == "1" or not os.getenv("OPENAI_API_KEY")
    if dummy_run:
        log("Running in DUMMY mode (no external LLM calls).")
        if simulate_timing:
            time.sleep(1)
        log("[SourcingAgent] Starting search...")
        if simulate_timing:
            time.sleep(1.2)
        mock_results = [
            {"name": "Dr. Evelyn Reed", "email": "e.reed@example.com", "expertise": "Quantum Computing", "status": "Sourced"},
            {"name": "Marco Jin", "email": "m.jin@example.com", "expertise": "AI in FinTech", "status": "Sourced"},
            {"name": "Anya Sharma", "email": "a.sharma@example.com", "expertise": "Decentralized Science", "status": "Sourced"},
        ]
        log("[SourcingAgent] Found 3 potential candidates.")
        if on_candidates_found:
            try:
                on_candidates_found(mock_results)
            except Exception:
                pass
        if simulate_timing:
            time.sleep(0.6)
        log("[SourcingAgent] Task complete. Passing results to SchedulingAgent.")
        if simulate_timing:
            time.sleep(1.0)
        log("[SchedulingAgent] Initializing outreach sequence...")
        if simulate_timing:
            time.sleep(1.2)
        # Outreach updates
        for idx, candidate in enumerate(mock_results):
            log(f"[SchedulingAgent] Sending outreach email to {candidate['name']}.")
            if on_candidate_status:
                try:
                    on_candidate_status(idx, "Contacted")
                except Exception:
                    pass
            if simulate_timing:
                time.sleep(0.9)
        # Acceptance
        log("[SchedulingAgent] Received positive reply from Dr. Evelyn Reed. Scheduling meeting.")
        if on_candidate_status:
            try:
                on_candidate_status(0, "Accepted")
            except Exception:
                pass
        if simulate_timing:
            time.sleep(0.8)
        log("[SchedulingAgent] Task complete.")
        if simulate_timing:
            time.sleep(0.4)
        log("--- Crew Run Complete (Simulated) ---")
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
    log("\n--- Crew Run Complete ---")
    log(str(result))


if __name__ == "__main__":
    run_orchestrator()
