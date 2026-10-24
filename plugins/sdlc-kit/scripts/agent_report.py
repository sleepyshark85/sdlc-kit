#!/usr/bin/env python3
"""Reports the agent team's activity and cost, by role and by model, from Claude Code's local session files.

  agent_report.py [--project <folder>] [--session <id>]... [--since <time>] [--until <time>]

It reads a project's sessions under <Claude config folder>/projects/<project>/ (by default the project of the current
folder): each lead's transcript (<session>.jsonl), its subagents' (<session>/subagents/agent-<id>.jsonl, with a
.meta.json holding the agent's type and description), and the block log git-gate.py writes beside them. It prints
Markdown: by role, by model, each role's tool mix, and the costliest agents.

An API response is written as several transcript entries that repeat its usage, so tokens are counted once per
message id. Cost uses prices.json (the Claude API's standard prices; fast mode and US-only routing cost more); a
model missing from it is listed as unpriced. --since and --until take ISO 8601 times in UTC, compared as text, so a
date alone works. These are AG1, AG2, AG4, AG5, AG7 and AG8 of docs/measuring.md: numbers for the owner, never for a
brief."""
import argparse
import importlib.util
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
PRICES = os.path.join(SCRIPTS, "prices.json")
LEAD = "lead"
TOKEN_FIELDS = ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens", "output_tokens")
COSTLIEST = 10
TOP_TOOLS = 5


