from flask import Flask, request, jsonify
from PyPDF2 import PdfReader
from flask_cors import CORS
import os
import json
import random
import uuid
import socket
from   apscheduler.schedulers.background  import   BackgroundScheduler
from datetime import datetime, timezone
from  decimal    import  Decimal
import  math
# ----------------------------
# Project imports
# ----------------------------
# sys.path.append(r"C:\BLS\EvalAI8\Quiz")
from Quiz.quiz_generator import generate_quiz_from_pdf
from Quiz.saving_quiz import save_quiz, save_user_attempt, load_existing_quiz
from Quiz.qa_evaluator import evaluate_saq
from Backend.initials import is_english_file, is_pdf_file, is_invalid_file


from   Backend.config   import  Config
from  Backend.extensions  import  db
from  Backend.models.candidate_models   import  CandidateResearch,  CandidateEvalAI  ,  CandidateQuizQuestion
# ======================================================
# FLASK APP SETUP
# ======================================================
app = Flask(__name__)
CORS(app)

app.config.from_object(Config)

db.init_app(app) 

FLASK_ROOT = os.path.dirname(os.path.abspath(__file__))  # D:\BLS_Main\Live_dev\AI-Quiz-Generator-Microservice\Backend
DJANGO_ROOT = os.path.abspath(os.path.join(FLASK_ROOT, "../../IAE-CRM"))  # resolves ..\.. properly
RESEARCH_FILES_ROOT = os.path.join(DJANGO_ROOT, "static", "Others", "Candidates", "Researches_Docs")
 
QUIZ_JSON_FOLDER = os.path.join(FLASK_ROOT, "Quiz/quizzes") 


@app.route("/candidate/<int:candidate_id>")
def get_candidate_records(candidate_id):
    # Fetch all researches for this candidate
    researches = CandidateResearch.query.filter_by(candidate_id=candidate_id).all()
    
    # Fetch the CandidateEvalAI record (one-to-one)
    eval_ai = CandidateEvalAI.query.filter_by(candidate_id=candidate_id).first()

    # Prepare response
    response = {
        "candidate_id": candidate_id,
        "researches": [
            {
                "id": r.id,
                "title": r.title,
                "journal": r.journal,
                "year": r.year,
                "file": r.file,
                "description": r.description,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            }
            for r in researches
        ],
        "eval_ai": {
            "id": eval_ai.id,
            "to_pickup": eval_ai.to_pickup,
            "picked_up": eval_ai.picked_up,
            "completed": eval_ai.completed,
            "progress_error_occured": eval_ai.progress_error_occured,
            "created_at": eval_ai.created_at.isoformat() if eval_ai.created_at else None,
            "updated_at": eval_ai.updated_at.isoformat() if eval_ai.updated_at else None,
        } if eval_ai else None
    }

    return jsonify(response) 

@app.route("/test-db")
def test_db():
    records = CandidateResearch.query.all()

    return {
        "count": len(records),
        "titles": [r.title for r in records]
    }


# UPLOAD_FOLDER = r"C:\BLS\EvalAI8\Uploads"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER =  os.path.join(BASE_DIR, "../Uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
MAX_QUESTIONS = 20

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Connect to a local network address instead to avoid firewall issues
        s.connect(("1.1.1.1", 443))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def make_quiz_key(pdf_list):
    return "_".join(
        sorted(os.path.basename(p) for p in pdf_list)
    )



