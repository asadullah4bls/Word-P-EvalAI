import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# =============================
# Quick rejection rules
# =============================
def quick_reject(user_answer, question):
    """
    Reject obvious bad answers before LLM call
    """
    ua = user_answer.strip().lower()
    q = question.strip().lower()

    if not ua:
        return "Empty answer"

    if ua == q:
        return "Answer repeats the question"

    return None


# =============================
# LLM-based SAQ evaluation
# =============================
def evaluate_saq(user_answer, correct_answer, question):
    """
    Evaluate short-answer questions using LLM-based factual reasoning
    """

    rejection_reason = quick_reject(user_answer, question)
    if rejection_reason:
        return {
            "is_correct": False,
            "score": 0.0,
            "verdict": "INCORRECT",
            "reason": rejection_reason
        }

    prompt = f"""
You are an expert quiz evaluator.

Your job is to correctly evaluate the student's submitted answer to a question
using your own general knowledge base and logical reasoning.

Important rules:
- Do NOT hallucinate facts.
- Do NOT assume missing information.
- The answer must be factually correct.
- Do NOT reward answers that repeat or paraphrase the question.
- Do NOT reward vague, circular, or keyword-stuffed answers.
- Partial correctness should receive partial credit.
- Use general knowledge only, NOT the source document.
- Ignore grammar and wording style.

Question:
{question}

Correct Answer:
{correct_answer}

Student Answer:
{user_answer}

Return ONLY valid JSON in this exact format:
{{
  "verdict": "CORRECT | PARTIALLY_CORRECT | INCORRECT",
  "score": 0.0 to 10.0,
  "reason": "one short sentence explaining why"
}}
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=200
        )

        raw = response.choices[0].message.content.strip()
        result = json.loads(raw)

        score = float(result.get("score", 0.0))
        verdict = result.get("verdict", "INCORRECT")

        return {
            "is_correct": score >= 0.7,
            "score": round(score, 2),
            "verdict": verdict,
            "reason": result.get("reason", "")
        }

    except Exception as e:
        # Safe fallback
        return {
            "is_correct": False,
            "score": 0.0,
            "verdict": "INCORRECT",
            "reason": f"Evaluation error: {str(e)}"
        }
