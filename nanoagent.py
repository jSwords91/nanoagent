"""nanoagent: the simplest coding agent that actually works."""
import json
import os
import platform
import subprocess
import urllib.error
import urllib.request


def load_env(path=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")):
    # A minimal .env reader: KEY=value lines. Real environment variables win.
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


# The model's only tool. Everything a developer does at a terminal, it can do.
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


def bash(command, timeout=120, limit=10_000):
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, errors="replace",
            stdin=subprocess.DEVNULL, timeout=timeout,  # no stdin: a command must not steal ours
        )
    except subprocess.TimeoutExpired:
        return f"Timed out after {timeout}s."
    output = result.stdout + result.stderr
    if len(output) > limit:  # keep the head and the tail, where errors usually are
        output = output[:limit // 2] + "\n... (truncated) ...\n" + output[-limit // 2:]
    return output


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
    return prompt


def main():
    messages = [{"role": "system", "content": system_prompt()}]
    while True:
        try:
            messages.append({"role": "user", "content": input("> ")})
        except (EOFError, KeyboardInterrupt):
            return
        # The agent loop: keep going until the model stops asking for tools.
        while True:
            output = complete(messages, TOOLS)
            messages += output  # the model's reply, including any reasoning, goes back in next time
            calls = [item for item in output if item["type"] == "function_call"]
            for item in output:
                if item["type"] == "message":
                    print("".join(part.get("text", "") for part in item["content"]))
            if not calls:
                break
            for call in calls:
                command = json.loads(call["arguments"])["command"]
                print(f"$ {command}")
                if input("run? [y/N] ").strip().lower() == "y":
                    result = bash(command)
                else:
                    result = "The user declined to run this command."
                messages.append({"type": "function_call_output", "call_id": call["call_id"], "output": result})


if __name__ == "__main__":
    main()
