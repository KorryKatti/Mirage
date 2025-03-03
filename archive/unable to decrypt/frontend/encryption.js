// Simple and reliable encryption/decryption system
// Uses a consistent algorithm that works reliably across sessions

// Store encryption keys in memory
const encryptionKeys = {};

/**
 * Generate a deterministic key from a username
 * This ensures the same key is generated for the same username every time
 */
function generateKey(username) {
    if (!username) {
        console.error('Cannot generate key for empty username');
        return null;
    }
    
    console.log(`Generating key for: ${username}`);
    
    // Create a simple but consistent hash from the username
    let hash = 0;
    for (let i = 0; i < username.length; i++) {
        const char = username.charCodeAt(i);
        hash = ((hash << 5) - hash) + char;
        hash = hash & hash; // Convert to 32bit integer
    }
    
    // Use the hash to create a fixed-length key (32 characters)
    const charset = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    let key = '';
    
    // Generate 32 characters
    for (let i = 0; i < 32; i++) {
        // Use a different part of the hash for each character
        const index = Math.abs((hash + i * 13) % charset.length);
        key += charset[index];
    }
    
    console.log(`Key generated for ${username}: ${key.substring(0, 5)}...`);
    return key;
}

/**
 * Simple XOR encryption
 * Takes a string message and returns a base64 encoded string
 */
function encryptMessage(message, key) {
    if (!message) {
        console.error('Cannot encrypt empty message');
        return null;
    }
    
    if (!key) {
        console.error('Cannot encrypt without a key');
        return null;
    }
    
    try {
        console.log(`Encrypting message with key: ${key.substring(0, 5)}...`);
        
        // Convert message and key to character arrays
        const msgChars = message.split('');
        const keyChars = key.split('');
        
        // XOR each character with a key character
        const encryptedChars = msgChars.map((char, i) => {
            const msgCode = char.charCodeAt(0);
            const keyCode = keyChars[i % keyChars.length].charCodeAt(0);
            return String.fromCharCode(msgCode ^ keyCode);
        });
        
        // Join and convert to base64
        const encryptedString = encryptedChars.join('');
        const base64 = btoa(encryptedString);
        
        console.log(`Encryption successful, result length: ${base64.length}`);
        return base64;
    } catch (error) {
        console.error('Encryption failed:', error);
        return null;
    }
}

/**
 * Simple XOR decryption
 * Takes a base64 encoded string and returns the original message
 */
function decryptMessage(encryptedBase64, key) {
    if (!encryptedBase64) {
        console.error('Cannot decrypt empty message');
        return 'Error: Empty message';
    }
    
    if (!key) {
        console.error('Cannot decrypt without a key');
        return 'Error: Missing key';
    }
    
    try {
        console.log(`Decrypting message with key: ${key.substring(0, 5)}...`);
        
        // Convert from base64 to string
        let encryptedString;
        try {
            encryptedString = atob(encryptedBase64);
        } catch (e) {
            console.error('Invalid base64 input:', e);
            return 'Error: Invalid encrypted message format';
        }
        
        // Convert encrypted string and key to character arrays
        const encryptedChars = encryptedString.split('');
        const keyChars = key.split('');
        
        // XOR each character with a key character to decrypt
        const decryptedChars = encryptedChars.map((char, i) => {
            const encryptedCode = char.charCodeAt(0);
            const keyCode = keyChars[i % keyChars.length].charCodeAt(0);
            return String.fromCharCode(encryptedCode ^ keyCode);
        });
        
        // Join characters back into a string
        const decryptedMessage = decryptedChars.join('');
        
        console.log(`Decryption successful, result length: ${decryptedMessage.length}`);
        return decryptedMessage;
    } catch (error) {
        console.error('Decryption failed:', error);
        return `Error: Decryption failed - ${error.message}`;
    }
}

/**
 * Initialize encryption for a user
 * Generates and stores the encryption key
 */
function initializeEncryption(username) {
    if (!username) {
        console.error('Cannot initialize encryption for empty username');
        return null;
    }
    
    // Generate the key
    const key = generateKey(username);
    
    // Store in memory and localStorage
    encryptionKeys[username] = key;
    localStorage.setItem(`encryptionKey_${username}`, key);
    
    console.log(`Initialized encryption for ${username}`);
    return key;
}

/**
 * Get the encryption key for a user
 * Retrieves from memory, localStorage, or generates a new one
 */
function getEncryptionKey(username) {
    if (!username) {
        console.error('Cannot get encryption key for empty username');
        return null;
    }
    
    // Try to get from memory first
    if (encryptionKeys[username]) {
        return encryptionKeys[username];
    }
    
    // Try to get from localStorage
    const savedKey = localStorage.getItem(`encryptionKey_${username}`);
    if (savedKey) {
        encryptionKeys[username] = savedKey;
        return savedKey;
    }
    
    // Generate new key if not found
    return initializeEncryption(username);
}

/**
 * Test encryption and decryption
 * Returns detailed information about the process
 */
function testEncryption(message, username) {
    console.log('===== ENCRYPTION TEST =====');
    console.log(`Original message: ${message}`);
    
    const key = getEncryptionKey(username);
    console.log(`Key for ${username}: ${key.substring(0, 5)}...`);
    
    const encrypted = encryptMessage(message, key);
    console.log(`Encrypted: ${encrypted}`);
    
    const decrypted = decryptMessage(encrypted, key);
    console.log(`Decrypted: ${decrypted}`);
    
    const success = message === decrypted;
    console.log(`Success: ${success}`);
    console.log('===== END TEST =====');
    
    return {
        original: message,
        key: key.substring(0, 5) + '...',
        encrypted: encrypted,
        decrypted: decrypted,
        success: success
    };
}

// Export functions
window.generateKey = generateKey;
window.encryptMessage = encryptMessage;
window.decryptMessage = decryptMessage;
window.initializeEncryption = initializeEncryption;
window.getEncryptionKey = getEncryptionKey;
window.testEncryption = testEncryption; 