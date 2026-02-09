import React, { useState } from "react";
import QuizScreen from "./QuizScreen";

function App() {
  const [uploadError, setUploadError] = useState(null);
  const [files, setFiles] = useState([]);
  const [activeQuiz, setActiveQuiz] = useState(null);
  const [mcqAnswers, setMcqAnswers] = useState({});
  const [saqAnswers, setSaqAnswers] = useState({});
  const [loading, setLoading] = useState(false);
  const [stage, setStage] = useState("UPLOAD");
  const [submissionResult, setSubmissionResult] = useState(null);

  const BASE_URL = `${window.location.protocol}//${window.location.hostname}:8005`;
  console.log("Backend URL:", BASE_URL);
  // ----------------------
  // File upload
  // ----------------------
  const handleFileChange = (e) => {
    const newFiles = Array.from(e.target.files);

    setFiles((prevFiles) => {
      // prevent duplicate filenames
      const fileMap = new Map();

      [...prevFiles, ...newFiles].forEach((file) => {
        fileMap.set(file.name, file);
      });

      return Array.from(fileMap.values());
    });

    // reset input so user can re-select files again
    e.target.value = null;
  };


  const handleSubmitPDFs = async () => {
    if (files.length === 0) {
      alert("Please select at least one PDF");
      return;
    }

    const formData = new FormData();
    files.forEach((file) => formData.append("files", file));

    setLoading(true);
    setUploadError(null); // reset previous error

    try {
      const res = await fetch(`${BASE_URL}/upload_pdfs/`, {
        method: "POST",
        body: formData,
      });

      const data = await res.json();

      if (!res.ok || data.error) {
        let message = data.message || "Upload failed";

        if (data.error === "invalid_file") {
          message = "Invalid file detected. Please upload a valid, unprotected PDF.";
        }

        setUploadError({
          message,
          files: data.files || [],
        });

        setLoading(false);
        return;
      }

      const mcq = data.quiz.filter((q) => q.type === "MCQ");
      const saq = data.quiz.filter((q) => q.type === "SAQ");

      setActiveQuiz({ mcq, saq });
      setMcqAnswers({});
      setSaqAnswers({});
      setStage("MCQ");
    } catch (err) {
      console.error(err);
      setUploadError({
        message: "Server not reachable",
        files: [],
      });
    }

    setLoading(false);
  };

  // ----------------------
  // Answer handlers
  // ----------------------
  const handleMcqAnswer = (id, option) => {
    setMcqAnswers((prev) => ({ ...prev, [id]: option }));
  };

  const handleSaqAnswer = (id, text) => {
    setSaqAnswers((prev) => ({ ...prev, [id]: text }));
  };

  // ----------------------
  // Submit quiz
  // ----------------------
  const submitUserQuiz = async () => {
    const payload = {
      pdf_names: files.map((f) => f.name),
      mcq_answers: mcqAnswers,
      saq_answers: saqAnswers,
    };

    setLoading(true);
    try {
      const res = await fetch(`${BASE_URL}/submit_quiz/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      setSubmissionResult(data);
      setStage("RESULT");
    } catch (err) {
      console.error(err);
      alert("Error submitting quiz");
    }
    setLoading(false);
  };

  // ----------------------
  // Retake quiz
  // ----------------------
  const handleRetakeQuiz = () => {
    setMcqAnswers({});
    setSaqAnswers({});
    setSubmissionResult(null);
    setStage("MCQ");
  };

  // ----------------------
  // New quiz
  // ----------------------
  const handleNewQuiz = () => {
    setFiles([]);
    setMcqAnswers({});
    setSaqAnswers({});
    setActiveQuiz(null);
    setSubmissionResult(null);
    setUploadError(null);
    setStage("UPLOAD");
  };

  // ======================
  // UI
  // ======================
  return (
    <div className="flex flex-col items-center min-h-screen p-6 bg-gray-100 mt-12">
      {/* Important Disclaimer */}
      <div className="w-full max-w-4xl mb-6 p-4 bg-yellow-100 border-2 border-yellow-500 rounded-lg">
        <p className="text-yellow-900 font-bold text-center">
          ⚠️ IMPORTANT: This system only supports AI/ML related documents in English language.
          Other document types or languages are not supported.
        </p>
      </div>

      <h1 className="text-3xl font-bold mb-6">Quiz Generator</h1>

      {loading && <p>Loading...</p>}

      {/* Upload */}
      {uploadError && (
        <div className="mb-4 p-4 bg-red-100 border-2 border-red-500 rounded-lg">
          <p className="text-red-800 font-semibold">
            🚫 {uploadError.message}
          </p>

          {uploadError.files.length > 0 && (
            <ul className="mt-2 text-sm text-red-700 list-disc ml-5">
              {uploadError.files.map((file, idx) => (
                <li key={idx}>{file}</li>
              ))}
            </ul>
          )}
        </div>
      )}
      {stage === "UPLOAD" && (
        <div className="w-full max-w-md">
          <input
            type="file"
            multiple
            accept="application/pdf"
            onChange={handleFileChange}
            className="mb-3"
          />

          {files.length > 0 && (
            <div className="p-3 bg-white rounded shadow">
              <p className="font-semibold mb-2">
                Selected PDFs ({files.length})
              </p>

              <ul className="text-sm text-gray-700 space-y-2">
                {files.map((file, index) => (
                  <li
                    key={index}
                    className="flex items-center justify-between"
                  >
                    <span className="truncate max-w-[220px]">📄 {file.name}</span>

                    <button
                      onClick={() =>
                        setFiles((prev) =>
                          prev.filter((_, i) => i !== index)
                        )
                      }
                      className="text-red-600 text-xs font-semibold hover:underline"
                    >
                      Remove
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <button
            onClick={handleSubmitPDFs}
            disabled={files.length === 0}
            className={`mt-4 w-full px-4 py-2 rounded ${files.length === 0
              ? "bg-gray-400 cursor-not-allowed"
              : "bg-blue-600 text-white"
              }`}
          >
            Generate Quiz
          </button>
        </div>

      )}

      {/* MCQ */}
      {stage === "MCQ" && (
        <QuizScreen
          questions={activeQuiz.mcq}
          type="MCQ"
          onAnswerChange={handleMcqAnswer}
          answers={mcqAnswers}
          onFinish={() => setStage("SAQ")}
        />
      )}

      {/* SAQ */}
      {stage === "SAQ" && (
        <QuizScreen
          questions={activeQuiz.saq}
          type="SAQ"
          onAnswerChange={handleSaqAnswer}
          answers={saqAnswers}
          onFinish={() => setStage("SUBMIT")}
        />
      )}

      {/* Submit */}
      {stage === "SUBMIT" && (
        <button onClick={submitUserQuiz} className="bg-purple-700 text-white px-6 py-2 rounded">
          Submit Quiz
        </button>
      )}

      {/* ======================
           RESULT VIEW
         ====================== */}
      {stage === "RESULT" && submissionResult && (
        <div className="w-full max-w-3xl mt-6">
          <h2 className="text-2xl font-bold mb-2">Quiz Results</h2>

          <p className="mb-4 text-lg">
            Score: <strong>{submissionResult.total_correct}</strong> /{" "}
            <strong>{submissionResult.total_questions}</strong>
          </p>

          {submissionResult.evaluated_quiz.map((q, index) => (
            <div
              key={q.question_id}
              className={`p-4 border rounded mb-4 ${q.is_correct ? "bg-green-100" : "bg-red-100"
                }`}
            >
              <p className="font-semibold">
                Q{index + 1}. {q.question}
              </p>

              {/* MCQ Options */}
              {q.type === "MCQ" && q.options && (
                <ul className="ml-4 mt-2">
                  {Object.entries(q.options).map(([key, val]) => (
                    <li key={key}>
                      <strong>{key}.</strong> {val}
                    </li>
                  ))}
                </ul>
              )}

              <p className="mt-2">
                <strong>Your Answer:</strong> {q.user_answer || "—"}
              </p>

              <p>
                <strong>Correct Answer:</strong> {q.correct_answer}
              </p>

              {q.similarity !== null && (
                <p>
                  <strong>Similarity:</strong> {q.similarity.toFixed(2)}
                </p>
              )}

              {q.explanation && (
                <p className="mt-2 text-sm text-gray-700">
                  <strong>Explanation:</strong> {q.explanation}
                </p>
              )}

              <p className="mt-1 font-semibold">
                {q.is_correct ? "✅ Correct" : "❌ Incorrect"}
              </p>
            </div>
          ))}

          <div className="mt-6 flex gap-4">
            <button
              onClick={handleRetakeQuiz}
              className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700"
            >
              Retake Quiz
            </button>
            <button
              onClick={handleNewQuiz}
              className="bg-green-600 text-white px-6 py-2 rounded-lg hover:bg-green-700"
            >
              New Quiz
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;