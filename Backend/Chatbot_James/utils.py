import   re 
import   json
from json_repair import repair_json  

def clean_llm_json(text):

    # remove code fences
    text = re.sub(r"```.*?```", "", text, flags=re.S)

    # normalize NBSP
    text = text.replace("\xa0", " ")

    # smart quotes → normal
    text = text.replace("“", '"').replace("”", '"')
    text = text.replace("‘", "'").replace("’", "'")

    # remove trailing commas
    text = re.sub(r",\s*]", "]", text)
    text = re.sub(r",\s*}", "}", text)

    # keep only JSON array block
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1:
        text = text[start:end+1]

    return text.strip()


def safe_load_json(text):

    try:
        return json.loads(text)

    except Exception as e:
        print("Normal JSON failed → repairing...")

        fixed = repair_json(text)

        return json.loads(fixed)


def validate_scores(data):

    clean = []

    for item in data:

        if not isinstance(item, dict):
            continue

        if "id" not in item:
            continue

        if "its_score" not in item:
            continue

        try:
            item["id"] = int(item["id"])
            item["its_score"] = int(item["its_score"])
        except:
            continue

        # clamp score
        item["its_score"] = max(0, min(10, item["its_score"]))

        clean.append(item)

    # remove duplicates by id (keep last)
    dedup = {}
    for x in clean:
        dedup[x["id"]] = x

    return list(dedup.values())


def safe_json_loads(text):

    # remove markdown fences if any
    text = re.sub(r"```json", "", text, flags=re.IGNORECASE)
    text = re.sub(r"```python", "", text, flags=re.IGNORECASE)
    text = text.replace("```", "")

    # ✅ normalize problematic escapes
    text = text.replace("\\xa0", " ")

    text = text.strip()

    print("final cleaned text preview:", text)

    return json.loads(text)

def safe_json_loads_v3(text):

    # remove markdown code fences only
    text = re.sub(r"```json", "", text, flags=re.IGNORECASE)
    text = re.sub(r"```python", "", text, flags=re.IGNORECASE)
    text = text.replace("```", "")

    text = text.strip()

    print("final text before json.loads:   and  safe  now  ", text)

    return json.loads(text)

def safe_json_loads_old(text):
    # remove code fences if any
    text = re.sub(r"```.*?\n", "", text)
    text = text.replace("```", "")

    # replace single quotes around keys/strings with double quotes
    # only where it looks like JSON keys
    text = re.sub(r"(?<!\\)'", '"', text)

    print(" final  text  before  doing  return json.loads(text)   ",text)

    return json.loads(text) 

def parse_evaluation_output(text: str) -> dict:
    if not isinstance(text, str):
        raise ValueError(f"Expected string, got {type(text)}")

    # -------- SCORE --------
    score_match = re.search(r'Role Fit Score:\s*(\d+)', text)
    score = int(score_match.group(1)) if score_match else None

    # -------- SUMMARY --------
    summary_match = re.search(r'Summary:\s*(.*?)(?:\n\n|Weaknesses:)', text, re.S)
    summary = summary_match.group(1).strip() if summary_match else ""

    # -------- WEAKNESSES --------
    weaknesses_match = re.search(r'Weaknesses:\s*(.*?)(?:\n\n|Feedback)', text, re.S)
    weaknesses = []
    if weaknesses_match:
        weaknesses = [
            w.strip("- ").strip()
            for w in weaknesses_match.group(1).split("\n")
            if w.strip()
        ]

    # -------- IMPROVEMENTS --------
    improvements_match = re.search(r'Feedback & Improvement Suggestions:\s*(.*?)(?:\n\n|Guidelines)', text, re.S)
    improvements = []
    if improvements_match:
        improvements = [
            i.strip("- ").strip()
            for i in improvements_match.group(1).split("\n")
            if i.strip()
        ]

    return {
        "score": score,
        "summary": summary,
        "weaknesses": weaknesses,
        "improvements": improvements,
    }


