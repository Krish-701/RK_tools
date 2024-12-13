# -*- coding: utf-8 -*-
import os

class RK_Concatenate_Text:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input_text_1": ("STRING", {
                    "multiline": True,
                    "default": "Enter your first text..."
                }),
                "input_text_2": ("STRING", {
                    "multiline": True,
                    "default": "Enter your second text..."
                }),
                "concatenation_mode": (["append", "prepend", "join_with_space", "join_with_newline"], {
                    "default": "append"
                }),
                "prefix": ("STRING", {
                    "default": "",
                    "multiline": False
                }),
                "suffix": ("STRING", {
                    "default": "",
                    "multiline": False
                }),
                "load_from_file": (["no", "yes"], {"default": "no"}),
                "file_path": ("STRING", {
                    "default": "",
                    "multiline": False
                })
            }
        }
    
    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("input_1_output", "input_2_output", "concatenated_text")
    FUNCTION = "concatenate_text"
    CATEGORY = "RK_tools_v02"

    def concatenate_text(self, input_text_1, input_text_2, concatenation_mode, prefix, suffix, load_from_file, file_path):
        try:
            # Optionally load text from file
            file_text = ""
            if load_from_file == "yes" and file_path.strip():
                if os.path.exists(file_path) and os.path.isfile(file_path):
                    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                        file_text = f.read()
                else:
                    print(f"Warning: The file path '{file_path}' does not exist or is not a file.")

            # Determine the concatenation approach
            if concatenation_mode == "append":
                # input_text_1 + input_text_2 + file_text
                combined_text = input_text_1 + input_text_2 + file_text
            elif concatenation_mode == "prepend":
                # file_text + input_text_1 + input_text_2
                combined_text = file_text + input_text_1 + input_text_2
            elif concatenation_mode == "join_with_space":
                # Join non-empty texts with a space
                segments = [t for t in [input_text_1, input_text_2, file_text] if t.strip()]
                combined_text = " ".join(segments)
            elif concatenation_mode == "join_with_newline":
                # Join non-empty texts with a newline
                segments = [t for t in [input_text_1, input_text_2, file_text] if t.strip()]
                combined_text = "\n".join(segments)
            else:
                # Default to just appending if somehow invalid mode is chosen
                combined_text = input_text_1 + input_text_2 + file_text

            # Add prefix and suffix
            if prefix:
                combined_text = prefix + combined_text
            if suffix:
                combined_text = combined_text + suffix

            return input_text_1, input_text_2, combined_text

        except Exception as e:
            print(f"Error in RK_Concatenate_Text: {str(e)}")
            raise e

# Node class mappings
NODE_CLASS_MAPPINGS = {
    "RK_Concatenate_Text": RK_Concatenate_Text
}

# Node display name mappings
NODE_DISPLAY_NAME_MAPPINGS = {
    "RK_Concatenate_Text": "✏️ RK Concatenate Text"
}
