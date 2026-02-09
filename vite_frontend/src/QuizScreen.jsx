import { useState } from "react";

export default function QuizScreen({ questions, type, onAnswerChange, answers, onFinish }) {
    const [currentIndex, setCurrentIndex] = useState(0);
    const [warning, setWarning] = useState(""); // for popup text
    const q = questions[currentIndex];

    // Ensure question has an id
    const qid = q.id || `q_${currentIndex}`;
    const selectedAnswer = answers[qid];

    const handleNext = () => {
        // For MCQ, do not proceed unless an option is selected
        if (type === "MCQ" && !selectedAnswer) {
            setWarning("Please choose an option before proceeding!");
            return;
        }

        // clear warning
        setWarning("");

        if (currentIndex + 1 < questions.length) {
            setCurrentIndex(currentIndex + 1);
        } else if (onFinish) {
            onFinish();
        }
    };

    return (
        <div className="max-w-xl mx-auto bg-white rounded-xl shadow-lg p-6 border">
            <h2 className="text-xl font-semibold mb-4">
                {type} Question {currentIndex + 1} of {questions.length}
            </h2>

            <p className="text-lg mb-4">{q.question}</p>

            {type === "MCQ" && (
                <div className="space-y-2">
                    {(Array.isArray(q.options) ? q.options : Object.values(q.options)).map((optText, idx) => {
                        const optLabel = ["A", "B", "C", "D"][idx] || `Option ${idx + 1}`;
                        return (
                            <button
                                key={optLabel}
                                onClick={() => onAnswerChange(qid, optLabel)}
                                className={`w-full text-left p-2 border rounded-md ${selectedAnswer === optLabel ? "bg-blue-500 text-white" : "bg-gray-100"
                                    }`}
                            >
                                {optLabel}. {optText}
                            </button>
                        );
                    })}
                </div>
            )}

            {type === "SAQ" && (
                <textarea
                    rows={5}
                    className="w-full border rounded-md p-2"
                    placeholder="Write your answer here..."
                    value={answers[qid] || ""}
                    onChange={(e) => onAnswerChange(qid, e.target.value)}
                />
            )}

            {/* Warning message */}
            {warning && <p className="text-red-600 mt-2">{warning}</p>}

            <div className="flex justify-end mt-4">
                <button
                    onClick={handleNext}
                    className="bg-blue-600 text-white px-6 py-2 rounded-lg"
                >
                    {currentIndex + 1 === questions.length
                        ? type === "MCQ"
                            ? "Start Short QAs"
                            : "Finish"
                        : "Next"}
                </button>
            </div>
        </div>
    );
}
