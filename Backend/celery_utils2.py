from sqlalchemy import create_engine, text
from datetime import datetime, timezone

engine = create_engine(

    "mysql+pymysql://wpflask:wpflaskpass@127.0.0.1:10005/local",

    pool_pre_ping=True,

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