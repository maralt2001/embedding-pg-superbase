// Global state
let currentPollInterval = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    initializeTabs();
    initializeUpload();
    initializeSearch();
    initializeChat();
    initializeDocuments();
    initializeSettings();
});

// ============================================================================
// Tab Management
// ============================================================================

function initializeTabs() {
    const tabButtons = document.querySelectorAll('.tab-btn');

    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const tabName = button.dataset.tab;
            switchTab(tabName);
        });
    });
}

function switchTab(tabName) {
    // Update buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

    // Update content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(`${tabName}-tab`).classList.add('active');

    // Load data or reset UI when switching to certain tabs
    if (tabName === 'documents') {
        loadDocuments();
    } else if (tabName === 'settings') {
        loadConfig();
    } else if (tabName === 'upload') {
        resetUploadUI();
    }
}

// ============================================================================
// File Upload
// ============================================================================

function initializeUpload() {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const browseBtn = document.getElementById('browseBtn');

    // Browse button
    browseBtn.addEventListener('click', () => {
        fileInput.click();
    });

    // File input change
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileUpload(e.target.files[0]);
        }
    });

    // Drag and drop
    dropZone.addEventListener('click', (e) => {
        if (e.target !== browseBtn) {
            fileInput.click();
        }
    });

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');

        if (e.dataTransfer.files.length > 0) {
            handleFileUpload(e.dataTransfer.files[0]);
        }
    });
}

async function handleFileUpload(file) {
    // Validate file type
    const allowedExtensions = ['.pdf', '.docx', '.txt'];
    const fileExtension = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();

    if (!allowedExtensions.includes(fileExtension)) {
        showError(`Unsupported file type. Allowed: ${allowedExtensions.join(', ')}`);
        return;
    }

    // Show progress UI
    document.getElementById('uploadProgress').classList.remove('hidden');
    document.getElementById('uploadFilename').textContent = file.name;
    document.getElementById('uploadStatus').textContent = 'Uploading';
    document.getElementById('uploadStatus').className = 'status-badge';
    document.getElementById('progressMessage').textContent = 'Uploading file...';
    document.getElementById('progressFill').style.width = '10%';
    document.getElementById('resultMessage').classList.add('hidden');

    try {
        // Upload file
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch('/api/documents/upload', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Upload failed');
        }

        const data = await response.json();
        const taskId = data.task_id;

        // Start polling for progress
        pollTaskStatus(taskId);

    } catch (error) {
        showUploadError(error.message);
    }
}

function pollTaskStatus(taskId) {
    // Clear any existing poll interval
    if (currentPollInterval) {
        clearInterval(currentPollInterval);
    }

    currentPollInterval = setInterval(async () => {
        try {
            const response = await fetch(`/api/tasks/${taskId}`);
            if (!response.ok) {
                throw new Error('Failed to get task status');
            }

            const task = await response.json();
            updateProgress(task);

            // Stop polling if completed or failed
            if (task.status === 'completed' || task.status === 'failed') {
                clearInterval(currentPollInterval);
                currentPollInterval = null;

                if (task.status === 'completed') {
                    showUploadSuccess(task.result);
                } else {
                    showUploadError(task.error);
                }
            }

        } catch (error) {
            clearInterval(currentPollInterval);
            currentPollInterval = null;
            showUploadError(error.message);
        }
    }, 1500); // Poll every 1.5 seconds
}

function updateProgress(task) {
    const progress = task.progress || {};
    const stage = progress.stage || 'processing';
    const message = progress.message || 'Processing...';

    document.getElementById('progressMessage').textContent = message;
    document.getElementById('uploadStatus').textContent = capitalizeFirst(stage);

    // Update progress bar based on stage
    const stageProgress = {
        'queued': 10,
        'reading': 25,
        'chunking': 40,
        'embedding': 70,
        'uploading': 90,
        'completed': 100
    };

    const width = stageProgress[stage] || 50;
    document.getElementById('progressFill').style.width = `${width}%`;
}

function showUploadSuccess(result) {
    const statusBadge = document.getElementById('uploadStatus');
    statusBadge.textContent = 'Completed';
    statusBadge.classList.add('success');

    document.getElementById('progressFill').style.width = '100%';

    const resultMsg = document.getElementById('resultMessage');
    resultMsg.classList.remove('hidden', 'error');
    resultMsg.classList.add('success');

    if (result.skipped) {
        resultMsg.textContent = `✓ Document already exists and unchanged (${result.chunks_created} chunks)`;
    } else {
        resultMsg.textContent = `✓ Successfully processed! Created ${result.chunks_created} chunks in ${result.processing_time}s`;
    }

    // Reset file input
    document.getElementById('fileInput').value = '';
}

