# quiz_generator.py (CLUSTER-BASED VERSION - NO MIXING)
import os
from groq import Groq
from dotenv import load_dotenv
import random
import textwrap
from collections import defaultdict
import time

# ----------------------------
# Correct import path
# ----------------------------
#sys.path.append(r"C:\BLS\EvalAI8\Cluster")
from Cluster.cluster import get_clusters
from Quiz.saving_quiz import parse_quiz, save_quiz, load_existing_quiz

# ----------------------------
# Load API Key
# ----------------------------
load_dotenv()
API_KEY = os.getenv("GROQ_API_KEY")
if API_KEY is None:
    raise ValueError("GROQ_API_KEY environment variable not set")

client = Groq(api_key=API_KEY)

# ============================================================
# API Call with Retry Logic
# ============================================================
def call_groq_with_retry(prompt, model="llama-3.1-8b-instant", temperature=0.3, max_tokens=2500, max_retries=3):
    """
    Make Groq API call with exponential backoff retry logic.
    Handles rate limits and transient errors.
    """
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
            
        except Exception as e:
            error_msg = str(e)
            
            # Check if it's a rate limit error
            if "rate" in error_msg.lower() or "429" in error_msg:
                wait_time = (2 ** attempt) * 2  # Exponential backoff: 2s, 4s, 8s
                print(f"⚠️ Rate limit hit. Waiting {wait_time}s before retry {attempt + 1}/{max_retries}...")
                time.sleep(wait_time)
                
            # Check if it's an auth error
            elif "401" in error_msg or "invalid" in error_msg.lower():
                print(f"❌ Authentication error: {error_msg}")
                raise  # Don't retry auth errors
                
            # Other errors
            else:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"⚠️ API error: {error_msg}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    print(f"❌ Failed after {max_retries} attempts: {error_msg}")
                    raise
    
    raise Exception(f"Failed to complete API call after {max_retries} retries")

# ============================================================
# 🔥 NEW: Format Single Cluster for Prompt
# ============================================================
def format_cluster_for_prompt(theme: str, keywords: list, pdf_name: str) -> str:
    """Format a single cluster into readable text for LLM."""
    formatted = f"SOURCE DOCUMENT: {pdf_name}\n"
    formatted += f"TOPIC/THEME: {theme}\n"
    formatted += "KEYWORDS:\n"
    for kw in keywords:
        formatted += f"  • {kw}\n"
    return formatted.strip()

