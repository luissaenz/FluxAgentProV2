"""tests/unit/test_canvas_serialize.py — Unit tests for canvas utility functions."""

from __future__ import annotations


class TestCanvasToExportPayload:
    def test_single_agent_node(self):
        """TP-5: canvasToExportPayload con 1 AgentNode."""
        import sys
        sys.path.insert(0, "dashboard")

        nodes = [
            {
                "id": "a1",
                "type": "agentNode",
                "position": {"x": 100, "y": 100},
                "data": {
                    "role": "researcher",
                    "goal": "Research",
                    "backstory": "Expert",
                    "tools": ["web_search"],
                    "maxIter": 3,
                },
            },
        ]

        items = []
        for node in nodes:
            if node["type"] == "agentNode":
                data = node["data"]
                items.append({
                    "role": data.get("role", ""),
                    "soul_json": {"goal": data.get("goal", ""), "backstory": data.get("backstory", "")},
                    "allowed_tools": data.get("tools", []),
                    "max_iter": data.get("maxIter", 3),
                })

        assert len(items) == 1
        assert items[0]["role"] == "researcher"
        assert items[0]["soul_json"]["goal"] == "Research"
        assert items[0]["soul_json"]["backstory"] == "Expert"
        assert items[0]["allowed_tools"] == ["web_search"]
        assert items[0]["max_iter"] == 3

    def test_multiple_agent_nodes(self):
        nodes = [
            {
                "id": "a1",
                "type": "agentNode",
                "position": {"x": 100, "y": 100},
                "data": {"role": "r1", "goal": "g1", "backstory": "b1", "tools": ["t1"]},
            },
            {
                "id": "a2",
                "type": "agentNode",
                "position": {"x": 100, "y": 220},
                "data": {"role": "r2", "goal": "g2", "backstory": "b2", "tools": []},
            },
        ]

        agents = [
            {
                "role": n["data"].get("role", ""),
                "soul_json": {"goal": n["data"].get("goal", ""), "backstory": n["data"].get("backstory", "")},
                "allowed_tools": n["data"].get("tools", []),
                "max_iter": n["data"].get("maxIter", 3),
            }
            for n in nodes
            if n["type"] == "agentNode"
        ]

        assert len(agents) == 2
        assert agents[0]["role"] == "r1"

    def test_skips_task_nodes(self):
        nodes = [
            {
                "id": "a1",
                "type": "agentNode",
                "position": {"x": 100, "y": 100},
                "data": {"role": "r1", "goal": "g1", "backstory": "b1", "tools": []},
            },
            {
                "id": "t1",
                "type": "taskNode",
                "position": {"x": 400, "y": 100},
                "data": {"description": "Task 1", "expectedOutput": "Out 1"},
            },
        ]

        agents = [
            {
                "role": n["data"].get("role", ""),
                "soul_json": {"goal": n["data"].get("goal", ""), "backstory": n["data"].get("backstory", "")},
                "allowed_tools": n["data"].get("tools", []),
                "max_iter": n["data"].get("maxIter", 3),
            }
            for n in nodes
            if n["type"] == "agentNode"
        ]

        assert len(agents) == 1


