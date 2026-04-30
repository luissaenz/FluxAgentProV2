class SmokeTestTool:
    """A tool for E2E certification"""

    name = "smoke_test"
    description = "A tool for E2E certification"

    def run(self, query):
        return f"Certified: {query}"
