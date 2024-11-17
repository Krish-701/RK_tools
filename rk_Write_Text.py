# -*- coding: utf-8 -*-
import os
import sys

class RK_Write_Text:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input_text": ("STRING", {
                    "multiline": True,
                    "default": "Write your text here..."
                }),
                "text_mode": (["normal", "uppercase", "lowercase", "title"],),
                "prefix": ("STRING", {
                    "default": "",
                    "multiline": False
                }),
                "suffix": ("STRING", {
                    "default": "",
                    "multiline": False
                })
            },
            "optional": {
                "received_text": ("STRING", {
                    "multiline": True,
                    "default": ""
                }),
            }
        }
    
    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("text_output", "formatted_text", "combined_text", "received_text")
    FUNCTION = "process_text"
    CATEGORY = "RK_tools_v02"

    def process_text(self, input_text, text_mode, prefix, suffix, received_text=None):
        try:
            # Process the input text based on the selected mode
            if text_mode == "uppercase":
                formatted_text = input_text.upper()
            elif text_mode == "lowercase":
                formatted_text = input_text.lower()
            elif text_mode == "title":
                formatted_text = input_text.title()
            else:  # normal mode
                formatted_text = input_text

            # Add prefix and suffix if provided
            if prefix or suffix:
                combined_text = f"{prefix}{formatted_text}{suffix}"
            else:
                combined_text = formatted_text

            # Handle received text
            if received_text:
                received_output = f"Received: {received_text}"
            else:
                received_output = "No text received"

            return (
                input_text,          # original input text
                formatted_text,      # formatted based on mode
                combined_text,       # text with prefix/suffix
                received_output      # received text status
            )

        except Exception as e:
            print(f"Error in RK_Write_Text: {str(e)}")
            raise e

# Node class mappings
NODE_CLASS_MAPPINGS = {
    "RK_Write_Text": RK_Write_Text
}

# Node display name mappings
NODE_DISPLAY_NAME_MAPPINGS = {
    "RK_Write_Text": "✏️ RK Write Text"
}