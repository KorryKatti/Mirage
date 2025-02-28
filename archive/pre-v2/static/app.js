// Global variables
let token = null;
let username = null;
let currentChannel = '#general';
let currentServer = null;

// DOM Elements
const authScreen = document.getElementById('auth-screen');
const chatScreen = document.getElementById('chat-screen');
const serverStatus = document.getElementById('server-status');
const usernameInput = document.getElementById('username');
const passwordInput = document.getElementById('password');
const loginBtn = document.getElementById('login-btn');
const registerBtn = document.getElementById('register-btn');
const messageInput = document.getElementById('message-input');
const messagesContainer = document.getElementById('messages');
const channelList = document.getElementById('channel-list');
const userList = document.getElementById('user-list');
const channelName = document.getElementById('channel-name');
const channelTopic = document.getElementById('channel-topic');
const currentServerDisplay = document.getElementById('current-server');
const nickLabel = document.getElementById('nick-label');

// Server configuration
async function loadServerConfig() {
    try {
        const response = await fetch('/static/servers.json');
        if (!response.ok) throw new Error('Failed to load server configuration');
        return await response.json();
    } catch (error) {
        console.error('Error loading server configuration:', error);
        showError('Failed to load server configuration');
        return null;
    }
}

// Find best server based on load
async function findBestServer(servers) {
    let bestServer = null;
    let lowestLoad = Infinity;

    for (const server of servers) {
        try {
            const response = await fetch(
                `http://${server.host}:${server.port}/api/server/stats`,
                {
                    headers: {
                        'Accept': 'application/json',
                        'Content-Type': 'application/json'
                    },
                    mode: 'cors'
                }
            );
            if (response.ok) {
                const stats = await response.json();
                const load = (
                    stats.stats.cpu_usage * 0.4 +
                    stats.stats.memory_usage * 0.3 +
                    (stats.stats.active_users_count / server.max_users) * 0.3
                );
                if (load < lowestLoad) {
                    lowestLoad = load;
                    bestServer = server;
                }
            }
        } catch (error) {
            console.error(`Error checking server ${server.id}:`, error);
        }
    }

    if (!bestServer && servers.length > 0) {
        bestServer = servers[0];
    }

    return bestServer;
}

// Authentication
async function register() {
    const username = usernameInput.value.trim();
    const password = passwordInput.value.trim();

    if (!username || !password) {
        showError('Please fill in all fields');
        return;
    }

    try {
        const response = await fetch(`http://${currentServer.host}:${currentServer.port}/api/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, password })
        });

        const data = await response.json();
        if (response.ok) {
            showSuccess('Registration successful! You can now login.');
        } else {
            showError(data.error || 'Registration failed');
        }
    } catch (error) {
        showError('Connection failed');
    }
}

async function login() {
    const username = usernameInput.value.trim();
    const password = passwordInput.value.trim();

    if (!username || !password) {
        showError('Please fill in all fields');
        return;
    }

    try {
        const response = await fetch(`http://${currentServer.host}:${currentServer.port}/api/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, password })
        });

        const data = await response.json();
        if (response.ok) {
            token = data.token;
            window.username = username;
            currentServer = data.server;
            showChatScreen();
            initializeChat();
        } else {
            showError(data.error || 'Login failed');
        }
    } catch (error) {
        showError('Connection failed');
    }
}

// Chat functionality
function showChatScreen() {
    authScreen.classList.add('hidden');
    chatScreen.classList.remove('hidden');
    currentServerDisplay.textContent = `Connected to ${currentServer.id}`;
    nickLabel.textContent = `${username} >`;
}

async function initializeChat() {
    await loadChannels();
    startPolling();
}

async function loadChannels() {
    try {
        const response = await fetch(`http://${currentServer.host}:${currentServer.port}/api/channels`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (response.ok) {
            const data = await response.json();
            updateChannelList(data.channels);
        }
    } catch (error) {
        console.error('Error loading channels:', error);
    }
}

function updateChannelList(channels) {
    channelList.innerHTML = '';
    channels.forEach(channel => {
        const li = document.createElement('li');
        li.textContent = `${channel.name} (${channel.users_count})`;
        li.addEventListener('click', () => joinChannel(channel.name));
        if (channel.name === currentChannel) {
            li.classList.add('active');
        }
        channelList.appendChild(li);
    });
}

async function createChannel(name, topic = '') {
    try {
        const response = await fetch(`http://${currentServer.host}:${currentServer.port}/api/channels/create`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ name, topic })
        });

        if (response.ok) {
            const data = await response.json();
            await loadChannels();
            joinChannel(data.name);
        } else {
            const data = await response.json();
            showError(data.error || 'Failed to create channel');
        }
    } catch (error) {
        showError('Failed to create channel');
    }
}

async function joinChannel(channel) {
    currentChannel = channel;
    channelName.textContent = channel;
    messagesContainer.innerHTML = '';
    await loadChannelTopic(channel);
    await loadChannelFiles();
    sendMessage('/join ' + channel);
    updateActiveChannel();
}

