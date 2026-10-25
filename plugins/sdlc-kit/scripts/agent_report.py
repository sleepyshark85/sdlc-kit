#!/usr/bin/env python3
"""Reports the agent team's activity and cost, by role and by model, from Claude Code's local session files.

  agent_report.py [--project <folder>] [--session <id>]... [--since <time>] [--until <time>]

It reads a project's sessions under <Claude config folder>/projects/<project>/ (by default the project of the current
folder): each lead's transcript (<session>.jsonl), its subagents' (<session>/subagents/agent-<id>.jsonl, with a
.meta.json holding the agent's type), and the block log git-gate.py writes beside them. It prints Markdown: by role,
by model, the spread per dispatch for each role and model (its tokens by kind and cost among them), and each role's
tool mix. Agents are never ranked one by one: a dispatch is a sample of one (docs/measuring.md, *Comparing models*).

An API response is written as several transcript entries that repeat its usage, so tokens are counted once per
message id across the whole run. Cost uses prices.json (the Claude API's prices; a dated model id matches its model,
and US-only routing costs its multiplier more). A fast-mode response, or a model missing from the table, is counted
as unpriced and listed. Cost is a lower bound: an interrupted request, and Claude Code's own side calls, record no
usage. --since and --until take an ISO 8601 date or time, in UTC unless it names its offset. These are AG1, AG5 and
AG7 of docs/measuring.md, AG2, AG4 and AG8 in part: numbers for the owner, never for a brief."""
import argparse
import importlib.util
import json
import os
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, fields
from datetime import datetime, timezone
from statistics import median

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
HOOKS = os.path.join(os.path.dirname(SCRIPTS), "hooks")
PRICES = os.path.join(SCRIPTS, "prices.json")
LEAD = "lead"
FAST = "fast"
US_ONLY = "us"
LONG = "long"
RESUMED = "resumedAgentId"
META = ".meta.json"
TOP_TOOLS = 5


