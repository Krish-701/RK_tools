# -*- coding: utf-8 -*-

class RK_Accumulate_Text_Multiline:
    # Class variable to store accumulated text
    accumulated_text = ""

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
                    "default": "\n"  # Default to newline
                }),
                "reset_accumulation": (["no", "yes"], {"default": "no"})
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("accumulated_string",)
    FUNCTION = "accumulate_text"
    CATEGORY = "RK_tools_v02"

    def accumulate_text(self, input_text_1, input_text_2, separator, reset_accumulation):
        try:
            # Reset if requested
            if reset_accumulation == "yes":
                self.__class__.accumulated_text = ""

            # Combine inputs into a new block of text
            if input_text_1.strip() and input_text_2.strip():
                new_block = input_text_1 + "\n" + input_text_2
            elif input_text_1.strip():
                new_block = input_text_1
            else:
                new_block = input_text_2

            # If there is already accumulated text and new_block is not empty
            if self.__class__.accumulated_text.strip() and new_block.strip():
                self.__class__.accumulated_text += separator + new_block
            else:
                # If accumulated text is empty, just set it to the new block
                # Or if the new block is empty, do nothing
                if new_block.strip():
                    self.__class__.accumulated_text += new_block

            return (self.__class__.accumulated_text,)

        except Exception as e:
            print(f"Error in RK_Accumulate_Text_Multiline: {str(e)}")
            raise e

# Node class mappings
NODE_CLASS_MAPPINGS = {
    "RK_Accumulate_Text_Multiline": RK_Accumulate_Text_Multiline
}

# Node display name mappings
NODE_DISPLAY_NAME_MAPPINGS = {
    "RK_Accumulate_Text_Multiline": "✏️ RK Accumulate Text (Multiline)"
}
