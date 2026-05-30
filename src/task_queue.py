"""
task_queue.py — NEXUS Task Queue
Allows batching multiple tasks and executing them sequentially.
Tasks are persisted to tasks_queue.json so they survive restarts.
"""

import json
import os


# ---------------------------------------------------------------------------
# Path to the queue file
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
QUEUE_FILE = os.path.join(PROJECT_ROOT, "tasks_queue.json")


# ---------------------------------------------------------------------------
# Write / Read queue
# ---------------------------------------------------------------------------
def write_queue(tasks_list):
    """
    Save a list of task dicts to tasks_queue.json.
    Each task: {"action": "ACTION:QA", "params": "what is python", "status": "pending"}
    """
    try:
        with open(QUEUE_FILE, "w", encoding="utf-8") as f:
            json.dump(tasks_list, f, indent=2)
    except IOError as e:
        print(f"[ERROR] Could not write task queue: {e}")


def read_queue():
    """
    Read and return the task queue list from tasks_queue.json.
    Returns an empty list if the file doesn't exist or is invalid.
    """
    if not os.path.isfile(QUEUE_FILE):
        return []

    try:
        with open(QUEUE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def _generate_qa(question):
    """Answer a general question using the model (replaces removed file_ops.answer_question)."""
    from model_loader import generate
    if not question or not question.strip():
        return "Please ask a question."
    prompt = "Answer the following question in 2-3 sentences. Be brief and direct:\n\n" + question
    return generate(prompt, max_tokens=200)


# ---------------------------------------------------------------------------
# Execute all pending tasks
# ---------------------------------------------------------------------------
def execute_queue():
    """
    Run all pending tasks in order. Updates status to 'done' after each.
    Clears the queue file after all tasks are complete.
    """
    tasks = read_queue()

    if not tasks:
        print("No tasks in queue.")
        return

    # Lazy import to avoid circular imports
    import file_ops
    import system_tasks

    # Map action strings to handler functions
    action_map = {
        "ACTION:SUMMARISE_FILE": lambda params: file_ops.summarise_file(params),
        "ACTION:SUMMARISE_FOLDER": lambda params: file_ops.summarise_folder(params),
        "ACTION:QA": lambda params: _generate_qa(params),
        "ACTION:BATTERY": lambda params: system_tasks.get_battery(),
        "ACTION:PROCESSES": lambda params: system_tasks.get_processes(),
    }

    total = len(tasks)

    for i, task in enumerate(tasks, 1):
        action = task.get("action", "ACTION:UNKNOWN")
        params = task.get("params", "")

        print(f"\nExecuting task {i} of {total}: [{action}]")
        print("-" * 40)

        handler = action_map.get(action)
        if handler:
            result = handler(params)
            print(result)
        else:
            print("Unknown action — skipped.")

        # Mark as done
        task["status"] = "done"
        write_queue(tasks)  # persist progress

    # Clear the queue after all tasks are done
    clear_queue()
    print("\nAll tasks complete.")


# ---------------------------------------------------------------------------
# Clear the queue
# ---------------------------------------------------------------------------
def clear_queue():
    """Reset the queue to an empty list."""
    write_queue([])
    print("Task queue cleared.")


