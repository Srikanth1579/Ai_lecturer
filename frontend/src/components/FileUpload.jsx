import React, { useState } from 'react';
import axios from 'axios';

export default function FileUpload() {
  const [file, setFile] = useState(null);
  const [question, setQuestion] = useState('');
  const [result, setResult] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    
    const formData = new FormData();
    formData.append('file', file);
    formData.append('question', question);

    try {
      const response = await axios.post('http://localhost:8000/upload/', formData, {
        headers: {'Content-Type': 'multipart/form-data'}
      });
      
      setResult({
        message: response.data.message,
        videoUrl: response.data.video_path 
          ? `http://localhost:8000/download/${response.data.video_path}`
          : null
      });
    } catch (error) {
      console.error("API Error:", error.response);
      setResult({ message: "Error: " + error.message });
    }
    setLoading(false);
  };

  return (
    <div className="upload-container">
      <form onSubmit={handleSubmit}>
        <input
          type="file"
          onChange={(e) => setFile(e.target.files[0])}
          accept=".txt,.pdf"
        />
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Enter your question..."
        />
        <button type="submit" disabled={loading}>
          {loading ? 'Processing...' : 'Generate Presentation'}
        </button>
      </form>
      
      {result.message && <div className="result">
        <p>{result.message}</p>
        {result.videoUrl && (
          <a href={result.videoUrl} download>
            Download Video
          </a>
        )}
      </div>}
    </div>
  );
}