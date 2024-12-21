import os
import sys
import random
import csv

class RK_Excel_File_State_Looper:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "file_path": ("STRING", {
                    "multiline": False,
                    "default": "path/to/your_file.csv"
                }),
                "loop_mode": (["disabled", "random", "increment"],),
                "start_index": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 100000,
                    "step": 1
                }),
                "end_index": ("INT", {
                    "default": 10,
                    "min": 0,
                    "max": 100000,
                    "step": 1
                }),
                "step_size": ("INT", {
                    "default": 1,
                    "min": 1,
                    "max": 1000,
                    "step": 1
                }),
                "delimiter": ("STRING", {
                    "default": ",",
                    "multiline": False
                })
            }
        }

    # Only one return type now
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("row_text",)
    FUNCTION = "read_row"
    CATEGORY = "RK_tools_v02"

    # Cache variables
    file_data_cache = None
    file_path_cache = None

    def load_file(self, file_path, delimiter):
        """
        Loads a CSV file into a list of lists and caches it.
        """
        if RK_Excel_File_State_Looper.file_path_cache != file_path:
            if not os.path.isfile(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")

            _, ext = os.path.splitext(file_path)
            ext = ext.lower()

            if ext != ".csv":
                raise ValueError(f"Unsupported file extension: {ext}. Only .csv is supported.")

            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f, delimiter=delimiter)
                data = list(reader)

            RK_Excel_File_State_Looper.file_data_cache = data
            RK_Excel_File_State_Looper.file_path_cache = file_path

        return RK_Excel_File_State_Looper.file_data_cache

    def get_row_count(self, data):
        return len(data)

    def get_state_file_path(self, file_path, start_index, end_index, step_size, loop_mode):
        base, ext = os.path.splitext(file_path)
        state_file = f"{base}_state_{loop_mode}_{start_index}_{end_index}_{step_size}.txt"
        return state_file

    def read_current_index(self, state_file, start_index):
        if os.path.isfile(state_file):
            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    val = f.read().strip()
                    return int(val)
            except:
                pass
        return start_index

    def write_current_index(self, state_file, index):
        with open(state_file, 'w', encoding='utf-8') as f:
            f.write(str(index))

    def read_row(self, file_path, loop_mode, start_index, end_index, step_size, delimiter):
        try:
            data = self.load_file(file_path, delimiter)
            total_rows = self.get_row_count(data)

            # Adjust indices if out of range
            if start_index < 0:
                start_index = 0
            if end_index >= total_rows:
                end_index = total_rows - 1
            if end_index < start_index:
                # Swap if end_index < start_index
                start_index, end_index = end_index, start_index

            state_file = self.get_state_file_path(file_path, start_index, end_index, step_size, loop_mode)

            # Determine chosen_index
            if loop_mode == "disabled":
                chosen_index = start_index

            elif loop_mode == "random":
                chosen_index = random.randint(start_index, end_index)

            elif loop_mode == "increment":
                current_index = self.read_current_index(state_file, start_index)
                chosen_index = current_index
                new_index = chosen_index + step_size
                if new_index > end_index:
                    new_index = start_index
                self.write_current_index(state_file, new_index)

            else:
                chosen_index = start_index

            row_data = data[chosen_index]
            # Join row data with the chosen delimiter (for display)
            row_text = delimiter.join(map(str, row_data))

            # Remove leading/trailing quotes (standard and fancy quotes)
            row_text = row_text.strip(' "“”')

            print(f"[DEBUG] Mode: {loop_mode}, Chosen Index: {chosen_index}")
            print(f"[DEBUG] Raw Row Text: {repr(row_text)}")

            # Return only the row_text
            return (row_text,)

        except Exception as e:
            print(f"Error in RK_Excel_File_State_Looper: {str(e)}")
            return ("",)

# Node class mappings
NODE_CLASS_MAPPINGS = {
    "RK_Excel_File_State_Looper": RK_Excel_File_State_Looper
}

# Node display name mappings
NODE_DISPLAY_NAME_MAPPINGS = {
    "RK_Excel_File_State_Looper": "📜 RK CSV File State Looper"
}
