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

# Dictionary of memory per model: { model_name: [ {title, description, style}, ... ] }
ALL_PROMPTS_MEMORY = {}

# ======================================
# HELPER: parse_ollama_output
# ======================================
def parse_ollama_output(response: str):
    """
    Attempt to parse lines like:
      Title: ...
      Description: ...
      Style: ...
    Return a dict {title, description, style} or None if not found.
    """
    title_match = re.search(r'(?im)^\s*Title:\s*["“]?(.+?)["”]?\s*$', response)
    desc_match  = re.search(r'(?im)^\s*Description:\s*(.+)$', response)
    style_match = re.search(r'(?im)^\s*Style:\s*(.+)$', response)

    if not title_match and not desc_match and not style_match:
        return None

    title = title_match.group(1).strip() if title_match else ""
    desc  = desc_match.group(1).strip()  if desc_match else ""
    style = style_match.group(1).strip() if style_match else ""

    if not title and not desc and not style:
        return None

    return {
        "title": title,
        "description": desc,
        "style": style
    }

# ======================================
# PROMPT BUILDING
# ======================================
def build_basic_system_prompt():
    """
    A basic system prompt if memory is off or no memory yet.
    """
    return """SYSTEM:
You are an AI specialized in creating random, photorealistic prompts.
Always produce unique results.

Structure:
Title: (5 words max)
Description: (20 words max, photorealistic)
Style: (1-3 words, e.g. cinematic, macro, surreal)
"""

def build_system_prompt_with_memory(model_name: str, basic_prompt: str):
    """
    Incorporate memory for a specific model, if any.
    """
    if model_name not in ALL_PROMPTS_MEMORY or not ALL_PROMPTS_MEMORY[model_name]:
        return basic_prompt

    memory_text = "\n".join(
        f"{idx+1}) {p['title']} | {p['description']} | {p['style']}"
        for idx, p in enumerate(ALL_PROMPTS_MEMORY[model_name])
    )

    return f"""SYSTEM:
You are an AI specialized in creating random, photorealistic prompts.
Already generated for {model_name}:
{memory_text}

Do NOT repeat those. Provide something brand-new and unique.

{basic_prompt}
"""

# ======================================
# MEMORY: RESET & SHOW
# ======================================
def reset_memory_func(gui_elements):
    """
    Clears all memory for all models.
    """
    global ALL_PROMPTS_MEMORY
    ALL_PROMPTS_MEMORY.clear()

    model1_log_box = gui_elements["model1_log_box"]
    model2_log_box = gui_elements["model2_log_box"]
    msg = "[INFO] All memory has been reset.\n"
    model1_log_box.insert(tk.END, msg)
    model2_log_box.insert(tk.END, msg)

    if gui_elements["auto_scroll_var"].get() == 1:
        model1_log_box.see(tk.END)
        model2_log_box.see(tk.END)

def show_memory_func(gui_elements):
    """
    Logs all memory content to both model logs.
    """
    global ALL_PROMPTS_MEMORY
    model1_log_box = gui_elements["model1_log_box"]
    model2_log_box = gui_elements["model2_log_box"]

    if not ALL_PROMPTS_MEMORY:
        msg = "[INFO] No memory stored for any model.\n"
        model1_log_box.insert(tk.END, msg)
        model2_log_box.insert(tk.END, msg)
    else:
        msg = "[INFO] Current stored memory:\n"
        model1_log_box.insert(tk.END, msg)
        model2_log_box.insert(tk.END, msg)
        for model, prompts in ALL_PROMPTS_MEMORY.items():
            line = f" Model: {model}\n"
            model1_log_box.insert(tk.END, line)
            model2_log_box.insert(tk.END, line)
            if not prompts:
                subline = "   (no prompts)\n"
                model1_log_box.insert(tk.END, subline)
                model2_log_box.insert(tk.END, subline)
            else:
                for idx, p in enumerate(prompts, start=1):
                    entry = (
                        f"   {idx}) Title:{p['title']}\n"
                        f"      Description:{p['description']}\n"
                        f"      Style:{p['style']}\n"
                    )
                    model1_log_box.insert(tk.END, entry)
                    model2_log_box.insert(tk.END, entry)

    if gui_elements["auto_scroll_var"].get() == 1:
        model1_log_box.see(tk.END)
        model2_log_box.see(tk.END)

