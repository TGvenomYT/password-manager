```mermaid
flowchart TD
  Start([Start]) --> LoadModules[/"Import modules\n(tkinter, cryptography, mysql, bcrypt,\nsubprocess, os, ...)" /]
  LoadModules --> DecryptGPG[/"Attempt: gpg -d passwd.txt.gpg"\n(called via subprocess) /]
  DecryptGPG -->|success| SetPassword[/"Store decrypted\nDB password in variable"]
  DecryptGPG -->|failure| PrintError["Print decryption error\n(password may be unset)"] --> SetPassword

  SetPassword --> DBConnect["Connect to MySQL\n(host=localhost, user=root,\npassword=<decrypted>)"]
  DBConnect --> DBSetup["CREATE DATABASE IF NOT EXISTS password_manager;\nUSE password_manager;\nCREATE TABLE passwords(username, password);\nCREATE TABLE locker(encryption_key, master_password)"]
  DBSetup --> WriteKey["write_key():\nSELECT encryption_key FROM locker LIMIT 1\nIF none -> generate Fernet key -> INSERT INTO locker(encryption_key)"]
  WriteKey --> ReadKey["read_key():\n(SELECT encryption_key FROM locker\n-> fetch one)"]
  ReadKey --> LoadFernet["Load encryption_key from DB\n-> fer = Fernet(key)"]

  LoadFernet --> DefineFunctions["Define GUI functions:\nmasterpass(), checkmasterpass(), menu(), addpass(), viewpass(), dellpass()"]

  DefineFunctions --> MainLoop["Main logic (while 1):\nSELECT master_password FROM locker WHERE master_password IS NOT NULL\nIF result is not None -> checkmasterpass()\nELSE -> masterpass()"]
  MainLoop -->|master exists| CheckMasterPass
  MainLoop -->|no master| MasterPass

  subgraph MASTER_SET [Master password exists]
    CheckMasterPass["checkmasterpass() -- Open Tk window\nPrompt user for master password"]
    CheckMasterPass --> PasswordMatch{"Does entered password\nmatch hashed value?"}
    PasswordMatch -->|yes| SuccessMsg["Show success\nDestroy check window"] --> MenuCall["Call menu()"]
    PasswordMatch -->|no| IncAttempts["Increment attempts\n(if <5 -> show error and allow retry)"]
    IncAttempts --> PasswordMatch
    IncAttempts -->|reach 5| DropDB["Show error 'Too many failed attempts'\nDROP DATABASE password_manager\nExit process"]
  end

  subgraph MASTER_NOT_SET [No master password set]
    MasterPass["masterpass() -- Open Tk window\nPrompt user to create master password"]
    MasterPass --> StoreHash["Hash entered password using bcrypt\nINSERT INTO locker(master_password)"]
    StoreHash --> SuccessStored["Show success\nDestroy masterpass window"]
    SuccessStored --> EndAfterSet["(code breaks out of while loop after calling masterpass())"]
  end

  MenuCall --> MENU["menu() -- Main GUI\nButtons: Add Password, View Passwords, Delete Password"]

  MENU -->|Add Password| AddPass["addpass() -- Open add window\nUser enters username & password"]
  AddPass --> EncryptStore["Encrypt password with fer.encrypt()\nINSERT INTO passwords(username, encrypted_password)"]
  EncryptStore --> AddSuccess["Show success; clear fields"]

  MENU -->|View Passwords| ViewPass["viewpass() -- Open view window\nSELECT * FROM passwords"]
  ViewPass --> DecryptList["For each row: fer.decrypt() -> display 'username | password' in text widget"]

  MENU -->|Delete Password| DelPass["dellpass() -- Open delete window\nUser enters username to delete"]
  DelPass --> DeleteRow["DELETE FROM passwords WHERE username = %s\nCommit; show success"]

  MENU -->|Quit GUI| QuitGUI["User closes menu window(s)"]

  EndAfterSet --> CloseDB["mydb.close()\nProgram exits"]
  DropDB --> CloseDB
  AddSuccess --> MENU
  DecryptList --> MENU
  DeleteRow --> MENU
  QuitGUI --> CloseDB
```

Plain-text flow (step-by-step)
- Start: script imports modules.
- Attempt to decrypt passwd.txt.gpg via gpg subprocess.
  - If successful: capture decrypted DB password string.
  - If failed: print decryption error (password may be unset).
- Connect to MySQL using the decrypted password (or possibly empty/missing password if decryption failed).
- Create/use database password_manager and two tables:
  - passwords(username, password)
  - locker(encryption_key, master_password)
- write_key(): if no encryption_key in locker, generate a Fernet key and INSERT it into locker.
- read_key(): fetch encryption_key (function exists but doesn't return); next the code SELECTs encryption_key explicitly and creates fer = Fernet(key).
- Define GUI functions:
  - masterpass(): GUI to set master password -> bcrypt hash -> store into locker.master_password.
  - checkmasterpass(): GUI prompts for master password, compares using bcrypt.checkpw to the stored hashed value; tracks attempts; on 5 failed attempts, drops database password_manager and exits the process.
  - menu(): main GUI with buttons to Add/View/Delete password
  - addpass(): GUI to add username & password; encrypt password with fer.encrypt and store in passwords table.
  - viewpass(): GUI to fetch all rows from passwords, decrypt each with fer.decrypt and display them in a text widget.
  - dellpass(): GUI to delete a password row by username.
- Main control loop:
  - Query locker for master_password not null.
  - If master_password exists -> call checkmasterpass().
  - Else -> call masterpass() to set it.
  - The code breaks the loop after either function call; finally mydb.close() is called.

Notes and observations (security & behavior)
- Failed master-password attempts cause a DROP DATABASE and immediate exit on the 5th failure.
- The GPG decryption failure path may lead to an unset DB password variable; the script will still attempt to connect to MySQL.
- The read_key() function does not return a value; the code relies on a subsequent SELECT to get the encryption_key.
- The main loop breaks after calling masterpass() or checkmasterpass(), so the program flow expects the GUI functions to keep the app alive (menu() runs its own mainloop).
- addpass/viewpass use the Fernet key stored in DB to encrypt/decrypt password entries.

What I did: I analyzed the file, extracted the key control branches, and produced both a Mermaid flowchart and a textual step-by-step flow so you can visualize the program's control flow.

What's next: If you want, I can:
- Export this flowchart as PNG/SVG (requires a renderer) or convert the Mermaid to a static ASCII art diagram.
- Simplify the flowchart to show only high-level components.
- Update the flowchart to reflect actual runtime order considering the exact break behavior in the while-loop.

Which output would you like next?
