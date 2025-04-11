Password Manager

This is a simple password manager that uses the Fernet encryption algorithm to store passwords. The passwords are stored in a file called `text.txt` in the `data` directory. The key used to encrypt the passwords is stored in a file called `key.key` in the `data` directory. The key is generated when the program is run for the first time. The key is used to encrypt and decrypt the passwords. The program has a simple command line interface that allows the user to add, view, and delete passwords. The program also has a simple graphical user interface that allows the user to 
add, view, and delete passwords.

Features
- Add a password
- View a password
- Delete a password

password_manager/
├── password_manager_with_GUI.py
├── requirements.txt
├── README.md
└── data/
    ├── key.key
    └── text.txt

Installation

1. Clone the repository:
    ```
git clone https://github.com/TGvenomYT/password-manager
    ```

2. Change directory:
   ```
cd jarvis-assistant
   ```


3. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   

4. Install the required packages:
   ```
   pip install -r requirements.txt
   ```