# ======================================
# SAVE PROMPTS
# ======================================
def save_prompts_to_csv(
    prompts_list, output_csv, save_mode, model_name, log_box, auto_scroll
):
    """
    Writes the given prompts_list to CSV, then clears it.
    """
    if not prompts_list:
        return

    # Ensure folder exists
    dirpath = os.path.dirname(output_csv)
    if dirpath and not os.path.exists(dirpath):
        os.makedirs(dirpath, exist_ok=True)

    file_mode = "a" if save_mode == "append" else "w"
    write_header = True
    if file_mode == "a" and os.path.exists(output_csv):
        write_header = False

    try:
        with open(output_csv, mode=file_mode, newline="", encoding="utf-8") as csvfile:
            fieldnames = ["Title", "Description", "Style"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            if write_header:
                writer.writeheader()
            for p in prompts_list:
                writer.writerow({
                    "Title": p["title"],
                    "Description": p["description"],
                    "Style": p["style"]
                })
        log_box.insert(
            tk.END, f"[{model_name}] Auto-saved {len(prompts_list)} prompts to {output_csv}.\n"
        )
        if auto_scroll:
            log_box.see(tk.END)

    except Exception as e:
        log_box.insert(
            tk.END, f"[ERROR] CSV write failed for model '{model_name}': {str(e)}\n"
        )
        if auto_scroll:
            log_box.see(tk.END)

    prompts_list.clear()

# ======================================
# GENERATION WORKER (SINGLE MODEL)
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
    auto_scroll: bool,
    auto_save_every: int
):
    """
    Runs the generation for one model from 1..num_prompts. 
    Numbering won't reset after auto-save.
    """
    global stop_generation, ALL_PROMPTS_MEMORY

    # Memory if not present yet
    if model_name not in ALL_PROMPTS_MEMORY:
        ALL_PROMPTS_MEMORY[model_name] = []

    # We'll keep a local list for unsaved prompts
    new_prompts_this_run = []
    base_prompt_text = build_basic_system_prompt()

    # We'll keep an overall prompt_index from 1..num_prompts
    prompt_index = 0
    attempts = 0
    max_attempts = num_prompts * 3

    while prompt_index < num_prompts and attempts < max_attempts:
        if stop_generation:
            log_box.insert(tk.END, f"\n[INFO] Generation for model '{model_name}' stopped by user.\n")
            if auto_scroll:
                log_box.see(tk.END)
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
            if auto_scroll:
                log_box.see(tk.END)
            break

        parsed = parse_ollama_output(response_text)
        if not parsed:
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
            if auto_scroll:
                log_box.see(tk.END)
            continue

        # It's new, so increment the overall index
        prompt_index += 1

        # Add to local list
        new_prompts_this_run.append(parsed)
        # Add to memory if needed
        if use_memory:
            ALL_PROMPTS_MEMORY[model_name].append(parsed)

        # Log with the correct numbering
        log_box.insert(
            tk.END,
            f"[{model_name}] Prompt #{prompt_index}/{num_prompts}\n"
            f"Title: {parsed['title']}\n"
            f"Description: {parsed['description']}\n"
            f"Style: {parsed['style']}\n\n"
        )
        if auto_scroll:
            log_box.see(tk.END)

        # Update progress bar
        progress_value = int((prompt_index / num_prompts) * 100)
        progress_bar["value"] = progress_value

        # Auto-save if we've reached a multiple
        if auto_save_every > 0 and (prompt_index % auto_save_every == 0):
            save_prompts_to_csv(
                prompts_list=new_prompts_this_run,
                output_csv=output_csv,
                save_mode=save_mode,
                model_name=model_name,
                log_box=log_box,
                auto_scroll=auto_scroll
            )

    # Final save of any leftover prompts
    if new_prompts_this_run:
        save_prompts_to_csv(
            prompts_list=new_prompts_this_run,
            output_csv=output_csv,
            save_mode=save_mode,
            model_name=model_name,
            log_box=log_box,
            auto_scroll=auto_scroll
        )
    else:
        log_box.insert(tk.END, f"[{model_name}] No new prompts left to save.\n")
        if auto_scroll:
            log_box.see(tk.END)