function showUploadError(message) {
    const statusBadge = document.getElementById('uploadStatus');
    statusBadge.textContent = 'Failed';
    statusBadge.classList.add('error');

    const resultMsg = document.getElementById('resultMessage');
    resultMsg.classList.remove('hidden', 'success');
    resultMsg.classList.add('error');
    resultMsg.textContent = `✗ Error: ${message}`;

    // Reset file input
    document.getElementById('fileInput').value = '';
}

function showError(message) {
    alert(message); // Simple error display
}

function resetUploadUI() {
    // Stop any ongoing polling
    if (currentPollInterval) {
        clearInterval(currentPollInterval);
        currentPollInterval = null;
    }

    // Hide progress section
    document.getElementById('uploadProgress').classList.add('hidden');

    // Reset progress bar
    document.getElementById('progressFill').style.width = '0%';

    // Reset status badge
    const statusBadge = document.getElementById('uploadStatus');
    statusBadge.textContent = 'Processing';
    statusBadge.className = 'status-badge';

    // Hide result message
    document.getElementById('resultMessage').classList.add('hidden');

    // Reset file input
    document.getElementById('fileInput').value = '';
}

// ============================================================================
// Search
// ============================================================================

function initializeSearch() {
    const searchBtn = document.getElementById('searchBtn');
    const searchQuery = document.getElementById('searchQuery');

    searchBtn.addEventListener('click', performSearch);

    searchQuery.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            performSearch();
        }
    });
}

async function performSearch() {
    const query = document.getElementById('searchQuery').value.trim();
    const limit = document.getElementById('searchLimit').value;

    if (!query) {
        showError('Please enter a search query');
        return;
    }

    const resultsDiv = document.getElementById('searchResults');
    resultsDiv.innerHTML = '<div class="loading">Searching...</div>';

    try {
        const response = await fetch(`/api/search?query=${encodeURIComponent(query)}&limit=${limit}`);

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Search failed');
        }

        const results = await response.json();
        displaySearchResults(results);

    } catch (error) {
        resultsDiv.innerHTML = `<div class="empty-state">
            <div class="empty-state-icon">⚠️</div>
            <p>Error: ${error.message}</p>
        </div>`;
    }
}

function displaySearchResults(results) {
    const resultsDiv = document.getElementById('searchResults');

    if (results.length === 0) {
        resultsDiv.innerHTML = `<div class="empty-state">
            <div class="empty-state-icon">🔍</div>
            <p>No results found. Try a different query.</p>
        </div>`;
        return;
    }

    let html = `<p style="margin-bottom: 20px; color: #6c757d;">Found ${results.length} result(s)</p>`;

    results.forEach((result, index) => {
        const similarity = (result.similarity * 100).toFixed(1);
        const content = result.content.length > 300
            ? result.content.substring(0, 300) + '...'
            : result.content;

        html += `
            <div class="search-result">
                <div class="search-result-header">
                    <div class="search-result-meta">
                        <strong>${result.document_name}</strong>
                        ${result.chunk_index !== undefined ? ` (chunk ${result.chunk_index})` : ''}
                    </div>
                    <div class="similarity-score">${similarity}% match</div>
                </div>
                <div class="search-result-content">${escapeHtml(content)}</div>
            </div>
        `;
    });

    resultsDiv.innerHTML = html;
}

// ============================================================================
// Chat
// ============================================================================

function initializeChat() {
    const sendBtn = document.getElementById('sendChatBtn');
    const chatInput = document.getElementById('chatInput');
    const clearBtn = document.getElementById('clearChatBtn');

    console.log('Initializing chat...', { sendBtn, chatInput, clearBtn });

    if (sendBtn) {
        sendBtn.addEventListener('click', () => {
            console.log('Send button clicked');
            sendChatMessage();
        });
    } else {
        console.error('Send button not found!');
    }

    if (chatInput) {
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                console.log('Enter key pressed');
                sendChatMessage();
            }
        });
    } else {
        console.error('Chat input not found!');
    }

    if (clearBtn) {
        clearBtn.addEventListener('click', clearChat);
    } else {
        console.error('Clear button not found!');
    }
}

