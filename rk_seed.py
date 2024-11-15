# -*- coding: utf-8 -*-
import os
import sys
import random
import math

class RK_seed:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "seed": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 0xffffffffffffffff,
                    "step": 1,
                    "display": "number"
                }),
                "loop_mode": (["disabled", "random", "increment", "decrement", "fixed"],),
                "start_value": ("FLOAT", {
                    "default": 0.1,
                    "min": 0.0,
                    "max": 100.0,
                    "step": 0.1
                }),
                "end_value": ("FLOAT", {
                    "default": 1.0,
                    "min": 0.0,
                    "max": 100.0,
                    "step": 0.1
                }),
                "step_size": ("FLOAT", {
                    "default": 0.1,
                    "min": 0.001,  # Reduced minimum step size
                    "max": 100.0,
                    "step": 0.1
                }),
                "loop_count": ("INT", {
                    "default": 10,
                    "min": 1,
                    "max": 100,  # Changed max from 1000 to 100
                    "step": 1
                }),
                "decimal_places": ("INT", {
                    "default": 2,
                    "min": 1,
                    "max": 6,
                    "step": 1
                }),
            },
            "optional": {
                "custom_values": ("STRING", {
                    "multiline": True,
                    "default": "0.1, 0.8, 1.6"
                }),
            }
        }

    RETURN_TYPES = ("SEED", "NUMBER", "FLOAT", "INT", "STRING", "FLOAT", "INT", "STRING")
    RETURN_NAMES = ("seed", "number", "float", "int", "string", "loop_value", "loop_index", "loop_value_string")
    FUNCTION = "process_seed"
    CATEGORY = "RK_tools_v02"

    def __init__(self):
        self.current_index = 0
        self.current_value = 0.0
        self.values_list = []

    def format_float(self, value, decimal_places):
        """Format float to specified decimal places"""
        format_str = f"{{:.{decimal_places}f}}"
        return float(format_str.format(value))

    def process_seed(self, seed, loop_mode, start_value, end_value, step_size, loop_count, decimal_places, custom_values=None):
        try:
            # Ensure start_value is not greater than end_value
            if start_value > end_value:
                start_value, end_value = end_value, start_value

            seed_dict = {"seed": int(seed)}

            # Initialize loop value
            loop_value = start_value

            # Process based on loop mode
            if loop_mode != "disabled":
                if loop_mode == "fixed" and custom_values:
                    try:
                        # Parse and format custom values
                        self.values_list = [self.format_float(float(x.strip()), decimal_places) 
                                          for x in custom_values.split(",")]
                        loop_value = self.values_list[self.current_index % len(self.values_list)]
                    except Exception as e:
                        print(f"Error parsing custom values: {e}")
                        # Fallback to start_value if parsing fails
                        loop_value = start_value

                elif loop_mode == "random":
                    loop_value = self.format_float(random.uniform(start_value, end_value), decimal_places)

                elif loop_mode in ["increment", "decrement"]:
                    # Calculate total steps
                    total_range = end_value - start_value
                    n_steps = int(round(total_range / step_size)) + 1

                    # Adjust index based on mode
                    adjusted_index = self.current_index % n_steps

                    if loop_mode == "increment":
                        loop_value = self.format_float(
                            start_value + (adjusted_index * step_size),
                            decimal_places
                        )
                    elif loop_mode == "decrement":
                        loop_value = self.format_float(
                            end_value - (adjusted_index * step_size),
                            decimal_places
                        )

                    # Increment counter
                    self.current_index += 1

                # Limit the loop_value to not exceed 100
                if loop_value > 100.0:
                    loop_value = 100.0

                # Ensure loop_count is not exceeded
                if self.current_index >= loop_count:
                    self.current_index = 0

            # Store current value
            self.current_value = loop_value

            # Format the string output with specified decimal places
            loop_value_string = f"{loop_value:.{decimal_places}f}"

            return (
                seed_dict,           # SEED
                float(seed),         # NUMBER
                float(seed),         # FLOAT
                int(seed),           # INT
                str(seed),           # STRING
                float(loop_value),   # loop_value
                self.current_index,  # loop_index
                loop_value_string    # loop_value_string
            )

        except Exception as e:
            print(f"Error in RK_seed: {str(e)}")
            raise e

# Node class mappings
NODE_CLASS_MAPPINGS = {
    "RK_seed": RK_seed
}

# Node display name mappings
NODE_DISPLAY_NAME_MAPPINGS = {
    "RK_seed": "🎲 RK Seed Loop"
}
