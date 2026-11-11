import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api/client';

export default function Dashboard() {
  const [topic, setTopic] = useState('');
  const [goal, setGoal] = useState('');
  const [sessions, setSessions] = useState([]);
  const navigate = useNavigate();

  useEffect(() => {
    fetchSessions();
  }, []);

  const fetchSessions = async () => {
    try {
      const response = await api.get('/sessions/');
      setSessions(response.data);
    } catch (err) {
      console.error('Failed to fetch sessions:', err);
    }
  };

  const handleCreateSession = async (e) => {
    e.preventDefault();
    try {
      const response = await api.post('/sessions/', { topic, learning_goal: goal });
      navigate(`/session/${response.data.id}`);
    } catch (err) {
      console.error('Failed to create session:', err);
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6 text-gray-800">Your Learning Dashboard</h1>
      
      <div className="bg-white p-6 rounded-lg shadow-md mb-8">
        <h2 className="text-xl font-semibold mb-4">Start a New Topic</h2>
        <form onSubmit={handleCreateSession} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">What do you want to learn?</label>
            <input 
              type="text" 
              required
              className="mt-1 w-full p-2 border rounded focus:outline-blue-500"
              placeholder="e.g., Quantum Physics, Python Decorators, French Revolution"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Goal (Optional)</label>
            <input 
              type="text" 
              className="mt-1 w-full p-2 border rounded focus:outline-blue-500"
              placeholder="e.g., Prepare for upcoming exam"
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
            />
          </div>
          <button type="submit" className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
            Create Learning Session
          </button>
        </form>
      </div>

      <div>
        <h2 className="text-xl font-semibold mb-4">Previous Sessions</h2>
        <div className="grid gap-4">
          {sessions.map(session => (
            <div key={session.id} className="p-4 border rounded shadow-sm bg-gray-50 flex justify-between items-center">
              <div>
                <h3 className="font-bold text-lg">{session.topic}</h3>
                <p className="text-sm text-gray-500">Status: {session.status}</p>
              </div>
              <button 
                onClick={() => navigate(`/session/${session.id}`)}
                className="text-blue-600 hover:underline"
              >
                Continue &rarr;
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}