def load_hook(name):
    """A hook of the plugin, for the names and thresholds the report shares with it."""
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), os.path.join(HOOKS, f"{name}.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


context_size = load_hook("context-size")
git_gate = load_hook("git-gate")
TOKEN_FIELDS = (context_size.INPUT, context_size.CACHE_READ, context_size.CACHE_WRITE, context_size.OUTPUT)


@dataclass
class Response:
    """One API response: its model, when it came, and its tokens by kind; prompt is the context hook's measure."""
    model: str
    time: datetime
    fresh: int
    write_5m: int
    write_1h: int
    read: int
    output: int
    prompt: int
    speed: str
    geo: str


class Agent:
    """One agent of a session: the lead, or a subagent it dispatched."""

    def __init__(self, session, agent_id, role):
        self.session, self.id, self.role = session, agent_id, role
        self.responses = []
        self.tools = Counter()
        self.errors = 0
        self.blocks = 0
        self.resumes = 0
        # The agents this one resumed with SendMessage; only the lead does.
        self.resumed = []

    def model(self):
        """The model that answered most of the agent's requests."""
        return Counter(response.model for response in self.responses).most_common(1)[0][0]

    def peak(self):
        return max(response.prompt for response in self.responses)

    def minutes(self):
        """From its first response to its last, the time between resumes included."""
        times = [response.time for response in self.responses]
        return (max(times) - min(times)).total_seconds() / 60


def parse_time(text):
    """An ISO 8601 date or time as a UTC-aware datetime; one without an offset is taken as UTC."""
    moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def recorded_time(text):
    """A time a session file records, or None when it records none it can read; such an entry is skipped."""
    try:
        return parse_time(text) if isinstance(text, str) else None
    except ValueError:
        return None


def within(moment, since, until):
    return (since is None or moment >= since) and (until is None or moment < until)


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


def content_blocks(message):
    content = message.get("content")
    return [block for block in content if isinstance(block, dict)] if isinstance(content, list) else []


def response_of(message, moment):
    """The message's tokens, or None for a message whose usage records none."""
    usage = message.get("usage") or {}
    if not any(usage.get(field) for field in TOKEN_FIELDS):
        return None
    written = usage.get(context_size.CACHE_WRITE) or 0
    hour = min(written, (usage.get("cache_creation") or {}).get("ephemeral_1h_input_tokens") or 0)
    return Response(message.get("model") or "-", moment, usage.get(context_size.INPUT) or 0, written - hour, hour,
                    usage.get(context_size.CACHE_READ) or 0, usage.get(context_size.OUTPUT) or 0,
                    context_size.prompt_tokens(usage), usage.get("speed") or "", usage.get("inference_geo") or "")


def read_transcript(agent, path, since, until, seen):
    """Adds the transcript's responses, tool calls and tool errors in the window to the agent. seen holds the
    message and tool-call ids already counted in this run. A response without a message id can't be told from its
    copies, so it is left out, and cost stays a lower bound."""
    for entry in lines(path):
        message = entry.get("message")
        moment = recorded_time(entry.get("timestamp"))
        if not isinstance(message, dict) or moment is None or not within(moment, since, until):
            continue
        if entry.get("type") == "assistant":
            key = message.get("id")
            response = response_of(message, moment)
            if response and key and key not in seen:
                seen.add(key)
                agent.responses.append(response)
            for block in content_blocks(message):
                if block.get("type") == "tool_use" and block.get("id") not in seen:
                    seen.add(block.get("id"))
                    agent.tools[block.get("name") or "?"] += 1
        elif entry.get("type") == "user":
            agent.errors += sum(1 for block in content_blocks(message)
                                if block.get("type") == "tool_result" and block.get("is_error"))
            result = entry.get("toolUseResult")
            if isinstance(result, dict) and result.get(RESUMED):
                agent.resumed.append(result[RESUMED])


def role_of(agent_type):
    """A plugin agent's type carries the plugin's name as a prefix: sdlc-kit:developer is the developer."""
    return (agent_type or "unknown").split(":")[-1]


def count_blocks(folder, session, agent, since, until):
    name = git_gate.MAIN if agent.id == LEAD else agent.id
    log = os.path.join(folder, session, git_gate.BLOCK_LOG, f"{name}{context_size.JSONL}")
    times = (recorded_time(entry.get("time")) for entry in lines(log))
    return sum(1 for moment in times if moment is not None and within(moment, since, until))


def session_agents(folder, session, since, until, seen):
    """The lead and each subagent of a session with a response in the window."""
    lead = Agent(session, LEAD, LEAD)
    read_transcript(lead, os.path.join(folder, f"{session}{context_size.JSONL}"), since, until, seen)
    agents = [lead]
    subagents = os.path.join(folder, session, context_size.SUBAGENTS)
    for name in sorted(os.listdir(subagents)) if os.path.isdir(subagents) else []:
        if not (name.startswith(context_size.SUBAGENT) and name.endswith(context_size.JSONL)):
            continue
        agent_id = name[len(context_size.SUBAGENT):-len(context_size.JSONL)]
        transcript = context_size.subagent_transcript(os.path.join(folder, session), agent_id)
        meta = next(lines(os.path.splitext(transcript)[0] + META), None) or {}
        agent = Agent(session, agent_id, role_of(meta.get("agentType")))
        read_transcript(agent, transcript, since, until, seen)
        agents.append(agent)
    by_id = {agent.id: agent for agent in agents}
    for agent_id in lead.resumed:
        if agent_id in by_id:
            by_id[agent_id].resumes += 1
    for agent in agents:
        agent.blocks = count_blocks(folder, session, agent, since, until)
    return [agent for agent in agents if agent.responses]


def price_of(model, prices):
    """The model's prices: its own, or those of the model its dated id names (claude-haiku-4-5-20251001)."""
    keys = [key for key in prices if model == key or model.startswith(key + "-")]
    return prices[max(keys, key=len)] if keys else None


def cost(response, prices, us_only_multiplier):
    """The response's cost in USD, or None when it can't be priced: a fast-mode response or an unknown model."""
    price = price_of(response.model, prices)
    if price is None or response.speed == FAST:
        return None
    if LONG in price and response.prompt > price[LONG]["over"]:
        price = price[LONG]
    spent = (response.fresh * price["input"] + response.write_5m * price["cache_write_5m"]
             + response.write_1h * price["cache_write_1h"] + response.read * price["cache_read"]
             + response.output * price["output"]) / 1_000_000
    return spent * us_only_multiplier if response.geo == US_ONLY else spent


@dataclass
class Totals:
    """What a group of responses adds up to."""
    requests: int = 0
    fresh: int = 0
    writes: int = 0
    read: int = 0
    output: int = 0
    cost: float = 0.0
    unpriced: int = 0

    def add(self, response, spent):
        self.requests += 1
        self.fresh += response.fresh
        self.writes += response.write_5m + response.write_1h
        self.read += response.read
        self.output += response.output
        if spent is None:
            self.unpriced += 1
        else:
            self.cost += spent

    def absorb(self, other):
        for field in fields(self):
            setattr(self, field.name, getattr(self, field.name) + getattr(other, field.name))

    def read_share(self):
        sent = self.fresh + self.writes + self.read
        return self.read / sent if sent else 0.0


def priced(agents, prices, us_only_multiplier):
    """Each agent's totals, and the totals by model."""
    by_agent, by_model, model_agents = {}, defaultdict(Totals), defaultdict(set)
    for agent in agents:
        by_agent[agent] = Totals()
        for response in agent.responses:
            spent = cost(response, prices, us_only_multiplier)
            by_agent[agent].add(response, spent)
            by_model[response.model].add(response, spent)
            model_agents[response.model].add(agent)
    return by_agent, by_model, model_agents


def past(peak, limit):
    """Whether the context hook warned an agent of this peak at this limit."""
    highest = context_size.crossed(0, peak)
    return highest is not None and limit <= highest


def money(value):
    return f"${value:,.2f}"


def spread(values):
    return f"{median(values):,.0f} / {max(values):,.0f}"


def table(header, rows):
    return "\n".join(["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
                     + ["| " + " | ".join(str(cell) for cell in row) + " |" for row in rows])


def role_row(role, members, by_agent):
    """A role's row: its agents' activity summed, and how many passed each context warning."""
    total = Totals()
    for agent in members:
        total.absorb(by_agent[agent])
    return [role, len(members), sum(agent.resumes for agent in members), total.requests,
            sum(sum(agent.tools.values()) for agent in members), sum(agent.errors for agent in members),
            sum(agent.blocks for agent in members), f"{total.output:,}", f"{total.read_share():.0%}",
            f"{max(agent.peak() for agent in members):,}",
            " / ".join(str(sum(1 for agent in members if past(agent.peak(), limit)))
                       for limit in context_size.THRESHOLDS),
            money(total.cost)]


def dispatch_row(role, model, members, by_agent):
    """A role and model's spread per dispatch: the median and the largest agent."""
    totals = [by_agent[agent] for agent in members]
    costs = [total.cost for total in totals]
    return [role, model, len(members), spread([len(agent.responses) for agent in members]),
            spread([sum(agent.tools.values()) for agent in members]), spread([agent.minutes() for agent in members]),
            spread([total.fresh for total in totals]), spread([total.writes for total in totals]),
            spread([total.read for total in totals]), spread([total.output for total in totals]),
            f"{money(median(costs))} / {money(max(costs))}"]


def report(agents, prices, us_only_multiplier):
    """The report's Markdown."""
    by_agent, by_model, model_agents = priced(agents, prices, us_only_multiplier)
    by_role, groups = defaultdict(list), defaultdict(list)
    for agent in agents:
        by_role[agent.role].append(agent)
        groups[(agent.role, agent.model())].append(agent)
    roles = sorted(by_role, key=lambda role: (-sum(by_agent[agent].cost for agent in by_role[role]), role))
    limits = " / ".join(f"{limit // 1000}k" for limit in context_size.THRESHOLDS)
    role_rows = [role_row(role, by_role[role], by_agent) for role in roles]
    dispatch_rows = [dispatch_row(role, model, members, by_agent) for (role, model), members in
                     sorted(groups.items(), key=lambda item: (roles.index(item[0][0]), item[0][1]))]
    parts = [
        "## By role",
        table(["Role", "Agents", "Resumes", "Requests", "Tool calls", "Tool errors", "Blocks", "Output tokens",
               "Cache read share", "Peak context", f"Past {limits}", "Cost"], role_rows),
        "## By model",
        table(["Model", "Agents", "Requests", "Input", "Cache write", "Cache read", "Output", "Cost"],
              [[model, len(model_agents[model]), totals.requests, f"{totals.fresh:,}", f"{totals.writes:,}",
                f"{totals.read:,}", f"{totals.output:,}",
                money(totals.cost) + (f" (+{totals.unpriced} unpriced)" if totals.unpriced else "")]
               for model, totals in sorted(by_model.items(), key=lambda item: (-item[1].cost, item[0]))]),
        "## Per dispatch (median / max)",
        table(["Role", "Model", "Agents", "Requests", "Tool calls", "Minutes", "Input", "Cache write", "Cache read",
               "Output", "Cost"], dispatch_rows),
        "## Tool mix",
        table(["Role", "Most used tools"],
              [[role, ", ".join(f"{name} {count}" for name, count in
                                sum((agent.tools for agent in by_role[role]), Counter()).most_common(TOP_TOOLS))]
               for role in roles]),
    ]
    unpriced = sorted(model for model, totals in by_model.items() if totals.unpriced)
    if unpriced:
        parts.append(f"Unpriced (fast mode, or not in prices.json), counted as $0: {', '.join(unpriced)}.")
    parts.append("Cost is a lower bound: interrupted requests and Claude Code's own side calls record no usage.")
    return "\n\n".join(parts) + "\n"


def project_folder(cwd):
    """Claude Code's folder for a project: its path with every character but letters and digits as a hyphen."""
    return os.path.join(context_size.projects_folder(), re.sub(r"[^A-Za-z0-9]", "-", os.path.abspath(cwd)))


def main(argv):
    parser = argparse.ArgumentParser(description="The agent team's activity and cost, by role and model.")
    parser.add_argument("--project", help="the project's folder of session files (default: the current folder's)")
    parser.add_argument("--session", action="append", help="a session id to read (repeatable; default: all)")
    parser.add_argument("--since", type=parse_time, help="ISO 8601 date or time (UTC by default) to start from")
    parser.add_argument("--until", type=parse_time, help="ISO 8601 date or time (UTC by default) to stop before")
    args = parser.parse_args(argv)
    folder = args.project or project_folder(os.getcwd())
    if not os.path.isdir(folder):
        print(f"No session files at {folder}.", file=sys.stderr)
        return 1
    sessions = args.session or sorted(name[:-len(context_size.JSONL)] for name in os.listdir(folder)
                                      if name.endswith(context_size.JSONL))
    with open(PRICES, encoding="utf-8") as file:
        prices = json.load(file)
    seen = set()
    agents = [agent for session in sessions for agent in session_agents(folder, session, args.since, args.until, seen)]
    if not agents:
        print("No agent activity in that window.", file=sys.stderr)
        return 1
    print(report(agents, prices["models"], prices["us_only_multiplier"]), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
