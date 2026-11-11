import axios from "axios";

// Create an Axios instance pointing to your FastAPI backend API
const api = axios.create({
  baseURL: "http://127.0.0.1:8000/api", // <-- Added /api here
});

// Automatically attach the JWT token to every request if it exists
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

export default api;