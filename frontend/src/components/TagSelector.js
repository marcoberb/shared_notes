
import React, { useEffect, useState, useRef } from 'react';
import tagsService from '../services/tagsService';
import './TagSelector.css';

function TagSelector({ selectedTags, setSelectedTags, disabled }) {
  const [allTags, setAllTags] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [open, setOpen] = useState(false);
  const dropdownRef = useRef(null);

  useEffect(() => {
    const fetchTags = async () => {
      try {
        setLoading(true);
        const tags = await tagsService.getAllTags();
        setAllTags(tags);
      } catch (err) {
        setError('Failed to load tags');
      } finally {
        setLoading(false);
      }
    };
    fetchTags();
  }, []);

  // Close dropdown on click outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleTagToggle = (tagId) => {
    if (selectedTags.includes(tagId.toString())) {
      setSelectedTags(selectedTags.filter(id => id !== tagId.toString()));
    } else {
      setSelectedTags([...selectedTags, tagId.toString()]);
    }
  };

  if (loading) return <div>Loading tags...</div>;
  if (error) return <div>{error}</div>;

  return (
    <div className="tag-selector" ref={dropdownRef}>
      <label>Tags:</label>
      <div
        className={`dropdown ${disabled ? 'disabled' : ''}`}
        tabIndex={0}
        onClick={() => !disabled && setOpen(!open)}
        onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') setOpen(!open); }}
      >
        <div className="dropdown-selected">
          {selectedTags.length === 0 ? (
            <span className="dropdown-placeholder">Select tags...</span>
          ) : (
            allTags.filter(tag => selectedTags.includes(tag.id.toString())).map(tag => (
              <span className="tag-badge" key={tag.id}>{tag.name}</span>
            ))
          )}
          <span className="dropdown-arrow">▼</span>
        </div>
        {open && (
          <div className="dropdown-list">
            {allTags.map(tag => (
              <div
                key={tag.id}
                className={`dropdown-item${selectedTags.includes(tag.id.toString()) ? ' selected' : ''}`}
                onClick={e => { e.stopPropagation(); handleTagToggle(tag.id); }}
              >
                <input
                  type="checkbox"
                  checked={selectedTags.includes(tag.id.toString())}
                  readOnly
                />
                <span>{tag.name}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default TagSelector;