# ============================================================
# 🔥 NEW: Generate Questions from Single Cluster
# ============================================================
def generate_questions_from_cluster(cluster_info: dict, num_saq: int, num_mcq: int):
    print(f" generate_questions_from_cluster  Asad  23/01/26  ➡ Generating {num_saq} SAQs and {num_mcq} MCQs ")
    """
    Generate questions from a SINGLE cluster only.
    No mixing with other clusters.
    """
    theme = cluster_info['theme']
    keywords = cluster_info['keywords']
    pdf_name = cluster_info['pdf_name']
    
    context_text = format_cluster_for_prompt(theme, keywords, pdf_name)
    
    # Generate SAQs if needed
    saq_list = []
    if num_saq > 0:
        saq_prompt = f"""
You are a highly skilled Quiz Generation expert with strong domain knowledge.

Your task is to generate up to {num_saq} Short Answer Questions (SAQs) from the provided cluster.

🚨 CRITICAL REQUIREMENTS:
- Generate questions ONLY from the keywords and topic provided below
- Do NOT mix information from other topics or documents
- Use the keywords ONLY to identify the topic
- Do not use keywords or pdf as single source of truth
- Use you own verified knowledge base to generate high-quality questions from the keywords
- If a keyword seems ambiguous, poorly defined, illogical or incorrect, then do NOT use it to generate questions
- Each question must be distinct and test different aspects
- You can generate at most {num_saq} questions
- If there is not enough information to create {num_saq} quality SAQs, generate fewer
- Do not use keywords in the question or answer directly

QUESTION QUALITY RULES:
- Questions must test conceptual understanding and real-world knowledge
- Avoid trivial or purely definitional questions
- Each question must be unique
- Questions should be appropriate for the topic complexity

ANSWER RULES:
- Answers must be factually correct
- Answers must be concise (1–2 lines)
- Provide a short explanation

CLUSTER INFORMATION:
{context_text}

OUTPUT FORMAT (STRICT):
Q1. <Question text>
Answer: <Correct answer>
Explanation: <Short explanation>

Q2. <Question text>
Answer: <Correct answer>
Explanation: <Short explanation>
"""
        
        print(f"    🤖 Generating {num_saq} SAQs from cluster '{theme}'...")
        saq_text = call_groq_with_retry(
            prompt=saq_prompt,
            model="llama-3.1-8b-instant",
            temperature=0.3,
            max_tokens=2000,
            max_retries=3
        )
        
        saq_list = parse_quiz(saq_text)
        for q in saq_list:
            q["type"] = "SAQ"
            q["source_cluster"] = theme
            q["source_pdf"] = pdf_name
    
    # Small delay between calls
    if num_saq > 0 and num_mcq > 0:
        time.sleep(1)
    
    # Generate MCQs if needed
    mcq_list = []
    if num_mcq > 0:
        mcq_prompt = f"""
You are an expert-level Quiz generator and subject-matter expert.

Your task is to generate up to {num_mcq} Multiple Choice Questions (MCQs) from the provided cluster.

🚨 CRITICAL REQUIREMENTS:
- Generate questions ONLY from the keywords and topic provided below
- Do NOT mix information from other topics or documents
- Use the keywords ONLY to identify the topic
- Do not use keywords or pdf as single source of truth
- Use you own verified knowledge base to generate high-quality questions from the keywords
- If a keyword seems ambiguous, poorly defined, illogical or incorrect, then do NOT use it to generate questions
- All questions must be distinct and test different aspects
- Do not use keywords in the question or options directly

MCQ CONSTRAINTS:
1. You can generate atmost up to {num_mcq} MCQs
2. Each MCQ should have exactly 4 options (A, B, C, D)
3. Each MCQ MUST have EXACTLY ONE correct option
4. The correct option must be fully correct and unambiguous and remaining all 3 options should be clearly incorrect. (Critical)
5. All incorrect options must be clearly wrong and must not be partially correct or acceptable under any circumstances. (Very Important for every mcq)
6. Provide a concise explanation
7. If there is not enough information to create {num_mcq} quality MCQs, generate fewer
CLUSTER INFORMATION:
{context_text}

STRICT OUTPUT FORMAT:
Q1. <Question text>
   A) <Option A>
   B) <Option B>
   C) <Option C>
   D) <Option D>
Correct Answer: <A/B/C/D>
Explanation: <2–3 line explanation>

Q2. ...
"""
        
        print(f"    🤖 Generating {num_mcq} MCQs from cluster '{theme}'...")
        mcq_text = call_groq_with_retry(
            prompt=mcq_prompt,
            model="llama-3.1-8b-instant",
            temperature=0.2,
            max_tokens=2000,
            max_retries=3
        )
        
        mcq_list = parse_quiz(mcq_text)
        for q in mcq_list:
            q["type"] = "MCQ"
            q["source_cluster"] = theme
            q["source_pdf"] = pdf_name
    
    return saq_list + mcq_list

# ============================================================
# Clean & Validate Parsed Questions
# ============================================================
def clean_parsed_questions(questions):
    """Remove empty/untitled questions, invalid MCQs, duplicate questions."""
    cleaned = []
    banned_phrases = [
        "based on the provided context",
        "i will generate",
        "following questions",
        "here are"
    ]

    for q in questions:
        question_text = q.get("question", "").strip()
        if not question_text:
            continue
        if any(bp in question_text.lower() for bp in banned_phrases):
            continue

        # MCQ validation
        if q.get("type") == "MCQ":
            options = q.get("options", {})
            if len(options) < 4 or any(not str(opt).strip() for opt in options.values()):
                continue
            if not q.get("correct_answer"):
                continue
        # SAQ validation
        else:
            if not q.get("answer"):
                continue

        # Clean explanation
        if "explanation" in q and q["explanation"]:
            q["explanation"] = " ".join(q["explanation"].split())

        cleaned.append(q)

    # Deduplicate questions by normalized text
    seen = set()
    final_cleaned = []
    for q in cleaned:
        key = q['question'].strip().lower()
        if key not in seen:
            final_cleaned.append(q)
            seen.add(key)

    return final_cleaned

