import os
import re
import csv
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, filedialog

# ======================================
# GLOBALS
# ======================================
stop_generation = False

# Dictionary of memory per model: { model_name: [ {title, desc, style}, ... ] }
ALL_PROMPTS_MEMORY = {}

# ======================================
# HELPER FUNCTIONS
# ======================================
def parse_ollama_output(response: str):
    """
    Attempt to parse the Ollama response to extract Title, Description, and Style.
    We'll handle lines like:
      Title: ...
      Description: ...
      Style: ...
    Also handle optional quotes, indentation, etc.
    Return None if nothing is matched.
    """
    title_match = re.search(r'(?im)^\s*Title:\s*["“]?(.+?)["”]?\s*$', response)
    desc_match  = re.search(r'(?im)^\s*Description:\s*(.+)$', response)
    style_match = re.search(r'(?im)^\s*Style:\s*(.+)$', response)

    if not title_match and not desc_match and not style_match:
        return None

    title = title_match.group(1).strip() if title_match else ""
    desc  = desc_match.group(1).strip()  if desc_match else ""
    style = style_match.group(1).strip() if style_match else ""

    # If all are empty, treat as unparsed
    if not title and not desc and not style:
        return None

    return {
        "title": title,
        "description": desc,
        "style": style
    }

def build_system_prompt_with_memory(model_name: str, basic_prompt: str):
    """
    Build a system prompt that includes the memory from ALL_PROMPTS_MEMORY[model_name].
    If there's no memory for that model, return basic_prompt.
    """
    global ALL_PROMPTS_MEMORY
    if model_name not in ALL_PROMPTS_MEMORY or not ALL_PROMPTS_MEMORY[model_name]:
        return basic_prompt

    memory_text = "\n".join(
        f"{idx+1}) {p['title']} | {p['description']} | {p['style']}"
        for idx, p in enumerate(ALL_PROMPTS_MEMORY[model_name])
    )

    system_prompt = f"""SYSTEM:
You are an AI specialized in creating random, photorealistic prompts.
Already generated for {model_name}:
{memory_text}

Do NOT repeat those. Provide something brand-new and unique.

{basic_prompt}
"""
    return system_prompt

def build_basic_system_prompt():
    """
    A simpler system prompt if memory is off or no memory exists yet.
    """
    return """SYSTEM:
You are an AI specialized in creating random, photorealistic prompts.
Always produce unique results.

Use this structure:
Title: (up to 5 words)
Description: (up to 20 words, photorealistic)
Style: (1-3 words, e.g. cinematic, macro, surreal)
"""

def reset_memory_func(gui_elements):
    """
    Clears ALL_PROMPTS_MEMORY for all models and updates the log box.
    """
    global ALL_PROMPTS_MEMORY
    ALL_PROMPTS_MEMORY.clear()
    log_box = gui_elements["log_box"]
    log_box.insert(tk.END, "[INFO] All memory has been reset.\n")
    log_box.see(tk.END)