async function sendChatMessage() {
    const input = document.getElementById('chatInput');
    const query = input.value.trim();

    if (!query) {
        return;
    }

    // Add user message
    addChatMessage('user', query);

    // Clear input
    input.value = '';

    // Add streaming assistant message
    const messageId = addStreamingMessage();

    // Scroll to bottom
    scrollToBottom();

    try {
        const response = await fetch(`/api/chat?query=${encodeURIComponent(query)}&limit=5`, {
            method: 'POST'
        });

        if (!response.ok) {
            throw new Error('Chat request failed');
        }

        // Read the stream
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let sources = null;
        let fullContent = '';

        while (true) {
            const { done, value } = await reader.read();

            if (done) {
                break;
            }

            // Decode the chunk
            buffer += decoder.decode(value, { stream: true });

            // Process complete lines
            const lines = buffer.split('\n');
            buffer = lines.pop(); // Keep incomplete line in buffer

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const dataStr = line.slice(6);
                    try {
                        const data = JSON.parse(dataStr);

                        if (data.type === 'sources') {
                            sources = data.sources;
                        } else if (data.type === 'content') {
                            fullContent += data.content;
                            updateStreamingMessage(messageId, fullContent, sources);
                            scrollToBottom();
                        } else if (data.type === 'done') {
                            // Streaming complete
                            finalizeStreamingMessage(messageId, fullContent, sources);
                        } else if (data.type === 'error') {
                            throw new Error(data.error);
                        }
                    } catch (e) {
                        console.error('Failed to parse SSE data:', e);
                    }
                }
            }
        }

    } catch (error) {
        console.error('Chat error:', error);
        removeStreamingMessage(messageId);
        addChatMessage('assistant', `Sorry, I encountered an error: ${error.message}`);
        scrollToBottom();
    }
}

