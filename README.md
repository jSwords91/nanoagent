# nanoagent

The simplest coding agent that actually works. One file, no dependencies.

## The whole idea

A coding agent is a language model in a `while` loop with a shell.

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

## Reading guide

The git history is the tutorial. Each commit adds one idea and leaves a working
program:

1. **README** - this file.
2. **chat** - a REPL that talks to an LLM over raw HTTP. A chatbot.
3. **bash** - give the model a shell and loop until it stops calling it. Now it is an agent.
4. **safety** - confirm each command, time out, truncate long output.
5. **system prompt** - tell the model where it is.
6. **skills** - instructions the model loads only when it needs them.

Read them in order with `git log --reverse -p`.