def load_context_size():
    """The context hook, for its warning thresholds."""
    path = os.path.join(SCRIPTS, "..", "hooks", "context-size.py")
    spec = importlib.util.spec_from_file_location("context_size", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


THRESHOLDS = load_context_size().THRESHOLDS


class Agent:
    """One agent of a session: the lead, or a subagent it dispatched."""

    def __init__(self, session, agent_id, role, description):
        self.session, self.id, self.role, self.description = session, agent_id, role, description
        self.responses = {}
        self.tools = Counter()
        self.errors = 0
        self.blocks = 0
        self.resumes = 0
        # The agents this one resumed with SendMessage; only the lead does.
        self.resumed = []

    def model(self):
        models = Counter(model for model, _, _ in self.responses.values())
        return models.most_common(1)[0][0] if models else "-"

    def minutes(self):
        times = sorted(time for _, _, time in self.responses.values() if time)
        if len(times) < 2:
            return 0.0
        return (datetime.fromisoformat(times[-1]) - datetime.fromisoformat(times[0])).total_seconds() / 60


def lines(path):
    """The JSON lines of a file; a line that does not parse, such as one still being written, is skipped."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as file:
        for line in file:
            try:
                yield json.loads(line)
            except ValueError:
                continue


def within(time, since, until):
    return (not since or time >= since) and (not until or time < until)


def content_blocks(message):
    content = message.get("content")
    return [block for block in content if isinstance(block, dict)] if isinstance(content, list) else []


def read_transcript(agent, path, since, until):
    """Adds the transcript's API responses, tool calls and tool errors in the window to the agent."""
    tool_ids = set()
    for entry in lines(path):
        message = entry.get("message")
        time = entry.get("timestamp") or ""
        if not isinstance(message, dict) or not within(time, since, until):
            continue
        if entry.get("type") == "assistant":
            usage = message.get("usage")
            if usage and any(usage.get(field) for field in TOKEN_FIELDS):
                key = message.get("id") or entry.get("requestId") or entry.get("uuid")
                agent.responses[key] = (message.get("model") or "-", usage, time)
            for block in content_blocks(message):
                if block.get("type") == "tool_use" and block.get("id") not in tool_ids:
                    tool_ids.add(block.get("id"))
                    agent.tools[block.get("name") or "?"] += 1
        elif entry.get("type") == "user":
            agent.errors += sum(1 for block in content_blocks(message)
                                if block.get("type") == "tool_result" and block.get("is_error"))
            result = entry.get("toolUseResult")
            if isinstance(result, dict) and result.get("resumedAgentId"):
                agent.resumed.append(result["resumedAgentId"])


def tokens(usage):
    """(input, 5-minute cache write, 1-hour cache write, cache read, output) of one response."""
    written = usage.get("cache_creation_input_tokens") or 0
    hour = min(written, (usage.get("cache_creation") or {}).get("ephemeral_1h_input_tokens") or 0)
    return (usage.get("input_tokens") or 0, written - hour, hour, usage.get("cache_read_input_tokens") or 0,
            usage.get("output_tokens") or 0)


def cost(model, usage, prices):
    """The response's cost in USD, or None when the model has no price."""
    price = prices.get(model)
    if price is None:
        return None
    fresh, write_5m, write_1h, read, output = tokens(usage)
    if "long" in price and fresh + write_5m + write_1h + read > price["long"]["over"]:
        price = price["long"]
    return (fresh * price["input"] + write_5m * price["cache_write_5m"] + write_1h * price["cache_write_1h"]
            + read * price["cache_read"] + output * price["output"]) / 1_000_000


def prompt(usage):
    fresh, write_5m, write_1h, read, _ = tokens(usage)
    return fresh + write_5m + write_1h + read


def project_folder(cwd):
    """Claude Code's folder for a project: its path with every character but letters and digits as a hyphen."""
    config = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude")
    return os.path.join(config, "projects", re.sub(r"[^A-Za-z0-9]", "-", os.path.abspath(cwd)))


def role_of(agent_type):
    """A plugin agent's type carries the plugin's name as a prefix: sdlc-kit:developer is the developer."""
    return (agent_type or "unknown").split(":")[-1]


def session_agents(folder, session, since, until):
    """The lead and each subagent of a session, read."""
    lead = Agent(session, LEAD, LEAD, "")
    read_transcript(lead, os.path.join(folder, f"{session}.jsonl"), since, until)
    agents = [lead]
    subagents = os.path.join(folder, session, "subagents")
    for name in sorted(os.listdir(subagents)) if os.path.isdir(subagents) else []:
        if not (name.startswith("agent-") and name.endswith(".jsonl")):
            continue
        agent_id = name[len("agent-"):-len(".jsonl")]
        meta = next(lines(os.path.join(subagents, f"agent-{agent_id}.meta.json")), None) or {}
        agent = Agent(session, agent_id, role_of(meta.get("agentType")), meta.get("description") or "")
        read_transcript(agent, os.path.join(subagents, name), since, until)
        agents.append(agent)
    by_id = {agent.id: agent for agent in agents}
    for agent_id in lead.resumed:
        if agent_id in by_id:
            by_id[agent_id].resumes += 1
    for agent in agents:
        log = os.path.join(folder, session, "git-gate", f"{'main' if agent.id == LEAD else agent.id}.jsonl")
        agent.blocks = sum(1 for entry in lines(log) if within(entry.get("time") or "", since, until))
    return [agent for agent in agents if agent.responses]


def money(value):
    return f"${value:,.2f}"


def table(header, rows):
    return "\n".join(["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
                     + ["| " + " | ".join(str(cell) for cell in row) + " |" for row in rows])


def report(agents, prices):
    """The report's Markdown."""
    unpriced = set()
    agent_cost = {}
    by_model = defaultdict(lambda: [set(), 0, 0, 0, 0, 0, 0.0])
    for agent in agents:
        agent_cost[agent] = 0.0
        for model, usage, _ in agent.responses.values():
            fresh, write_5m, write_1h, read, output = tokens(usage)
            spent = cost(model, usage, prices)
            if spent is None:
                unpriced.add(model)
                spent = 0.0
            agent_cost[agent] += spent
            row = by_model[model]
            row[0].add(agent)
            for index, value in enumerate((1, fresh, write_5m + write_1h, read, output), start=1):
                row[index] += value
            row[6] += spent
    by_role = defaultdict(list)
    for agent in agents:
        by_role[agent.role].append(agent)

    def role_row(role, members):
        usages = [usage for agent in members for _, usage, _ in agent.responses.values()]
        sent = sum(prompt(usage) for usage in usages)
        read = sum(usage.get("cache_read_input_tokens") or 0 for usage in usages)
        peaks = [max(prompt(usage) for _, usage, _ in agent.responses.values()) for agent in members]
        return [role, len(members), sum(agent.resumes for agent in members), len(usages),
                sum(sum(agent.tools.values()) for agent in members), sum(agent.errors for agent in members),
                sum(agent.blocks for agent in members), f"{sum(usage.get('output_tokens') or 0 for usage in usages):,}",
                f"{read / sent:.0%}" if sent else "-", f"{max(peaks):,}",
                " / ".join(str(sum(1 for peak in peaks if peak > limit)) for limit in THRESHOLDS),
                money(sum(agent_cost[agent] for agent in members))]

    roles = sorted(by_role, key=lambda role: -sum(agent_cost[agent] for agent in by_role[role]))
    limits = " / ".join(f"{limit // 1000}k" for limit in THRESHOLDS)
    parts = [
        "## By role",
        table(["Role", "Agents", "Resumes", "Requests", "Tool calls", "Tool errors", "Blocks", "Output tokens",
               "Cache read share", "Peak context", f"Past {limits}", "Cost"],
              [role_row(role, by_role[role]) for role in roles]),
        "## By model",
        table(["Model", "Agents", "Requests", "Input", "Cache write", "Cache read", "Output", "Cost"],
              [[model, len(row[0]), row[1], f"{row[2]:,}", f"{row[3]:,}", f"{row[4]:,}", f"{row[5]:,}",
                money(row[6]) if model not in unpriced else "unpriced"]
               for model, row in sorted(by_model.items(), key=lambda item: -item[1][6])]),
        "## Tool mix",
        table(["Role", "Most used tools"],
              [[role, ", ".join(f"{name} {count}" for name, count in
                                sum((agent.tools for agent in by_role[role]), Counter()).most_common(TOP_TOOLS))]
               for role in roles]),
        f"## Costliest agents (top {COSTLIEST})",
        table(["Agent", "Role", "Description", "Model", "Requests", "Minutes", "Peak context", "Cost"],
              [[agent.id, agent.role, agent.description.replace("|", "/"), agent.model(), len(agent.responses),
                f"{agent.minutes():.0f}", f"{max(prompt(usage) for _, usage, _ in agent.responses.values()):,}",
                money(agent_cost[agent])]
               for agent in sorted(agents, key=lambda agent: -agent_cost[agent])[:COSTLIEST]]),
    ]
    if unpriced:
        parts.append(f"Unpriced models (not in prices.json, counted as $0): {', '.join(sorted(unpriced))}.")
    return "\n\n".join(parts) + "\n"


def main(argv):
    parser = argparse.ArgumentParser(description="The agent team's activity and cost, by role and model.")
    parser.add_argument("--project", help="the project's folder of session files (default: the current folder's)")
    parser.add_argument("--session", action="append", help="a session id to read (repeatable; default: all)")
    parser.add_argument("--since", help="ISO 8601 UTC time or date to start from")
    parser.add_argument("--until", help="ISO 8601 UTC time or date to stop before")
    args = parser.parse_args(argv)
    folder = args.project or project_folder(os.getcwd())
    if not os.path.isdir(folder):
        print(f"No session files at {folder}.", file=sys.stderr)
        return 1
    sessions = args.session or sorted(name[:-len(".jsonl")] for name in os.listdir(folder) if name.endswith(".jsonl"))
    with open(PRICES, encoding="utf-8") as file:
        prices = json.load(file)["models"]
    agents = [agent for session in sessions for agent in session_agents(folder, session, args.since, args.until)]
    if not agents:
        print("No agent activity in that window.", file=sys.stderr)
        return 1
    print(report(agents, prices), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
