from typing import Any

class RK_Calc:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "number1": ("FLOAT", {"default": 1.0, "description": "First number"}),
                "operator": ("STRING", {
                    "default": "*",
                    "choices": ["+", "-", "*", "/"],
                    "description": "Operator"
                }),
                "number2": ("FLOAT", {"default": 1.0, "description": "Second number"}),
            }
        }

    RETURN_TYPES = ("INT", "FLOAT", "STRING")
    FUNCTION = "calculate"
    CATEGORY = "RK_tools_v02"
    OUTPUT_NODE = True

    def calculate(self, number1: float, operator: str, number2: float) -> Any:
        try:
            if operator == '+':
                result_float = number1 + number2
            elif operator == '-':
                result_float = number1 - number2
            elif operator == '*':
                result_float = number1 * number2
            elif operator == '/':
                if number2 == 0:
                    raise ValueError("Division by zero is not allowed.")
                result_float = number1 / number2
            else:
                raise ValueError(f"Unsupported operator: {operator}")
        except Exception as e:
            raise ValueError(f"Error in calculation: {e}")

        result_int = int(result_float)
        result_string = str(result_float)
        return (result_int, result_float, result_string)

# Register the node
NODE_CLASS_MAPPINGS = {"RK_Calc": RK_Calc}
NODE_DISPLAY_NAME_MAPPINGS = {"RK_Calc": "RK_Calc"}
