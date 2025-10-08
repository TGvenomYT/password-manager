**Password Manager**

This is a simple password manager that uses the Fernet encryption and MYSQL database algorithm to store passwords. The passwords are stored in a DB called password_manager in the 'passwords' table. The key used to encrypt the passwords is stored in a table called locker in the DB password_manager. The key is generated when the program is run for the first time. The key is used to encrypt and decrypt the passwords. The program has a simple command line interface that allows the user to add, view, and delete passwords. The program also has a simple graphical user interface that allows the user to 
add, view, and delete passwords.

Features
- Add a password
- View a password
- Delete a password

password_manager/
├── password_manager MARK IVI.py
├── requirements.txt
├── README.md
└── data/
    ├── locker
    └── passwords

The  SQL password is stored in password.text.gpg file(encrypted).The user and password given are stored in the table "password_manage" after encryption of  the given password.
Therefore this software securely stores your passwords locally on your machine


Installation

1. Clone the repository:
   ```
   git clone https://github.com/TGvenomYT/Deepseek-Jarvis.git
   cd jarvis-assistant
   ```

2. install and setup the dependencies 

 3.  .click on 'PasswordManager v-2.4.0