# ======================================================
# 1️⃣ UPLOAD PDFs & GENERATE QUIZ
# ======================================================
@app.route("/upload_pdfs/", methods=["POST"])
def upload_pdfs():
    if "files" not in request.files:
        return jsonify({"error": "No files part in request"}), 400

    files = request.files.getlist("files")
    if not files:
        return jsonify({"error": "No files uploaded"}), 400

    pdf_paths = []

    for file in files:
        # 1️⃣ PDF check
        if not is_pdf_file(file):
            return jsonify({
                "error": "invalid_file",
                "message": f"File '{file.filename}' is not a valid PDF",
                "files": [file.filename]
            }), 200

        pdf_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(pdf_path)

        # ✅ 1.5️⃣ Empty / corrupt PDF check (BEST placement)
        if is_invalid_file(pdf_path):
            return jsonify({
                "error": "invalid_file",
                "message": f"File '{file.filename}' is invalid",
                "files": [file.filename]
            }), 200

        # 3️⃣ English check (using new detector class)
        if not is_english_file(file):
            print("❌ Non-English file detected:", file.filename)
            return jsonify({
                "error": "non_english_file",
                "message": f"File '{file.filename}' is not in English",
                "files": [file.filename]
            }), 200
        print("✅ English file confirmed:", file.filename)
        pdf_paths.append(pdf_path)

    # ======================================================
    # Process ALL PDFs together → global clusters → single LLM call
    # ======================================================
    quiz_data = generate_quiz_from_pdf(
        pdf_path=pdf_paths,
        max_questions=MAX_QUESTIONS,
        save=False
    )

    combined_quiz = quiz_data.get("quiz", [])

    for idx, q in enumerate(combined_quiz):
        if "id" not in q or not q["id"]:
            q["id"] = f"q_{idx}"

    quiz_key = make_quiz_key(pdf_paths)
    save_quiz(quiz_key, combined_quiz)

    return jsonify({
        "total_questions": len(combined_quiz),
        "mcq_count": sum(1 for q in combined_quiz if q["type"] == "MCQ"),
        "saq_count": sum(1 for q in combined_quiz if q["type"] == "SAQ"),
        "quiz": combined_quiz
    })

# ======================================================
# 2️⃣ SUBMIT QUIZ (MCQ AUTO, SAQ STORED)
# ======================================================
@app.route("/submit_quiz/", methods=["POST"])
def submit_quiz():
    print("Submitting Quiz...")
    try:
        data = request.get_json()
        print("Received data:", data)

        pdf_names = data.get("pdf_names")
        mcq_answers = data.get("mcq_answers", {})
        saq_answers = data.get("saq_answers", {})
        user_id = str(uuid.uuid4())

        if not pdf_names:
            return jsonify({"error": "Missing pdf_names"}), 400

        # --------------------------------------------------
        # Load saved quiz (PASS PDF NAMES, NOT KEY)
        # --------------------------------------------------
        saved_quiz_data = load_existing_quiz(pdf_names)
        print("entering if else block for saved quiz data")
        if not saved_quiz_data or not saved_quiz_data.get("quiz"):
            print("❌ Saved quiz not found or empty for PDFs:", saved_quiz_data)
            return jsonify({
                "error": "Saved quiz not found for given PDFs",
                "pdf_names": pdf_names
            }), 404
        else:
            print("✅ Everything was fine:", pdf_names)
        saved_quiz = saved_quiz_data["quiz"]

        # =====================
        # Evaluation
        # =====================
        evaluated_questions = []
        total_correct = 0
        total_questions = 0

        for idx, q in enumerate(saved_quiz):
            if not isinstance(q, dict):
                continue

            qid = q.get("id") or f"q_{idx}"
            question_text = q.get("question", "")
            qtype = q.get("type")
            explanation = q.get("explanation", "")

            total_questions += 1

            # ---------- MCQ ----------
            if qtype == "MCQ":
                user_answer = mcq_answers.get(qid, "")
                correct_answer = q.get("correct_answer", "")
                options = q.get("options", {})

                is_correct = user_answer == correct_answer
                if is_correct:
                    total_correct += 1

                evaluated_questions.append({
                    "question_id": qid,
                    "question": question_text,
                    "type": "MCQ",
                    "options": options,
                    "correct_answer": correct_answer,
                    "user_answer": user_answer,
                    "similarity": None,
                    "is_correct": is_correct,
                    "explanation": explanation
                })

            # ---------- SAQ ----------
            elif qtype == "SAQ":
                user_answer = saq_answers.get(qid, "")
                correct_answer = q.get("answer", "")

                # 🔹 NEW: pass question_text
                eval_result = evaluate_saq(
                    user_answer=user_answer,
                    correct_answer=correct_answer,
                    question=question_text
                )

                is_correct = eval_result["is_correct"]

                if is_correct:
                    total_correct += 1

                evaluated_questions.append({
                    "question_id": qid,
                    "question": question_text,
                    "type": "SAQ",
                    "options": None,
                    "correct_answer": correct_answer,
                    "user_answer": user_answer,

                    # 🔹 similarity no longer exists → set to None
                    "similarity": None,

                    "is_correct": is_correct,

                    # 🔹 Better explanation from LLM if available
                    "explanation": eval_result.get("reason", explanation),

                    # 🔹 OPTIONAL but useful (won't break frontend)
                    "score": eval_result.get("score"),
                    "verdict": eval_result.get("verdict")
                })

        # =====================
        # Save Attempt
        # =====================
        attempt_record = {
            "total_questions": total_questions,
            "total_correct": total_correct,
            "evaluated_quiz": evaluated_questions
        }

        save_user_attempt(user_id, pdf_names, attempt_record)

        return jsonify({
            "message": "Quiz submitted successfully",
            "total_questions": total_questions,
            "total_correct": total_correct,
            "evaluated_quiz": evaluated_questions
        })

    except Exception as e:
        print("❌ submit_quiz error:", e)
        return jsonify({"error": str(e)}), 500


