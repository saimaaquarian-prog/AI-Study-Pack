import json

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
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        raise RuntimeError(f"Groq API error: {e}") from e


def call_json(client, system_prompt, user_prompt, temperature=0.2):
    raw = call_llm(
        client,
        system_prompt,
        user_prompt + "\n\nReturn ONLY valid JSON. No Markdown fences or extra text.",
        temperature,
    ).strip()

    if raw.startswith("```"):
        raw = raw.replace("```json", "", 1).replace("```", "", 1).strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(raw[start:end + 1])
            except json.JSONDecodeError:
                pass
        raise RuntimeError("The AI returned invalid JSON. Please try again.")


def planning_stage(client, context, prompts):
    return call_json(client, prompts["planning_system"], prompts["planning_user"].format(**context))


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
        0.3,
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
        0.2,
    )


def run_workflow(client, context, prompts, on_stage=None):
    results = {}
    stages = [
        ("Planning", lambda: planning_stage(client, context, prompts)),
        ("Content Generation", lambda: content_stage(client, context, results["plan"], prompts)),
        ("Assessment", lambda: assessment_stage(client, context, results["plan"], results["content"], prompts)),
        ("Review", lambda: review_stage(client, results["plan"], results["content"], results["assessment"], prompts)),
        ("Refinement", lambda: refinement_stage(client, context, results["plan"], results["content"], results["assessment"], results["review"], prompts)),
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
