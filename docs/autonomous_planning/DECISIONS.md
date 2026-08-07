# M5.6 Architecture Decisions

## AD-1

M5.6 plans engineering work but never executes tools or edits repositories directly.

## AD-2

Planning contracts are immutable and versioned.

## AD-3

Planning identifiers and ordering are deterministic.

## AD-4

Dependencies are explicit graph edges rather than implicit sequence assumptions.

## AD-5

Destructive work requires explicit approval.

## AD-6

Validation is mandatory before a plan can become executable.

## AD-7

M5.7 is the execution consumer of approved M5.6 plans.

## AD-8

Repository, memory, capability, and architecture context are inputs to planning rather than duplicated planning-owned subsystems.