def save_quiz_json_to_db(candidate_id, json_file_path,quiz_id):
    """
    Reads a generated quiz JSON file and saves it into DB for the given candidate.
    """
    if not os.path.exists(json_file_path):
        print(f"Quiz JSON file does not exist: {json_file_path}")
        return

    # Read JSON file
    with open(json_file_path, "r", encoding="utf-8") as f:
        quiz_data = json.load(f)

    # Get pdf_names
    pdf_names = quiz_data.get("pdf_names", "Unknown_Quiz")

     

    # Iterate over questions
    questions = quiz_data.get("quiz", [])
    questions_count =  0
    for q in questions:
        questions_count =  questions_count  +  1

        q_type = q.get("type", "").upper()

        # ---------- MCQ handling ----------
        options_dict = None
        correct_answer = None

        if q_type == "MCQ":
            options_raw = q.get("options", {})

            # store dict as JSON string in TextField
            if isinstance(options_raw, dict):
                options_dict = json.dumps(options_raw)
            else:
                options_dict = None

            correct_answer = q.get("correct_answer")


        question = CandidateQuizQuestion(
            quiz_id=quiz_id,
            question_text=q.get("question", ""),
            answer_text=q.get("answer", ""),
            explanation_text=q.get("explanation", ""),
            question_type=q.get("type", ""),
            source_pdf=q.get("source_pdf", ""),
            options=options_dict,
            correct_answer=correct_answer
        )
        db.session.add(question)

    # Commit all questions
    db.session.commit()
    print(f"Saved quiz '{pdf_names}' with {len(questions)} questions for candidate_id {candidate_id}")

    return   questions_count



 
def   sched_score_saq_questions(quiz_id):

    print("sched_score_saq_questions  quiz_id ",quiz_id)

    saq_questions = CandidateQuizQuestion.query.filter_by(
        quiz_id=quiz_id,
        question_type="SAQ"
    ).all()

    total_obt_score  =  0.00
 

    for q in saq_questions:

        if not q.user_answer:
            continue

        eval_result = evaluate_saq(
            user_answer=q.user_answer,
            correct_answer=q.answer_text,
            question=q.question_text
        )
        eval_result_score =  eval_result["score"] 

        total_obt_score =  total_obt_score  +    eval_result_score

        q.its_score = eval_result_score

    db.session.commit()

    return  total_obt_score



