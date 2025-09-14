import api from './api';

export const shareNote = async (noteId, emails) => {
  const response = await api.post(`/notes/${noteId}/share`, {
    note_id: noteId,
    emails: emails
  });
  return response.data;
};

export const getNoteShares = async (noteId) => {
  const response = await api.get(`/notes/${noteId}/shares`);
  return response.data;
};

export const removeShareById = async (noteId, shareId) => {
  const response = await api.delete(`/notes/${noteId}/shares/${shareId}`);
  return response.data;
};

export const removeShareByEmail = async (noteId, email) => {
  const response = await api.delete(`/notes/${noteId}/shares/by-email/${email}`);
  return response.data;
};

// Legacy methods for backward compatibility
export const revokeShare = async (shareId) => {
  const response = await api.delete(`/share/${shareId}`);
  return response.data;
};

export const getSharedWithMe = async () => {
  const response = await api.get('/share/shared-with-me');
  return response.data;
};

export const getSharedByMe = async () => {
  const response = await api.get('/share/shared-by-me');
  return response.data;
};

// Export as default object for easier importing
const shareService = {
  shareNote,
  getNoteShares,
  removeShareById,
  removeShareByEmail,
  revokeShare,  // legacy
  getSharedWithMe,  // legacy
  getSharedByMe     // legacy
};

export default shareService;
export { shareService };
