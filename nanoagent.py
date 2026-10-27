"""nanoagent: the simplest coding agent."""
import glob
import json
import os
import platform
import re
import subprocess
import urllib.error
import urllib.request


def load_env(path=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")):
    if os.path.exists(path):
        for line in open(path):
            key, sep, value = line.strip().partition("=")
            if sep and not key.startswith("#"):
                os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


load_env()
# Any endpoint that speaks the OpenAI Responses API works.
BASE_URL = os.environ.get("NANO_BASE_URL", "https://api.openai.com/v1")
API_KEY = os.environ.get("NANO_API_KEY", "")
MODEL = os.environ.get("NANO_MODEL", "gpt-6-sol")
SKILLS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "skills")
MAX_STEPS = 20  # most model calls per user message, so a confused model can't loop forever


def tool(name, description, **params):
    """A tool is described to the model by a name, a description and its parameters (all strings here)."""
    return {
        "type": "function",
        "name": name,
        "description": description,
        "parameters": {
            "type": "object",
            "properties": {key: {"type": "string", "description": text} for key, text in params.items()},
            "required": list(params),
        },
    }


TOOLS = [
    tool("bash", "Run a shell command and return its output.", command="The command to run."),
    tool("read", "Read a file.", path="Path to the file."),
    tool("write", "Create or overwrite a file.", path="Path to the file.", content="The full new contents."),
    tool("edit", "Replace one exact piece of text in a file.", path="Path to the file.",
         old="The text to replace. It must appear exactly once in the file.", new="The replacement text."),
    tool("glob", "List files matching a pattern.", pattern="A glob pattern, e.g. **/*.py"),
    tool("grep", "Search files for a regex. Returns file:line:text.", pattern="A Python regular expression.",
         path="A file, or a directory to search recursively, e.g. ."),
    tool("colorise_text", "Colorise text in the terminal using ANSI escape codes.", text="The text to colorise.",
         color="An ANSI colour code, e.g. 31 red, 33 yellow, 32 green, 36 cyan, 34 blue, 35 magenta."),
]


def bash(command, timeout=120):
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, errors="replace",
            stdin=subprocess.DEVNULL, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return f"Timed out after {timeout}s."
    output = result.stdout + result.stderr
    return output


def read_file(path):
    return open(path, errors="replace").read()


def write_file(path, content):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        f.write(content)
    return f"Wrote {path}."


def edit_file(path, old, new):
    text = open(path).read()
    if text.count(old) != 1:  # one exact match, so the model can't change the wrong spot
        return f"The old text appears {text.count(old)} times in {path}; it must appear exactly once."
    with open(path, "w") as f:
        f.write(text.replace(old, new))
    return f"Edited {path}."


def glob_files(pattern):
    return "\n".join(sorted(glob.glob(pattern, recursive=True))) or "No files match."


def grep_files(pattern, path):
    regex = re.compile(pattern)
    files = glob.glob(os.path.join(path, "**"), recursive=True) if os.path.isdir(path) else [path]
    hits = []
    for file in filter(os.path.isfile, files):
        for number, line in enumerate(open(file, errors="replace"), 1):
            if regex.search(line):
                hits.append(f"{file}:{number}:{line.rstrip()}")
    return "\n".join(hits) or "No matches."


def colorise_text(text, color):
    return f"\033[{color}m{text}\033[0m"


# tool name -> the Python function that runs it
FUNCTIONS = {
    "bash": bash, "read": read_file, "write": write_file, "edit": edit_file,
    "glob": glob_files, "grep": grep_files, "colorise_text": colorise_text,
}
READ_ONLY = {"read", "glob", "grep"}  # these can't change anything, so they run without asking


def complete(messages, tools):
    """Send the conversation to the model, get its new output items back."""
    body = {"model": MODEL, "input": messages, "tools": tools}
    request = urllib.request.Request(
        BASE_URL + "/responses",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request) as response:
            return json.load(response)["output"]
    except urllib.error.HTTPError as e:
        raise SystemExit(f"API error {e.code}: {e.read().decode()}")


def system_prompt():
    prompt = (
        f"You are a coding agent working in {os.getcwd()} on {platform.system()}."
    )
    if os.path.exists("AGENTS.md"):  # per-project instructions, the convention most agents share
        prompt += "\n\nProject instructions from AGENTS.md:\n" + open("AGENTS.md").read()
    skills = sorted(glob.glob(os.path.join(SKILLS_DIR, "*", "SKILL.md")))
    if skills:  # only each skill's description goes in; the model reads the rest with bash when needed
        prompt += "\n\nSkills (when a task matches one, read its file with bash before you start):"
        for path in skills:
            header = open(path).read().split("---")[1]  # the frontmatter between the first two ---
            fields = dict(line.split(":", 1) for line in header.strip().splitlines() if ":" in line)
            prompt += f"\n- {fields['name'].strip()}: {fields['description'].strip()} ({path})"
    return prompt


def main():
    messages = [{"role": "system", "content": system_prompt()}]
    while True:
        messages.append({"role": "user", "content": input("> ")})
        # The agent loop: keep going until the model stops asking for tools, or we hit MAX_STEPS.
        steps = 0
        while steps < MAX_STEPS:
            steps += 1
            output = complete(messages, TOOLS)
            messages += output  # the model's reply, including any reasoning, goes back in next time
            calls = [item for item in output if item["type"] == "function_call"]
            for item in output:
                if item["type"] == "message":
                    # make llm blue text in terminal
                    print("\033[94m" + "".join(part.get("text", "") for part in item["content"]) + "\033[0m")
            if not calls:
                break
            for call in calls:
                print(f"{call['name']} {call['arguments']}")
                if call["name"] not in FUNCTIONS:  # models sometimes invent tools; say so rather than crash
                    result = f"There is no tool called {call['name']}."
                elif call["name"] in READ_ONLY or input("run? [y/N] ").strip().lower() == "y":
                    try:  # bad arguments or a failing tool become a message to the model, not a crash
                        result = FUNCTIONS[call["name"]](**json.loads(call["arguments"]))
                    except Exception as e:
                        result = f"Error: {e}"
                else:
                    result = "The user declined this tool call."
                messages.append({"type": "function_call_output", "call_id": call["call_id"], "output": result})
        else:  # only runs when the loop ran out of steps, not on break
            print(f"Stopped after {MAX_STEPS} steps.")


if __name__ == "__main__":
    try:
        main()
    except (EOFError, KeyboardInterrupt):  # Ctrl-D or Ctrl-C at any prompt quits
        print()