def parse_evaluation_output_old(text: str):
    result = {
        "score": None,
        "summary": "",
        "weaknesses": [],
        "improvements": []
    }

    # 🔢 Score
    score_match = re.search(r"Role Fit Score:\s*(\d+)", text)
    if score_match:
        result["score"] = int(score_match.group(1))

    # 📄 Summary
    summary_match = re.search(r"Summary:\s*(.*?)(Weaknesses:|$)", text, re.S)
    if summary_match:
        result["summary"] = summary_match.group(1).strip()

    # ⚠️ Weaknesses
    weakness_block = re.search(r"Weaknesses:\s*(.*?)(Feedback|$)", text, re.S)
    if weakness_block:
        weaknesses = re.findall(r"-\s*(.+)", weakness_block.group(1))
        result["weaknesses"] = list(dict.fromkeys(w.strip() for w in weaknesses))

    # 🚀 Improvements (deduplicate HARD)
    improvement_blocks = re.findall(
        r"Feedback\s*&\s*Improvement\s*Suggestions:\s*(.*?)(Weaknesses|Guidelines|$)",
        text,
        re.S
    )

    improvements = []
    for block in improvement_blocks:
        improvements += re.findall(r"-\s*(.+)", block)

    result["improvements"] = list(dict.fromkeys(i.strip() for i in improvements))

    return result



SECTION_MAP = {
    "skills": "skills",
    "experience": "experience",
    "academic background": "academic_background",
    "academic": "academic_background"
}

LEVELS = ["easy", "medium", "hard"]


def normalize_text(text):
    # Remove markdown bold markers
    text = text.replace("**", "")

    # Force every section header onto a new line
    text = re.sub(
        r"(Skills|Experience|Academic Background)\s*\((Easy|Medium|Hard)\)",
        r"\n\1 (\2)",
        text,
        flags=re.IGNORECASE
    )

    # Collapse weird spacing
    text = re.sub(r"\s+", " ", text)

    # Restore line breaks for parsing
    text = re.sub(r"\)\s*:", "):\n", text)

    return text.strip()


def parse_llm_questions(raw_text):
    raw_text = normalize_text(raw_text)

    questions = []
    serial_no = 1

    current_section = None
    current_mode = None

    for line in raw_text.split("\n"):
        line = line.strip()
        if not line:
            continue

        # Detect section + difficulty
        header_match = re.search(
            r"(Skills|Experience|Academic Background)\s*\((Easy|Medium|Hard)\)",
            line,
            re.IGNORECASE
        )

        if header_match:
            section_raw = header_match.group(1).lower()
            mode_raw = header_match.group(2).lower()

            current_section = SECTION_MAP.get(section_raw, section_raw)
            current_mode = mode_raw

            # Remove header from line to isolate question
            line = re.sub(
                r"(Skills|Experience|Academic Background)\s*\((Easy|Medium|Hard)\)\s*:?",
                "",
                line,
                flags=re.IGNORECASE
            ).strip()

        if current_section and current_mode and line:
            questions.append({
                "serial_no": serial_no,
                "section": current_section,
                "mode": current_mode,
                "question": line
            })
            serial_no += 1

    return questions


def parse_llm_questions_old2(raw_text):
    questions = []
    serial_no = 1

    pattern = re.compile(
        r"\*\*(.*?)\s*\((Easy|Medium|Hard)\)\*\*\s*:\s*(.+)",
        re.IGNORECASE
    )

    for section_raw, mode_raw, question_text in pattern.findall(raw_text):
        section = section_raw.strip().lower().replace(" ", "_")
        mode = mode_raw.lower()

        questions.append({
            "serial_no": serial_no,
            "section": section,
            "mode": mode,
            "question": question_text.strip()
        })
        serial_no += 1

    return questions

def parse_llm_questions_old(raw_text):
    """
    Parses LLM output into structured JSON
    """
    questions = []
    serial_no = 1

    # Regex to capture:
    # 1. Section
    # 2. Mode
    # 3. Question text
    pattern = re.compile(
        r"\*\*(.*?)\s*\((Easy|Medium|Hard)\):\*\*\s*(.+)",
        re.IGNORECASE
    )

    for match in pattern.findall(raw_text):
        section_raw, mode_raw, question_text = match

        # Normalize section names
        section = section_raw.strip().lower().replace(" ", "_")

        # Normalize mode
        mode = mode_raw.strip().lower()

        questions.append({
            "serial_no": serial_no,
            "section": section,
            "mode": mode,
            "question": question_text.strip()
        })

        serial_no += 1

    return questions
