import os
from dotenv import load_dotenv
from groq import Groq
import json

# Load environment variables
load_dotenv()
API_KEY = os.getenv("GROQ_API_KEY")

if not API_KEY:
    raise RuntimeError("GROQ_API_KEY not found in environment variables")

QUESTIONS_FILE = "questions.json"

# Initialize Groq client
client = Groq(api_key=API_KEY)

#------------------------------------
# Step 1- Question Generation Functions
#------------------------------------
def generate_questions(domain: str):
    print("generate_questions  recieved  domain  ",domain)
    """
    Ask LLM to generate 3 interview-style questions
    based on user's domain.
    """

    prompt = f"""
        You are an interviewer. The user's domain is: {domain}

        Ask the user **domain-specific questions** in three categories: skills, experience, and academic background.
        For each category, ask **2 easy, 2 medium, and 2 hard questions**.

        Definitions:
        - Easy: Basic, factual questions to assess general knowledge or familiarity.
        - Medium: Practical questions that require applying knowledge or experience in real scenarios.
        - Hard: Advanced questions that test problem-solving, critical thinking, or deep domain understanding.

        Requirements:
        1. Skills Questions: Focus on programming, frameworks, techniques, and tools relevant to the domain.
        2. Experience Questions: Focus on projects, collaboration, production usage, and problem-solving within the domain.
        3. Academic Background Questions: Focus on relevant courses, theory, research, and advanced concepts.

        Format:
        - Return only the questions, one per line.
        - Clearly label category and difficulty. Example format:
        Skills (Easy): ...
        Skills (Medium): ...
        Skills (Hard): ...
        Experience (Easy): ...
        Experience (Medium): ...
        Experience (Hard): ...
        Academic Background (Easy): ...
        Academic Background (Medium): ...
        Academic Background (Hard): ...

        Guidelines:
        - Medium questions should be **practical**, e.g., explain an approach, give an example, or describe a scenario you have handled.
        - Hard questions should be **challenging**, requiring reasoning, troubleshooting, optimization, or advanced domain knowledge.
    """

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )

    questions_json = response.choices[0].message.content.strip()

    return    questions_json

    # # Save to file
    # with open(QUESTIONS_FILE, "w", encoding="utf-8") as f:
    #     f.write(questions_json)
    # try:
    #     clean_json = extract_json(questions_json)
    #     return json.loads(clean_json)
    # except Exception as e:
    #     print("Failed generate_questions  . ",e)
    #     print("Raw LLM output:\n", questions_json)
    #     return   False

#------------------------------------
# Step 2- JSON Extractor
#------------------------------------
def extract_json(text: str):
    """
    Extract JSON object from LLM output safely.
    """
    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1:
        raise ValueError("No JSON object found in LLM response")

    return text[start:end + 1]

#------------------------------------
# Step 3- Interview Process Functions
#------------------------------------
def conduct_interview(questions: dict):
    """
    Ask questions from JSON and collect answers.
    """
    answers = {}
    for category, levels in questions.items():
        print(f"\n===== {category.upper()} =====")

        for level, qs in levels.items():
            for q in qs:
                print(f"\n[{level}] {q}")
                ans = input("> ").strip()
                answers[q] = ans if ans else "No response"

    return answers

#------------------------------------
# Step 4- Evaluation Functions
#------------------------------------
def evaluate_candidate(domain: str, responses: dict):
    """
    Send user's responses to LLM for role-fit evaluation.
    """
    formatted_answers = "\n".join(
        [f"Q: {q}\nA: {a}" for q, a in responses.items()]
    )

    prompt = f"""
You are a hiring assistant.

Candidate Domain:
{domain}

Interview Q&A:
{formatted_answers}

Evaluate the candidate using the following structure ONLY:

Role Fit Score: <number>/100

Summary:
<3–4 line professional summary>

Weaknesses:
- <point 1>
- <point 2>
- <point 3>

Feedback & Improvement Suggestions:
- <suggestion 1>
- <suggestion 2>
- <suggestion 3>

Guidelines:
- Give partial credit for short but correct answers.
- Penalize missing or incorrect reasoning.
- Be constructive and professional.
"""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )

    return response.choices[0].message.content.strip()

