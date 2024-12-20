# -*- coding: utf-8 -*-
import os
import sys
import pandas as pd

class RK_Read_Excel_Row:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "file_path": ("STRING", {
                    "multiline": False,
                    "default": "path/to/your.xlsx"
                }),
                "row_index": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 100000
                }),
                "delimiter": ("STRING", {
                    "default": " ",
                    "multiline": False
                })
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("row_text",)
    FUNCTION = "read_excel_row"
    CATEGORY = "RK_tools_v02"

    def read_excel_row(self, file_path, row_index, delimiter):
        try:
            # Check if file exists
            if not os.path.isfile(file_path):
                raise FileNotFoundError(f"Excel file not found: {file_path}")

            # Read the Excel file using pandas
            df = pd.read_excel(file_path, header=None)  # No header, treat all rows as data
            
            # Check if row_index is within range
            if row_index < 0 or row_index >= len(df):
                raise IndexError(f"Row index {row_index} is out of range. File has {len(df)} rows.")

            # Extract the row data
            row_data = df.iloc[row_index].tolist()

            # Convert all values to strings and join them
            row_text = delimiter.join(map(str, row_data))

            return (row_text,)

        except Exception as e:
            print(f"Error in RK_Read_Excel_Row: {str(e)}")
            return ("",)

# Node class mappings
NODE_CLASS_MAPPINGS = {
    "RK_Read_Excel_Row": RK_Read_Excel_Row
}

# Node display name mappings
NODE_DISPLAY_NAME_MAPPINGS = {
    "RK_Read_Excel_Row": "🗃️ RK Read Excel Row"
}
