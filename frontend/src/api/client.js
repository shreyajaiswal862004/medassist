import axios from 'axios';

// base URL of your FastAPI backend
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// create axios instance with base URL
const client = axios.create({
    baseURL: API_BASE_URL,
});

// automatically attach JWT token to every request
// so you don't have to add it manually each time
client.interceptors.request.use((config) => {
    const token = localStorage.getItem('token');
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

// handle 401 errors globally
// if token expires, redirect to login automatically
client.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401) {
            localStorage.removeItem('token');
            localStorage.removeItem('user');
            window.location.href = '/login';
        }
        return Promise.reject(error);
    }
);

export default client;