"""
Phase 10 — Input Guardrails (Agents SDK).

Purpose: Detect and reject requests that are clearly outside the scope of a
Pakistan-based flight booking & travel assistant.

APPROPRIATE requests include:
  * finding flights (routes, dates, prices, airlines, cabins)
  * flight details (schedules, durations, stops, baggage)
  * comparing flights
  * general travel questions (terminology, what to consider, how to prepare)

OUT-OF-SCOPE requests include:
  * writing code (Python, React, etc.)
  * debugging applications
  * generating creative content (poems, stories, games)
  * unrelated technical questions

The guardrail uses an LLM classifier to distinguish in-scope from out-of-scope,
rather than brittle keyword matching. This avoids rejecting valid questions like
"What is baggage allowance?" or "I need help planning my trip."

IMPORTANT: Do NOT overblock. Ambiguous travel-related requests ("I need help
with my trip") should be allowed — the agent can ask for clarification. Only
reject CLEARLY unrelated requests.
"""
from agents import Agent, RunContextWrapper
from agents.guardrail import GuardrailFunctionOutput, input_guardrail


@input_guardrail(name="scope_check", run_in_parallel=False)
async def scope_input_guardrail(
    ctx: RunContextWrapper,
    agent: Agent,
    user_input: str | list,
) -> GuardrailFunctionOutput:
    """Check if the request is within the scope of a flight/travel assistant.

    Runs BEFORE the agent starts (run_in_parallel=False) so out-of-scope requests
    are rejected immediately without wasting agent/tool calls.

    Returns:
        GuardrailFunctionOutput with tripwire_triggered=True if clearly out-of-scope.
    """
    # Normalize input to a single string for classification.
    if isinstance(user_input, list):
        # SDK may pass list of items; extract text content.
        text = " ".join(
            str(getattr(item, "text", None) or getattr(item, "content", ""))
            for item in user_input
        )
    else:
        text = user_input

    text = text.strip()
    if not text:
        # Empty input is not out-of-scope per se; let the agent handle it.
        return GuardrailFunctionOutput(
            output_info={"check": "empty_input"}, tripwire_triggered=False
        )

    # Use the model to classify scope (lightweight, no tools). This avoids brittle
    # keyword rules that would reject valid questions like "What is baggage allowance?"
    from agents import Runner
    from config.model_config import DEFAULT_MODEL

    classifier_prompt = f"""You are a scope classifier for a Pakistan-based flight booking and travel assistant.

Your task: determine if the following user request is IN-SCOPE or OUT-OF-SCOPE.

IN-SCOPE requests:
- Finding flights (routes, dates, prices, airlines, cabins, stops)
- Flight details (schedules, durations, baggage, availability)
- Comparing flights
- General travel questions (terminology like "What is a connecting flight?", "What does baggage allowance mean?", advice like "What should I consider when choosing a flight?")
- Ambiguous travel-related requests like "I need help with my trip" or "I'm traveling soon" (these should be allowed — the agent will clarify)

OUT-OF-SCOPE requests (clearly unrelated):
- Writing code (Python, JavaScript, React, etc.)
- Debugging applications or technical troubleshooting
- Generating creative content (poems, stories, games, essays on non-travel topics)
- General knowledge questions unrelated to travel/flights
- Requests about other domains (medical advice, legal advice, financial planning not related to flights)

User request:
\"\"\"
{text}
\"\"\"

Respond with EXACTLY one word: IN-SCOPE or OUT-OF-SCOPE.
If the request is ambiguous or could plausibly be travel-related, respond IN-SCOPE.
Only respond OUT-OF-SCOPE if the request is CLEARLY unrelated to flights/travel."""

    from agents import Agent as ClassifierAgent

    # Lightweight classifier agent (no tools, no structured output).
    classifier = ClassifierAgent(
        name="Scope Classifier",
        instructions="You classify user requests as IN-SCOPE or OUT-OF-SCOPE for a flight/travel assistant. Respond with exactly one word: IN-SCOPE or OUT-OF-SCOPE.",
        model=DEFAULT_MODEL,
    )

    try:
        result = await Runner.run(
            starting_agent=classifier, input=classifier_prompt, context=None
        )
        decision = str(result.final_output).strip().upper()

        if "OUT-OF-SCOPE" in decision or "OUT OF SCOPE" in decision:
            return GuardrailFunctionOutput(
                output_info={
                    "check": "scope_classifier",
                    "decision": "out_of_scope",
                    "input": text[:200],
                },
                tripwire_triggered=True,
            )

        # IN-SCOPE or ambiguous → allow.
        return GuardrailFunctionOutput(
            output_info={"check": "scope_classifier", "decision": "in_scope"},
            tripwire_triggered=False,
        )

    except Exception as e:
        # If the classifier fails (network, quota, etc.), fail OPEN — allow the
        # request rather than breaking the system. Log the error for debugging.
        return GuardrailFunctionOutput(
            output_info={"check": "scope_classifier", "error": str(e), "failsafe": "allow"},
            tripwire_triggered=False,
        )

