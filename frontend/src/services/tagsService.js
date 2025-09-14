import api from './api';

// Service to fetch all available tags
const tagsService = {
  getAllTags: async () => {
    const response = await api.get('/tags');
    return response.data;
  }
};

export default tagsService;
