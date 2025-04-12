from typing import Optional

from backend.grid import create_toolbinding


def sample_method(param1: str, param2: int, param3: float, param4: bool, param5: Optional[str] = None):
    """Sample method for testing create_toolbinding."""
    pass


def test_create_toolbinding():
    toolbinding = create_toolbinding(sample_method, name="sample_method")

    expected_schema = {
        "type": "function",
        "name": "sample_method",
        "description": "Sample method for testing create_toolbinding.",
        "parameters": {
            "properties": {
                "param1": {"title": "Param1", "type": "string"},
                "param2": {"title": "Param2", "type": "integer"},
                "param3": {"title": "Param3", "type": "number"},
                "param4": {"title": "Param4", "type": "boolean"},
                "param5": {"anyOf": [{"type": "string"}, {"type": "null"}], "title": "Param5"},
            },
            "required": ["param1", "param2", "param3", "param4", "param5"],
            "title": "sample_methodParameters",
            "type": "object",
            "additionalProperties": False,
        },
    }

    # Adjust the test to ignore additional fields like 'title' in the schema
    generated_schema = toolbinding["schema"]

    assert generated_schema == expected_schema
