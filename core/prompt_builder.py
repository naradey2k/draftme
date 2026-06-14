from models.cv import CVData


def build_extract_prompt(cv_text: str) -> list[dict]:
    return [
        {
            "role": "system",
            "content": (
                "You are a CV parser. Extract structured data exactly as it appears. "
                "Do not infer, add, or summarize. Return only JSON."
            ),
        },
        {"role": "user", "content": cv_text},
    ]


def build_optimize_prompt(
    cv_data: CVData,
    jd_text: str,
    feedback: str,
    tone: str,
    language: str,
    iteration: int,
) -> list[dict]:
    system = (
        "You are a professional resume writer. Rules:\n"
        "- Output a single self-contained HTML string in key 'html'\n"
        "- One page only when rendered to PDF\n"
        "- Inline CSS only, no images, ATS-safe fonts (Arial, Calibri, Georgia)\n"
        "- Do not invent facts. Only use information from the provided CV JSON.\n"
        f"- Tone: {tone}. Language: {language}.\n"
        f"- This is iteration {iteration}."
    )
    user = cv_data.model_dump_json() + "\n\nJob Description:\n" + jd_text
    if feedback:
        user += f"\n\nPrevious attempt failed filters:\n{feedback}\nFix these issues."
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]