# ----------------------------
# Main Chat Flow
# ----------------------------
def startChat():
    domain = input("What is your major / area of interest / domain?\n> ")

    print("\nGenerating interview questions...\n")

    questions = generate_questions(domain)

    print("Interview started. Please answer the following questions.")

    answers = conduct_interview(questions)

    print("\nEvaluating your profile...\n")

    evaluation = evaluate_candidate(domain, answers)

    print("===== CANDIDATE EVALUATION =====")
    print(evaluation)
    print("================================")


def evaluate_candidate_in_api_old2(domain: str, answers: list[dict]):
    """
    LLM evaluates each Q/A independently and appends its_score.
    """

    prompt = f"""
        You are a hiring assistant  and  a candidate  domain  is  :  {domain} .
        the  candidate  interview  questions  and  answers  response  consists  of  list  of  dicts  as below  : {answers}.  
        Each dict has:
        - id
        - question
        - answer 

        Your TASK is  to : 
        - Evaluate each answer relevance, correctness, and clarity
        - Assign each answer a score between 0 and 10 according  to  your  evaluation( relevance, correctness, and clarity) and  add  that score as a new  key (its_score).

         
        Key  Note :
        please  return  your  response  very  carefully  according  to  what  your  task  is 
    """

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )

    print("evaluation  llm  response.choices[0]   ",response.choices[0])

    return response.choices[0].message.content


def evaluate_candidate_in_api(domain: str, answers: list[dict]):

    prompt = f"""
        You are an interview evaluator.

        Candidate domain: {domain}

        You will receive a JSON array of objects.
        Each object contains:
        - id
        - question
        - answer

        Your job:
        Score EACH answer from 0 to 10 based on:
        - relevance
        - correctness
        - clarity

        IMPORTANT RULES:
        - Return ONLY JSON
        - Do NOT return code
        - Do NOT return markdown
        - Do NOT explain anything
        - Do NOT wrap in ``` blocks
        - Do NOT create functions
        - Do NOT change id/question/answer
        - Only add: "its_score"

        Return the SAME array with the new field added.

        INPUT JSON:
        {answers}
        
        STRICT JSON REQUIREMENTS:
        - Use double quotes only
        - No single quotes anywhere
        - Must be valid JSON.parse compatible

    """

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": "You output strict JSON only."},
            {"role": "user", "content": prompt}
        ],
        temperature=0,
    )

    response_choices  =  response.choices[0].message.content
    print("response_choices  (response.choices[0].message.content)     ", response_choices)

    return response_choices


def evaluate_candidate_in_api_old3(domain: str, answers: list[dict]):
    """
    LLM evaluates each Q/A independently and appends its_score.
    """

    prompt = f"""
        You are a hiring assistant.

        Candidate Domain:
        {domain}

        You will receive a list of interview question-answer objects.

        Each object has:
        - id
        - question
        - answer

        TASK:
        For EACH object:
        - Evaluate the answer relevance, correctness, and clarity
        - Assign a score between 0 and 10 (decimals allowed)
        - Append a new field: "its_score"

        RULES:
        - Do NOT modify id, question, or answer
        - Do NOT add or remove objects
        - Return ONLY valid JSON
        - No explanation, no markdown, no extra text

        INPUT:
        {answers}

        OUTPUT FORMAT (example):
        [
        {{
            "id": 1,
            "question": "...",
            "answer": "...",
            "its_score": 7.5
        }}
        ]
    """

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )

    print("evaluation  llm  response.choices[0]   ",response.choices[0])

    return response.choices[0].message.content


#
def evaluate_candidate_in_api_old(domain: str, formatted_answers):
    """
    Send user's responses to LLM for role-fit evaluation.
    """ 

    prompt = f"""
        You are a hiring assistant.

        Candidate Domain:
        {domain}

        Interview Q&A:
        {formatted_answers}

        Evaluate the candidate using the following structure ONLY:

        Role Fit Score: <number>/100

        Summary:
        <3–4 line professional summary>

        Weaknesses:
        - <point 1>
        - <point 2>
        - <point 3>

        Feedback & Improvement Suggestions:
        - <suggestion 1>
        - <suggestion 2>
        - <suggestion 3>

        Guidelines:
        - Give partial credit for short but correct answers.
        - Penalize missing or incorrect reasoning.
        - Be constructive and professional.
    """

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )

    print("evaluation  llm  response.choices[0]   ",response.choices[0])

    return response.choices[0].message.content

if __name__ == "__main__":
    startChat()