import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { notesService } from '../services/notesService';
import { searchService } from '../services/searchService';
import { shareService } from '../services/shareService';
import tagsService from '../services/tagsService';
import { useAuth } from '../utils/AuthContext';
import TagSelector from './TagSelector';

const Dashboard = () => {
  const [notes, setNotes] = useState([]);
  const [activeSection, setActiveSection] = useState('my-notes'); // 'my-notes', 'shared-by-me', 'shared-with-me'
  const [sectionCounts, setSectionCounts] = useState({
    'my-notes': 0,
    'shared-by-me': 0,
    'shared-with-me': 0
  });
  const [pagination, setPagination] = useState({
    current_page: 1,
    total_pages: 1,
    total_notes: 0,
    notes_per_page: 15,
    has_next: false,
    has_previous: false
  });
  const [currentPage, setCurrentPage] = useState(1);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedNote, setSelectedNote] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editedTitle, setEditedTitle] = useState('');
  const [editedContent, setEditedContent] = useState('');
  const [selectedTags, setSelectedTags] = useState([]); // Array of tag IDs (string)
  const [hasChanges, setHasChanges] = useState(false);
  const [saving, setSaving] = useState(false);
  
  // Tag filtering state
  const [allTags, setAllTags] = useState([]); // All available tags from DB
  const [selectedFilterTags, setSelectedFilterTags] = useState([]); // Tags selected for filtering (array of tag IDs)
  
  // Share management state
  const [noteShares, setNoteShares] = useState([]); // Current note's shares
  const [emailInput, setEmailInput] = useState(''); // Email input for sharing
  const [modalError, setModalError] = useState(null); // Error state specific to modal
  const { user, logout } = useAuth();

  // Load all available tags on component mount
  const loadAllTags = async () => {
    try {
      const tagsData = await tagsService.getAllTags();
      setAllTags(tagsData);
    } catch (error) {
      console.error('Error loading tags:', error);
    }
  };

  // Carica i conteggi per tutte le sezioni
  const loadAllSectionCounts = async () => {
    try {
      const sections = ['my-notes', 'shared-by-me', 'shared-with-me'];
      const counts = {};
      
      for (const section of sections) {
        let response;
        switch (section) {
          case 'my-notes':
            response = await notesService.getMyNotes(1);
            break;
          case 'shared-by-me':
            response = await notesService.getNotesSharedByMe(1);
            break;
          case 'shared-with-me':
            response = await notesService.getNotesSharedWithMe(1);
            break;
        }
        counts[section] = response?.pagination?.total_notes || 0;
      }
      
      setSectionCounts(counts);
    } catch (error) {
      console.error('Error loading section counts:', error);
    }
  };

  useEffect(() => {
    loadAllSectionCounts(); // Carica i conteggi all'inizio
    loadAllTags(); // Load available tags
    loadNotes(currentPage, activeSection);
  }, [currentPage, activeSection]);

  // Effect to reload notes when tag filters change
  useEffect(() => {
    setCurrentPage(1); // Reset to first page when filters change
    loadNotes(1, activeSection);
  }, [selectedFilterTags]);

  const loadNotes = async (page = 1, section = 'my-notes') => {
    try {
      setLoading(true);
      let response;
      
      // Create tags parameter if filters are selected
      const tagsParam = selectedFilterTags.length > 0 ? selectedFilterTags.join(',') : null;
      
      switch (section) {
        case 'my-notes':
          response = await notesService.getMyNotes(page, tagsParam);
          break;
        case 'shared-by-me':
          response = await notesService.getNotesSharedByMe(page, tagsParam);
          break;
        case 'shared-with-me':
          response = await notesService.getNotesSharedWithMe(page, tagsParam);
          break;
        default:
          response = await notesService.getMyNotes(page, tagsParam);
      }
      
      console.log('Notes response:', response); // Debug log
      setNotes(response.notes || []);
      
      const paginationData = response.pagination || {
        current_page: 1,
        total_pages: 1,
        total_notes: 0,
        notes_per_page: 15,
        has_next: false,
        has_previous: false
      };
      
      setPagination(paginationData);
      
      // Aggiorna il conteggio per la sezione specifica
      setSectionCounts(prev => ({
        ...prev,
        [section]: paginationData.total_notes
      }));
    } catch (error) {
      setError('Errore nel caricamento delle note');
      console.error('Error loading notes:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async (page = 1) => {
    // Se viene chiamato da un event (form submit), gestisci l'evento
    if (page && page.preventDefault) {
      page.preventDefault();
      page = 1;
    }
    
    if (!searchQuery.trim()) {
      setCurrentPage(1);
      loadNotes(1, activeSection);
      return;
    }

    try {
      setLoading(true);
      // Include selected filter tags in search
      const response = await searchService.searchNotes(searchQuery, selectedFilterTags, page);
      console.log('Search response:', response); // Debug log
      setNotes(response.notes || []);
      setPagination(response.pagination || {
        current_page: 1,
        total_pages: 1,
        total_notes: 0,
        notes_per_page: 0,
        has_next: false,
        has_previous: false
      });
    } catch (error) {
      setError('Errore nella ricerca');
      console.error('Error searching notes:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSectionChange = (section) => {
    setActiveSection(section);
    setCurrentPage(1);
    setSearchQuery(''); // Clear search when changing sections
    setSelectedFilterTags([]); // Clear tag filters when changing sections
  };

  // Handle tag filter selection
  const handleTagFilterToggle = (tagId) => {
    setSelectedFilterTags(prev => {
      if (prev.includes(tagId)) {
        // Remove tag if already selected
        return prev.filter(id => id !== tagId);
      } else {
        // Add tag if not selected
        return [...prev, tagId];
      }
    });
  };

  // Clear all tag filters
  const clearTagFilters = () => {
    setSelectedFilterTags([]);
  };

  // Share management functions
  const loadNoteShares = async (noteId) => {
    try {
      const response = await shareService.getNoteShares(noteId);
      setNoteShares(response.shares || []);
    } catch (error) {
      console.error('Error loading note shares:', error);
      setNoteShares([]);
    }
  };

  const addEmailShare = async () => {
    const email = emailInput.trim().toLowerCase();
    if (email && isValidEmail(email) && selectedNote) {
      try {
        setModalError(null); // Clear any previous errors
        await shareService.shareNote(selectedNote.id, [email]);
        setEmailInput('');
        await loadNoteShares(selectedNote.id); // Reload shares
      } catch (error) {
        console.error('Error sharing note:', error);
        
        // Extract more specific error message if available
        let errorMessage = 'Errore nella condivisione della nota';
        if (error.response?.data?.detail) {
          errorMessage = error.response.data.detail;
        } else if (error.message) {
          errorMessage = error.message;
        }
        
        setModalError(errorMessage);
      }
    }
  };

  const removeEmailShare = async (email) => {
    if (selectedNote) {
      try {
        setModalError(null); // Clear any previous errors
        await shareService.removeShareByEmail(selectedNote.id, email);
        await loadNoteShares(selectedNote.id); // Reload shares
      } catch (error) {
        console.error('Error removing share:', error);
        
        // Extract more specific error message if available
        let errorMessage = 'Errore nella rimozione della condivisione';
        if (error.response?.data?.detail) {
          errorMessage = error.response.data.detail;
        } else if (error.message) {
          errorMessage = error.message;
        }
        
        setModalError(errorMessage);
      }
    }
  };

  const isValidEmail = (email) => {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  };

  const handleEmailKeyPress = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      addEmailShare();
    }
  };

  const handleDeleteNote = async (noteId) => {
    if (!window.confirm('Sei sicuro di voler eliminare questa nota?')) {
      return;
    }

    try {
      await notesService.deleteNote(noteId);
      // Ricarica la pagina corrente per aggiornare la paginazione
      loadNotes(currentPage, activeSection);
    } catch (error) {
      setError('Errore nell\'eliminazione della nota');
      console.error('Error deleting note:', error);
    }
  };

  const handleViewNote = async (note) => {
    setSelectedNote(note);
    setEditedTitle(note.title);
    setEditedContent(note.content);
    
    // Set selected tags
    if (note.tags) {
      const tagIds = note.tags.length && typeof note.tags[0] === 'object'
        ? note.tags.map(t => t.id.toString())
        : note.tags.map(String);
      setSelectedTags(tagIds);
    } else {
      setSelectedTags([]);
    }
    
    // Load note shares
    await loadNoteShares(note.id);
    
    setIsEditing(false);
    setHasChanges(false);
    setEmailInput(''); // Clear email input
    setModalError(null); // Clear modal errors
    setShowModal(true);
  };

  const handleCloseModal = () => {
    if (hasChanges) {
      if (window.confirm('Ci sono modifiche non salvate. Sei sicuro di voler chiudere senza salvare?')) {
        resetModalState();
      }
    } else {
      resetModalState();
    }
  };

  const resetModalState = () => {
    setShowModal(false);
    setSelectedNote(null);
    setIsEditing(false);
    setEditedTitle('');
    setEditedContent('');
    setSelectedTags([]);
    setHasChanges(false);
    setSaving(false);
    setModalError(null); // Clear modal errors
  };

  const handleEditNote = () => {
    setIsEditing(true);
  };

  const handleTitleChange = (e) => {
    setEditedTitle(e.target.value);
    setHasChanges(
      e.target.value !== selectedNote.title || 
      editedContent !== selectedNote.content ||
      JSON.stringify(selectedTags) !== JSON.stringify(selectedNote.tags ? 
        (selectedNote.tags.length && typeof selectedNote.tags[0] === 'object' ? 
          selectedNote.tags.map(t => t.id.toString()) : 
          selectedNote.tags.map(String)) : [])
    );
  };

  const handleContentChange = (e) => {
    setEditedContent(e.target.value);
    setHasChanges(
      editedTitle !== selectedNote.title || 
      e.target.value !== selectedNote.content ||
      JSON.stringify(selectedTags) !== JSON.stringify(selectedNote.tags ? 
        (selectedNote.tags.length && typeof selectedNote.tags[0] === 'object' ? 
          selectedNote.tags.map(t => t.id.toString()) : 
          selectedNote.tags.map(String)) : [])
    );
  };

  const handleTagsChange = (newTags) => {
    setSelectedTags(newTags);
    setHasChanges(
      editedTitle !== selectedNote.title || 
      editedContent !== selectedNote.content ||
      JSON.stringify(newTags) !== JSON.stringify(selectedNote.tags ? 
        (selectedNote.tags.length && typeof selectedNote.tags[0] === 'object' ? 
          selectedNote.tags.map(t => t.id.toString()) : 
          selectedNote.tags.map(String)) : [])
    );
  };

  const handleSaveNote = async () => {
    if (!hasChanges) return;

    try {
      setSaving(true);
      const updatedNote = await notesService.updateNote(selectedNote.id, {
        title: editedTitle,
        content: editedContent,
        tags: selectedTags.map(id => parseInt(id, 10))
      });
      
      // Aggiorna la lista delle note
      setNotes(notes.map(note => 
        note.id === selectedNote.id ? updatedNote : note
      ));
      
      // Aggiorna la nota selezionata
      setSelectedNote(updatedNote);
      setIsEditing(false);
      setHasChanges(false);
    } catch (error) {
      setError('Errore nel salvataggio della nota');
      console.error('Error saving note:', error);
    } finally {
      setSaving(false);
    }
  };

  const handleCancelEdit = () => {
    if (hasChanges) {
      if (window.confirm('Ci sono modifiche non salvate. Sei sicuro di voler annullare?')) {
        setEditedTitle(selectedNote.title);
        setEditedContent(selectedNote.content);
        // Reset selected tags
        if (selectedNote.tags) {
          const tagIds = selectedNote.tags.length && typeof selectedNote.tags[0] === 'object'
            ? selectedNote.tags.map(t => t.id.toString())
            : selectedNote.tags.map(String);
          setSelectedTags(tagIds);
        } else {
          setSelectedTags([]);
        }
        setIsEditing(false);
        setHasChanges(false);
      }
    } else {
      setIsEditing(false);
    }
  };

  const handlePageChange = (newPage) => {
    if (newPage >= 1 && newPage <= pagination.total_pages) {
      setCurrentPage(newPage);
      // Se siamo in modalità ricerca, ricarica i risultati di ricerca per la nuova pagina
      if (searchQuery) {
        handleSearch(newPage);
      }
    }
  };

  const renderPaginationNumbers = () => {
    const pageNumbers = [];
    const maxVisiblePages = 5;
    let startPage = Math.max(1, currentPage - Math.floor(maxVisiblePages / 2));
    let endPage = Math.min(pagination.total_pages, startPage + maxVisiblePages - 1);
    
    // Adjust start page if we're near the end
    if (endPage - startPage + 1 < maxVisiblePages) {
      startPage = Math.max(1, endPage - maxVisiblePages + 1);
    }

    for (let i = startPage; i <= endPage; i++) {
      pageNumbers.push(
        <button
          key={i}
          onClick={() => handlePageChange(i)}
          className={`pagination-number ${i === currentPage ? 'active' : ''}`}
        >
          {i}
        </button>
      );
    }

    return pageNumbers;
  };

  if (loading) {
    return (
      <div className="dashboard">
        <div className="loading">Caricamento...</div>
      </div>
    );
  }

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <div className="user-welcome">
          <h1>📝 SharedNotes</h1>
          <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
            <p style={{ margin: 0 }}>Welcome back, <strong>{user?.name || user?.preferred_username || user?.username}</strong>!</p>
            <button onClick={logout} className="btn btn-secondary">
              Logout
            </button>
          </div>
        </div>
        <div className="header-actions">
          <Link to="/create" className="btn btn-primary">
            Nuova Nota
          </Link>
        </div>
      </header>

      {/* Section Tabs */}
      <div className="section-tabs" style={{ marginTop: '20px', borderBottom: '1px solid #e0e0e0' }}>
        <div style={{ display: 'flex', gap: '0' }}>
          <button
            onClick={() => handleSectionChange('my-notes')}
            className={`tab-button ${activeSection === 'my-notes' ? 'active' : ''}`}
            style={{
              padding: '12px 24px',
              border: 'none',
              background: activeSection === 'my-notes' ? '#007bff' : 'transparent',
              color: activeSection === 'my-notes' ? 'white' : '#666',
              borderRadius: '8px 8px 0 0',
              cursor: 'pointer',
              fontSize: '14px',
              fontWeight: activeSection === 'my-notes' ? 'bold' : 'normal',
              borderBottom: activeSection === 'my-notes' ? '2px solid #007bff' : '2px solid transparent'
            }}
          >
            Le Mie Note ({sectionCounts['my-notes'] || 0})
          </button>
          <button
            onClick={() => handleSectionChange('shared-by-me')}
            className={`tab-button ${activeSection === 'shared-by-me' ? 'active' : ''}`}
            style={{
              padding: '12px 24px',
              border: 'none',
              background: activeSection === 'shared-by-me' ? '#007bff' : 'transparent',
              color: activeSection === 'shared-by-me' ? 'white' : '#666',
              borderRadius: '8px 8px 0 0',
              cursor: 'pointer',
              fontSize: '14px',
              fontWeight: activeSection === 'shared-by-me' ? 'bold' : 'normal',
              borderBottom: activeSection === 'shared-by-me' ? '2px solid #007bff' : '2px solid transparent'
            }}
          >
            Condivise da Me ({sectionCounts['shared-by-me'] || 0})
          </button>
          <button
            onClick={() => handleSectionChange('shared-with-me')}
            className={`tab-button ${activeSection === 'shared-with-me' ? 'active' : ''}`}
            style={{
              padding: '12px 24px',
              border: 'none',
              background: activeSection === 'shared-with-me' ? '#007bff' : 'transparent',
              color: activeSection === 'shared-with-me' ? 'white' : '#666',
              borderRadius: '8px 8px 0 0',
              cursor: 'pointer',
              fontSize: '14px',
              fontWeight: activeSection === 'shared-with-me' ? 'bold' : 'normal',
              borderBottom: activeSection === 'shared-with-me' ? '2px solid #007bff' : '2px solid transparent'
            }}
          >
            Condivise con Me ({sectionCounts['shared-with-me'] || 0})
          </button>
        </div>
      </div>

      <div className="search-section" style={{ marginTop: '30px' }}>
        <form onSubmit={handleSearch} className="search-form" style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
          <input
            type="text"
            placeholder="Cerca nelle tue note..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="search-input"
            style={{ 
              height: '36px', 
              padding: '6px 12px',
              flex: '1',
              maxWidth: '400px',
              fontSize: '14px'
            }}
          />
          <button 
            type="submit" 
            className="btn btn-primary"
            style={{ height: '36px', padding: '6px 16px', fontSize: '14px' }}
          >
            Cerca
          </button>
          {searchQuery && (
            <button 
              type="button" 
              onClick={() => {
                setSearchQuery('');
                setSelectedFilterTags([]); // Clear tag filters when resetting search
                setCurrentPage(1);
                loadNotes(1, activeSection);
              }}
              className="btn btn-secondary"
              style={{ height: '36px', padding: '6px 16px', fontSize: '14px' }}
            >
              Reset
            </button>
          )}
        </form>

        {/* Tag Filtering Interface */}
        {allTags.length > 0 && (
          <div className="tag-filters" style={{ marginTop: '15px' }}>
            <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
              <span style={{ fontSize: '14px', fontWeight: '500', color: '#666', marginRight: '8px' }}>
                Filtra per tag:
              </span>
              {allTags.map(tag => (
                <button
                  key={tag.id}
                  onClick={() => handleTagFilterToggle(tag.id)}
                  className={`tag-badge ${selectedFilterTags.includes(tag.id) ? 'selected' : ''}`}
                  style={{
                    display: 'inline-block',
                    padding: '4px 8px',
                    fontSize: '12px',
                    borderRadius: '12px',
                    border: selectedFilterTags.includes(tag.id) ? '1px solid #007bff' : '1px solid #ddd',
                    backgroundColor: selectedFilterTags.includes(tag.id) ? '#007bff' : '#f8f9fa',
                    color: selectedFilterTags.includes(tag.id) ? 'white' : '#666',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                    lineHeight: '1.2'
                  }}
                  onMouseEnter={(e) => {
                    if (!selectedFilterTags.includes(tag.id)) {
                      e.target.style.backgroundColor = '#e9ecef';
                      e.target.style.borderColor = '#adb5bd';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!selectedFilterTags.includes(tag.id)) {
                      e.target.style.backgroundColor = '#f8f9fa';
                      e.target.style.borderColor = '#ddd';
                    }
                  }}
                >
                  {tag.name}
                </button>
              ))}
              {selectedFilterTags.length > 0 && (
                <button
                  onClick={clearTagFilters}
                  style={{
                    padding: '4px 8px',
                    fontSize: '12px',
                    borderRadius: '12px',
                    border: '1px solid #dc3545',
                    backgroundColor: '#dc3545',
                    color: 'white',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                    lineHeight: '1.2',
                    marginLeft: '8px'
                  }}
                >
                  Pulisci filtri ({selectedFilterTags.length})
                </button>
              )}
            </div>
          </div>
        )}
      </div>

      {error && (
        <div className="error-message">
          {error}
        </div>
      )}

      <div className="notes-grid">
        {notes.length === 0 ? (
          <div className="no-notes">
            <p>Nessuna nota trovata.</p>
          </div>
        ) : (
          notes.map((note) => (
            <div key={note.id} className="note-card">
              <div className="note-header">
                <h3>{note.title}</h3>
                <div className="note-actions">
                  <button 
                    onClick={() => handleViewNote(note)}
                    className="btn btn-sm"
                  >
                    Visualizza
                  </button>
                  <button 
                    onClick={() => handleDeleteNote(note.id)}
                    className="btn btn-sm btn-danger"
                  >
                    Elimina
                  </button>
                </div>
              </div>
              <div className="note-content">
                <p>{note.content.substring(0, 150)}...</p>
              </div>
              {note.is_shared && (
                <div className="note-meta">
                  <span className="note-shared">Condivisa</span>
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {/* Pagination Controls */}
      {pagination.total_notes > 0 && (
        <div className="pagination-container">
          <div className="pagination-info">
            <span>
              Pagina {pagination.current_page} di {pagination.total_pages} 
              ({pagination.total_notes} note totali)
            </span>
          </div>
          <div className="pagination-controls">
            <button
              onClick={() => handlePageChange(1)}
              disabled={!pagination.has_previous}
              className="pagination-btn"
            >
              «
            </button>
            <button
              onClick={() => handlePageChange(currentPage - 1)}
              disabled={!pagination.has_previous}
              className="pagination-btn"
            >
              ‹
            </button>
            
            {renderPaginationNumbers()}
            
            <button
              onClick={() => handlePageChange(currentPage + 1)}
              disabled={!pagination.has_next}
              className="pagination-btn"
            >
              ›
            </button>
            <button
              onClick={() => handlePageChange(pagination.total_pages)}
              disabled={!pagination.has_next}
              className="pagination-btn"
            >
              »
            </button>
          </div>
        </div>
      )}

      {/* Modal per visualizzare/modificare la nota completa */}
      {showModal && selectedNote && (
        <div className="modal-overlay" onClick={handleCloseModal}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              {isEditing ? (
                <input
                  type="text"
                  value={editedTitle}
                  onChange={handleTitleChange}
                  className="modal-title-input"
                  placeholder="Titolo della nota"
                />
              ) : (
                <h2>{selectedNote.title}</h2>
              )}
              <div className="modal-header-actions">
                {!isEditing && (
                  <button 
                    onClick={handleEditNote}
                    className="btn btn-sm btn-secondary"
                    style={{ marginRight: '10px' }}
                  >
                    ✏️ Modifica
                  </button>
                )}
                <button className="modal-close" onClick={handleCloseModal}>
                  ×
                </button>
              </div>
            </div>
            <div className="modal-body">
              <div className="note-meta">
                <p><strong>Creata il:</strong> {new Date(selectedNote.created_at).toLocaleDateString('it-IT', {
                  year: 'numeric',
                  month: 'long', 
                  day: 'numeric',
                  hour: '2-digit',
                  minute: '2-digit'
                })}</p>
                {selectedNote.updated_at !== selectedNote.created_at && (
                  <p><strong>Modificata il:</strong> {new Date(selectedNote.updated_at).toLocaleDateString('it-IT', {
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric', 
                    hour: '2-digit',
                    minute: '2-digit'
                  })}</p>
                )}
                {selectedNote.tags && selectedNote.tags.length > 0 && (
                  <div className="note-tags">
                    <strong>Tags:</strong> {selectedNote.tags.map(tag => tag.name).join(', ')}
                  </div>
                )}
              </div>
              
              <div className="note-content-full">
                {isEditing ? (
                  <>
                    <textarea
                      value={editedContent}
                      onChange={handleContentChange}
                      className="modal-content-textarea"
                      placeholder="Contenuto della nota"
                      rows={15}
                    />
                    <div style={{ marginTop: '20px', marginBottom: '20px' }}>
                      <TagSelector
                        selectedTags={selectedTags}
                        setSelectedTags={handleTagsChange}
                        disabled={false}
                      />
                    </div>

                    {/* Share management section */}
                    <div style={{ marginTop: '20px', marginBottom: '20px', borderTop: '1px solid #eee', paddingTop: '20px' }}>
                      <h4 style={{ marginBottom: '15px', fontSize: '16px', fontWeight: '600' }}>Condivisioni</h4>
                      
                      {/* Modal error display */}
                      {modalError && (
                        <div style={{
                          backgroundColor: '#f8d7da',
                          border: '1px solid #f5c6cb',
                          color: '#721c24',
                          padding: '12px',
                          borderRadius: '4px',
                          marginBottom: '15px',
                          fontSize: '14px'
                        }}>
                          {modalError}
                        </div>
                      )}
                      
                      {/* Current shares */}
                      {noteShares.length > 0 && (
                        <div style={{ marginBottom: '15px' }}>
                          <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500', fontSize: '14px' }}>
                            Condiviso con:
                          </label>
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                            {noteShares.map((share, index) => (
                              <span 
                                key={share.id || index}
                                style={{
                                  display: 'inline-flex',
                                  alignItems: 'center',
                                  padding: '6px 10px',
                                  backgroundColor: '#f0f7ff',
                                  border: '1px solid #b3d9ff',
                                  borderRadius: '14px',
                                  fontSize: '13px',
                                  gap: '8px'
                                }}
                              >
                                {share.shared_with_email}
                                <button
                                  type="button"
                                  onClick={() => removeEmailShare(share.shared_with_email)}
                                  style={{
                                    background: 'none',
                                    border: 'none',
                                    color: '#0066cc',
                                    cursor: 'pointer',
                                    fontSize: '16px',
                                    lineHeight: '1',
                                    padding: '0',
                                    marginLeft: '4px'
                                  }}
                                  title="Rimuovi condivisione"
                                >
                                  ×
                                </button>
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                      
                      {/* Add new share */}
                      <div>
                        <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500', fontSize: '14px' }}>
                          Condividi con nuova email:
                        </label>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                          <input
                            type="email"
                            value={emailInput}
                            onChange={(e) => {
                              setEmailInput(e.target.value);
                              // Clear modal error when user starts typing
                              if (modalError) {
                                setModalError(null);
                              }
                            }}
                            onKeyPress={handleEmailKeyPress}
                            placeholder="email@esempio.com"
                            style={{
                              flex: 1,
                              padding: '8px 12px',
                              border: '1px solid #ddd',
                              borderRadius: '4px',
                              fontSize: '14px'
                            }}
                          />
                          <button 
                            type="button" 
                            onClick={addEmailShare}
                            disabled={!emailInput.trim() || !isValidEmail(emailInput.trim())}
                            style={{
                              padding: '8px 16px',
                              backgroundColor: '#007bff',
                              color: 'white',
                              border: 'none',
                              borderRadius: '4px',
                              fontSize: '14px',
                              cursor: emailInput.trim() && isValidEmail(emailInput.trim()) ? 'pointer' : 'not-allowed',
                              opacity: emailInput.trim() && isValidEmail(emailInput.trim()) ? 1 : 0.6,
                              whiteSpace: 'nowrap'
                            }}
                          >
                            Condividi
                          </button>
                        </div>
                      </div>
                    </div>
                  </>
                ) : (
                  <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit' }}>
                    {selectedNote.content}
                  </pre>
                )}
              </div>
              
              {isEditing && (
                <div className="modal-footer">
                  {hasChanges && (
                    <div className="changes-warning">
                      <span style={{ color: '#f39c12', fontSize: '14px' }}>
                        ⚠️ Ci sono modifiche non salvate
                      </span>
                    </div>
                  )}
                  <div className="modal-actions">
                    <button 
                      onClick={handleCancelEdit}
                      className="btn btn-secondary"
                      disabled={saving}
                    >
                      Annulla
                    </button>
                    <button 
                      onClick={handleSaveNote}
                      className="btn btn-primary"
                      disabled={!hasChanges || saving}
                    >
                      {saving ? 'Salvataggio...' : 'Salva'}
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Dashboard;