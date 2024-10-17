# Mirage
# NOT UPDATED TO LATEST UPDATES TO THE APP || USE ISSUES INSTEAD

[![Hacktoberfest 2024](https://img.shields.io/badge/Hacktoberfest-2024-blueviolet)](https://hacktoberfest.com/)

Mirage is a lightweight chat application that prioritizes privacy by not storing messages on the server. It features an easily customizable client and straightforward server hosting using Flask.

## Features

- **Privacy First**: Messages are never stored on the server permanently , ensuring that your conversations remain private.
- **Customizable Client**: Modify the client as per your needs and preferences.
- **Simple Hosting**: Hosting the Mirage server is easy with Python and Flask, so you can set it up without hassle.

## Getting Started

### Prerequisites

To get started, you will need:

- [Python 3](https://www.python.org/downloads/) installed.
- [Flask](https://flask.palletsprojects.com/) for the server.

### Installation

1. Clone the repository:

    ```sh
    git clone https://github.com/korrykatti/mirage.git
    cd mirage
    ```

2. Install the required Python packages:

    ```sh
    pip install -r requirements.txt
    ```

3. Start the Flask server:

    ```sh
    python server.py
    ```

4. Use the custom client to start chatting!

## Contributing

We welcome contributions! This project is participating in **Hacktoberfest 2024**. Check out [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to contribute.

## License

Mirage is open-source software licensed under the [MIT License](LICENSE).

## Contact

If you have questions or suggestions, feel free to open an issue or contribute directly!


# Some bugs

1. The server url is not meant to be opened , that is why you are getting the 404 not found error. You have to run the server.py then run `client.py`
2. You will have to first make a `userinfo.json` file in same folder as `client.py` . Here is what you can paste in it for basic testing
```json
{"username": "user", "email": "user@example.com", "secret_key": "secret"}
```
