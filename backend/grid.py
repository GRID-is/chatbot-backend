from .types import ToolBinding


class GridAPI:
    def __init__(self):
        self._tools: dict[str, ToolBinding] = {
            "make_calculation": {
                "ref": self.make_calculation,
                "schema": {
                    "type": "function",
                    "name": "make_calculation",
                    "description": "Calculate with A, B, and C.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "A": {"type": "number"},
                            "B": {"type": "number"},
                            "C": {"type": "number"},
                        },
                        "required": ["A", "B", "C"],
                        "additionalProperties": False,
                    },
                },
            }
        }

    def make_calculation(self, A: int, B: int, C: int) -> int:
        """
        Perform a calculation using three numbers A, B, and C.
        This is a placeholder function that sums the numbers.
        """
        print(f"Calculating({A=}, {B=}, {C=})")
        result = A + B + C  # Replace this with your actual calculation logic
        return result

    @property
    def tools(self):
        return self._tools
