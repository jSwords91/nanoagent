"""nanoagent: the simplest coding agent that actually works."""
import json
import os
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


def complete(messages):
    """Send the conversation to the model, get its new output items back."""
    body = {"model": MODEL, "input": messages}
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


def main():
    messages = []
    while True:
        try:
            messages.append({"role": "user", "content": input("> ")})
        except (EOFError, KeyboardInterrupt):
            return
        output = complete(messages)
        messages += output  # the model's reply, including any reasoning, goes back in next time
        for item in output:
            if item["type"] == "message":
                print("".join(part.get("text", "") for part in item["content"]))


if __name__ == "__main__":
    main()
