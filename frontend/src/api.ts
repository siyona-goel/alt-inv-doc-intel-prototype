import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export const api = {
  async upload(file: File): Promise<{ document_id: string }> {
    const form = new FormData()
    form.append('file', file)
    const res = await axios.post(`${BASE_URL}/upload`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return res.data
  },

  async getDocument(id: string) {
    const res = await axios.get(`${BASE_URL}/document/${id}`)
    return res.data
  },
}