function addChatMessage(role, content, sources = null) {
    const messagesDiv = document.getElementById('chatMessages');

    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${role}`;

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = role === 'user' ? 'You' : 'AI';

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';

    const textDiv = document.createElement('div');
    textDiv.className = 'message-text';
    textDiv.innerHTML = formatMessageContent(content);
    contentDiv.appendChild(textDiv);

    // Add sources if available
    if (sources && sources.length > 0) {
        const sourcesDiv = document.createElement('div');
        sourcesDiv.className = 'message-sources';

        const sourcesTitle = document.createElement('div');
        sourcesTitle.className = 'message-sources-title';
        sourcesTitle.textContent = 'Sources:';
        sourcesDiv.appendChild(sourcesTitle);

        // Group sources by document name and keep highest similarity
        const uniqueSources = {};
        sources.forEach(source => {
            const docName = source.document_name;
            if (!uniqueSources[docName] || source.similarity > uniqueSources[docName].similarity) {
                uniqueSources[docName] = source;
            }
        });

        // Display unique sources
        Object.values(uniqueSources).forEach(source => {
            const sourceItem = document.createElement('div');
            sourceItem.className = 'source-item';

            const similarity = (source.similarity * 100).toFixed(1);
            sourceItem.innerHTML = `
                <span class="source-name">${escapeHtml(source.document_name)}</span>
                <span class="source-similarity"> (${similarity}% match)</span>
            `;

            sourcesDiv.appendChild(sourceItem);
        });

        contentDiv.appendChild(sourcesDiv);
    }

    messageDiv.appendChild(avatar);
    messageDiv.appendChild(contentDiv);
    messagesDiv.appendChild(messageDiv);
}

function addStreamingMessage() {
    const messagesDiv = document.getElementById('chatMessages');
    const messageId = `streaming-${Date.now()}`;

    const messageDiv = document.createElement('div');
    messageDiv.className = 'chat-message assistant';
    messageDiv.id = messageId;

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = 'AI';

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';

    const textDiv = document.createElement('div');
    textDiv.className = 'message-text';
    textDiv.innerHTML = '<span class="typing-cursor">▋</span>';

    contentDiv.appendChild(textDiv);
    messageDiv.appendChild(avatar);
    messageDiv.appendChild(contentDiv);
    messagesDiv.appendChild(messageDiv);

    return messageId;
}

function updateStreamingMessage(messageId, content, sources) {
    const messageDiv = document.getElementById(messageId);
    if (!messageDiv) return;

    const textDiv = messageDiv.querySelector('.message-text');
    if (textDiv) {
        textDiv.innerHTML = formatMessageContent(content) + '<span class="typing-cursor">▋</span>';
    }
}

function finalizeStreamingMessage(messageId, content, sources) {
    const messageDiv = document.getElementById(messageId);
    if (!messageDiv) return;

    const contentDiv = messageDiv.querySelector('.message-content');
    const textDiv = messageDiv.querySelector('.message-text');

    // Remove cursor
    if (textDiv) {
        textDiv.innerHTML = formatMessageContent(content);
    }

    // Add sources if available
    if (sources && sources.length > 0) {
        const sourcesDiv = document.createElement('div');
        sourcesDiv.className = 'message-sources';

        const sourcesTitle = document.createElement('div');
        sourcesTitle.className = 'message-sources-title';
        sourcesTitle.textContent = 'Sources:';
        sourcesDiv.appendChild(sourcesTitle);

        // Group sources by document name and keep highest similarity
        const uniqueSources = {};
        sources.forEach(source => {
            const docName = source.document_name;
            if (!uniqueSources[docName] || source.similarity > uniqueSources[docName].similarity) {
                uniqueSources[docName] = source;
            }
        });

        // Display unique sources
        Object.values(uniqueSources).forEach(source => {
            const sourceItem = document.createElement('div');
            sourceItem.className = 'source-item';

            const similarity = (source.similarity * 100).toFixed(1);
            sourceItem.innerHTML = `
                <span class="source-name">${escapeHtml(source.document_name)}</span>
                <span class="source-similarity"> (${similarity}% match)</span>
            `;

            sourcesDiv.appendChild(sourceItem);
        });

        contentDiv.appendChild(sourcesDiv);
    }
}

function removeStreamingMessage(messageId) {
    const messageDiv = document.getElementById(messageId);
    if (messageDiv) {
        messageDiv.remove();
    }
}

function clearChat() {
    const messagesDiv = document.getElementById('chatMessages');
    messagesDiv.innerHTML = `
        <div class="chat-message assistant">
            <div class="message-avatar">AI</div>
            <div class="message-content">
                <p>Hello! I'm ready to answer questions about your documents. What would you like to know?</p>
            </div>
        </div>
    `;
}

function scrollToBottom() {
    const messagesDiv = document.getElementById('chatMessages');
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

// ============================================================================
// Documents Management
// ============================================================================

function initializeDocuments() {
    const refreshBtn = document.getElementById('refreshDocumentsBtn');
    refreshBtn.addEventListener('click', loadDocuments);

    // Load initially
    loadDocuments();
}

async function loadDocuments() {
    const container = document.getElementById('documentsContainer');
    container.innerHTML = '<div class="loading">Loading documents...</div>';

    try {
        const response = await fetch('/api/documents');

        if (!response.ok) {
            throw new Error('Failed to load documents');
        }

        const documents = await response.json();
        displayDocuments(documents);

    } catch (error) {
        container.innerHTML = `<div class="empty-state">
            <div class="empty-state-icon">⚠️</div>
            <p>Error loading documents: ${error.message}</p>
        </div>`;
    }
}

function displayDocuments(documents) {
    const container = document.getElementById('documentsContainer');

    if (documents.length === 0) {
        container.innerHTML = `<div class="empty-state">
            <div class="empty-state-icon">📂</div>
            <p>No documents yet. Upload your first document to get started!</p>
        </div>`;
        return;
    }

    let html = `
        <table class="documents-table">
            <thead>
                <tr>
                    <th>Document Name</th>
                    <th>Chunks</th>
                    <th>Processed</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
    `;

    documents.forEach(doc => {
        const processedDate = new Date(doc.processed_at).toLocaleString();

        html += `
            <tr>
                <td class="document-name">${escapeHtml(doc.document_name)}</td>
                <td class="chunk-count">${doc.chunk_count}</td>
                <td>${processedDate}</td>
                <td>
                    <button class="btn btn-danger" onclick="deleteDocument('${escapeHtml(doc.document_name)}')">
                        Delete
                    </button>
                </td>
            </tr>
        `;
    });

    html += '</tbody></table>';
    container.innerHTML = html;
}

async function deleteDocument(documentName) {
    if (!confirm(`Are you sure you want to delete "${documentName}" and all its chunks?`)) {
        return;
    }

    try {
        const response = await fetch(`/api/documents/${encodeURIComponent(documentName)}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Delete failed');
        }

        // Reload documents list
        loadDocuments();

    } catch (error) {
        showError(`Failed to delete document: ${error.message}`);
    }
}

