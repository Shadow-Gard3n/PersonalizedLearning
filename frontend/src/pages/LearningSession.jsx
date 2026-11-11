import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import api from '../api/client';

export default function LearningSession() {
  const { id: sessionId } = useParams();
  const navigate = useNavigate();

  // State Management
  const [loading, setLoading] = useState(false);
  const [syllabus, setSyllabus] = useState(null);
  const [content, setContent] = useState(null);
  
  // Chat & Doubt State
  const [doubtInput, setDoubtInput] = useState('');
  const [chatHistory, setChatHistory] = useState([]);
  
  // Quiz State
  const [questionsReady, setQuestionsReady] = useState(false);
  const [evaluation, setEvaluation] = useState(null);
  const [image, setImage] = useState(null);
  const [isFinished, setIsFinished] = useState(false);

  // STEP 1: Generate Roadmap & First Topic
  const startSession = async () => {
    setLoading(true);
    try {
      const planRes = await api.post(`/learning/${sessionId}/plan`);
      setSyllabus(planRes.data);
      await fetchCurrentContent();
    } catch (err) {
      console.error('Failed to generate roadmap:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchCurrentContent = async () => {
    try {
      const res = await api.post(`/learning/${sessionId}/content`);
      if (res.data.completed) {
        setIsFinished(true);
      } else {
        setContent(res.data);
        setQuestionsReady(false);
        setEvaluation(null);
        setImage(null);
      }
    } catch (err) {
      console.error('Failed to fetch content:', err);
    }
  };

  // STEP 2: Ask a Doubt
  const handleAskDoubt = async (e) => {
    e.preventDefault();
    if (!doubtInput.trim()) return;

    const newChat = [...chatHistory, { role: 'user', content: doubtInput }];
    setChatHistory(newChat);
    setDoubtInput('');

    try {
      const res = await api.post(`/learning/${sessionId}/doubt`, {
        question: doubtInput,
        subtopic_title: content.subtopic_title,
        current_material: content.material,
        chat_history: chatHistory
      });
      setChatHistory([...newChat, { role: 'model', content: res.data.answer }]);
    } catch (err) {
      console.error('Failed to resolve doubt:', err);
    }
  };

  // STEP 3: Generate Quiz
  const handleGenerateQuiz = async () => {
    setLoading(true);
    try {
      await api.post(`/learning/${sessionId}/generate-questions`);
      setQuestionsReady(true);
    } catch (err) {
      console.error('Failed to generate quiz:', err);
    } finally {
      setLoading(false);
    }
  };

  // STEP 4: Submit Notebook Image
  const handleImageUpload = async (e) => {
    e.preventDefault();
    setLoading(true);
    
    const formData = new FormData();
    formData.append('file', image);

    try {
      const res = await api.post(`/learning/${sessionId}/evaluate-upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setEvaluation(res.data);
    } catch (err) {
      console.error('Failed to evaluate upload:', err);
    } finally {
      setLoading(false);
    }
  };

  // STEP 5: Advance to Next Topic
  const handleNextTopic = async () => {
    setLoading(true);
    try {
      await api.post(`/learning/${sessionId}/next`);
      await fetchCurrentContent();
      setChatHistory([]);
    } catch (err) {
      console.error('Failed to advance topic:', err);
    } finally {
      setLoading(false);
    }
  };

  if (isFinished) {
    return (
      <div className="text-center mt-20">
        <h1 className="text-3xl font-bold text-green-600">Session Complete! 🎉</h1>
        <p className="mt-4">You have successfully mastered this topic.</p>
        <button onClick={() => navigate('/dashboard')} className="mt-6 bg-blue-600 text-white px-6 py-2 rounded">
          Back to Dashboard
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto p-4 flex gap-6">
      
      {/* LEFT PANEL: Progress & Actions */}
      <div className="w-1/3 bg-gray-50 p-4 border rounded-lg h-fit sticky top-4">
        {!content ? (
          <div className="text-center">
            <h2 className="text-xl font-bold mb-4">Ready to Learn?</h2>
            <button 
              onClick={startSession} 
              disabled={loading}
              className="bg-blue-600 text-white px-4 py-2 rounded w-full disabled:opacity-50"
            >
              {loading ? 'Generating Syllabus...' : 'Generate Syllabus & Start'}
            </button>
          </div>
        ) : (
          <div>
            <h2 className="text-xl font-bold mb-2">Current Topic:</h2>
            <p className="text-blue-700 font-semibold text-lg mb-6">{content.subtopic_title}</p>
            
            <div className="space-y-4">
              {!questionsReady ? (
                <button 
                  onClick={handleGenerateQuiz} 
                  disabled={loading}
                  className="bg-purple-600 text-white px-4 py-2 rounded w-full disabled:opacity-50"
                >
                  {loading ? 'Preparing Quiz...' : 'I am ready for the Quiz'}
                </button>
              ) : !evaluation ? (
                <form onSubmit={handleImageUpload} className="bg-white p-3 border rounded shadow-sm">
                  <p className="text-sm font-bold mb-2">Upload Notebook Answer</p>
                  <input 
                    type="file" 
                    accept="image/*" 
                    onChange={(e) => setImage(e.target.files[0])} 
                    className="mb-2 text-sm w-full"
                    required
                  />
                  <button type="submit" disabled={loading} className="bg-green-600 text-white px-4 py-2 rounded w-full text-sm">
                    {loading ? 'Grading...' : 'Submit for Grading'}
                  </button>
                </form>
              ) : (
                <div className="bg-green-50 p-4 border border-green-200 rounded">
                  <h3 className="font-bold text-green-800">Score: {evaluation.score}%</h3>
                  <p className="text-sm mt-2">{evaluation.feedback}</p>
                  {evaluation.weak_topics.length > 0 && (
                    <p className="text-xs text-red-600 mt-2">Needs review: {evaluation.weak_topics.join(', ')}</p>
                  )}
                  <button 
                    onClick={handleNextTopic} 
                    className="mt-4 bg-blue-600 text-white px-4 py-2 rounded w-full"
                  >
                    Move to Next Topic &rarr;
                  </button>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* RIGHT PANEL: Content & Tutor Chat */}
      <div className="w-2/3">
        {content && (
          <div className="space-y-8">
            {/* Study Material */}
            <div className="bg-white p-8 border rounded-lg shadow-sm prose max-w-none">
              <ReactMarkdown>{content.material}</ReactMarkdown>
            </div>

            {/* Interactive Tutor Chat */}
            {!questionsReady && (
              <div className="bg-white border rounded-lg overflow-hidden shadow-sm">
                <div className="bg-blue-600 text-white p-3 font-bold">Ask the AI Tutor</div>
                <div className="h-64 overflow-y-auto p-4 space-y-4 bg-gray-50">
                  {chatHistory.length === 0 && <p className="text-gray-400 text-sm">Have a doubt about this topic? Ask below!</p>}
                  {chatHistory.map((msg, i) => (
                    <div key={i} className={`p-3 rounded-lg max-w-[80%] ${msg.role === 'user' ? 'bg-blue-100 ml-auto' : 'bg-gray-200 mr-auto'}`}>
                      <ReactMarkdown className="text-sm">{msg.content}</ReactMarkdown>
                    </div>
                  ))}
                </div>
                <form onSubmit={handleAskDoubt} className="p-3 bg-white border-t flex gap-2">
                  <input 
                    type="text" 
                    value={doubtInput}
                    onChange={(e) => setDoubtInput(e.target.value)}
                    placeholder="E.g., I don't understand the second paragraph..."
                    className="flex-1 p-2 border rounded focus:outline-blue-500"
                  />
                  <button type="submit" className="bg-blue-600 text-white px-4 py-2 rounded">Ask</button>
                </form>
              </div>
            )}
          </div>
        )}
      </div>

    </div>
  );
}