# ============================================================
# 🔥 NEW: Distribute Questions Across Clusters
# ============================================================
def distribute_questions_across_clusters(all_clusters_info, max_questions, min_per_cluster=2, max_per_cluster=None):
    """
    Distribute questions more fairly across clusters.
    - Ensures each cluster gets at least `min_per_cluster` questions.
    - Caps dominant clusters if `max_per_cluster` is set.
    """
    total_keywords = sum(len(c['keywords']) for c in all_clusters_info)
    if total_keywords == 0 or len(all_clusters_info) == 0:
        return []

    # Step 1: initial proportional allocation
    distribution = []
    total_saq = int(max_questions * 0.7)
    total_mcq = max_questions - total_saq

    for c in all_clusters_info:
        weight = len(c['keywords']) / total_keywords
        saq_for_cluster = max(min_per_cluster, round(total_saq * weight))
        mcq_for_cluster = max(0, round(total_mcq * weight))

        # Apply max cap if needed
        if max_per_cluster:
            saq_for_cluster = min(saq_for_cluster, max_per_cluster)
            mcq_for_cluster = min(mcq_for_cluster, max_per_cluster)

        distribution.append({
            'cluster_info': c,
            'num_saq': saq_for_cluster,
            'num_mcq': mcq_for_cluster
        })

    # Step 2: Adjust if we allocated too many questions
    total_allocated = sum(d['num_saq'] + d['num_mcq'] for d in distribution)
    remaining = max_questions - total_allocated

    if remaining > 0:
        # Round-robin distribute leftover questions to clusters
        idx = 0
        while remaining > 0:
            d = distribution[idx % len(distribution)]
            d['num_saq'] += 1
            remaining -= 1
            idx += 1

    elif remaining < 0:
        # Scale down proportionally
        scale = max_questions / total_allocated
        for d in distribution:
            d['num_saq'] = max(min_per_cluster, round(d['num_saq'] * scale))
            d['num_mcq'] = max(0, round(d['num_mcq'] * scale))

    return distribution

