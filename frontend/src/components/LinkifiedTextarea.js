import React, { useState, useCallback, useRef, useEffect } from 'react';

const LinkifiedTextarea = ({ 
  value, 
  onChange, 
  placeholder, 
  className, 
  disabled, 
  rows,
  style,
  ...props 
}) => {
  const ref = useRef(null);

  const URL_REGEX = /(https?:\/\/[^\s<>"{}|\\^`[\]]+|www\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*[^\s<>"{}|\\^`[\]]*)/gi;

  const textToHtml = useCallback((text) => {
    if (!text) return '';
    
    let escapedText = text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
    
    const linkedText = escapedText.replace(URL_REGEX, (url) => {
      const href = url.startsWith('www.') ? `https://${url}` : url;
      return `<a href="${href}" target="_blank" rel="noopener noreferrer" style="color: #007bff; text-decoration: underline;">${url}</a>`;
    });
    
    return linkedText.replace(/\n/g, '<br>');
  }, [URL_REGEX]);

  const htmlToText = useCallback((htmlString) => {
    if (!htmlString) return '';
    
    let text = htmlString
      .replace(/<div><br\s*\/?><\/div>/gi, '\n')
      .replace(/<div(\s[^>]*)?>(\s*<br\s*\/?>)*\s*<\/div>/gi, '\n')
      .replace(/<div(\s[^>]*)?>/gi, '\n')
      .replace(/<\/div>/gi, '')
      .replace(/<br\s*\/?>/gi, '\n')
      .replace(/<[^>]*>/g, '');
    
    const div = document.createElement('div');
    div.innerHTML = text;
    const decodedText = div.textContent || div.innerText || '';
    
    return decodedText.replace(/^\n+/, '').replace(/\n+$/, '').replace(/\n{2,}/g, '\n');
  }, []);

  const handleInput = useCallback(() => {
    if (!ref.current) return;
    
    const currentHtml = ref.current.innerHTML;
    const plainText = htmlToText(currentHtml);
    
    if (onChange) {
      onChange({ target: { value: plainText } });
    }
  }, [onChange, htmlToText]);

  const handleBlur = useCallback(() => {
    if (!ref.current) return;
    
    const plainText = htmlToText(ref.current.innerHTML);
    const newHtml = textToHtml(plainText);
    
    if (newHtml !== ref.current.innerHTML) {
      ref.current.innerHTML = newHtml;
    }
  }, [htmlToText, textToHtml]);

  const handleKeyDown = useCallback((evt) => {
    if (evt.key === ' ') {
      setTimeout(() => {
        if (ref.current) {
          const currentHtml = ref.current.innerHTML;
          const plainText = htmlToText(currentHtml);
          const newHtml = textToHtml(plainText);
          
          if (newHtml !== currentHtml) {
            const selection = window.getSelection();
            let caretPos = 0;
            
            if (selection.rangeCount > 0) {
              const range = selection.getRangeAt(0);
              const preCaretRange = range.cloneRange();
              preCaretRange.selectNodeContents(ref.current);
              preCaretRange.setEnd(range.endContainer, range.endOffset);
              caretPos = preCaretRange.toString().length;
            }
            
            ref.current.innerHTML = newHtml;
            
            const newSelection = window.getSelection();
            const newRange = document.createRange();
            let charCount = 0;
            let nodeStack = [ref.current];
            let foundNode = false;
            
            while (nodeStack.length > 0 && !foundNode) {
              const node = nodeStack.pop();
              
              if (node.nodeType === Node.TEXT_NODE) {
                const nodeLength = node.textContent.length;
                if (charCount + nodeLength >= caretPos) {
                  const offset = caretPos - charCount;
                  newRange.setStart(node, Math.min(offset, nodeLength));
                  newRange.setEnd(node, Math.min(offset, nodeLength));
                  foundNode = true;
                } else {
                  charCount += nodeLength;
                }
              } else {
                for (let i = node.childNodes.length - 1; i >= 0; i--) {
                  nodeStack.push(node.childNodes[i]);
                }
              }
            }
            
            if (foundNode) {
              newSelection.removeAllRanges();
              newSelection.addRange(newRange);
            } else {
              newRange.selectNodeContents(ref.current);
              newRange.collapse(false);
              newSelection.removeAllRanges();
              newSelection.addRange(newRange);
            }
          }
        }
      }, 10);
    }
  }, [htmlToText, textToHtml]);

  useEffect(() => {
    if (ref.current && value !== undefined) {
      const currentText = htmlToText(ref.current.innerHTML);
      if (currentText !== value) {
        const newHtml = textToHtml(value);
        ref.current.innerHTML = newHtml;
      }
    }
  }, [value, textToHtml, htmlToText]);

  const minHeight = rows ? `${rows * 1.5}em` : '300px';

  const baseStyle = {
    minHeight,
    maxHeight: '400px',
    overflowY: 'auto',
    padding: '20px',
    border: '1px solid #e9ecef',
    borderRadius: '8px',
    fontSize: '16px',
    fontFamily: 'inherit',
    lineHeight: '1.6',
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-word',
    backgroundColor: disabled ? '#f8f9fa' : 'white',
    color: disabled ? '#6c757d' : '#333',
    outline: 'none',
    textAlign: 'left',
    width: '100%',
    ...style
  };

  return (
    <div
      ref={ref}
      contentEditable={!disabled}
      onInput={handleInput}
      onBlur={handleBlur}
      onKeyDown={handleKeyDown}
      className={className}
      style={baseStyle}
      data-placeholder={placeholder}
      suppressContentEditableWarning={true}
      {...props}
    />
  );
};

export default LinkifiedTextarea;