# ----------------- Task Function -----------------
def process_candidate_eval():
    with app.app_context():  # 🔑 Important: provides Flask context for DB operations
        print(f"[{datetime.now(timezone.utc)}] Running  process_candidate_eval...")

        # Step 1: Get CandidateEvalAI records to process
        pending_records = CandidateEvalAI.query.filter_by(
            to_pickup=True,
            picked_up=False,
            completed=False
        ).all()

        evaluation_pending_records = CandidateEvalAI.query.filter_by(
            candidate_attempted=True,
            evaluation_picked_up=False,
            evaluation_completed  = False
        ).all()

        if  evaluation_pending_records:

            for  record in  evaluation_pending_records:
                try: 
                    record.evaluation_picked_up = True
                    db.session.commit()
                    print(f"Evaluation  Picked up  and  updating  picked_up  for  candidate  id  {record.candidate_id}   and   CandidateEvalAI id: {record.id}")
                except Exception as e:
                    print(f"Evaluation  Erro   updating  picked_up  for  candidate  id  {record.candidate_id}   and    CandidateEvalAI id {record.id}: {str(e)}")
                    record.evaluation_progress_error_occured = True
                    db.session.commit() 

            for  record  in  evaluation_pending_records:
                try:
                    total_obt_score =  sched_score_saq_questions(record.id)
                    eva_obt_score  =   Decimal(record.obt_score)  + Decimal(total_obt_score)
                    record.obt_score =   eva_obt_score
                    eval_obt_perc  =      Decimal((math.trunc((eva_obt_score/ record.tot_score) * 100) / 100))  *  Decimal("100")
                    # print("bot_obt_perc   as  here  ",bot_obt_perc  ,  "   type   ",type(bot_obt_perc))
                    if   Decimal(eval_obt_perc)  >  Decimal("70"):
                        record.candidate_passed  =  True 


                    eval_obt_perc = str(eval_obt_perc) + "%"
                    record.obt_perc  =  eval_obt_perc
                    record.evaluation_completed  =  True
                    db.session.commit() 
                except Exception as e:
                    print(f"Evaluation  Error  in  processing  for  candidate  id  {record.candidate_id}   and  CandidateEvalAI id {record.id}: {str(e)}")
                    record.evaluation_progress_error_occured = True
                    record.evaluation_picked_up  =  False
                    db.session.commit() 
        else:
            print("No   evaluation_pending_records")

        if  pending_records:

            for record in pending_records:
                try: 
                    record.picked_up = True
                    db.session.commit()
                    print(f"Picked up  and  updating  picked_up  for  candidate  id  {record.candidate_id}   and   CandidateEvalAI id: {record.id}")
                except Exception as e:
                    print(f"Erro   updating  picked_up  for  candidate  id  {record.candidate_id}   and    CandidateEvalAI id {record.id}: {str(e)}")
                    record.progress_error_occured = True
                    db.session.commit() 
            

            for record in pending_records:
                try: 

                    # Step 3: Fetch related CandidateResearch records
                    candidate_id = record.candidate_id
                    research_records = CandidateResearch.query.filter_by(candidate_id=candidate_id).all()
                    if   research_records: 

                        pdf_paths =  []

                        for research in research_records:
                            file_name = os.path.basename(research.file)
                            file_path = os.path.join(RESEARCH_FILES_ROOT, file_name)
                            file_path = os.path.abspath(file_path)  # ✅ ensure absolute path
                            print(f"Absolute PDF path: {file_path}")

                            if os.path.isfile(file_path) and file_path.lower().endswith(".pdf"):
                                print(f"Processing PDF: {file_path}")
                                pdf_paths.append(file_path)
                            else:
                                print(f"File does not exist or not a PDF: {file_path}") 
                             

                        print("pdf_paths  ",pdf_paths)

                        
                        

                        # ======================================================
                        # Process ALL PDFs together → global clusters → single LLM call
                        # ======================================================
                        quiz_data = generate_quiz_from_pdf(
                            pdf_path=pdf_paths,
                            max_questions=MAX_QUESTIONS,
                            save=False
                        )

                        combined_quiz = quiz_data.get("quiz", [])

                        for idx, q in enumerate(combined_quiz):
                            if "id" not in q or not q["id"]:
                                q["id"] = f"q_{idx}"

                        quiz_key = make_quiz_key(pdf_paths)
                        json_file_name = save_quiz(quiz_key, combined_quiz)

                        print("json_file_name  ",json_file_name)

                        json_file_path = os.path.join(QUIZ_JSON_FOLDER, json_file_name)

                        questions_count = save_quiz_json_to_db(candidate_id, json_file_path,record.id)
                        record.tot_score =   Decimal(questions_count  *  10)
                        record.completed  =  True
                        db.session.commit() 
                    else:
                        print(f"No  research  records   for  candidate  id  {record.candidate_id}   and  CandidateEvalAI id {record.id}")

                    print(f"Success  in  processing  for  candidate  id  {record.candidate_id}   and  CandidateEvalAI id {record.id}")

                except Exception as e:
                    print(f"Error  in  processing  for  candidate  id  {record.candidate_id}   and  CandidateEvalAI id {record.id}: {str(e)}")
                    record.progress_error_occured = True
                    record.picked_up  =  False
                    db.session.commit() 
        else:
            print("no  pending_records")

# ----------------- Scheduler Setup -----------------
scheduler = BackgroundScheduler()
scheduler.add_job(func=process_candidate_eval, trigger="interval", minutes=3)
scheduler.start()

# Shut down scheduler when exiting Flask
import atexit
atexit.register(lambda: scheduler.shutdown())


# ======================================================
if __name__ == "__main__":
    host_ip = get_local_ip()
    print(f"  [{datetime.now(timezone.utc)}]  🚀 EvalAI_8 application running on http://{host_ip}:8005")
 
    app.run(
        host=host_ip,
        port=8005,
        debug=True
    )