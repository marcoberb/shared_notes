
const URL_REGEX = /(https?:\/\/[^\s<>"{}|\\^`[\]]+|www\.[^\s<>"{}|\\^`[\]]+)/gi;

export const linkifyText = (text) => {
  if (!text) return [];
  
  const parts = [];
  let lastIndex = 0;
  let match;
  
  
  URL_REGEX.lastIndex = 0;
  
  while ((match = URL_REGEX.exec(text)) !== null) {
    
    if (match.index > lastIndex) {
      parts.push(text.substring(lastIndex, match.index));
    }
    
    
    const url = match[0];
    
    const href = url.startsWith('www.') ? `https:
    parts.push({
      type: 'link',
      url: href,
      text: url
    });
    
    lastIndex = match.index + match[0].length;
  }
  
  
  if (lastIndex < text.length) {
    parts.push(text.substring(lastIndex));
  }
  
  return parts;
};

export const renderTextWithLinks = (text) => {
  const parts = linkifyText(text);
  
  return parts.map((part, index) => {
    if (typeof part === 'string') {
      return part;
    } else if (part.type === 'link') {
      return (
        <a
          key={index}
          href={part.url}
          target="_blank"
          rel="noopener noreferrer"
          style={{
            color: '#007bff',
            textDecoration: 'underline',
            wordBreak: 'break-all'
          }}
          onMouseEnter={(e) => {
            e.target.style.color = '#0056b3';
          }}
          onMouseLeave={(e) => {
            e.target.style.color = '#007bff';
          }}
        >
          {part.text}
        </a>
      );
    }
    return part;
  });
};

export const renderMultilineTextWithLinks = (text) => {
  if (!text) return null;
  
  const lines = text.split('\n');
  
  return lines.map((line, lineIndex) => (
    <span key={lineIndex}>
      {renderTextWithLinks(line)}
      {lineIndex < lines.length - 1 && <br />}
    </span>
  ));
};
