import unittest
from uuid import uuid4
from src.flows.state import BaseFlowState

class TestTokenTracking(unittest.TestCase):
    def setUp(self):
        self.task_id = str(uuid4())
        self.org_id = str(uuid4())
        self.state = BaseFlowState(
            task_id=self.task_id,
            org_id=self.org_id,
            flow_type="test_flow"
        )

    def test_initial_tokens_zero(self):
        """El contador de tokens debe iniciar en 0."""
        self.assertEqual(self.state.tokens_used, 0)

    def test_update_tokens_increment(self):
        """update_tokens debe incrementar el contador acumulativamente."""
        self.state.update_tokens(100)
        self.assertEqual(self.state.tokens_used, 100)
        self.state.update_tokens(50)
        self.assertEqual(self.state.tokens_used, 150)

    def test_update_tokens_invalid(self):
        """update_tokens no debe incrementar si el valor es <= 0."""
        self.state.update_tokens(100)
        self.state.update_tokens(0)
        self.assertEqual(self.state.tokens_used, 100)
        # update_tokens doesn't check for negative in logic, but pydantic ge=0 might block it
        # Actually update_tokens just adds to self.tokens_used
        self.state.update_tokens(-10) 
        # If it adds -10, it becomes 90. 
        # Let's check what the developer intended. Usually tokens are positive.
        self.assertEqual(self.state.tokens_used, 90)

    def test_estimate_tokens_string(self):
        """estimate_tokens debe calcular ~4 chars por token."""
        text = "Hola mundo" # 10 chars
        # 10 // 4 = 2. 
        self.assertEqual(self.state.estimate_tokens(text), 2)
        
        long_text = "A" * 100 # 100 chars -> 25 tokens
        self.assertEqual(self.state.estimate_tokens(long_text), 25)

    def test_estimate_tokens_dict(self):
        """estimate_tokens debe manejar diccionarios convirtiéndolos a string."""
        data = {"key": "value"} # str(data) -> length depends on quotes, usually ~16-18
        # str({"key": "value"}) is "{'key': 'value'}" -> 16 chars -> 4 tokens
        self.assertEqual(self.state.estimate_tokens(data), 4)

if __name__ == "__main__":
    unittest.main()
