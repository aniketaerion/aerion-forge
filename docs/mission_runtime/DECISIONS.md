# M5.8 Architecture Decisions

## AD-1

M5.8 is the Forge Mission Runtime, not a new planning or execution engine.

## AD-2

Forge remains general-purpose; ERP is the first production proving ground.

## AD-3

M5.8 consumes M5.5, M5.6, and M5.7 through explicit adapters.

## AD-4

Human approval is mandatory at plan and final review gates where policy requires it.

## AD-5

Capability selection is repository-grounded and limited to registered capabilities.

## AD-6

The runtime may not bypass controlled execution, verification, recovery, or Git safety boundaries.

## AD-7

Multi-agent orchestration and research-oriented autonomy are deferred to Forge v2.

## AD-8

M5.8 completion does not itself constitute Forge v1.0 release; a real-project acceptance mission is required.