# ======================================
# GENERATION LOGIC (for one model)
# ======================================
def generate_prompts_for_model(
    model_name: str,
    num_prompts: int,
    output_csv: str,
    reference_text: str,
    use_memory: bool,
    save_mode: str,
    log_box: tk.Text,
    progress_bar: ttk.Progressbar,
):
    """
    Generates prompts for a single model in a loop, saving to CSV.
    Uses a separate memory list for each model in ALL_PROMPTS_MEMORY[model_name].
    """
    global stop_generation
    global ALL_PROMPTS_MEMORY

    # If the model doesn't have a memory list yet, create one
    if model_name not in ALL_PROMPTS_MEMORY:
        ALL_PROMPTS_MEMORY[model_name] = []

    # We'll store newly generated prompts in a local list for this run
    new_prompts_this_run = []
    total_prompts = num_prompts

    # For duplicates/fallback
    max_attempts = num_prompts * 3
    attempts = 0

    # Build a base system prompt
    base_prompt_text = build_basic_system_prompt()

    # Start generation loop
    while len(new_prompts_this_run) < total_prompts and attempts < max_attempts:
        if stop_generation:
            log_box.insert(tk.END, f"\n[INFO] Generation for model '{model_name}' stopped by user.\n")
            break

        attempts += 1

        # Possibly build memory-based system prompt
        if use_memory:
            system_part = build_system_prompt_with_memory(model_name, base_prompt_text)
        else:
            system_part = base_prompt_text

        # Build final user instructions
        if reference_text.strip():
            user_part = f"USER:\nIncorporate this reference: '{reference_text}'\nGenerate 1 new prompt.\nTitle:\nDescription:\nStyle:"
        else:
            user_part = "USER:\nGenerate 1 new random prompt.\nTitle:\nDescription:\nStyle:"

        final_prompt = f"{system_part}\n\n{user_part}\n"

        # Call Ollama via stdin (avoid WinError 206)
        try:
            result = subprocess.run(
                ["ollama", "run", model_name],
                input=final_prompt,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace"
            )
            response_text = result.stdout.strip()
        except Exception as e:
            log_box.insert(tk.END, f"[ERROR] Ollama call failed for model '{model_name}': {str(e)}\n")
            break

        parsed = parse_ollama_output(response_text)
        if not parsed:
            # fallback: store entire text as UNPARSED
            parsed = {
                "title": "UNPARSED",
                "description": response_text,
                "style": ""
            }

        # Check duplicates if memory is on
        if use_memory:
            is_duplicate = any(
                p["title"] == parsed["title"]
                and p["description"] == parsed["description"]
                and p["style"] == parsed["style"]
                for p in ALL_PROMPTS_MEMORY[model_name]
            )
        else:
            is_duplicate = any(
                p["title"] == parsed["title"]
                and p["description"] == parsed["description"]
                and p["style"] == parsed["style"]
                for p in new_prompts_this_run
            )

        if is_duplicate:
            log_box.insert(tk.END, f"[{model_name}] Attempt {attempts}: Found duplicate, skipping.\n")
            continue

        # It's new, add it
        new_prompts_this_run.append(parsed)
        if use_memory:
            ALL_PROMPTS_MEMORY[model_name].append(parsed)

        log_box.insert(tk.END,
            f"[{model_name}] Prompt #{len(new_prompts_this_run)}/{total_prompts}\n"
            f"Title: {parsed['title']}\n"
            f"Description: {parsed['description']}\n"
            f"Style: {parsed['style']}\n\n"
        )
        log_box.see(tk.END)

        # Update progress bar (for single-model scenario, or partial for multi-model)
        # We won't do a perfect 2-model combined progress. We'll just show each model's local progress.
        progress_value = int((len(new_prompts_this_run) / total_prompts) * 100)
        progress_bar["value"] = progress_value

    # Write CSV
    if new_prompts_this_run:
        try:
            dirpath = os.path.dirname(output_csv)
            if dirpath and not os.path.exists(dirpath):
                os.makedirs(dirpath, exist_ok=True)

            file_mode = "a" if save_mode == "append" else "w"

            # Only write header if overwriting or new file
            write_header = True
            if file_mode == "a" and os.path.exists(output_csv):
                write_header = False

            with open(output_csv, mode=file_mode, newline="", encoding="utf-8") as csvfile:
                fieldnames = ["Title", "Description", "Style"]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                if write_header:
                    writer.writeheader()
                for p in new_prompts_this_run:
                    writer.writerow({
                        "Title": p["title"],
                        "Description": p["description"],
                        "Style": p["style"]
                    })
            log_box.insert(
                tk.END, f"[{model_name}] Saved {len(new_prompts_this_run)} prompts to {output_csv}.\n\n"
            )
            log_box.see(tk.END)
        except Exception as e:
            log_box.insert(tk.END, f"[ERROR] CSV write failed for model '{model_name}': {str(e)}\n")
    else:
        log_box.insert(tk.END, f"[{model_name}] No new prompts generated; nothing saved.\n")

