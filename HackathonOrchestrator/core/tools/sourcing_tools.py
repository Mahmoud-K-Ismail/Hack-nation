from crewai_tools import BaseTool


class SourcingTools:
    @staticmethod
    def search_linkedin(topic: str) -> str:
        """A dummy function to simulate searching for experts on a given topic."""
        print("\n--- DUMMY SOURCING TOOL ---")
        print(f"ACTION: Searching for experts on the topic: '{topic}'")
        # In a real scenario, this would use a web scraping tool or LinkedIn API.
        mock_results = [
            {"name": "Dr. Evelyn Reed", "email": "e.reed@example.com", "expertise": "Quantum Computing"},
            {"name": "Marco Jin", "email": "m.jin@example.com", "expertise": "AI in FinTech"},
            {"name": "Anya Sharma", "email": "a.sharma@example.com", "expertise": "Decentralized Science"},
        ]
        return f"Found 3 potential candidates: {mock_results}"


class SearchForExpertsTool(BaseTool):
    name: str = "Search for Experts"
    description: str = (
        "Searches for high-profile speakers or jurors based on a specific topic of expertise."
    )

    def _run(self, topic: str) -> str:
        return SourcingTools.search_linkedin(topic)
