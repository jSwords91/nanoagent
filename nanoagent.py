"""nanoagent: the simplest coding agent."""
import glob
import json
import os
import platform
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


# tools are a list of dictionaries, each with a type, name, description, and parameters
TOOLS = [{
    "type": "function",
    "name": "bash",
    "description": "Run a shell command and return its output.",
    "parameters": {
        "type": "object",
        "properties": {"command": {"type": "string"}},
        "required": ["command"],
    },
}]

def bash(command):
    result = subprocess.run(command, shell=True, capture_output=True, text=True, errors="replace",
                            stdin=subprocess.DEVNULL, timeout=120)
    return result.stdout + result.stderr


FUNCTIONS = {"bash": bash}  # tool name -> the Python function that runs it


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
                elif input("run? [y/N] ").strip().lower() == "y":
                    try:  # bad JSON, a timeout or a missing file: tell the model, don't crash
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
        print("\nExiting...")
