# nanoagent

The simplest coding agent. One file, no dependencies.

## Why this exists

Coding agents can seem opaque but, at their core, there isn't much to them. I wanted to
simply show how the pieces fit together:

- **The loop** - a language model in a `while` loop. It asks for a tool, the
  agent runs it, and the result goes back in.
- **Tools** - plain Python functions, described to the model with a small
  schema. Here that's `bash`, plus the classic `read`, `write`, `edit`, `glob`
  and `grep`.
- **Skills** - markdown files. The model only sees each one's short
  description, and reads the full file when it needs it.
- **AGENTS.md** - project instructions, which are just more text in the system
  prompt.
- **Memory** - a file the model writes notes to, which goes back into the
  system prompt next time.

None of these is complicated on its own. Once you've seen each one in a few
lines, it's much easier to understand what the bigger agents are doing.

## Quickstart

You need Python 3.10+ and an OpenAI API key. There is nothing to install.

1. Add your key. Copy the example config and fill in `NANO_API_KEY`:

   ```sh
   cd nanoagent
   cp .env.example .env
   ```

   | Variable | Default | |
   |---|---|---|
   | `NANO_API_KEY` | (required) | your API key |
   | `NANO_MODEL` | `gpt-6-sol` | any model with tool calling |
   | `NANO_BASE_URL` | `https://api.openai.com/v1` | any endpoint that speaks the OpenAI Responses API |

   `.env` is read from next to `nanoagent.py` and is gitignored. Real environment
   variables override it.

2. Run it from the project you want it to work on:

   ```sh
   cd your-project
   python3 /path/to/nanoagent/nanoagent.py
   ```

3. Type a request at the `>` prompt. Try `what can you do?` (the greeting skill)
   or `what does this project do?`. It shows each tool call, e.g.
   `bash {"command": "ls"}`. The read-only tools (`read`, `glob`, `grep`) run
   straight away. For anything else it asks `run? [y/N]`: type `y` to run it,
   anything else to decline. Ctrl-D quits.

## Warning

The `bash` tool runs real shell commands on your machine, as you, with no
sandbox. Anything you can do from a terminal, it can do: delete files, read
secrets (including your `.env`), push code, install packages. The `run? [y/N]`
prompt is the only safeguard, so read every command before you type `y`. The
read-only tools skip that prompt, so the model can read any file you can,
and what it reads is sent to the API. Files
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

This is a sketch, not the real code. The actual loop is `main()` in
`nanoagent.py`: the same shape, but the model's reply comes back as a list of
output items (OpenAI Responses API), its text is printed after each reply, you
approve each command that can change something, and it stops after `MAX_STEPS`
model calls per message.

The model never executes anything. It only emits text that *asks* for a tool
call. The harness decides whether to run it and feeds the result back as more
text. Everything else in a real coding agent (permission prompts, file editing
tools, project instructions, context compaction, subagents, a fancy UI) is a
refinement of this loop.

In principle one tool (`bash`) is enough. A new tool is just a function, a
schema in `TOOLS` and one line in `FUNCTIONS`. The classic file tools (`read`,
`write`, `edit`, `glob`, `grep`) are each a few lines of Python. They're not strictly needed, but models use them more reliably than
`cat` and `sed`. `edit` replaces one exact piece of text, which must appear
exactly once in the file, so the model can't change the wrong spot.

Project instructions are just as plain. This repo has its own `AGENTS.md` saying
"You always reply in lower case." Run the agent from inside this folder and it
will. An `AGENTS.md` is nothing more than text added to the system prompt.

Memory works the same way. Within a session, the agent's memory is the
`messages` list: everything said so far goes back to the model on every call.
To remember across sessions, it needs somewhere outside that list. Here that's
`memory.md`, next to `nanoagent.py`. The system prompt includes the file and
tells the model it can add to it. The model writes it with the same `write` and
`edit` tools it uses on code, so you approve each new memory. `AGENTS.md` is
what you tell the agent about a project. `memory.md` is what the agent notes
about you, in any project.

## Reading guide

The git history is the tutorial. Each step adds one idea and leaves a working
program:

1. **README** - this file.
2. **chat** - a REPL that talks to an LLM over raw HTTP. A chatbot.
3. **bash** - give the model a shell and loop until it stops calling it. Now it is an agent.
4. **safety** - confirm each command and time out long-running ones.
5. **system prompt** - tell the model where it is.
6. **skills** - instructions the model loads only when it needs them.
7. **tools** - a second tool, to show how little it takes to add one.
8. **step cap** - stop a confused model from looping forever.
9. **file tools** - `read`, `write`, `edit`, `glob` and `grep`. The read-only ones run without asking.
10. **simplify** - drop the toy tool now that real ones show the pattern.
11. **memory** - a file the model writes to and the system prompt reads back.

Read them in order with `git log --reverse -p`.
