import React, { useState } from 'react';

function SearchBar({ value, onChange, placeholder = '搜索任务标题或描述...' }) {
  const [focused, setFocused] = useState(false);

  const handleClear = () => {
    onChange('');
  };

  return (
    <div className={`search-bar ${focused ? 'focused' : ''}`}>
      <span className="search-icon">🔍</span>
      <input
        type="text"
        className="search-input"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
      />
      {value && (
        <button
          type="button"
          className="search-clear-btn"
          onClick={handleClear}
          aria-label="清除搜索"
        >
          ✕
        </button>
      )}
    </div>
  );
}

export default SearchBar;
