import api from './api';

export const searchNotes = async (query, tags = [], page = 1) => {
  const params = new URLSearchParams();
  if (query) params.append('q', query);
  if (tags.length > 0) params.append('tags', tags.join(','));
  params.append('page', page);

  const response = await api.get(`/search?${params}`);
  return response.data;
};

export const getSharedNotes = async () => {
  const response = await api.get('/share/shared-with-me');
  return response.data;
};

export const getSearchSuggestions = async (query) => {
  const response = await api.get(`/search/suggestions?q=${query}`);
  return response.data;
};

export const getPopularTags = async (limit = 20) => {
  const response = await api.get(`/search/tags?limit=${limit}`);
  return response.data;
};

// Export as default object for easier importing
const searchService = {
  searchNotes,
  getSharedNotes,
  getSearchSuggestions,
  getPopularTags
};

export default searchService;
export { searchService };
