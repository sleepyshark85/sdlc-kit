# .NET rules

How .NET code is written here, on top of `docs/conventions.md`. The code lives in `dotnet/`: `src/` (libraries),
`tests/`, and `apps/` or `samples/` where there are any, beside one solution.

## Code

- **One class, record, struct, interface or enum per file,** named after it (the after-edit hook checks it). Related
  types share a folder; the namespace stays the project's.
- **Nullable on, warnings are errors,** `latest-recommended` analyzers and the style in `.editorconfig`. A
  suppression needs a reason the reviewer agrees with, on its line.
- **Public items have doc comments** (CS1591) and are declared in the project's `PublicAPI.Unshipped.txt`
  (`Microsoft.CodeAnalysis.PublicApiAnalyzers`, which `src/Directory.Build.props` adds to every library): a new
  public item shows in the diff. Each library starts with both `PublicAPI.Shipped.txt` and `PublicAPI.Unshipped.txt`,
  empty. `internal` is the default.
- **Each project registers its own services** (`Add…` extension methods on `IServiceCollection`); the application
  composes them in one place, and that composition is the switch for dark work: an unfinished feature's `Add…` call
  arrives with its switch-on task.
- **Async all the way,** with a `CancellationToken` on every I/O path; `TimeProvider` for time, never `DateTime.Now`.
- **Packages are versioned centrally** in `Directory.Packages.props`, restored from `packages.lock.json`; a new one
  needs its line in `docs/decisions.md`.

## Tests

- xUnit v3, one test project per library; test names carry the requirement ID (`API_01_rejects_an_empty_name`).
- Boundaries only are faked; a real database runs in a container (Testcontainers).
- Property tests for parsers and validators (for example CsCheck), with the seed printed on failure.

## Commands

| What | Command, in `dotnet/` |
|---|---|
| Build | `dotnet build --configuration Release` |
| Test | `dotnet test --configuration Release` |
| Format | `dotnet format` |
| Mutation, changed code only | `dotnet stryker --since:origin/main`, in the library's folder |
| Mutation, whole library | `dotnet stryker`, in the library's folder |

A library gets mutation testing by a `stryker-config.json` in its folder, from `stryker-config.template.json`; its
`break` threshold is its floor, recorded in `docs/decisions.md`. Every library, the app and the test kit need one:
the `dotnet-mutation` check fails when `dotnet/` has none.