# ======================================
# THREAD TARGET FOR (ONE OR TWO) MODELS
# ======================================
def generate_prompts_threaded(gui_elements):
    """
    Top-level function invoked in a background thread.
    Checks whether user selected one model or two models,
    then calls generate_prompts_for_model accordingly.
    """
    global stop_generation
    stop_generation = False

    number_of_models = gui_elements["number_of_models_var"].get()

    # Common settings (memory, ref, save_mode)
    use_memory = (gui_elements["use_memory_var"].get() == 1)
    reference_text = gui_elements["reference_prompt_text"].get("1.0", tk.END).strip()
    save_mode = gui_elements["save_mode_var"].get()
    log_box = gui_elements["log_box"]

    # We'll store threads in a list if user selected two models
    threads = []

    if number_of_models == "one":
        # Single model
        model_name = gui_elements["model1_var"].get().strip()
        num_prompts = int(gui_elements["prompt_count1_var"].get())
        output_csv = gui_elements["output_file1_var"].get().strip()

        # Basic checks
        if not model_name:
            log_box.insert(tk.END, "[ERROR] Model #1 name cannot be empty.\n")
            return
        if num_prompts < 1:
            log_box.insert(tk.END, "[ERROR] Number of prompts for Model #1 must be >= 1.\n")
            return
        if not output_csv:
            log_box.insert(tk.END, "[ERROR] Output CSV for Model #1 cannot be empty.\n")
            return

        # Call generation for single model on the current thread
        generate_prompts_for_model(
            model_name=model_name,
            num_prompts=num_prompts,
            output_csv=output_csv,
            reference_text=reference_text,
            use_memory=use_memory,
            save_mode=save_mode,
            log_box=log_box,
            progress_bar=gui_elements["progress_bar1"]
        )
    else:
        # Two models in parallel
        model_name1 = gui_elements["model1_var"].get().strip()
        num_prompts1 = int(gui_elements["prompt_count1_var"].get())
        output_csv1 = gui_elements["output_file1_var"].get().strip()

        model_name2 = gui_elements["model2_var"].get().strip()
        num_prompts2 = int(gui_elements["prompt_count2_var"].get())
        output_csv2 = gui_elements["output_file2_var"].get().strip()

        # Basic checks for model 1
        if not model_name1:
            log_box.insert(tk.END, "[ERROR] Model #1 name cannot be empty.\n")
            return
        if num_prompts1 < 1:
            log_box.insert(tk.END, "[ERROR] Number of prompts for Model #1 must be >= 1.\n")
            return
        if not output_csv1:
            log_box.insert(tk.END, "[ERROR] Output CSV for Model #1 cannot be empty.\n")
            return

        # Basic checks for model 2
        if not model_name2:
            log_box.insert(tk.END, "[ERROR] Model #2 name cannot be empty.\n")
            return
        if num_prompts2 < 1:
            log_box.insert(tk.END, "[ERROR] Number of prompts for Model #2 must be >= 1.\n")
            return
        if not output_csv2:
            log_box.insert(tk.END, "[ERROR] Output CSV for Model #2 cannot be empty.\n")
            return

        # We'll spawn two separate threads
        def worker1():
            generate_prompts_for_model(
                model_name=model_name1,
                num_prompts=num_prompts1,
                output_csv=output_csv1,
                reference_text=reference_text,
                use_memory=use_memory,
                save_mode=save_mode,
                log_box=log_box,
                progress_bar=gui_elements["progress_bar1"]
            )

        def worker2():
            generate_prompts_for_model(
                model_name=model_name2,
                num_prompts=num_prompts2,
                output_csv=output_csv2,
                reference_text=reference_text,
                use_memory=use_memory,
                save_mode=save_mode,
                log_box=log_box,
                progress_bar=gui_elements["progress_bar2"]
            )

        t1 = threading.Thread(target=worker1)
        t2 = threading.Thread(target=worker2)
        threads.extend([t1, t2])

        for t in threads:
            t.start()

        for t in threads:
            t.join()

    log_box.insert(tk.END, "[INFO] Generation process finished.\n")
    log_box.see(tk.END)

def start_generation(gui_elements):
    """
    Starts the generation in a background thread so the UI remains responsive.
    """
    thread = threading.Thread(target=generate_prompts_threaded, args=(gui_elements,))
    thread.start()

