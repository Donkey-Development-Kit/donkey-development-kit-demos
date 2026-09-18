"""Exemptions, and the two ways of writing one wrong.

A scenario an agent genuinely cannot pass is recorded as an *asserted* exemption
with a reason — never a silent skip, and never a scenario quietly dropped from
the run. The reason is meant to be published: the SDK's own README lists its
adapters' exemptions as credibility rather than hiding them.

The plugin validates the mapping at collection time, before a single scenario
runs, so a mistake here fails the run loudly instead of excusing a check.
"""

from __future__ import annotations

# A real one. Frameworks that route through their own transport layer (the
# LiteLLM-backed ones, for example) cannot thread a per-run correlation id
# through it, so the agent cannot carry it into its logs no matter how it is
# written. That is a property of the framework, not a defect in the agent.
FRAMEWORK_LIMITS = {
    "correlation_id_propagated": (
        "This agent's framework owns the HTTP transport and offers no per-request "
        "context hook, so a run-scoped correlation id cannot reach the agent's logs."
    ),
}

# Wrong way #1: a typo'd scenario name. Without validation this would silently
# exempt nothing and the scenario would run and fail, or worse, look excused.
TYPO = {
    "retries_tokn_budget": "we know about this one",
}

# Wrong way #2: an exemption with no reason. An exemption you cannot justify in
# a sentence is a skip wearing a costume.
NO_REASON = {
    "retries_token_budget": "",
}
