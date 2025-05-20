// lib/api.ts
import axios from 'axios';
import { Comment } from './db/schema';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';


const api = {
  async getComments(): Promise<Comment[]> {
    const response = await axios.get(`${API_URL}/comments`);
    return response.data;
  },
  
  async getComment(id: string): Promise<Comment> {
    const response = await axios.get(`${API_URL}/comments/${id}`);
    return response.data;
  },
  
  async analyzeComment(id: string): Promise<Comment> {
    const response = await axios.post(`${API_URL}/analysis/${id}`);
    return response.data;
  },
  
  async searchComments(query: string): Promise<Comment[]> {
    const response = await axios.get(`${API_URL}/comments/search?q=${encodeURIComponent(query)}`);
    return response.data;
  }
};

export default api;