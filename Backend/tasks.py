from  Backend.celery_worker import make_celery
from Quiz.saving_quiz import save_quiz
# from Quiz.quiz_generator import generate_quiz_from_pdf
from sqlalchemy import create_engine, text
# from Quiz.qa_evaluator import evaluate_saq
from datetime import datetime, timezone

import json
import  os
 
celery = make_celery()

engine = create_engine(

    "mysql+pymysql://wpflask:wpflaskpass@127.0.0.1:10005/local",

    pool_pre_ping=True,

)
 
# engine = create_engine(

#     "mysql+pymysql://wpflask:wpflaskpass@172.17.128.1:10005/local",

#     pool_pre_ping=True,

# )


@celery.task(bind=True)
def  Eval_quz_cel(self,quiz_id):
    print(f"[{datetime.now(timezone.utc)}] Eval_quz_cel {quiz_id}")

    from Quiz.qa_evaluator import evaluate_saq

    with engine.begin() as conn:
        questions = conn.execute(
            text("""
                SELECT *
                FROM wp_ai_questions
                WHERE quiz_id=:qid
            """),
            {"qid": quiz_id}
        ).fetchall()

        print("questions", len(questions))

        for q in questions:

            if not q.user_answer:
                continue

            eval_result = evaluate_saq(
                user_answer=q.user_answer,
                correct_answer=q.correct_answer,
                question=q.question
            )

            conn.execute(
                text("""
                    UPDATE wp_ai_questions
                    SET its_score=:score
                    WHERE id=:id
                """),
                {
                    "score": eval_result["score"],
                    "id": q.id
                }
            )

        conn.execute(
            text("""
                UPDATE wp_ai_quizzes
                SET evaluated=1
                WHERE id=:id
            """),
            {"id": quiz_id}
        )


def  store_james_quiz_wp_db(user_id,questions):

    print(f"[{datetime.now(timezone.utc)}] store_james_quiz_wp_db {user_id}")

    try: 

        if not questions:
            raise ValueError("No questions generated")

        with engine.begin() as conn:

            # 2️⃣ Get chatbot record
            chatbot = conn.execute(
                text("""
                    SELECT id 
                    FROM wp_chatbot_james 
                    WHERE user_id = :user_id
                """),
                {"user_id": user_id}
            ).fetchone()

            if not chatbot:
                raise ValueError("Chatbot record not found")

            chatbot_id = chatbot[0]

            # 3️⃣ Insert questions
            for q in questions:

                conn.execute(
                    text("""
                        INSERT INTO wp_chatbotjames_questions
                        (chatbotjames_id, question, section, mode, answer, its_score)
                        VALUES
                        (:chatbotjames_id, :question, :section, :mode, NULL, NULL)
                    """),
                    {
                        "chatbotjames_id": chatbot_id,
                        "question": q.get("question", ""),
                        "section": q.get("section", ""),
                        "mode": q.get("mode", "")
                    }
                )

            # 4️⃣ Mark quiz ready
            # conn.execute(
            #     text("""
            #         UPDATE wp_chatbot_james
            #         SET quiz_status = 'ready'
            #         WHERE id = :chatbot_id
            #     """),
            #     {"chatbot_id": chatbot_id}
            # )

        return {"status": "ready"}

    except Exception as e:

        # Mark failed
        # with engine.begin() as conn:
        #     conn.execute(
        #         text("""
        #             UPDATE wp_chatbot_james
        #             SET quiz_status = 'failed'
        #             WHERE user_id = :user_id
        #         """),
        #         {"user_id": user_id}
        #     )

        raise e
 
@celery.task(bind=True)
def quiz_gen(self, pdf_paths, user_id, MAX_QUESTIONS):
 
    print(f"[{datetime.now(timezone.utc)}] quiz_gen celery {user_id}")

    from Quiz.quiz_generator import generate_quiz_from_pdf
 
    quiz_data = generate_quiz_from_pdf(

        pdf_path=pdf_paths,

        max_questions=MAX_QUESTIONS,

        save=False

    )
 
    combined_quiz = quiz_data.get("quiz", [])
 
    if not combined_quiz:

        raise ValueError("No quiz generated")
 
    with engine.begin() as conn:
 
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
 
    return {"quiz_id": quiz_id}

 