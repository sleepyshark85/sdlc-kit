# Release flags

Each flag that keeps an unfinished feature off on `main` (`plan-wave`, *Off on `main` until switched on*). A flag is
off by default, read at one point, and removed within two waves of its switch-on. A flag not listed here, or past
its removal task, is a must-fix in review.

The daily run (`.github/workflows/daily.yml`) runs the full suite twice: with the defaults, and with every flag
whose *State* is `off` turned on. It turns a flag on by setting its component's `flag_variable` from
`.sdlc/checks.toml` to `true`, `{flag}` standing for the name in the *Flag* column (the .NET pack's `Flags__{flag}`
is the configuration key `Flags:<Name>`), so a flag's name is letters, digits and underscores, and its state one of
`off`, `on` or `removed`; a row the run cannot read fails it.

| Flag | Feature | Added by | Switch-on | Removal task | State |
|---|---|---|---|---|---|
| {{…}} | {{requirement IDs}} | {{wave and task}} | {{wave and task}} | {{wave and task}} | {{off, on, removed}} |