# ======================================
# THREAD TARGET FOR 1 OR 2 MODELS
# ======================================
def generate_prompts_threaded(gui_elements):
    """
    Called in background thread. If 'two' models, run each in parallel.
    """
    global stop_generation
    stop_generation = False

    use_memory = (gui_elements["use_memory_var"].get() == 1)
    save_mode = gui_elements["save_mode_var"].get()
    auto_scroll = (gui_elements["auto_scroll_var"].get() == 1)
    auto_save_every_str = gui_elements["auto_save_every_var"].get()

    try:
        auto_save_every = int(auto_save_every_str)
        if auto_save_every < 0:
            auto_save_every = 0
    except ValueError:
        auto_save_every = 50

    # Model #1
    model1_name = gui_elements["model1_var"].get().strip()
    model1_count = int(gui_elements["prompt_count1_var"].get())
    model1_csv = gui_elements["output_file1_var"].get().strip()
    model1_log_box = gui_elements["model1_log_box"]
    progress_bar1 = gui_elements["progress_bar1"]
    reference1_text = gui_elements["reference1_text"].get("1.0", tk.END).strip()

    # Model #2
    model2_name = gui_elements["model2_var"].get().strip()
    model2_count = int(gui_elements["prompt_count2_var"].get())
    model2_csv = gui_elements["output_file2_var"].get().strip()
    model2_log_box = gui_elements["model2_log_box"]
    progress_bar2 = gui_elements["progress_bar2"]
    reference2_text = gui_elements["reference2_text"].get("1.0", tk.END).strip()

    number_of_models = gui_elements["number_of_models_var"].get()

    threads = []

    # Worker for Model #1
    def worker1():
        generate_prompts_for_model(
            model_name=model1_name,
            num_prompts=model1_count,
            output_csv=model1_csv,
            reference_text=reference1_text,
            use_memory=use_memory,
            save_mode=save_mode,
            log_box=model1_log_box,
            progress_bar=progress_bar1,
            auto_scroll=auto_scroll,
            auto_save_every=auto_save_every
        )

    t1 = threading.Thread(target=worker1)
    threads.append(t1)

    if number_of_models == "two":
        def worker2():
            generate_prompts_for_model(
                model_name=model2_name,
                num_prompts=model2_count,
                output_csv=model2_csv,
                reference_text=reference2_text,
                use_memory=use_memory,
                save_mode=save_mode,
                log_box=model2_log_box,
                progress_bar=progress_bar2,
                auto_scroll=auto_scroll,
                auto_save_every=auto_save_every
            )
        t2 = threading.Thread(target=worker2)
        threads.append(t2)

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Indicate finished
    model1_log_box.insert(tk.END, "[INFO] Generation process finished (Model #1).\n")
    if auto_scroll:
        model1_log_box.see(tk.END)

    if number_of_models == "two":
        model2_log_box.insert(tk.END, "[INFO] Generation process finished (Model #2).\n")
        if auto_scroll:
            model2_log_box.see(tk.END)

def start_generation(gui_elements):
    thread = threading.Thread(target=generate_prompts_threaded, args=(gui_elements,))
    thread.start()

def stop_generation_func():
    global stop_generation
    stop_generation = True

def browse_csv_file(output_file_var):
    filepath = filedialog.asksaveasfilename(
        defaultextension=".csv",
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
    )
    if filepath:
        output_file_var.set(filepath)

# CLEAR LOGS FOR EACH MODEL
def clear_model1_log(gui_elements):
    gui_elements["model1_log_box"].delete("1.0", tk.END)

def clear_model2_log(gui_elements):
    gui_elements["model2_log_box"].delete("1.0", tk.END)

