# -*- coding: utf-8 -*-

class RK_Accumulate_Text_Multiline_Numbered:
    # Class variables to store accumulated text and line count
    accumulated_text = ""
    line_count = 1

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input_text_1": ("STRING", {
                    "multiline": True,
                    "default": "Enter first multiline text..."
                }),
                "input_text_2": ("STRING", {
                    "multiline": True,
                    "default": ""
                }),
                "separator": ("STRING", {
                    "multiline": False,
                    "default": "\n"  # Default to newline between appended blocks
                }),
                "reset_accumulation": (["no", "yes"], {"default": "no"}),
                "line_numbering": (["no", "yes"], {"default": "no"})
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("accumulated_string",)
    FUNCTION = "accumulate_text"
    CATEGORY = "RK_tools_v02"

    def accumulate_text(self, input_text_1, input_text_2, separator, reset_accumulation, line_numbering):
        try:
            # Reset if requested
            if reset_accumulation == "yes":
                self.__class__.accumulated_text = ""
                self.__class__.line_count = 1

            # Combine inputs into a new block of text
            if input_text_1.strip() and input_text_2.strip():
                new_block = input_text_1.rstrip("\n") + "\n" + input_text_2.lstrip("\n")
            elif input_text_1.strip():
                new_block = input_text_1
            else:
                new_block = input_text_2

            # If no new text, just return current state
            if not new_block.strip():
                return (self.__class__.accumulated_text,)

            # Split the new block into lines
            new_lines = new_block.split("\n")

            # Prepare the block with or without numbering
            formatted_block = []
            if line_numbering == "yes":
                # Add line numbers to each line
                for line in new_lines:
                    if line.strip():
                        formatted_block.append(f"{self.__class__.line_count}. {line}")
                        self.__class__.line_count += 1
                    else:
                        # Even if line is empty, we might still increment line_count if desired.
                        # For simplicity, let's not increment on empty lines, so numbering only increments on actual text lines.
                        formatted_block.append(line)
            else:
                # No numbering, just use lines as-is
                formatted_block = new_lines

            # Join the formatted lines back into a single block
            new_block_formatted = "\n".join(formatted_block)

            # Append to the accumulated text
            # If there's already accumulated text, add the separator
            if self.__class__.accumulated_text.strip() and new_block_formatted.strip():
                self.__class__.accumulated_text += separator + new_block_formatted
            else:
                # If there's no accumulated text yet or new_block_formatted is the first significant addition
                if not self.__class__.accumulated_text.strip():
                    self.__class__.accumulated_text = new_block_formatted
                else:
                    # accumulated text is empty or no new meaningful text
                    self.__class__.accumulated_text += new_block_formatted

            return (self.__class__.accumulated_text,)

        except Exception as e:
            print(f"Error in RK_Accumulate_Text_Multiline_Numbered: {str(e)}")
            raise e

# Node class mappings
NODE_CLASS_MAPPINGS = {
    "RK_Accumulate_Text_Multiline_Numbered": RK_Accumulate_Text_Multiline_Numbered
}

# Node display name mappings
NODE_DISPLAY_NAME_MAPPINGS = {
    "RK_Accumulate_Text_Multiline_Numbered": "✏️ RK Accumulate Text (Multiline, Numbered)"
}
