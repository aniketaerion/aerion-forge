# M5.9 Architecture Decisions

## AD-1 — M5.9 Extends M5.8
M5.9 reuses the production mission runtime and safety gates proven by M5.8 rather than creating a competing agent runtime.

## AD-2 — Provider Proposes, Forge Executes
Engineering providers have reasoning authority only. Repository mutation remains governed by Forge.

## AD-3 — Repository Grounding Is Mandatory
General engineering plans must cite repository evidence for selected files and symbols.

## AD-4 — Plans and Edits Are Structured Contracts
Free-form provider prose is insufficient for execution authority.

## AD-5 — Multi-file Work Is Bounded
Coordinated multi-file changes remain inside approved scope and transaction controls.

## AD-6 — Repair Is Bounded
Repair attempts are finite and policy-governed. Default maximum: three.

## AD-7 — Provider Independence
Core contracts remain independent from OpenAI, Ollama, and other provider SDKs.

## AD-8 — Acceptance Must Be Previously Unseen
Release acceptance includes tasks not encoded into Forge implementation beforehand.

## AD-9 — No Default Self-Modification
General engineering capability does not override existing self-modification policy.

## AD-10 — No Scope Drift
Material requirement, target, or risk expansion requires replanning and renewed authority.

## AD-11 — M5.9 Is Not Multi-agent
Multi-agent coordination, autonomous deployment, browser automation, and unrestricted shell agents remain outside M5.9.