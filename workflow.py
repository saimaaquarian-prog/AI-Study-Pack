import json
import re

MODEL = "openai/gpt-oss-20b"


def call_llm(client, system_prompt, user_prompt, temperature=0.2):
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_completion_tokens=12000,
        )
        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("The AI returned an empty response.")
        return content.strip()
    except Exception as e:
        raise RuntimeError(f"Groq API error: {e}") from e


def _extract_json_object(raw):
    """Parse JSON even if a model accidentally adds a small wrapper around it."""
    raw = (raw or "").strip()

    # Remove common Markdown code fences.
    raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\s*```$", "", raw)
    raw = raw.strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Fallback: find the outermost JSON object.
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end > start:
        candidate = raw[start:end + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    raise ValueError("The AI response could not be parsed as JSON.")


def call_json(client, system_prompt, user_prompt, temperature=0.2):
    """Call Groq in JSON Object Mode, with a small retry for transient failures."""
    json_instruction = (
        "\n\nIMPORTANT: Return exactly ONE valid JSON object. "
        "Do not use Markdown, code fences, explanations, or comments outside the JSON object."
    )

    last_error = None
    for attempt in range(2):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt + json_instruction,
                    },
                    {
                        "role": "user",
                        "content": user_prompt + json_instruction,
                    },
                ],
                temperature=temperature,
                max_completion_tokens=12000,
                response_format={"type": "json_object"},
                reasoning_format="hidden",
            )

            raw = response.choices[0].message.content or ""
            return _extract_json_object(raw)

        except json.JSONDecodeError as e:
            last_error = e
        except ValueError as e:
            last_error = e
        except Exception as e:
            # Preserve the useful Groq error instead of hiding it.
            raise RuntimeError(f"Groq structured-output error: {e}") from e

    raise RuntimeError(
        "The AI returned JSON that could not be parsed after two attempts. "
        "Please click Generate Study Pack again."
    ) from last_error


def planning_stage(client, context, prompts):
    return call_json(
        client,
        prompts["planning_system"],
        prompts["planning_user"].format(**context),
        0.1,
    )


def content_stage(client, context, plan, prompts):
    return call_json(
        client,
        prompts["content_system"],
        prompts["content_user"].format(
            context=json.dumps(context, indent=2),
            plan=json.dumps(plan, indent=2),
            source_text=context["source_text"],
            question_count=context["question_count"],
        ),
        0.2,
    )


def assessment_stage(client, context, plan, content, prompts):
    return call_json(
        client,
        prompts["assessment_system"],
        prompts["assessment_user"].format(
            source_text=context["source_text"],
            plan=json.dumps(plan, indent=2),
            content=json.dumps(content, indent=2),
        ),
        0.1,
    )


def review_stage(client, plan, content, assessment, prompts):
    return call_json(
        client,
        prompts["review_system"],
        prompts["review_user"].format(
            plan=json.dumps(plan, indent=2),
            content=json.dumps(content, indent=2),
            assessment=json.dumps(assessment, indent=2),
        ),
        0.1,
    )


def refinement_stage(client, context, plan, content, assessment, review, prompts):
    return call_json(
        client,
        prompts["refinement_system"],
        prompts["refinement_user"].format(
            context=json.dumps(context, indent=2),
            plan=json.dumps(plan, indent=2),
            content=json.dumps(content, indent=2),
            assessment=json.dumps(assessment, indent=2),
            review=json.dumps(review, indent=2),
            question_count=context["question_count"],
        ),
        0.15,
    )


def run_workflow(client, context, prompts, on_stage=None):
    results = {}
    stages = [
        ("Planning", lambda: planning_stage(client, context, prompts)),
        ("Content Generation", lambda: content_stage(client, context, results["plan"], prompts)),
        ("Assessment", lambda: assessment_stage(client, context, results["plan"], results["content"], prompts)),
        ("Review", lambda: review_stage(client, results["plan"], results["content"], results["assessment"], prompts)),
        (
            "Refinement",
            lambda: refinement_stage(
                client,
                context,
                results["plan"],
                results["content"],
                results["assessment"],
                results["review"],
                prompts,
            ),
        ),
    ]

    keys = {
        "Planning": "plan",
        "Content Generation": "content",
        "Assessment": "assessment",
        "Review": "review",
        "Refinement": "final",
    }

    for name, function in stages:
        if on_stage:
            on_stage(name, "Running")
        try:
            results[keys[name]] = function()
            if on_stage:
                on_stage(name, "Completed")
        except Exception:
            if on_stage:
                on_stage(name, "Error")
            raise

    return results
