from celery import Celery
from Quiz.saving_quiz import save_quiz
from Quiz.quiz_generator import generate_quiz_from_pdf
from  sqlalchemy   import  create_engine
import json
from datetime import datetime, timezone
from sqlalchemy import text
engine = create_engine(
    "mysql+pymysql://wpflask:wpflaskpass@172.17.128.1:10005/local",
    pool_pre_ping=True,
)

# Initialize Celery
celery_app = Celery(
    "tasks",
    broker="redis://172.17.128.1:6379/0",
    backend="redis://172.17.128.1:6379/0"
)

def make_quiz_key(pdf_list):
    return "_".join(
        sorted(os.path.basename(p) for p in pdf_list)
    )

# Example task
@celery_app.task
def   quiz_gen(pdf_paths, user_id,MAX_QUESTIONS):
    # try:

        print(f"[{datetime.now(timezone.utc)}] quiz_gen  celery  {user_id}")
 
        quiz_data = generate_quiz_from_pdf(
            pdf_path=pdf_paths,
            max_questions=MAX_QUESTIONS,
            save=False
        )
 
       
        combined_quiz = quiz_data.get("quiz", [])
 
        if not combined_quiz:
            print("No quiz generated")
            raise ValueError("No quiz generated") 
 
        with engine.begin() as conn:
 
            # 1️⃣ Insert quiz
            result = conn.execute(
                text("""
                    INSERT INTO wp_ai_quizzes
                    (pdf_names, user_id, quiz_attempted, evaluated, evaluation_picked)
                    VALUES (:pdf_names, :user_id, 0, 0, 0)
                """),
                {
                    "pdf_names": "Uploaded PDFs Quiz",
                    "user_id": user_id
                }
            )
 
            quiz_id = result.lastrowid
 
 
            print("quiz_id   ",quiz_id)
 
            # 2️⃣ Insert questions
            for q in combined_quiz:
 
                options_json = json.dumps(q["options"]) if "options" in q else None
                correct_answer = q.get("correct_answer") or q.get("answer")
 
                conn.execute(
                    text("""
                        INSERT INTO wp_ai_questions
                        (quiz_id, question, type, options_json,
                         correct_answer, explanation, source_pdf, source_cluster)
                        VALUES
                        (:quiz_id, :question, :type, :options_json,
                         :correct_answer, :explanation, :source_pdf, :source_cluster)
                    """),
                    {
                        "quiz_id": quiz_id,
                        "question": q["question"],
                        "type": q["type"],
                        "options_json": options_json,
                        "correct_answer": correct_answer,
                        "explanation": q.get("explanation", ""),
                        "source_pdf": q.get("source_pdf", ""),
                        "source_cluster": q.get("source_cluster", "")
                    }
                )


        for idx, q in enumerate(combined_quiz):
            if "id" not in q or not q["id"]:
                q["id"] = f"q_{idx}"

        quiz_key = make_quiz_key(pdf_paths)
        save_quiz(quiz_key, combined_quiz)
 
        print("succeded  quiz   save  from  flask celery  into  wordpress")
 
    # except Exception as e:
    #     print("Exception in upload_pdfs:", e) 
    #     raise ValueError("Exception in upload_pdfs") 