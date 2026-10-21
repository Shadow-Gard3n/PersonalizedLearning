
import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import api from "../api/client";


export default function LearningSession() {
  const { sessionId } = useParams();
  const navigate = useNavigate();

  const [session, setSession] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [index, setIndex] = useState(0);
  const [selected, setSelected] = useState("");
  const [feedback, setFeedback] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  async function loadSession() {
    try {
      const [sessionResponse, questionsResponse] = await Promise.all([
        api.get(`/sessions/${sessionId}`),
        api.get(`/learning/${sessionId}/questions`),
      ]);

      setSession(sessionResponse.data);
      setQuestions(questionsResponse.data);
    } catch (err) {
      if (err.response?.status === 401) {
        localStorage.removeItem("access_token");
        navigate("/login");
      } else {
        setError(err.response?.data?.detail || "Could not load session");
      }
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadSession();
  }, [sessionId]);

  async function submitAnswer(event) {
    event.preventDefault();
    if (selected === "") return;

    const question = questions[index];

    try {
      const response = await api.post(
        `/learning/${sessionId}/answer`,
        {
          question_id: question.id,
          selected_option: Number(selected),
        }
      );

      setFeedback(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || "Could not submit answer");
    }
  }

  function nextQuestion() {
    setIndex((current) => current + 1);
    setSelected("");
    setFeedback(null);
    setError("");
  }

  if (loading) return <main className="dashboard">Loading session...</main>;

  if (error && !session) {
    return <main className="dashboard"><p className="error">{error}</p></main>;
  }

  if (!session) return null;

  const question = questions[index];
  const finished = questions.length > 0 && index >= questions.length;

  return (
    <main className="dashboard">
      <header className="topbar">
        <Link to="/" className="brand">LearnWise</Link>
        <Link to="/" className="text-link">Dashboard</Link>
      </header>

      <section className="welcome">
        <p className="eyebrow">LEARNING SESSION</p>
        <h1>{session.topic}</h1>
        <p>{session.learning_goal || "Learn and practice at your own pace."}</p>
      </section>

      {questions.length === 0 ? (
        <section className="panel">
          <h2>Your session is ready</h2>
          <p>No questions have been added to this session yet.</p>
          <p className="muted">
            You can add a question through the backend API documentation.
            AI-generated lessons and questions will be added in a later phase.
          </p>
          <a
            className="button-link"
            href={`${import.meta.env.VITE_API_URL}/docs`}
            target="_blank"
            rel="noreferrer"
          >
            Open API documentation
          </a>
        </section>
      ) : finished ? (
        <section className="panel">
          <h2>Practice completed!</h2>
          <p>You have reached the end of the questions in this session.</p>
          <Link className="button-link" to="/">Return to dashboard</Link>
        </section>
      ) : (
        <section className="panel">
          <div className="question-meta">
            <span>Question {index + 1} of {questions.length}</span>
            <span>{question.difficulty}</span>
          </div>

          <p className="eyebrow">{question.concept}</p>
          <h2>{question.prompt}</h2>

          <form onSubmit={submitAnswer}>
            <div className="option-list">
              {question.options.map((option, optionIndex) => (
                <label
                  key={optionIndex}
                  className={`option ${
                    selected === String(optionIndex) ? "selected" : ""
                  }`}
                >
                  <input
                    type="radio"
                    name="answer"
                    value={optionIndex}
                    checked={selected === String(optionIndex)}
                    disabled={!!feedback}
                    onChange={(e) => setSelected(e.target.value)}
                  />
                  <span>{option}</span>
                </label>
              ))}
            </div>

            {error && <p className="error">{error}</p>}

            {!feedback ? (
              <button disabled={selected === ""}>Submit answer</button>
            ) : (
              <div className="feedback">
                <h3>{feedback.correct ? "Correct!" : "Not quite."}</h3>
                <p>
                  Correct answer: {question.options[feedback.correct_option]}
                </p>
                {feedback.explanation && <p>{feedback.explanation}</p>}

                <button type="button" onClick={nextQuestion}>
                  {index + 1 === questions.length
                    ? "Finish session"
                    : "Next question"}
                </button>
              </div>
            )}
          </form>
        </section>
      )}
    </main>
  );
}