from flask import Flask, request, jsonify 
from flask_cors import CORS
from   Backend.Chatbot_James.chat    import  generate_questions, evaluate_candidate_in_api
from   Backend.Chatbot_James.utils   import   parse_llm_questions, safe_json_loads,  clean_llm_json,validate_scores,safe_load_json
import socket
import  json

app = Flask(__name__)
CORS(app)

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

#Generate  Chatbot_James  Questions
@app.route("/generate_james_bot_qs/", methods=["POST"], strict_slashes=False)
def  Generate_Chatbot_James_Questions():
    try :
        data = request.get_json()
        domain = data.get("domain")
        print("domain  recieved   at   Generate_Chatbot_James_Questions  ",domain)
        questions_json  =  generate_questions(domain)
        print("Raw LLM output:\n", questions_json)
        structured_questions = parse_llm_questions(questions_json)
        print("structured_questions   ",structured_questions)
        return  jsonify({
            "success": True,
            "questions": structured_questions
        })
    except   Exception  as   e:
        print("Failed  Generate_Chatbot_James_Questions   . ",e)
        return  jsonify({
            "success": False
        })


@app.route("/evaluate_candidate/", methods=["POST"])
def evaluate_candidate_api():
    # try:
        data = request.get_json()

        domain = data.get("domain")
        answers = data.get("answers")  # list of {question, answer}

        if not domain or not answers:
            return jsonify({"success": False, "error": "Invalid payload"}), 400

        # Format answers for LLM
        # formatted_answers = ""
        # for i, qa in enumerate(answers, 1):
        #     formatted_answers += f"Q{i}: {qa['question']}\nA{i}: {qa['answer']}\n\n"

        # print(" evaluate_candidate_api   formatted_answers  ", answers)

        evaluation = evaluate_candidate_in_api(domain, answers)

         

        print("RAW LLM:", evaluation[:500])

        clean_text = clean_llm_json(evaluation)

        print("CLEANED:", clean_text[:500]) 


        # print(" evaluate_candidate_api   evaluation  type ", type(evaluation),len(evaluation))

        try:
            data = safe_load_json(clean_text)

            validated = validate_scores(data) 

            # scored_answers = safe_json_loads(evaluation)
            # print("scored_answers  ",type(scored_answers))
        except json.JSONDecodeError  as   e:
            print("LLM returned invalid JSON"  ,e)
            return jsonify({
                "success": False,
                "error": "LLM returned invalid JSON"
            }), 500
        

        return jsonify({
            "success": True,
            "answers": validated
        })


        # return jsonify({
        #     "success": True,
        #     "answers": scored_answers
        # })

        # parsed_evaluation_by_llm = parse_evaluation_output(evaluation)

        # print(" evaluate_candidate_api   parsed_evaluation_by_llm  ", parsed_evaluation_by_llm)



        # return jsonify({
        #     "success": True,
        #     "evaluation": evaluation
        # })

    # except Exception as e:
    #     print("❌ Evaluation failed:", e)
    #     return jsonify({
    #         "success": False,
    #         "error": str(e)
    #     }), 500



if __name__ == "__main__":
    host_ip = get_local_ip()
    print(f"🚀 Chat  James flask  app running on http://{host_ip}:8007")
 
    app.run(
        host=host_ip,
        port=8007,
        debug=True
    )