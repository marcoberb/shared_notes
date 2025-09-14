import api from './api';

const tagsService = {
  getAllTags: async () => {
    const response = await api.get('/tags');
    return response.data;
  }
};

export default tagsService;
