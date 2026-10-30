# nanoagent

The simplest coding agent. One file, no dependencies.

## Why this exists

Coding agents can seem opaque but, at their core, there isn't much to them. I wanted to
simply show how the pieces fit together:

- **The loop** - a language model in a `while` loop. It asks for a tool, the
  agent runs it, and the result goes back in.
- **Tools** - plain Python functions, described to the model with a small
  schema. Here that's mainly `bash`.
- **Skills** - markdown files. The model only sees each one's short
  description, and reads the full file when it needs it.
- **AGENTS.md** - project instructions, which are just more text in the system
  prompt.

None of these is complicated on its own. Once you've seen each one in a few
lines, it's much easier to understand what the bigger agents are doing.

## Quickstart

You need Python 3.10+. There is nothing to install. Set up OpenAI or Ollama, then
run it.

### OpenAI

1. Create a key on [OpenAI's API keys page](https://platform.openai.com/api-keys).

2. Create a `.env` file in the `nanoagent` folder:

   ```sh
   NANO_API_KEY=sk-...
   NANO_MODEL=gpt-6-sol
   ```

Any other endpoint that speaks the OpenAI Responses API works too: set
`NANO_BASE_URL` to it.

### Ollama

Run a model on your own machine, with no account or API key.

1. [Install Ollama](https://ollama.com/download), or update it if it's an old
   version. It needs the Responses API.

2. Download a model that can call tools (`gemma4:e4b` is about 10 GB):

   ```sh
   ollama pull gemma4:e4b
   ```

   `ollama list` shows what you have, and `ollama show <model>` lists `tools`
   under `Capabilities` if the model can call them.

3. Create a `.env` file in the `nanoagent` folder:

   ```sh
   NANO_BASE_URL=http://localhost:11434/v1
   NANO_API_KEY=ollama
   NANO_MODEL=gemma4:e4b
   ```

### Run it

1. Run it from the project you want it to work on:

   ```sh
   cd your-project
   python3 /path/to/nanoagent/nanoagent.py
   ```

2. Type a request at the `>` prompt. Try `what can you do?` (the overview skill)
   or `what does this project do?`. Before each tool call it shows the call, e.g.
   `bash {"command": "ls"}`, and asks `run? [y/N]`: type `y` to run it, anything
   else to decline. Ctrl-D quits.

`.env` is gitignored. Real environment variables override it.

## Warning

The `bash` tool runs real shell commands on your machine, as you, with no
sandbox. Anything you can do from a terminal, it can do: delete files, read
secrets (including your `.env`), push code, install packages. The `run? [y/N]`
prompt is the only safeguard, so read every command before you type `y`. Files
the agent reads can contain instructions aimed at the model, so be most careful
in code you don't trust. Use it in a git repo with your work committed, or
inside a container or VM.

## The whole idea

A coding agent is a language model in a `while` loop with tools. In pseudocode:

```python
messages = [system_prompt]
while True:
    messages.append({"role": "user", "content": input("> ")})
    while True:
        reply = llm(messages, tools)        # one HTTP call
        messages.append(reply)
        if not reply.tool_calls: break      # model is done, user's turn
        for call in reply.tool_calls:
            out = run(call)                 # the harness runs it, not the model
            messages.append(tool_result(call, out))
    print(reply.content)
```

The model never executes anything. It only emits text that *asks* for a tool
call. The harness decides whether to run it and feeds the result back as more
text. Everything else in a real coding agent (permission prompts, file editing
tools, project instructions, context compaction, subagents, a fancy UI) is a
refinement of this loop.

One tool, `bash`, is enough. A new tool is just a function, a schema in `TOOLS` and one line in `FUNCTIONS`. Often you'll see more tools such as `read_file`, `write_file` and `edit_file` - feel free to add them if you like.

Project instructions are just as plain. This repo has its own `AGENTS.md` saying
"You always reply in lower case." Run the agent from inside this folder and it
will. An `AGENTS.md` is nothing more than text added to the system prompt.

## Reading guide

The git history is the tutorial. Each step adds one idea and leaves a working
program:

1. **README** - this file.
2. **chat** - a REPL that talks to an LLM over raw HTTP. A chatbot.
3. **bash** - give the model a shell and loop until it stops calling it. Now it is an agent.
4. **safety** - confirm each command and time out long-running ones.
5. **system prompt** - tell the model where it is.
6. **skills** - instructions the model loads only when it needs them.

Read them in order with `git log --reverse -p`.
