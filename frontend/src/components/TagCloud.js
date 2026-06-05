import React from 'react';

function TagCloud({ tags, selectedTagId, onTagClick }) {
  const getTagSize = (count) => {
    if (count === 0) return 'tag-size-sm';
    if (count <= 2) return 'tag-size-md';
    if (count <= 5) return 'tag-size-lg';
    return 'tag-size-xl';
  };

  const handleTagClick = (tagId) => {
    if (selectedTagId === tagId) {
      onTagClick(null);
    } else {
      onTagClick(tagId);
    }
  };

  if (tags.length === 0) {
    return null;
  }

  return (
    <div className="tag-cloud-section">
      <h3 className="tag-cloud-title">
        🏷️ 标签云
        {selectedTagId && (
          <button
            className="tag-clear-filter"
            onClick={() => onTagClick(null)}
          >
            清除筛选
          </button>
        )}
      </h3>
      <div className="tag-cloud">
        <button
          className={`tag-cloud-item ${selectedTagId === null ? 'active' : ''}`}
          onClick={() => onTagClick(null)}
        >
          全部
        </button>
        {tags.map((tag) => (
          <button
            key={tag.id}
            className={`tag-cloud-item ${getTagSize(tag.task_count || 0)} ${selectedTagId === tag.id ? 'active' : ''}`}
            style={{
              borderColor: tag.color,
              color: selectedTagId === tag.id ? 'white' : tag.color,
              backgroundColor: selectedTagId === tag.id ? tag.color : 'transparent',
            }}
            onClick={() => handleTagClick(tag.id)}
            title={`${tag.name} (${tag.task_count || 0} 个任务)`}
          >
            <span
              className="tag-cloud-dot"
              style={{ backgroundColor: tag.color }}
            />
            {tag.name}
            <span className="tag-cloud-count">({tag.task_count || 0})</span>
          </button>
        ))}
      </div>
    </div>
  );
}

export default TagCloud;