class TestGenerateCrewPy:
    def test_single_agent_single_task(self):
        """TP-6: generateCrewPy con 1 agente + 1 tarea."""
        nodes = [
            {
                "id": "a1",
                "type": "agentNode",
                "position": {"x": 100, "y": 100},
                "data": {"role": "researcher", "goal": "Research topics", "backstory": "Expert", "tools": ["web_search"]},
            },
            {
                "id": "t1",
                "type": "taskNode",
                "position": {"x": 400, "y": 100},
                "data": {"description": "Search information", "expectedOutput": "Report"},
            },
        ]
        edges = [
            {"id": "e1", "source": "a1", "target": "t1", "sourceHandle": "bottom", "targetHandle": "left"},
        ]

        code = _generate_py(nodes, edges)
        assert "from crewai import Agent, Task, Crew, Process" in code
        assert "agent_0 = Agent(" in code
        assert "role='researcher'" in code
        assert "goal='Research topics'" in code
        assert "tools=['web_search']" in code
        assert "task_0 = Task(" in code
        assert "description='Search information'" in code
        assert "agent=agent_0" in code
        assert "crew = Crew(" in code
        assert "result = crew.kickoff()" in code

    def test_empty_canvas(self):
        code = _generate_py([], [])
        assert "from crewai" in code
        assert "crew = Crew" not in code

    def test_multiple_agents_multiple_tasks(self):
        nodes = [
            {
                "id": "a1",
                "type": "agentNode",
                "position": {"x": 100, "y": 100},
                "data": {"role": "researcher", "goal": "Research", "backstory": "Expert", "tools": ["search"]},
            },
            {
                "id": "a2",
                "type": "agentNode",
                "position": {"x": 100, "y": 250},
                "data": {"role": "writer", "goal": "Write", "backstory": "Writer", "tools": []},
            },
            {
                "id": "t1",
                "type": "taskNode",
                "position": {"x": 400, "y": 100},
                "data": {"description": "Search", "expectedOutput": "Data"},
            },
            {
                "id": "t2",
                "type": "taskNode",
                "position": {"x": 400, "y": 250},
                "data": {"description": "Write report", "expectedOutput": "Report"},
            },
        ]
        edges = [
            {"id": "e1", "source": "a1", "target": "t1"},
            {"id": "e2", "source": "a2", "target": "t2"},
        ]

        code = _generate_py(nodes, edges)
        assert "agent_0 = Agent(" in code
        assert "agent_1 = Agent(" in code
        assert "task_0 = Task(" in code
        assert "task_1 = Task(" in code
        assert "process=Process.sequential" in code


def _generate_py(nodes, edges):
    agent_nodes = [n for n in nodes if n.get("type") == "agentNode"]
    task_nodes = [n for n in nodes if n.get("type") == "taskNode"]
    agent_var_map = {}

    lines = []
    lines.append("from crewai import Agent, Task, Crew, Process")
    lines.append("")

    for i, node in enumerate(agent_nodes):
        data = node["data"]
        var_name = f"agent_{i}"
        agent_var_map[node["id"]] = var_name
        role = str(data.get("role", "")).replace("'", "\\'")
        goal = str(data.get("goal", "")).replace("'", "\\'")
        backstory = str(data.get("backstory", "")).replace("'", "\\'")
        tools = data.get("tools", [])

        lines.append(f"{var_name} = Agent(")
        lines.append(f"    role='{role}',")
        lines.append(f"    goal='{goal}',")
        lines.append(f"    backstory='{backstory}',")
        if tools:
            tools_str = ", ".join(f"'{t}'" for t in tools)
            lines.append(f"    tools=[{tools_str}],")
        lines.append("    allow_code_execution=False,")
        lines.append(")")
        lines.append("")

    agent_edge_map = {}
    for edge in edges:
        source_node = next((n for n in nodes if n["id"] == edge["source"]), None)
        target_node = next((n for n in nodes if n["id"] == edge["target"]), None)
        if source_node and source_node["type"] == "agentNode" and target_node and target_node["type"] == "taskNode":
            agent_edge_map[edge["target"]] = edge["source"]

    for i, node in enumerate(task_nodes):
        data = node["data"]
        var_name = f"task_{i}"
        description = str(data.get("description", "")).replace("'", "\\'")
        expected_output = str(data.get("expectedOutput", "")).replace("'", "\\'")
        assigned_source = agent_edge_map.get(node["id"])
        assigned_var = agent_var_map.get(assigned_source) if assigned_source else None

        lines.append(f"{var_name} = Task(")
        lines.append(f"    description='{description}',")
        lines.append(f"    expected_output='{expected_output}',")
        if assigned_var:
            lines.append(f"    agent={assigned_var},")
        lines.append(")")
        lines.append("")

    agent_vars = list(agent_var_map.values())
    task_vars = [f"task_{i}" for i in range(len(task_nodes))]

    if agent_vars or task_vars:
        lines.append("crew = Crew(")
        if agent_vars:
            lines.append(f"    agents=[{', '.join(agent_vars)}],")
        if task_vars:
            lines.append(f"    tasks=[{', '.join(task_vars)}],")
        lines.append("    process=Process.sequential,")
        lines.append(")")
        lines.append("")
        lines.append("result = crew.kickoff()")

    return "\n".join(lines)
