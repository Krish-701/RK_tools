# -*- coding: utf-8 -*-
import os
import sys
import random
import pandas as pd

class RK_Excel_File_State_Looper:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "file_path": ("STRING", {
                    "multiline": False,
                    "default": "path/to/your.xlsx"
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
                    "default": " ",
                    "multiline": False
                })
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("row_text", "chosen_index_str")
    FUNCTION = "read_row"
    CATEGORY = "RK_tools_v02"

    df_cache = None
    df_path = None

    def load_excel(self, file_path):
        # Cache the DataFrame to avoid reloading on each call
        if RK_Excel_File_State_Looper.df_path != file_path:
            if not os.path.isfile(file_path):
                raise FileNotFoundError(f"Excel file not found: {file_path}")
            RK_Excel_File_State_Looper.df_cache = pd.read_excel(file_path, header=None)
            RK_Excel_File_State_Looper.df_path = file_path
        return RK_Excel_File_State_Looper.df_cache

    def get_row_count(self, df):
        return len(df)

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
            df = self.load_excel(file_path)
            total_rows = self.get_row_count(df)

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

            row_data = df.iloc[chosen_index].tolist()
            row_text = delimiter.join(map(str, row_data))

            # Remove leading/trailing quotes (standard and fancy quotes)
            row_text = row_text.strip(' "“”')

            chosen_index_str = f"Current Row Index: {chosen_index}"

            print(f"[DEBUG] Mode: {loop_mode}, Chosen Index: {chosen_index}")
            print(f"[DEBUG] Raw Row Text: {repr(row_text)}")

            return (row_text, chosen_index_str)

        except Exception as e:
            print(f"Error in RK_Excel_File_State_Looper: {str(e)}")
            return ("", "")

# Node class mappings
NODE_CLASS_MAPPINGS = {
    "RK_Excel_File_State_Looper": RK_Excel_File_State_Looper
}

# Node display name mappings
NODE_DISPLAY_NAME_MAPPINGS = {
    "RK_Excel_File_State_Looper": "📜 RK Excel File State Looper"
}
