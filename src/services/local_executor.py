"""src/services/local_executor.py — Orchestrator for local bundle execution and transient mocking."""

import json
import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Generator, List
from unittest.mock import MagicMock, patch

from src.flows.dynamic_flow import DynamicWorkflow
from src.flows.registry import flow_registry
from src.services.security_guard import SecurityGuard
from src.tools.registry import tool_registry

logger = logging.getLogger(__name__)

class LocalExecutor:
    """Handles transient registration and mocking for local 'fap run' execution."""

    def __init__(self, bundle_path: Path, org_id: str = "local-org"):
        self.bundle_path = bundle_path
        self.org_id = org_id
        self.agents: List[Dict[str, Any]] = []
        self.flows: List[Dict[str, Any]] = []
        self.skills: Dict[str, str] = {}
        self.guard = SecurityGuard()

    def prepare(self):
        """Scan bundle directory, validate security and register components in memory."""
        if not self.bundle_path.exists():
            raise FileNotFoundError(f"Bundle path {self.bundle_path} not found")

        # 1. Load Skills (.py) as Tools
        skills_dir = self.bundle_path / "skills"
        if skills_dir.exists():
            from RestrictedPython import safe_builtins
            for py_file in skills_dir.glob("*.py"):
                code = py_file.read_text(encoding="utf-8")
                # Security validation
                self.guard.validate_skill(code, py_file.name)
                self.skills[py_file.name] = code
                
                # Transient registration as a tool
                try:
                    # We use the same pattern as ToolRegistry._load_from_db
                    loc: Dict[str, Any] = {}
                    # Note: We don't use compile_restricted here to avoid issues with decorators
                    # since we are in 'fap run' local mode. But we still validate with SecurityGuard.
                    exec(code, {"__builtins__": safe_builtins}, loc)
                    
                    for attr in loc.values():
                        if (isinstance(attr, type) and 
                            "Tool" in attr.__name__ and 
                            not attr.__name__.startswith("Base")):
                            
                            # Register as local tool (by filename stem)
                            tool_name = py_file.stem.lower()
                            tool_registry.register(name=f"{self.org_id}:{tool_name}")(attr)
                            
                            # Also register by class name for AgentFactory resolution
                            tool_registry.register(name=f"{self.org_id}:{attr.__name__}")(attr)
                            
                            logger.info("Transiently registered tool: %s (and class: %s)", tool_name, attr.__name__)
                except Exception as e:
                    logger.warning("Failed to register tool from %s: %s", py_file.name, e)

        # 2. Load Agents (.json)
        agents_dir = self.bundle_path / "agents"
        if agents_dir.exists():
            for json_file in agents_dir.glob("*.json"):
                data = json.loads(json_file.read_text(encoding="utf-8"))
                self.agents.append(data)

        # 3. Load Flows (.json)
        flows_dir = self.bundle_path / "flows"
        if flows_dir.exists():
            for json_file in flows_dir.glob("*.json"):
                data = json.loads(json_file.read_text(encoding="utf-8"))
                flow_type = data.get("flow_type") or json_file.stem
                self.flows.append(data)
                # Transient registration in FlowRegistry
                DynamicWorkflow.register(flow_type, data)
                logger.info("Transiently registered flow: %s", flow_type)

    @contextmanager
    def mock_persistence(self) -> Generator[None, None, None]:
        """Intercept DB calls to prevent production side-effects during local run."""
        
        # Mock for Supabase clients
        mock_db = MagicMock()
        mock_db.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[])
        mock_db.table.return_value.upsert.return_value.execute.return_value = MagicMock(data=[])
        mock_db.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(data=None)
        
        # Mocking get_tenant_client and get_service_client
        # Also mocking execute_with_retry if needed
        
        with patch("src.db.session.get_tenant_client", return_value=mock_db), \
             patch("src.db.session.get_service_client", return_value=mock_db), \
             patch("src.db.session.execute_with_retry", side_effect=lambda x: x):
            
            # Additional mock for BaseCrew._load_agent_config if we want to use bundle agents
            def mocked_load_agent_config(crew_self):
                for agent in self.agents:
                    if agent.get("role") == crew_self.role:
                        return agent
                raise ValueError(f"Agent role '{crew_self.role}' not found in local bundle")

            with patch("src.crews.base_crew.BaseCrew._load_agent_config", autospec=True) as m_load:
                m_load.side_effect = mocked_load_agent_config
                yield

    def cleanup(self):
        """Clear transient registrations."""
        flow_registry.clear()
        tool_registry.clear()