// ============================================================================
// Settings/Configuration
// ============================================================================

function initializeSettings() {
    // Setup backend selector
    const saveBackendBtn = document.getElementById('saveBackendBtn');
    saveBackendBtn.addEventListener('click', saveBackend);

    loadConfig();
}

async function loadConfig() {
    const configDiv = document.getElementById('configDisplay');
    configDiv.innerHTML = '<div class="loading">Loading configuration...</div>';

    try {
        const response = await fetch('/api/config');

        if (!response.ok) {
            throw new Error('Failed to load configuration');
        }

        const config = await response.json();
        displayConfig(config);

        // Set the backend selector to current backend
        const backendSelect = document.getElementById('backendSelect');
        backendSelect.value = config.backend_type;

    } catch (error) {
        configDiv.innerHTML = `<div class="empty-state">
            <div class="empty-state-icon">⚠️</div>
            <p>Error loading configuration: ${error.message}</p>
        </div>`;
    }
}

function displayConfig(config) {
    const configDiv = document.getElementById('configDisplay');

    const items = [
        { label: 'LM Studio URL', value: config.lm_studio_url },
        { label: 'Table Name', value: config.table_name },
        { label: 'Chunk Size', value: config.chunk_size },
        { label: 'Chunk Overlap', value: config.chunk_overlap },
        { label: 'Chunking Strategy', value: config.chunking_strategy },
        { label: 'Semantic Threshold', value: config.semantic_similarity_threshold },
        { label: 'Skip If Exists', value: config.skip_if_exists ? 'Yes' : 'No' }
    ];

    let html = '';
    items.forEach(item => {
        html += `
            <div class="config-item">
                <span class="config-label">${item.label}:</span>
                <span class="config-value">${escapeHtml(String(item.value))}</span>
            </div>
        `;
    });

    configDiv.innerHTML = html;
}

async function saveBackend() {
    const backendSelect = document.getElementById('backendSelect');
    const selectedBackend = backendSelect.value;
    const messageDiv = document.getElementById('backendMessage');
    const saveBtn = document.getElementById('saveBackendBtn');

    // Disable button during save
    saveBtn.disabled = true;
    saveBtn.textContent = 'Saving...';

    // Show info message
    messageDiv.className = 'backend-message info';
    messageDiv.textContent = `Switching to ${selectedBackend}...`;
    messageDiv.classList.remove('hidden');

    try {
        const response = await fetch(`/api/config?backend_type=${selectedBackend}`, {
            method: 'PUT'
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to change backend');
        }

        const result = await response.json();

        // Show success message
        messageDiv.className = 'backend-message success';
        messageDiv.textContent = `✓ ${result.message}`;

        // Reload configuration to update display
        setTimeout(() => {
            loadConfig();
            messageDiv.classList.add('hidden');
        }, 2000);

    } catch (error) {
        // Show error message
        messageDiv.className = 'backend-message error';
        messageDiv.textContent = `✗ Error: ${error.message}`;
    } finally {
        // Re-enable button
        saveBtn.disabled = false;
        saveBtn.textContent = 'Save Backend';
    }
}

// ============================================================================
// Utility Functions
// ============================================================================

function capitalizeFirst(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatMessageContent(content) {
    // Escape HTML first
    let formatted = escapeHtml(content);

    // Convert markdown-style formatting
    // Bold: **text** or __text__
    formatted = formatted.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    formatted = formatted.replace(/__(.+?)__/g, '<strong>$1</strong>');

    // Italic: *text* or _text_
    formatted = formatted.replace(/\*(.+?)\*/g, '<em>$1</em>');
    formatted = formatted.replace(/_(.+?)_/g, '<em>$1</em>');

    // Code: `code`
    formatted = formatted.replace(/`(.+?)`/g, '<code>$1</code>');

    // Line breaks: preserve \n as <br>
    formatted = formatted.replace(/\n/g, '<br>');

    // Lists: convert - or * at start of line to bullets
    formatted = formatted.replace(/^[\-\*]\s+(.+)$/gm, '<li>$1</li>');

    // Wrap consecutive list items in <ul>
    formatted = formatted.replace(/(<li>.*<\/li>(?:<br>)?)+/g, (match) => {
        return '<ul>' + match.replace(/<br>/g, '') + '</ul>';
    });

    return formatted;
}
