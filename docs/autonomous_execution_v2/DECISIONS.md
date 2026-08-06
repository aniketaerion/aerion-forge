# M5.7 Architecture Decisions

## AD-1

M5.7 orchestrates execution but does not bypass M5.2 controlled tool execution.

## AD-2

Approved M5.6 plans are the only executable source of work.

## AD-3

Execution state and attempts are immutable records updated through explicit services.

## AD-4

Retries are bounded and policy controlled.

## AD-5

Evidence is mandatory for successful completion.

## AD-6

The CLI namespace shall be `autonomous-execution-v2` to avoid collision with the existing autonomous execution CLI.