def stop_generation_func():
    """
    Sets the global stop flag to True to stop generation gracefully.
    """
    global stop_generation
    stop_generation = True

def browse_csv_file(output_file_var):
    """
    Opens a file dialog to choose the CSV output path.
    """
    filepath = filedialog.asksaveasfilename(
        defaultextension=".csv",
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
    )
    if filepath:
        output_file_var.set(filepath)

# ======================================
# MAIN GUI
# ======================================
def main():
    root = tk.Tk()
    root.title("Ollama Prompt Generator - Single or Dual Model")

    # Window size
    root.geometry("820x800")

    # Frame: Model Selection (One or Two)
    model_select_frame = ttk.LabelFrame(root, text="Number of Models")
    model_select_frame.pack(fill=tk.X, padx=10, pady=5)

    number_of_models_var = tk.StringVar(value="one")

    one_model_radio = ttk.Radiobutton(
        model_select_frame, text="One Model", variable=number_of_models_var, value="one"
    )
    two_model_radio = ttk.Radiobutton(
        model_select_frame, text="Two Models", variable=number_of_models_var, value="two"
    )
    one_model_radio.pack(side=tk.LEFT, padx=5)
    two_model_radio.pack(side=tk.LEFT, padx=5)

    # We'll define a function that toggles the second model frame's visibility
    def toggle_second_model(*args):
        if number_of_models_var.get() == "two":
            model2_frame.pack(fill=tk.X, padx=10, pady=5)
        else:
            model2_frame.forget()

    number_of_models_var.trace_add("write", toggle_second_model)

    # Frame for model #1
    model1_frame = ttk.LabelFrame(root, text="Model #1 Configuration")
    model1_frame.pack(fill=tk.X, padx=10, pady=5)

    ttk.Label(model1_frame, text="Model Name:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
    model1_var = tk.StringVar(value="marco-o1:7b-fp16")
    model1_entry = ttk.Entry(model1_frame, textvariable=model1_var, width=25)
    model1_entry.grid(row=0, column=1, padx=5, pady=2, sticky=tk.W)

    ttk.Label(model1_frame, text="Number of Prompts:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
    prompt_count1_var = tk.StringVar(value="10")
    prompt_count1_entry = ttk.Entry(model1_frame, textvariable=prompt_count1_var, width=25)
    prompt_count1_entry.grid(row=1, column=1, padx=5, pady=2, sticky=tk.W)

    ttk.Label(model1_frame, text="Output CSV:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
    output_file1_var = tk.StringVar(value="C:/prompts/unique_prompts1.csv")
    output_file1_entry = ttk.Entry(model1_frame, textvariable=output_file1_var, width=40)
    output_file1_entry.grid(row=2, column=1, padx=5, pady=2, sticky=tk.W)

    browse1_btn = ttk.Button(
        model1_frame, text="Browse...",
        command=lambda: browse_csv_file(output_file1_var)
    )
    browse1_btn.grid(row=2, column=2, padx=5, pady=2, sticky=tk.W)

    # Frame for model #2 (initially hidden if "one model" is selected)
    model2_frame = ttk.LabelFrame(root, text="Model #2 Configuration")

    ttk.Label(model2_frame, text="Model Name:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
    model2_var = tk.StringVar(value="marco-o1:7b-fp16")
    model2_entry = ttk.Entry(model2_frame, textvariable=model2_var, width=25)
    model2_entry.grid(row=0, column=1, padx=5, pady=2, sticky=tk.W)

    ttk.Label(model2_frame, text="Number of Prompts:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
    prompt_count2_var = tk.StringVar(value="10")
    prompt_count2_entry = ttk.Entry(model2_frame, textvariable=prompt_count2_var, width=25)
    prompt_count2_entry.grid(row=1, column=1, padx=5, pady=2, sticky=tk.W)

    ttk.Label(model2_frame, text="Output CSV:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
    output_file2_var = tk.StringVar(value="C:/prompts/unique_prompts2.csv")
    output_file2_entry = ttk.Entry(model2_frame, textvariable=output_file2_var, width=40)
    output_file2_entry.grid(row=2, column=1, padx=5, pady=2, sticky=tk.W)

    browse2_btn = ttk.Button(
        model2_frame, text="Browse...",
        command=lambda: browse_csv_file(output_file2_var)
    )
    browse2_btn.grid(row=2, column=2, padx=5, pady=2, sticky=tk.W)

    # By default, hide model2_frame if "one" is selected
    if number_of_models_var.get() == "two":
        model2_frame.pack(fill=tk.X, padx=10, pady=5)

    # Frame: Memory & Save Mode
    config_frame = ttk.LabelFrame(root, text="Settings")
    config_frame.pack(fill=tk.X, padx=10, pady=5)

    # USE MEMORY
    use_memory_var = tk.IntVar(value=1)
    memory_check = ttk.Checkbutton(
        config_frame, text="Use Memory (avoid repeats across old prompts)",
        variable=use_memory_var
    )
    memory_check.grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)

    # SAVE MODE
    ttk.Label(config_frame, text="Save Mode:").grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
    save_mode_var = tk.StringVar(value="overwrite")
    overwrite_radio = ttk.Radiobutton(config_frame, text="Overwrite", variable=save_mode_var, value="overwrite")
    append_radio    = ttk.Radiobutton(config_frame, text="Append",   variable=save_mode_var, value="append")
    overwrite_radio.grid(row=0, column=2, sticky=tk.W, padx=5, pady=2)
    append_radio.grid(row=0, column=3, sticky=tk.W, padx=5, pady=2)

    # Frame: Reference Prompt
    ref_frame = ttk.LabelFrame(root, text="Reference Prompt (Optional)")
    ref_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

    reference_prompt_text = tk.Text(ref_frame, height=5, wrap=tk.WORD)
    reference_prompt_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    example_prompt = (
        "Example: A hyper-realistic close-up shot of a futuristic cityscape with neon lights. "
        "Incorporate vibrant colors and surreal elements for a dynamic vibe."
    )
    reference_prompt_text.insert(tk.END, example_prompt)

    # Frame: Action + Progress
    action_frame = ttk.Frame(root)
    action_frame.pack(fill=tk.X, padx=10, pady=5)

    start_button = ttk.Button(
        action_frame, text="Start Generation",
        command=lambda: start_generation({
            "number_of_models_var": number_of_models_var,
            "model1_var": model1_var,
            "prompt_count1_var": prompt_count1_var,
            "output_file1_var": output_file1_var,
            "model2_var": model2_var,
            "prompt_count2_var": prompt_count2_var,
            "output_file2_var": output_file2_var,
            "use_memory_var": use_memory_var,
            "save_mode_var": save_mode_var,
            "reference_prompt_text": reference_prompt_text,
            "log_box": log_box,
            # We'll store two separate progress bars for each model
            "progress_bar1": progress_bar1,
            "progress_bar2": progress_bar2
        })
    )
    start_button.pack(side=tk.LEFT, padx=5)

    stop_button = ttk.Button(action_frame, text="Stop", command=stop_generation_func)
    stop_button.pack(side=tk.LEFT, padx=5)

    reset_button = ttk.Button(
        action_frame, text="Reset Memory",
        command=lambda: reset_memory_func({"log_box": log_box})
    )
    reset_button.pack(side=tk.LEFT, padx=5)

    # We define two separate progress bars for model 1 and model 2
    progress_bar1 = ttk.Progressbar(action_frame, orient="horizontal", length=150, mode="determinate")
    progress_bar1.pack(side=tk.RIGHT, padx=5)
    progress_bar2 = ttk.Progressbar(action_frame, orient="horizontal", length=150, mode="determinate")
    progress_bar2.pack(side=tk.RIGHT, padx=5)

    # Frame: Log
    log_frame = ttk.Frame(root)
    log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

    log_scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL)
    log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    log_box = tk.Text(log_frame, wrap=tk.WORD, yscrollcommand=log_scrollbar.set)
    log_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    log_scrollbar.config(command=log_box.yview)

    root.mainloop()

if __name__ == "__main__":
    main()
