<!-- Adapted from arc42 (https://arc42.org) by Gernot Starke and Peter Hruschka, licensed under CC BY-SA 4.0
     (https://creativecommons.org/licenses/by-sa/4.0/). The content a project writes into it is its own. -->
# {{Subsystem}}

One subsystem (arc42 §5 level 2 and its part of §6), language-neutral: no code, type, package or API names.

## Responsibility

{{What it does and what it never does; the requirement areas it serves.}}

## Interfaces

The contracts it offers and uses: each one's operations, their inputs and outputs, and their failure modes.

## Components

| Component | Responsibility | Depends on |
|---|---|---|
| {{…}} | {{…}} | {{…}} |

## Flows

{{The flows inside this subsystem, step by step, failure and cancellation included.}}

## Threats

The untrusted inputs only this subsystem receives; the system-wide ones are in `concepts.md` §8.2.

| Input | Threat | Mitigation | Test |
|---|---|---|---|
| {{…}} | {{…}} | {{…}} | {{…}} |
