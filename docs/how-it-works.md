# 3 How logdruid works

The following sections assume this picture.

The console and the file exist only in the `main` process, that is, in the
process that starts the application and creates the other processes. A thread
of logdruid runs there that collects and writes all messages.

Each child process gets a pipe of its own to the `main` process when it
starts, in one direction: from the child process to the `main` process. Only
that one child process writes into it, so no lock across process boundaries
is needed. A child process can block only on its own pipe, when it is full
because the `main` process cannot keep up. When a child process ends, even
hard, its pipe ends; whatever it had written into it until then arrives.

Filtering happens where a message arises. Whatever does not reach the
configured minimum level never goes through the pipe at all.

Per message, the pipe carries: the time stamp the reporting process sets at
the call, the level, the name and id of the process, the name of the message,
the module, function and line of the call, and the finished text of the
message, a traceback included as text. Nothing more goes through; what this
means for the format of the output is described in
[section 5.3](configuration.md#53-outputs).

The `main` process puts its own messages into the same order. It holds every
message back for a short time window, 100 ms by default, and then writes the
messages ordered by their time stamps. A message that arrives only after this
window has passed is written at once, so possibly out of order.

In every process, logdruid also takes over the messages that arise through
`logging` and hands them on to loguru's logger
([section 6](libraries.md)).
