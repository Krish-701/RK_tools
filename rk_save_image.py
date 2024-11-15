import os
import json
import numpy as np
from PIL import Image
from PIL.PngImagePlugin import PngInfo
import folder_paths

class rk_save_image:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE",),
                "filename_prefix": ("STRING", {"default": "ComfyUI"}),
                "save_metadata": ("BOOLEAN", {"default": True}),
            },
            "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"},
        }

    RETURN_TYPES = ()
    FUNCTION = "save_images"
    OUTPUT_NODE = True
    CATEGORY = "RK_tools_v02"

    def save_images(self, images, filename_prefix="ComfyUI", save_metadata=True, prompt=None, extra_pnginfo=None):
        output_dir = folder_paths.get_output_directory()
        
        # Find the highest existing number
        existing_files = [f for f in os.listdir(output_dir) if f.startswith(filename_prefix) and f.endswith('.png')]
        highest_num = 0
        
        for file in existing_files:
            try:
                # Extract number from filename (e.g., "ComfyUI_00001.png" -> 1)
                num = int(file.split('_')[-1].split('.')[0])
                highest_num = max(highest_num, num)
            except:
                continue
        
        # Start numbering from the next number
        counter = highest_num + 1
        
        results = list()
        for image in images:
            i = 255. * image.cpu().numpy()
            img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))
            
            metadata = PngInfo()
            if save_metadata:
                if prompt is not None:
                    metadata.add_text("prompt", json.dumps(prompt))
                if extra_pnginfo is not None:
                    for x in extra_pnginfo:
                        metadata.add_text(x, json.dumps(extra_pnginfo[x]))
            
            # Format filename with counter
            file = f"{filename_prefix}_{counter:05}.png"
            full_path = os.path.join(output_dir, file)
            
            # Save the image
            img.save(full_path, pnginfo=metadata, optimize=True)
            
            results.append({
                "filename": file,
                "subfolder": "",
                "type": "output"
            })
            counter += 1

        return {"ui": {"images": results}}

NODE_CLASS_MAPPINGS = {
    "rk_save_image": rk_save_image
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "rk_save_image": "RK Save Image"
}