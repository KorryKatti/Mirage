// File handling functions
let uploadBtn = document.getElementById('upload-btn');
let fileInput = document.getElementById('file-input');
let fileList = document.getElementById('file-list');
let modal = document.querySelector('.modal');
let closeBtn = document.querySelector('.close-btn');
let fileGrid = document.querySelector('.file-grid');

uploadBtn.addEventListener('click', () => {
    fileInput.click();
});

fileInput.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);
    formData.append('channel', currentChannel);

    try {
        showUploadProgress(file.name);
        const response = await fetch('/api/upload', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            },
            body: formData
        });

        if (!response.ok) {
            throw new Error('Upload failed');
        }

        const data = await response.json();
        hideUploadProgress();
        addFileToList(data.file);
    } catch (error) {
        console.error('Error uploading file:', error);
        hideUploadProgress();
        showError('Failed to upload file');
    }
});

function showUploadProgress(filename) {
    const progress = document.createElement('div');
    progress.className = 'upload-progress';
    progress.innerHTML = `
        <div class="file-name">${filename}</div>
        <div class="progress-bar">
            <div class="progress-fill" style="width: 0%"></div>
        </div>
    `;
    document.body.appendChild(progress);

    // Simulate progress (in a real app, you'd use XMLHttpRequest or fetch with progress events)
    let width = 0;
    const interval = setInterval(() => {
        width += 5;
        if (width <= 100) {
            progress.querySelector('.progress-fill').style.width = width + '%';
        } else {
            clearInterval(interval);
        }
    }, 100);
}

function hideUploadProgress() {
    const progress = document.querySelector('.upload-progress');
    if (progress) {
        progress.remove();
    }
}

function addFileToList(file) {
    const li = document.createElement('li');
    li.innerHTML = `
        <div class="file-icon">📄</div>
        <div class="file-info">
            <span class="file-name">${file.original_name}</span>
            <span class="file-meta">
                Uploaded by ${file.uploader} • ${formatFileSize(file.size)}
            </span>
        </div>
    `;
    li.addEventListener('click', () => downloadFile(file.id));
    fileList.appendChild(li);
}

async function loadChannelFiles() {
    if (!currentChannel) return;

    try {
        const response = await fetch(`/api/files/${currentChannel}`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) {
            throw new Error('Failed to load files');
        }

        const data = await response.json();
        fileList.innerHTML = '';
        data.files.forEach(file => addFileToList(file));
    } catch (error) {
        console.error('Error loading files:', error);
        showError('Failed to load channel files');
    }
}

async function downloadFile(fileId) {
    try {
        const response = await fetch(`/api/download/${fileId}`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) {
            throw new Error('Download failed');
        }

        const blob = await response.blob();
        const filename = response.headers.get('Content-Disposition')
            ?.split('filename=')[1]
            ?.replace(/"/g, '') || 'downloaded-file';

        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        a.remove();
    } catch (error) {
        console.error('Error downloading file:', error);
        showError('Failed to download file');
    }
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Update the channel join handler to load files
async function joinChannel(channel) {
    // ... existing channel join code ...
    
    // Load channel files after joining
    await loadChannelFiles();
}

// Add file message handling
function handleMessage(message) {
    // ... existing message handling code ...
    
    if (message.type === 'file') {
        const fileElement = document.createElement('div');
        fileElement.className = 'message file-message';
        fileElement.innerHTML = `
            <span class="timestamp">${formatTimestamp(message.timestamp)}</span>
            <span class="username">${message.username}:</span>
            <a href="#" class="file-download" data-file-id="${message.file.id}">
                📎 ${message.file.original_name} (${formatFileSize(message.file.size)})
            </a>
        `;
        
        fileElement.querySelector('.file-download').addEventListener('click', (e) => {
            e.preventDefault();
            downloadFile(message.file.id);
        });
        
        messageContainer.appendChild(fileElement);
        scrollToBottom();
    }
} 