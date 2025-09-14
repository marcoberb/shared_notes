import api from './api';

export const getMyNotes = async (page = 1, tags = null) => {
  let url = `/notes/my-notes?page=${page}&limit=15`;
  if (tags) {
    url += `&tags=${tags}`;
  }
  const response = await api.get(url);
  return response.data;
};

export const getNotesSharedByMe = async (page = 1, tags = null) => {
  let url = `/notes/shared-by-me?page=${page}&limit=15`;
  if (tags) {
    url += `&tags=${tags}`;
  }
  const response = await api.get(url);
  return response.data;
};

export const getNotesSharedWithMe = async (page = 1, tags = null) => {
  let url = `/notes/shared-with-me?page=${page}&limit=15`;
  if (tags) {
    url += `&tags=${tags}`;
  }
  const response = await api.get(url);
  return response.data;
};

export const getNote = async (id) => {
  const response = await api.get(`/notes/${id}`);
  return response.data;
};

export const createNote = async (noteData) => {
  const response = await api.post('/notes/', noteData);
  return response.data;
};

export const updateNote = async (id, noteData) => {
  const response = await api.put(`/notes/${id}`, noteData);
  return response.data;
};

export const deleteNote = async (id) => {
  const response = await api.delete(`/notes/${id}`);
  return response.data;
};

export const getTags = async () => {
  const response = await api.get('/tags/');
  return response.data;
};

// Export as default object for easier importing
const notesService = {
  getMyNotes,
  getNotesSharedByMe,
  getNotesSharedWithMe,
  getNote,
  createNote,
  updateNote,
  deleteNote,
  getTags
};

export default notesService;
export { notesService };
