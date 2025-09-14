import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { notesService } from '../services/notesService';
import { searchService } from '../services/searchService';
import { shareService } from '../services/shareService';
import tagsService from '../services/tagsService';
import { useAuth } from '../utils/AuthContext';
import TagSelector from './TagSelector';
import { renderMultilineTextWithLinks } from '../utils/linkUtils';
import LinkifiedTextarea from './LinkifiedTextarea';

const Dashboard = () => {
  const [notes, setNotes] = useState([]);
  const [activeSection, setActiveSection] = useState('my-notes');
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
  const [selectedTags, setSelectedTags] = useState([]);
  const [hasChanges, setHasChanges] = useState(false);
  const [saving, setSaving] = useState(false);
  
  const [allTags, setAllTags] = useState([]);
  const [selectedFilterTags, setSelectedFilterTags] = useState([]);
  
  const [noteShares, setNoteShares] = useState([]);
  const [emailInput, setEmailInput] = useState('');
  const [modalError, setModalError] = useState(null);
  const { user, logout } = useAuth();

  const loadAllTags = async () => {
    try {
      const tagsData = await tagsService.getAllTags();
      setAllTags(tagsData);
    } catch (error) {
      console.error('Error loading tags:', error);
    }
  };

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
    loadAllSectionCounts();
    loadAllTags();
    loadNotes(currentPage, activeSection);
  }, [currentPage, activeSection]);

  useEffect(() => {
    setCurrentPage(1);
    loadNotes(1, activeSection);
  }, [selectedFilterTags]);

  const loadNotes = async (page = 1, section = 'my-notes') => {
    try {
      setLoading(true);
      let response;
      
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
      
      setSectionCounts(prev => ({
        ...prev,
        [section]: paginationData.total_notes
      }));
    } catch (error) {
      setError('Errore nel caricamento delle note');
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async (page = 1) => {
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
      
      const response = await searchService.searchNotes(searchQuery, selectedFilterTags, page, activeSection);
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
    } finally {
      setLoading(false);
    }
  };

  const handleSectionChange = (section) => {
    setActiveSection(section);
    setCurrentPage(1);
    setSearchQuery('');
    setSelectedFilterTags([]);
  };

  const handleTagFilterToggle = (tagId) => {
    setSelectedFilterTags(prev => {
      if (prev.includes(tagId)) {
        return prev.filter(id => id !== tagId);
      } else {
        return [...prev, tagId];
      }
    });
  };

  const clearTagFilters = () => {
    setSelectedFilterTags([]);
  };

  const loadNoteShares = async (noteId) => {
    try {
      const response = await shareService.getNoteShares(noteId);
      setNoteShares(response.shares || []);
    } catch (error) {
      setNoteShares([]);
    }
  };

  const addEmailShare = async () => {
    const email = emailInput.trim().toLowerCase();
    if (email && isValidEmail(email) && selectedNote) {
      try {
        setModalError(null);
        await shareService.shareNote(selectedNote.id, [email]);
        setEmailInput('');
        await loadNoteShares(selectedNote.id);
        // Ricarica le note per aggiornare i conteggi delle sezioni
        // dato che la nota potrebbe spostarsi da "Note private" a "Condivise da me"
        loadNotes(currentPage, activeSection);
      } catch (error) {
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
        setModalError(null);
        await shareService.removeShareByEmail(selectedNote.id, email);
        await loadNoteShares(selectedNote.id);
        // Ricarica le note per aggiornare i conteggi delle sezioni
        // dato che la nota potrebbe spostarsi da "Condivise da me" a "Note private"
        loadNotes(currentPage, activeSection);
      } catch (error) {
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
      loadNotes(currentPage, activeSection);
    } catch (error) {
      setError('Errore nell\'eliminazione della nota');
    }
  };

  const handleViewNote = async (note) => {
    setSelectedNote(note);
    setEditedTitle(note.title);
    setEditedContent(note.content);
    
    if (note.tags) {
      const tagIds = note.tags.length && typeof note.tags[0] === 'object'
        ? note.tags.map(t => t.id.toString())
        : note.tags.map(String);
      setSelectedTags(tagIds);
    } else {
      setSelectedTags([]);
    }
    
    await loadNoteShares(note.id);
    
    setIsEditing(false);
    setHasChanges(false);
    setEmailInput('');
    setModalError(null);
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
    setModalError(null);
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
        tags: selectedTags // UUID strings, no conversion needed
      });
      
      setNotes(notes.map(note => 
        note.id === selectedNote.id ? updatedNote : note
      ));
      
      setSelectedNote(updatedNote);
      setIsEditing(false);
      setHasChanges(false);
    } catch (error) {
      setError('Errore nel salvataggio della nota');
    } finally {
      setSaving(false);
    }
  };

  const handleCancelEdit = () => {
    if (hasChanges) {
      if (window.confirm('Ci sono modifiche non salvate. Sei sicuro di voler annullare?')) {
        setEditedTitle(selectedNote.title);
        setEditedContent(selectedNote.content);
        
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

      <div className="section-tabs">
        <button 
          className={`btn ${activeSection === 'my-notes' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => handleSectionChange('my-notes')}
        >
          Note private ({sectionCounts['my-notes']})
        </button>
        <button 
          className={`btn ${activeSection === 'shared-by-me' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => handleSectionChange('shared-by-me')}
        >
          Condivise da me ({sectionCounts['shared-by-me']})
        </button>
        <button 
          className={`btn ${activeSection === 'shared-with-me' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => handleSectionChange('shared-with-me')}
        >
          Condivise con me ({sectionCounts['shared-with-me']})
        </button>
      </div>

      <div className="search-section">
        <form onSubmit={handleSearch} className="search-form">
          <input
            type="text"
            placeholder="Cerca note..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="search-input"
          />
          <button type="submit" className="btn">
            🔍 Cerca
          </button>
        </form>

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
                  {activeSection !== 'shared-with-me' && (
                    <button 
                      onClick={() => handleDeleteNote(note.id)}
                      className="btn btn-sm btn-danger"
                    >
                      Elimina
                    </button>
                  )}
                </div>
              </div>
              <div className="note-content">
                <p style={{ 
                  lineHeight: 1.5,
                  wordBreak: 'break-word',
                  overflow: 'hidden',
                  display: '-webkit-box',
                  WebkitLineClamp: 3,
                  WebkitBoxOrient: 'vertical'
                }}>
                  {renderMultilineTextWithLinks(
                    note.content.length > 150 
                      ? note.content.substring(0, 150) + '...' 
                      : note.content
                  )}
                </p>
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

      <div className="pagination-footer" style={{ 
        marginTop: '20px', 
        padding: '15px 0', 
        borderTop: '1px solid #e9ecef',
        textAlign: 'center',
        color: '#666',
        fontSize: '14px'
      }}>
        {loading ? (
          <span>Caricamento...</span>
        ) : (
          <div>
            <div style={{ marginBottom: '15px', fontWeight: '500' }}>
              Pagina {pagination.current_page} di {pagination.total_pages} ({pagination.total_notes} note totali)
            </div>
            
            <div className="pagination" style={{ 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'center',
              gap: '8px' 
            }}>
              <button 
                onClick={() => handlePageChange(1)}
                disabled={pagination.current_page === 1}
                className="pagination-btn"
                title="Prima pagina"
              >
                ⏮ Prima
              </button>
              
              <button 
                onClick={() => handlePageChange(currentPage - 1)}
                disabled={!pagination.has_previous}
                className="pagination-btn"
              >
                ← Precedente
              </button>
              
              {renderPaginationNumbers()}
              
              <button 
                onClick={() => handlePageChange(currentPage + 1)}
                disabled={!pagination.has_next}
                className="pagination-btn"
              >
                Successiva →
              </button>
              
              <button 
                onClick={() => handlePageChange(pagination.total_pages)}
                disabled={pagination.current_page === pagination.total_pages}
                className="pagination-btn"
                title="Ultima pagina"
              >
                Ultima ⏭
              </button>
            </div>
          </div>
        )}
      </div>

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
                {!isEditing && activeSection !== 'shared-with-me' && (
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
                    <LinkifiedTextarea
                      value={editedContent}
                      onChange={handleContentChange}
                      placeholder="Contenuto della nota...&#10;&#10;💡 URL (http://, https://, www.) verranno automaticamente convertiti in link cliccabili!"
                      rows={15}
                      style={{ width: '100%', marginBottom: '20px' }}
                    />
                    
                    <div style={{ marginTop: '20px', marginBottom: '20px' }}>
                      <TagSelector
                        selectedTags={selectedTags}
                        setSelectedTags={handleTagsChange}
                        disabled={false}
                      />
                    </div>

                    <div style={{ marginTop: '20px', padding: '15px', backgroundColor: '#f8f9fa', borderRadius: '6px' }}>
                      <h4 style={{ marginTop: 0, marginBottom: '15px', fontSize: '16px' }}>Gestione condivisioni</h4>
                      
                      {noteShares.length > 0 && (
                        <div style={{ marginBottom: '15px' }}>
                          <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500', fontSize: '14px' }}>
                            Attualmente condivisa con:
                          </label>
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                            {noteShares.map((share, index) => (
                              <div key={index} style={{
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'center',
                                padding: '8px 12px',
                                backgroundColor: 'white',
                                border: '1px solid #dee2e6',
                                borderRadius: '4px',
                                fontSize: '14px'
                              }}>
                                <span>{share.shared_with_email}</span>
                                <button
                                  onClick={() => removeEmailShare(share.shared_with_email)}
                                  style={{
                                    padding: '4px 8px',
                                    backgroundColor: '#dc3545',
                                    color: 'white',
                                    border: 'none',
                                    borderRadius: '3px',
                                    fontSize: '12px',
                                    cursor: 'pointer'
                                  }}
                                >
                                  Rimuovi
                                </button>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

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
                  <div style={{ 
                    whiteSpace: 'pre-wrap', 
                    fontFamily: 'inherit',
                    lineHeight: 1.6,
                    wordBreak: 'break-word',
                    textAlign: 'left'
                  }}>
                    {renderMultilineTextWithLinks(selectedNote.content)}
                  </div>
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