
import asyncio
import os
import sys
import json

# Agregar src/ al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.crews.analytical_crew import AnalyticalCrew

async def check_summary():
    os.environ["PYTHONUTF8"] = "1"
    crew = AnalyticalCrew(org_id="00000000-0000-0000-0000-000000000000")
    result = await crew.ask(question="¿Cual es el agente con mayor tasa de exito?")
    print("QUERY TYPE:", result["query_type"])
    print("SUMMARY:", result["summary"])
    print("METADATA:", result["metadata"])

if __name__ == "__main__":
    asyncio.run(check_summary())
