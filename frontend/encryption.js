// Simple encryption/decryption using CryptoJS
// This is a basic implementation for demonstration purposes

// Generate a random key for encryption
function generateKey() {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    let key = '';
    for (let i = 0; i < 32; i++) {
        key += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return key;
}

// Encrypt a message
function encryptMessage(message, key) {
    // In a real implementation, use a proper encryption library like CryptoJS
    // For demonstration, we'll use a simple XOR encryption
    let encrypted = '';
    for (let i = 0; i < message.length; i++) {
        encrypted += String.fromCharCode(message.charCodeAt(i) ^ key.charCodeAt(i % key.length));
    }
    return btoa(encrypted); // Base64 encode
}

// Decrypt a message
function decryptMessage(encryptedMessage, key) {
    // Decrypt using the same XOR operation
    const encrypted = atob(encryptedMessage); // Base64 decode
    let decrypted = '';
    for (let i = 0; i < encrypted.length; i++) {
        decrypted += String.fromCharCode(encrypted.charCodeAt(i) ^ key.charCodeAt(i % key.length));
    }
    return decrypted;
}

// Store encryption keys for different users
const encryptionKeys = {};

// Initialize encryption for a user
function initializeEncryption(username) {
    if (!encryptionKeys[username]) {
        encryptionKeys[username] = generateKey();
    }
    return encryptionKeys[username];
}

// Get encryption key for a user
function getEncryptionKey(username) {
    return encryptionKeys[username] || initializeEncryption(username);
} 