
import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import api from "../api/client";


export default function Dashboard() {
  const navigate = useNavigate();

  const [topic, setTopic] = useState("");
  const [goal, setGoal] = useState("");
  const [sessions, setSessions] = useState([]);
  const [profile, setProfile] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function loadDashboard() {
    try {
      const [sessionResponse, profileResponse] = await Promise.all([
        api.get("/sessions/"),
        api.get("/learning/profile"),
      ]);

      setSessions(sessionResponse.data);
      setProfile(profileResponse.data);
    } catch (err) {
      if (err.response?.status === 401) {
        localStorage.removeItem("access_token");
        navigate("/login");
      } else {
        setError("Could not load your dashboard.");
      }
    }
  }

  useEffect(() => {
    loadDashboard();
  }, []);

  async function createSession(event) {
    event.preventDefault();
    setError("");
    setLoading(true);

    try {
      const response = await api.post("/sessions/", {
        topic,
        learning_goal: goal,
      });

      navigate(`/session/${response.data.id}`);
    } catch (err) {
      setError(err.response?.data?.detail || "Could not create session");
    } finally {
      setLoading(false);
    }
  }

  function logout() {
    localStorage.removeItem("access_token");
    navigate("/login");
  }

  return (
    <main className="dashboard">
      <header className="topbar">
        <Link to="/" className="brand">LearnWise</Link>
        <button className="secondary" onClick={logout}>Logout</button>
      </header>

      <section className="welcome">
        <p className="eyebrow">YOUR PERSONAL LEARNING SPACE</p>
        <h1>What do you want to learn today?</h1>
        <p>Start a session and build your understanding step by step.</p>
      </section>

      <section className="panel">
        <h2>Create a learning session</h2>

        <form onSubmit={createSession}>
          <label>Topic</label>
          <input
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="e.g. Binary Search, Neural Networks"
            minLength={2}
            maxLength={150}
            required
          />

          <label>Learning goal (optional)</label>
          <textarea
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            placeholder="What would you like to understand?"
            maxLength={500}
          />

          {error && <p className="error">{error}</p>}

          <button disabled={loading}>
            {loading ? "Creating..." : "Start learning"}
          </button>
        </form>
      </section>

      <section className="panel">
        <h2>Your learning progress</h2>

        {profile.length === 0 ? (
          <p className="muted">Your concept progress will appear here after you answer questions.</p>
        ) : (
          <div className="progress-grid">
            {profile.map((item) => (
              <article className="progress-card" key={item.concept}>
                <h3>{item.concept}</h3>
                <p>{item.correct_attempts} / {item.attempts} correct</p>
                <p>Accuracy: {Math.round(item.accuracy * 100)}%</p>
              </article>
            ))}
          </div>
        )}
      </section>

      <section className="panel">
        <h2>Previous sessions</h2>

        {sessions.length === 0 ? (
          <p className="muted">You haven't created any sessions yet.</p>
        ) : (
          <div className="session-list">
            {sessions.map((session) => (
              <Link
                className="session-card"
                key={session.id}
                to={`/session/${session.id}`}
              >
                <div>
                  <h3>{session.topic}</h3>
                  <p>{session.learning_goal || "No learning goal added"}</p>
                </div>
                <span>{session.status}</span>
              </Link>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}