# ============================================================
# 🔥 NEW: Full PDF → Quiz Pipeline (Cluster-Based)
# ============================================================
def generate_quiz_from_pdf(pdf_path, max_questions=20, save=True):
    # ----------------------------------
    # Normalize input
    # ----------------------------------
    print("🔥 generate_quiz_from_pdf CALLED WITH:", pdf_path)
    pdf_paths = pdf_path if isinstance(pdf_path, list) else [pdf_path]
    num_pdfs = len(pdf_paths)

    print(f"\n📚 Processing {num_pdfs} PDF(s):")
    for i, p in enumerate(pdf_paths, 1):
        print(f"  {i}. {os.path.basename(p)}")

    # Check cache
    existing = load_existing_quiz(pdf_paths)
    if existing is not None:
        print("✅ Using cached quiz")
        return existing

    # ----------------------------------
    # Step 1: Extract Clusters from Each PDF
    # ----------------------------------
    print("\n🔍 Step 1: Extracting keywords and clustering each PDF...")
    all_clusters_info = []
    per_pdf_clusters = {}

    for idx, path in enumerate(pdf_paths, 1):
        pdf_name = os.path.basename(path).replace('.pdf', '')
        print(f"\n  Processing PDF {idx}/{num_pdfs}: {pdf_name}")
        
        clusters = get_clusters(path)
        per_pdf_clusters[path] = clusters
        
        # Store each cluster with metadata
        for theme, keywords in clusters.items():
            all_clusters_info.append({
                'theme': theme,
                'keywords': keywords,
                'pdf_name': pdf_name,
                'pdf_path': path
            })
            print(f"    ✓ Cluster '{theme}': {len(keywords)} keywords")
    
    total_clusters = len(all_clusters_info)
    print(f"\n  📊 Total clusters across all PDFs: {total_clusters}")

    # ----------------------------------
    # Step 2: Distribute Questions Across Clusters
    # ----------------------------------
    print(f"\n📝 Step 2: Distributing {max_questions} questions across {total_clusters} clusters...")
    
    question_distribution = distribute_questions_across_clusters(all_clusters_info, max_questions)
    
    for d in question_distribution:
        cluster = d['cluster_info']
        print(f"  • {cluster['pdf_name']} - {cluster['theme']}: {d['num_saq']} SAQs, {d['num_mcq']} MCQs")

    # ----------------------------------
    # Step 3: Generate Questions Per Cluster
    # ----------------------------------
    print(f"\n🎯 Step 3: Generating questions from each cluster independently...")
    
    all_questions = []
    
    for idx, d in enumerate(question_distribution, 1):
        cluster_info = d['cluster_info']
        num_saq = d['num_saq']
        num_mcq = d['num_mcq']

        print("nahi    ja  rhy  ",num_saq,num_mcq)
        
        if num_saq == 0 and num_mcq == 0:
            continue
        
        print(f"\n  [{idx}/{len(question_distribution)}] Cluster: {cluster_info['theme']} ({cluster_info['pdf_name']})")
        
        questions = generate_questions_from_cluster(cluster_info, num_saq, num_mcq)
        questions = clean_parsed_questions(questions)
        
        print(f"    ✓ Generated {len(questions)} valid questions")
        all_questions.extend(questions)
        
        # Delay between clusters to avoid rate limits
        if idx < len(question_distribution):
            time.sleep(1.5)
    
    # ----------------------------------
    # Step 4: Shuffle and Finalize
    # ----------------------------------
    print(f"\n🔀 Step 4: Shuffling questions...")
    random.shuffle(all_questions)
    
    # Add question IDs
    for idx, q in enumerate(all_questions):
        if "id" not in q or not q["id"]:
            q["id"] = f"q_{idx}"
    
    mcq_count = sum(1 for q in all_questions if q.get("type") == "MCQ")
    saq_count = sum(1 for q in all_questions if q.get("type") == "SAQ")
    
    print(f"\n✅ Final Quiz Summary:")
    print(f"  • Total Questions: {len(all_questions)}")
    print(f"  • SAQs: {saq_count}")
    print(f"  • MCQs: {mcq_count}")
    
    # Show distribution by PDF
    pdf_distribution = defaultdict(int)
    for q in all_questions:
        pdf_distribution[q.get('source_pdf', 'Unknown')] += 1
    
    print(f"\n  📊 Questions per PDF:")
    for pdf_name, count in pdf_distribution.items():
        print(f"    • {pdf_name}: {count} questions")

    # ----------------------------------
    # Step 5: Save
    # ----------------------------------
    if save:
        print("\n💾 Step 5: Saving quiz...")
        save_quiz(pdf_paths, all_questions)

    return {
        "pdf_path": pdf_paths,
        "clusters": per_pdf_clusters,
        "quiz": all_questions
    }


# ============================================================
# Pretty Print Quiz
# ============================================================
def display_quiz_pretty(quiz):
    print("\n==================== QUIZ ====================\n")
    wrap_width = 100
    for idx, q in enumerate(quiz["quiz"], start=1):
        # Show source info
        source_pdf = q.get('source_pdf', 'Unknown')
        source_cluster = q.get('source_cluster', 'Unknown')
        print(f"[Source: {source_pdf} - {source_cluster}]")
        
        print(f"Q{idx}. {q['question']}")
        if 'options' in q:
            for opt in ["A","B","C","D"]:
                print(f"   {opt}) {textwrap.fill(q['options'][opt], wrap_width, subsequent_indent='      ')}")
            print(f"Correct Answer: {q['correct_answer']}")
        else:
            print(f"Answer: {textwrap.fill(q['answer'], wrap_width, subsequent_indent='   ')}")
        if 'explanation' in q:
            print(f"Explanation: {textwrap.fill(q['explanation'], wrap_width, subsequent_indent='   ')}")
        print("\n---------------------------------------------\n")

# ============================================================
# Test Entry Point
# ============================================================
if __name__ == "__main__":
    test_pdfs = [
        r"C:\BLS\EvalAI8\Uploads\AI_in_Healthcare_Paper.pdf",
        r"C:\BLS\EvalAI8\Uploads\Transformer_attention_3.pdf"
    ]
    max_questions = 20
    quiz_data = generate_quiz_from_pdf(test_pdfs, max_questions, save=True)
    display_quiz_pretty(quiz_data)