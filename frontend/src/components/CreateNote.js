import React, { useState } from 'react';
import TagSelector from './TagSelector';
import { useNavigate, Link } from 'react-router-dom';
import { notesService } from '../services/notesService';

const CreateNote = () => {
  const navigate = useNavigate();
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedTags, setSelectedTags] = useState([]); // Array of tag IDs
  const [shareEmails, setShareEmails] = useState([]); // Array of email addresses
  const [emailInput, setEmailInput] = useState(''); // Current email being typed

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!title.trim() || !content.trim()) {
      setError('Titolo e contenuto sono obbligatori');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      

      const noteData = {
        title: title.trim(),
        content: content.trim(),
        tags: selectedTags.map(id => parseInt(id, 10)), // send as array of IDs
        share_emails: shareEmails // include emails for sharing
      };

      const response = await notesService.createNote(noteData);
      
      // Reindirizza alla dashboard
      navigate('/');
    } catch (error) {
      console.error('Error creating note:', error);
      
      // Extract more specific error message if available
      let errorMessage = 'Errore nella creazione della nota';
      if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      } else if (error.message) {
        errorMessage = error.message;
      }
      
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  // Email management functions
  const addEmail = () => {
    const email = emailInput.trim().toLowerCase();
    if (email && isValidEmail(email) && !shareEmails.includes(email)) {
      setShareEmails([...shareEmails, email]);
      setEmailInput('');
    }
  };

  const removeEmail = (emailToRemove) => {
    setShareEmails(shareEmails.filter(email => email !== emailToRemove));
  };

  const isValidEmail = (email) => {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  };

  const handleEmailKeyPress = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      addEmail();
    }
  };

  const handleCancel = () => {
    if (title.trim() || content.trim()) {
      if (window.confirm('Sei sicuro di voler annullare? I dati non salvati andranno persi.')) {
        navigate('/');
      }
    } else {
      navigate('/');
    }
  };

  return (
    <div className="create-note">
      <header className="create-note-header">
        <h1>Crea Nuova Nota</h1>
        <div className="header-actions">
          <Link to="/" className="btn btn-secondary">
            ← Torna alla Dashboard
          </Link>
        </div>
      </header>

      {error && (
        <div className="error-message">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="create-note-form">
        <div className="form-group">
          <label htmlFor="title">Titolo *</label>
          <input
            id="title"
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Inserisci il titolo della nota"
            className="form-input form-input-wide"
            disabled={loading}
            maxLength="200"
          />
        </div>

        <div className="form-group">
          <label htmlFor="content">Contenuto *</label>
          <textarea
            id="content"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="Scrivi qui il contenuto della tua nota..."
            className="form-textarea form-textarea-wide"
            disabled={loading}
            rows="10"
          />
        </div>

        <TagSelector
          selectedTags={selectedTags}
          setSelectedTags={setSelectedTags}
          disabled={loading}
        />

        {/* Email sharing section */}
        <div className="form-group">
          <label htmlFor="share-emails">Condividi con (email)</label>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '10px' }}>
            <input
              id="share-emails"
              type="email"
              value={emailInput}
              onChange={(e) => setEmailInput(e.target.value)}
              onKeyPress={handleEmailKeyPress}
              placeholder="Inserisci email per condividere la nota"
              className="form-input"
              disabled={loading}
              style={{ flex: 1 }}
            />
            <button 
              type="button" 
              onClick={addEmail}
              className="btn btn-secondary"
              disabled={loading || !emailInput.trim() || !isValidEmail(emailInput.trim())}
              style={{ whiteSpace: 'nowrap' }}
            >
              Aggiungi
            </button>
          </div>
          
          {/* Display added emails */}
          {shareEmails.length > 0 && (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginTop: '10px' }}>
              {shareEmails.map((email, index) => (
                <span 
                  key={index} 
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    padding: '4px 8px',
                    backgroundColor: '#e3f2fd',
                    border: '1px solid #90caf9',
                    borderRadius: '12px',
                    fontSize: '14px',
                    gap: '6px'
                  }}
                >
                  {email}
                  <button
                    type="button"
                    onClick={() => removeEmail(email)}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: '#1976d2',
                      cursor: 'pointer',
                      fontSize: '16px',
                      lineHeight: '1',
                      padding: '0',
                      marginLeft: '4px'
                    }}
                    title="Rimuovi email"
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
          )}
        </div>

        <div className="form-actions">
          <button 
            type="submit" 
            className="btn btn-primary"
            disabled={loading || !title.trim() || !content.trim()}
          >
            {loading ? 'Salvataggio...' : 'Crea Nota'}
          </button>
          <button 
            type="button" 
            onClick={handleCancel}
            className="btn btn-secondary"
            disabled={loading}
          >
            Annulla
          </button>
        </div>
      </form>
    </div>
  );
};

export default CreateNote;