# ======================================
# MAIN GUI
# ======================================
def main():
    root = tk.Tk()
    root.title("Ollama Prompt Generator (Two Models, Separate Logs, Separate References)")
    root.geometry("1100x900")
    root.resizable(True, True)

    # Master Canvas & Scroll
    main_canvas = tk.Canvas(root)
    main_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    v_scrollbar = ttk.Scrollbar(root, orient=tk.VERTICAL, command=main_canvas.yview)
    v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    main_canvas.configure(yscrollcommand=v_scrollbar.set)

    container = ttk.Frame(main_canvas)
    main_canvas.create_window((0,0), window=container, anchor="nw")

    def update_scrollregion(event=None):
        main_canvas.config(scrollregion=main_canvas.bbox("all"))

    container.bind("<Configure>", update_scrollregion)

    # ============ Number of Models ============
    model_select_frame = ttk.LabelFrame(container, text="Number of Models")
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

    # ============ Model #1 ============
    model1_frame = ttk.LabelFrame(container, text="Model #1 Configuration")
    model1_frame.pack(fill=tk.X, padx=10, pady=5)

    ttk.Label(model1_frame, text="Model Name:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
    model1_var = tk.StringVar(value="marco-o1:7b-fp16")
    model1_entry = ttk.Entry(model1_frame, textvariable=model1_var, width=30)
    model1_entry.grid(row=0, column=1, padx=5, pady=2, sticky=tk.W)

    ttk.Label(model1_frame, text="Number of Prompts:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
    prompt_count1_var = tk.StringVar(value="5")
    prompt_count1_entry = ttk.Entry(model1_frame, textvariable=prompt_count1_var, width=10)
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

    # Reference Prompt for Model #1
    ref1_frame = ttk.LabelFrame(model1_frame, text="Reference Prompt (Model #1)")
    ref1_frame.grid(row=3, column=0, columnspan=3, sticky=tk.W+tk.E, padx=5, pady=5)

    reference1_text = tk.Text(ref1_frame, height=4, wrap=tk.WORD)
    reference1_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    reference1_text.insert(tk.END, "Example: This is a unique reference for Model #1 only.\n")

    # ============ Model #2 ============
    model2_frame = ttk.LabelFrame(container, text="Model #2 Configuration")
    model2_frame.pack(fill=tk.X, padx=10, pady=5)

    ttk.Label(model2_frame, text="Model Name:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
    model2_var = tk.StringVar(value="marco-o1:7b-fp16")
    model2_entry = ttk.Entry(model2_frame, textvariable=model2_var, width=30)
    model2_entry.grid(row=0, column=1, padx=5, pady=2, sticky=tk.W)

    ttk.Label(model2_frame, text="Number of Prompts:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
    prompt_count2_var = tk.StringVar(value="5")
    prompt_count2_entry = ttk.Entry(model2_frame, textvariable=prompt_count2_var, width=10)
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

    # Reference Prompt for Model #2
    ref2_frame = ttk.LabelFrame(model2_frame, text="Reference Prompt (Model #2)")
    ref2_frame.grid(row=3, column=0, columnspan=3, sticky=tk.W+tk.E, padx=5, pady=5)

    reference2_text = tk.Text(ref2_frame, height=4, wrap=tk.WORD)
    reference2_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    reference2_text.insert(tk.END, "Example: This is a unique reference for Model #2 only.\n")

    # ============ Settings ============
    settings_frame = ttk.LabelFrame(container, text="Settings")
    settings_frame.pack(fill=tk.X, padx=10, pady=5)

    use_memory_var = tk.IntVar(value=1)
    memory_check = ttk.Checkbutton(
        settings_frame, text="Use Memory (avoid repeats across old prompts)",
        variable=use_memory_var
    )
    memory_check.grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)

    ttk.Label(settings_frame, text="Save Mode:").grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
    save_mode_var = tk.StringVar(value="append")  # default to append
    overwrite_radio = ttk.Radiobutton(settings_frame, text="Overwrite", variable=save_mode_var, value="overwrite")
    append_radio    = ttk.Radiobutton(settings_frame, text="Append",   variable=save_mode_var, value="append")
    overwrite_radio.grid(row=0, column=2, sticky=tk.W, padx=5, pady=2)
    append_radio.grid(row=0, column=3, sticky=tk.W, padx=5, pady=2)

    ttk.Label(settings_frame, text="Auto Save Every:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
    auto_save_every_var = tk.StringVar(value="50")
    auto_save_every_entry = ttk.Entry(settings_frame, textvariable=auto_save_every_var, width=8)
    auto_save_every_entry.grid(row=1, column=1, padx=5, pady=2, sticky=tk.W)
    ttk.Label(settings_frame, text="prompts").grid(row=1, column=2, sticky=tk.W, padx=5, pady=2)

    auto_scroll_var = tk.IntVar(value=1)
    auto_scroll_check = ttk.Checkbutton(
        settings_frame, text="Auto-scroll to bottom",
        variable=auto_scroll_var
    )
    auto_scroll_check.grid(row=1, column=3, padx=5, pady=2, sticky=tk.W)

    # ============ Action Buttons ============
    action_frame = ttk.Frame(container)
    action_frame.pack(fill=tk.X, padx=10, pady=5)

    start_button = ttk.Button(
        action_frame, text="Start Generation",
        command=lambda: start_generation({
            "model1_var": model1_var,
            "prompt_count1_var": prompt_count1_var,
            "output_file1_var": output_file1_var,

            "model2_var": model2_var,
            "prompt_count2_var": prompt_count2_var,
            "output_file2_var": output_file2_var,

            "reference1_text": reference1_text,
            "reference2_text": reference2_text,

            "use_memory_var": use_memory_var,
            "save_mode_var": save_mode_var,

            "model1_log_box": model1_log_box,
            "model2_log_box": model2_log_box,
            "progress_bar1": progress_bar1,
            "progress_bar2": progress_bar2,

            "auto_scroll_var": auto_scroll_var,
            "auto_save_every_var": auto_save_every_var,
            "number_of_models_var": number_of_models_var
        })
    )
    start_button.pack(side=tk.LEFT, padx=5)

    stop_button = ttk.Button(action_frame, text="Stop", command=stop_generation_func)
    stop_button.pack(side=tk.LEFT, padx=5)

    reset_button = ttk.Button(
        action_frame, text="Reset Memory",
        command=lambda: reset_memory_func({
            "model1_log_box": model1_log_box,
            "model2_log_box": model2_log_box,
            "auto_scroll_var": auto_scroll_var
        })
    )
    reset_button.pack(side=tk.LEFT, padx=5)

    showmem_button = ttk.Button(
        action_frame, text="Show Memory",
        command=lambda: show_memory_func({
            "model1_log_box": model1_log_box,
            "model2_log_box": model2_log_box,
            "auto_scroll_var": auto_scroll_var
        })
    )
    showmem_button.pack(side=tk.LEFT, padx=5)

    # ============ Clear Logs ============
    clear_logs_frame = ttk.Frame(container)
    clear_logs_frame.pack(fill=tk.X, padx=10, pady=5)

    ttk.Label(clear_logs_frame, text="Clear Model Logs:").pack(side=tk.LEFT, padx=5)
    clear1_button = ttk.Button(
        clear_logs_frame, text="Clear Model #1 Log", 
        command=lambda: model1_log_box.delete("1.0", tk.END)
    )
    clear1_button.pack(side=tk.LEFT, padx=5)

    clear2_button = ttk.Button(
        clear_logs_frame, text="Clear Model #2 Log", 
        command=lambda: model2_log_box.delete("1.0", tk.END)
    )
    clear2_button.pack(side=tk.LEFT, padx=5)

    # ============ Model #1 Log ============
    model1_log_frame = ttk.LabelFrame(container, text="Model #1 Log")
    model1_log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

    model1_scrollbar = ttk.Scrollbar(model1_log_frame, orient=tk.VERTICAL)
    model1_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    model1_log_box = tk.Text(model1_log_frame, wrap=tk.WORD, yscrollcommand=model1_scrollbar.set)
    model1_log_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    model1_scrollbar.config(command=model1_log_box.yview)

    # ============ Model #2 Log ============
    model2_log_frame = ttk.LabelFrame(container, text="Model #2 Log")
    model2_log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

    model2_scrollbar = ttk.Scrollbar(model2_log_frame, orient=tk.VERTICAL)
    model2_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    model2_log_box = tk.Text(model2_log_frame, wrap=tk.WORD, yscrollcommand=model2_scrollbar.set)
    model2_log_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    model2_scrollbar.config(command=model2_log_box.yview)

    # ============ Progress Bars ============
    progress_frame = ttk.Frame(container)
    progress_frame.pack(fill=tk.X, padx=10, pady=5)

    progress_bar2 = ttk.Progressbar(progress_frame, orient="horizontal", length=450, mode="determinate")
    progress_bar2.pack(side=tk.RIGHT, padx=5)
    progress_bar1 = ttk.Progressbar(progress_frame, orient="horizontal", length=450, mode="determinate")
    progress_bar1.pack(side=tk.RIGHT, padx=5)

    root.mainloop()

if __name__ == "__main__":
    main()
