# {{project}}

{{What it is, in two sentences.}}

## Prerequisites

- {{Runtime and tools, such as Docker and the .NET SDK}}
- Python 3.11 or later, for the git hook and the repository's tooling
- Claude Code with the `sdlc-kit` plugin (`/plugin marketplace add sleepyshark85/sdlc-kit`, then
  `/plugin install sdlc-kit@sdlc-kit`)

## Build and test

{{Commands.}}

## How we work

[`docs/conventions.md`](docs/conventions.md): every change through a pull request, reviewed by a fresh reviewer agent
and merged once the required checks pass.

Built with [sdlc-kit](https://github.com/sleepyshark85/sdlc-kit); its notice is in [`NOTICE`](NOTICE).
