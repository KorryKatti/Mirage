# Mirage - Privacy-Focused Chat & Blog Platform

Mirage is a privacy-focused, encrypted chat application with integrated blogging features. It uses a combination of P2P messaging and relay servers, allowing users to communicate securely while also maintaining personalized blogs.

## Features

- **End-to-End Encrypted Messaging**: Messages are encrypted using client-side encryption.
- **Temporary Message Storage**: Messages expire after a set duration.
- **File Transfers**: Share files using URLs, with images auto-rendering via Markdown.
- **User Profiles & Blogs**: Customizable using HTML/CSS, with images fetched via URLs.
- **Reactions & Threaded Comments**: For blogs and messages.
- **Jitsi Integration for Calls**: Leveraging free Jitsi Meet servers for video/audio calls.

## Tech Stack

### Backend:
- **Language:** Python (FastAPI)
- **Database:** SQLite (for testing), MongoDB (for production)
- **Authentication:** JWT (JSON Web Tokens) for secure login
- **Messaging:** Long polling (since free cloud services don't support WebSockets)
- **File Handling:** Free file transfer API (users provide URLs instead of uploads)
- **Encryption:** E2EE (Libsodium or AES-256)
- **CORS Support:** Enabled for cross-origin requests

### Frontend:
- **Framework:** CDN-based approaches (no Node.js to reduce costs)
- **Markdown Support:** Allows messages to render images and rich text

## Setup

### Backend Setup

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/mirage.git
   cd mirage
   ```

2. Create a virtual environment and install dependencies:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the root directory with the following variables:
   ```
   SECRET_KEY=your_secret_key
   ```

4. Run the backend server:
   ```
   uvicorn mirage.main:app --reload
   ```

Note: The application uses SQLite for testing purposes. For production, you can switch to MongoDB by modifying the database.py file.

### Frontend Setup

1. Open the `frontend/index.html` file in a web browser.

## Usage

1. **Signup/Login**: Create an account or log in to an existing account.
2. **Chat**: Send encrypted messages to other users.
3. **File Sharing**: Share files by providing URLs.
4. **Blogs**: Create and read blog posts.
5. **Video/Audio Calls**: Start a Jitsi call and share the link with others.

## Security Features

- **End-to-End Encryption**: Messages are encrypted on the client side before being sent to the server.
- **Temporary Storage**: Messages are stored temporarily and expire after a set duration.
- **JWT Authentication**: Secure authentication using JSON Web Tokens.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 