# nanoagent

The simplest coding agent. One file, no dependencies.

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
   or `what does this project do?`. Before each tool call it shows the call, e.g.
   `bash {"command": "ls"}`, and asks `run? [y/N]`: type `y` to run it, anything
   else to decline. Ctrl-D quits.

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

This is a sketch, not the real code. The actual loop is `main()` in
`nanoagent.py`: the same shape, but the model's reply comes back as a list of
output items (OpenAI Responses API), its text is printed as it arrives, and you
approve each command before it runs.

The model never executes anything. It only emits text that *asks* for a tool
call. The harness decides whether to run it and feeds the result back as more
text. Everything else in a real coding agent (permission prompts, file editing
tools, project instructions, context compaction, subagents, a fancy UI) is a
refinement of this loop.

Here I give just one tool (`bash`), but in principle this is enough. Often you'll see more tools such as `read_file`, `write_file` and `edit_file` - feel free to add them if you like.

## Reading guide

The git history is the tutorial. Each commit adds one idea and leaves a working
program:

1. **README** - this file.
2. **chat** - a REPL that talks to an LLM over raw HTTP. A chatbot.
3. **bash** - give the model a shell and loop until it stops calling it. Now it is an agent.
4. **safety** - confirm each command and time out long-running ones.
5. **system prompt** - tell the model where it is.
6. **skills** - instructions the model loads only when it needs them.

Read them in order with `git log --reverse -p`.