async function loadChannelTopic(channel) {
    try {
        const response = await fetch(`http://${currentServer.host}:${currentServer.port}/api/channels/${channel}`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (response.ok) {
            const data = await response.json();
            channelTopic.textContent = data.topic;
        }
    } catch (error) {
        console.error('Error loading channel topic:', error);
    }
}

function updateActiveChannel() {
    const items = channelList.getElementsByTagName('li');
    for (const item of items) {
        if (item.textContent.startsWith(currentChannel)) {
            item.classList.add('active');
        } else {
            item.classList.remove('active');
        }
    }
}

function sendMessage(content = null) {
    const message = content || messageInput.value.trim();
    if (!message) return;

    const isCommand = message.startsWith('/');
    fetch(`http://${currentServer.host}:${currentServer.port}/api/message`, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            type: isCommand ? 'command' : 'message',
            content: message,
            channel: currentChannel
        })
    }).then(() => {
        if (!content) messageInput.value = '';
    }).catch(error => {
        console.error('Error sending message:', error);
        showError('Failed to send message');
    });
}

let polling = true;
async function startPolling() {
    while (polling) {
        try {
            const response = await fetch(`http://${currentServer.host}:${currentServer.port}/api/poll`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (response.ok) {
                const data = await response.json();
                data.messages.forEach(addMessage);
                if (data.users) {
                    updateUserList(data.users[currentChannel] || []);
                }
            } else if (response.status === 401) {
                polling = false;
                showError('Session expired');
                showAuthScreen();
                return;
            }
        } catch (error) {
            console.error('Polling error:', error);
        }

        await new Promise(resolve => setTimeout(resolve, 1000));
    }
}

function addMessage(message) {
    const messageElement = document.createElement('div');
    messageElement.className = 'message';
    
    // Check if this is a system message
    if (message.startsWith('*')) {
        messageElement.classList.add('system-message');
        
        // Check if this is a file share message
        if (message.includes('shared a file:')) {
            // Extract file information
            const fileMatch = message.match(/shared a file: (.*?) \((.*?)\) - \[Preview\/Download: (\/api\/download\/\d+)\]/);
            if (fileMatch) {
                const [_, filename, size, downloadUrl] = fileMatch;
                
                // Create formatted message with clickable link
                const timestamp = message.split(']')[0] + ']';
                const username = message.split('*')[1].split('shared')[0].trim();
                
                messageElement.innerHTML = `${timestamp} * ${username} shared a file:<br>
                    <div class="file-share">
                        <span class="file-name">${filename}</span>
                        <span class="file-size">(${size})</span>
                        <div class="file-actions">
                            <a href="${downloadUrl}" target="_blank" class="file-action">Download</a>
                            <a href="#" class="file-action preview-link" data-url="${downloadUrl}">Preview</a>
                        </div>
                    </div>`;
                
                // Add click handler for preview
                const previewLink = messageElement.querySelector('.preview-link');
                if (previewLink) {
                    previewLink.addEventListener('click', (e) => {
                        e.preventDefault();
                        previewFile(downloadUrl, filename);
                    });
                }
                
                messagesContainer.appendChild(messageElement);
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
                return;
            }
        }
    }
    
    messageElement.textContent = message;
    messagesContainer.appendChild(messageElement);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function previewFile(url, filename) {
    const ext = filename.split('.').pop().toLowerCase();
    const isImage = ['jpg', 'jpeg', 'png', 'gif'].includes(ext);
    const isText = ['txt', 'md', 'json', 'js', 'css', 'html'].includes(ext);
    
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.innerHTML = `
        <div class="modal-content">
            <div class="modal-header">
                <h3>${filename}</h3>
                <button class="close-btn">×</button>
            </div>
            <div class="modal-body">
                ${isImage ? `<img src="${url}" alt="${filename}" style="max-width: 100%;">` :
                  isText ? '<pre class="text-preview"></pre>' :
                  '<div class="preview-error">Preview not available for this file type</div>'}
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    // Add close handler
    const closeBtn = modal.querySelector('.close-btn');
    closeBtn.addEventListener('click', () => modal.remove());
    modal.addEventListener('click', (e) => {
        if (e.target === modal) modal.remove();
    });
    
    // Load text content if it's a text file
    if (isText) {
        fetch(url, {
            headers: { 'Authorization': `Bearer ${token}` }
        })
        .then(response => response.text())
        .then(text => {
            const pre = modal.querySelector('.text-preview');
            pre.textContent = text;
        })
        .catch(error => {
            console.error('Error loading text preview:', error);
        });
    }
}

function updateUserList(users) {
    userList.innerHTML = '';
    users.forEach(user => {
        const li = document.createElement('li');
        li.textContent = user;
        userList.appendChild(li);
    });
}

// UI helpers
function showError(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.textContent = message;
    document.body.appendChild(errorDiv);
    setTimeout(() => errorDiv.remove(), 5000);
    console.error(message);
}

function showSuccess(message) {
    const successDiv = document.createElement('div');
    successDiv.className = 'success-message';
    successDiv.textContent = message;
    document.body.appendChild(successDiv);
    setTimeout(() => successDiv.remove(), 5000);
    console.log(message);
}

// Event listeners
loginBtn.addEventListener('click', login);
registerBtn.addEventListener('click', register);
messageInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        sendMessage();
    }
});

// Initialize
(async () => {
    const config = await loadServerConfig();
    if (config) {
        currentServer = await findBestServer(config.servers);
        if (currentServer) {
            serverStatus.textContent = `Connected to ${currentServer.id}`;
        } else {
            serverStatus.textContent = 'No servers available';
        }
    }
})(); 