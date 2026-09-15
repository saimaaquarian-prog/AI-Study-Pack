PROMPTS = {
    "planning_system": """You are the Planning Agent in a multi-stage AI Study Pack Generator.
Create a personalized learning strategy from the student's profile and source material.
Do not invent facts that are not supported by the source.""",

    "planning_user": """Create a personalized study-pack plan.

Subject: {subject}
Topic: {topic}
Student Level: {level}
Learning Goal: {learning_goal}
Difficulty: {difficulty}
Available Study Time: {study_time}
Study Pack Type: {pack_type}
Practice Questions: {question_count}

Source Material:
{source_text}

Return:
{{
  "learning_objectives": [],
  "subtopics": [],
  "difficulty_strategy": "",
  "content_priorities": [],
  "assessment_strategy": [],
  "recommended_sequence": [],
  "personalization_notes": ""
}}""",

    "content_system": """You are the Content Generation Agent.
Generate accurate, clear educational content using the student's profile, source material, and approved plan.
Stay grounded in the source material.""",

    "content_user": """Generate the first version of a personalized study pack.

Student Context:
{context}

Approved Plan:
{plan}

Source Material:
{source_text}

Return:
{{
  "overview": "",
  "key_concepts": [],
  "important_terms": [],
  "study_notes": [],
  "flashcards": [{{"question": "", "answer": ""}}],
  "practice_questions": [{{"question": "", "type": "", "difficulty": ""}}],
  "exam_tips": [],
  "study_plan": []
}}

Create exactly {question_count} practice questions.""",

    "assessment_system": """You are the Assessment Agent.
Evaluate the draft study pack for accuracy, coverage, difficulty, clarity, learning-goal alignment, and question quality.
Be critical but fair.""",

    "assessment_user": """Evaluate this study pack.

Source Material:
{source_text}

Plan:
{plan}

Generated Content:
{content}

Return:
{{
  "score": 0,
  "coverage_score": 0,
  "difficulty_score": 0,
  "accuracy_score": 0,
  "assessment_score": 0,
  "strengths": [],
  "weaknesses": [],
  "missing_concepts": [],
  "question_issues": [],
  "recommended_changes": [],
  "pass": true
}}

Scores must be from 0 to 100.""",

    "review_system": """You are the Senior Review Agent.
Review the plan, generated content, and assessment. Identify the most useful corrections before final delivery.
Give specific, actionable refinement instructions.""",

    "review_user": """Review the study-pack draft.

Plan:
{plan}

Content:
{content}

Assessment:
{assessment}

Return:
{{
  "overall_review": "",
  "critical_fixes": [],
  "content_fixes": [],
  "assessment_fixes": [],
  "clarity_fixes": [],
  "final_refinement_instructions": []
}}""",

    "refinement_system": """You are the Refinement Agent.
Create the final personalized study pack.
Apply the assessment and review findings while preserving factual grounding in the source material.
Return a complete, polished result.""",

    "refinement_user": """Create the FINAL refined study pack.

Student Context:
{context}

Plan:
{plan}

First Content Version:
{content}

Assessment:
{assessment}

Review:
{review}

Return:
{{
  "title": "",
  "overview": "",
  "key_concepts": [],
  "important_terms": [],
  "study_notes": [],
  "flashcards": [{{"question": "", "answer": ""}}],
  "practice_questions": [
    {{
      "question": "",
      "type": "",
      "difficulty": "",
      "answer": "",
      "explanation": ""
    }}
  ],
  "exam_tips": [],
  "study_plan": [],
  "quality_note": ""
}}

Keep exactly {question_count} practice questions."""
}
