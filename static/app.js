class MirageClient {
    constructor() {
        this.servers = null;
        this.currentServer = null;
        this.token = null;
        this.username = null;
        this.currentChannel = '#general';
        this.polling = false;

        // Load servers configuration
        this.loadServers();

        // Bind UI elements
        this.bindElements();
        this.bindEvents();
    }

    bindElements() {
        // Screens
        this.authScreen = document.getElementById('auth-screen');
        this.chatScreen = document.getElementById('chat-screen');
        
        // Auth elements
        this.serverStatus = document.getElementById('server-status');
        this.usernameInput = document.getElementById('username');
        this.passwordInput = document.getElementById('password');
        this.loginBtn = document.getElementById('login-btn');
        this.registerBtn = document.getElementById('register-btn');
        
        // Chat elements
        this.currentServerLabel = document.getElementById('current-server');
        this.channelList = document.getElementById('channel-list');
        this.userList = document.getElementById('user-list');
        this.channelName = document.getElementById('channel-name');
        this.channelTopic = document.getElementById('channel-topic');
        this.messages = document.getElementById('messages');
        this.nickLabel = document.getElementById('nick-label');
        this.messageInput = document.getElementById('message-input');
    }

    bindEvents() {
        this.loginBtn.addEventListener('click', () => this.login());
        this.registerBtn.addEventListener('click', () => this.register());
        this.messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.sendMessage();
        });
    }

    async loadServers() {
        try {
            const response = await fetch('servers.json');
            this.servers = await response.json();
            await this.findBestServer();
        } catch (error) {
            this.serverStatus.textContent = 'Error: Could not load server list';
        }
    }

    async findBestServer() {
        let bestServer = null;
        let lowestLoad = Infinity;

        for (const server of this.servers.servers) {
            try {
                const response = await fetch(
                    `http://${server.host}:${server.port}/api/server/stats`
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
                console.log(`Server ${server.id} not available`);
            }
        }

        if (bestServer) {
            this.currentServer = bestServer;
            this.serverStatus.textContent = 
                `Connected to ${bestServer.id} (${bestServer.host}:${bestServer.port})`;
        } else {
            this.serverStatus.textContent = 'Error: No servers available';
        }
    }

    getServerUrl() {
        return `http://${this.currentServer.host}:${this.currentServer.port}/api`;
    }

    async register() {
        if (!this.currentServer) {
            await this.findBestServer();
            if (!this.currentServer) return;
        }

        const username = this.usernameInput.value.trim();
        const password = this.passwordInput.value.trim();

        if (!username || !password) {
            alert('Please fill in all fields');
            return;
        }

        try {
            const response = await fetch(`${this.getServerUrl()}/register`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });

            const data = await response.json();
            if (response.ok) {
                alert('Registration successful! You can now login.');
            } else {
                alert(data.error || 'Registration failed');
            }
        } catch (error) {
            alert('Connection failed');
        }
    }

    async login() {
        if (!this.currentServer) {
            await this.findBestServer();
            if (!this.currentServer) return;
        }

        const username = this.usernameInput.value.trim();
        const password = this.passwordInput.value.trim();

        if (!username || !password) {
            alert('Please fill in all fields');
            return;
        }

        try {
            const response = await fetch(`${this.getServerUrl()}/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });

            const data = await response.json();
            if (response.ok) {
                this.token = data.token;
                this.username = data.username;
                this.currentServer = data.server;
                this.initializeChat(data.channels);
            } else {
                alert(data.error || 'Login failed');
            }
        } catch (error) {
            alert('Connection failed');
        }
    }

    initializeChat(channels) {
        this.authScreen.classList.add('hidden');
        this.chatScreen.classList.remove('hidden');
        
        this.currentServerLabel.textContent = 
            `${this.currentServer.id} (${this.currentServer.host}:${this.currentServer.port})`;
        this.nickLabel.textContent = `${this.username} >`;
        
        this.updateChannelList(channels);
        this.startPolling();
    }

    updateChannelList(channels) {
        this.channelList.innerHTML = '';
        for (const channel of channels) {
            const li = document.createElement('li');
            li.textContent = channel;
            li.addEventListener('click', () => this.switchChannel(channel));
            this.channelList.appendChild(li);
        }
    }

    switchChannel(channel) {
        this.currentChannel = channel;
        this.channelName.textContent = channel;
        this.messages.innerHTML = '';
    }

    async sendMessage() {
        const message = this.messageInput.value.trim();
        if (!message) return;

        const data = message.startsWith('/') 
            ? { type: 'command', content: message, channel: this.currentChannel }
            : { type: 'message', content: message, channel: this.currentChannel };

        try {
            const response = await fetch(`${this.getServerUrl()}/message`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': this.token
                },
                body: JSON.stringify(data)
            });

            if (response.ok) {
                this.messageInput.value = '';
            } else {
                const error = await response.json();
                this.addMessage(`Error: ${error.error || 'Failed to send message'}`);
            }
        } catch (error) {
            this.addMessage('Error: Connection failed');
        }
    }

    addMessage(message) {
        const div = document.createElement('div');
        div.className = message.startsWith('*') ? 'message system-message' : 'message';
        div.textContent = message;
        this.messages.appendChild(div);
        this.messages.scrollTop = this.messages.scrollHeight;
    }

    async pollMessages() {
        while (this.polling) {
            try {
                const response = await fetch(`${this.getServerUrl()}/poll`, {
                    headers: { 'Authorization': this.token }
                });

                if (response.ok) {
                    const data = await response.json();
                    for (const message of data.messages) {
                        this.addMessage(message);
                    }
                    this.updateUserLists(data.users);
                } else if (response.status === 401) {
                    this.polling = false;
                    alert('Session expired');
                    location.reload();
                    return;
                }
            } catch (error) {
                console.log('Polling error:', error);
            }

            await new Promise(resolve => setTimeout(resolve, 1000));
        }
    }

    updateUserLists(users) {
        this.userList.innerHTML = '';
        const channelUsers = users[this.currentChannel] || [];
        for (const user of channelUsers) {
            const li = document.createElement('li');
            li.textContent = user;
            this.userList.appendChild(li);
        }
    }

    startPolling() {
        this.polling = true;
        this.pollMessages();
    }
}

// Initialize the client when the page loads
window.addEventListener('load', () => {
    window.mirageClient = new MirageClient();
}); 