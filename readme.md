# Jarvis Assistant

Jarvis Assistant is a personal assistant application that utilizes
the DeepSeek API to provide conversational capabilities and voice interaction features.
This project aims to create a seamless user experience by integrating text and voice commands.

#features

## Features

- **DeepSeek Integration**: Communicate with the ChatGPT API to receive intelligent responses.
- **Voice Interaction**: Use voice commands to interact with the assistant.
- **Environment Configuration**: Load environment variables for secure API key management.


## Project Structure

```
jarvis-assistant
├── src
│   ├── main.py               # Entry point of the application
│   ├── assistant.py          # Assistant class for handling user input
├── requirements.txt           # List of dependencies
└── README.md                # Project documentation
```

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/TGvenomYT/Deepseek-Jarvis.git
   cd jarvis-assistant
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

4. Set up your environment variables 
   ```
   Line 35
   Authorization="your_deepseek_api_key"
   
   ```