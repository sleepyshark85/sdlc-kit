<!-- Adapted from arc42 (https://arc42.org), © Dr. Peter Hruschka, Dr. Gernot Starke and contributors, licensed
     under CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0/). What a project writes into it is its own. -->
# Crosscutting concepts

The rules every subsystem keeps (arc42 §8), language-neutral.

## 8.1 Runtime model

Concurrency, cancellation, timeouts, persistence points and event order, each with the rule every implementation
keeps.

## 8.2 Threat model

Each untrusted input, what it could make the system do, and the rule that stops it. Each mitigation names its test.

| Input | Threat | Mitigation | Test |
|---|---|---|---|
| {{User input}} | {{Injection}} | {{Validated at the boundary; parameterized queries}} | {{…}} |

For a system that runs a language model, add a row for each OWASP Top 10 for LLM Applications category that applies
(prompt injection, sensitive information disclosure, excessive agency, improper output handling, unbounded
consumption…) and say why the others don't.

## 8.3 Other concepts

{{Each concept every subsystem follows once it exists: persistence, error handling, observability, configuration…;
one subsection each.}}
