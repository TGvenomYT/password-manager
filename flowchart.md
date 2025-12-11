```mermaid
flowchart TD
  %% Layout & styles for a cleaner design
  %% Nodes
  Start([Start]):::startEnd --> LoadModules[/"Import modules\n(tkinter, cryptography, mysql, bcrypt,\nsubprocess, os, ...)"/]:::process
  LoadModules --> DecryptGPG[/"Attempt: gpg -d passwd.txt.gpg"\n(called via subprocess) /]:::process

  DecryptGPG -->|success| SetPassword[/"Store decrypted\nDB password in variable"/]:::success
  DecryptGPG -->|failure| PrintError["Print decryption error\n(password may be unset)"]:::danger --> SetPassword

  SetPassword --> DBConnect[(MySQL Connect)\nhost=localhost, user=root, password=<decrypted>]:::db
  DBConnect --> DBSetup["DB setup:\nCREATE DATABASE IF NOT EXISTS password_manager;\nUSE password_manager;\nCREATE TABLE passwords(username, password);\nCREATE TABLE locker(encryption_key, master_password)"]:::process

  DBSetup --> WriteKey["write_key():\nSELECT encryption_key FROM locker LIMIT 1\nIF none -> generate Fernet key -> INSERT INTO locker(encryption_key)"]:::process
  WriteKey --> ReadKey["read_key():\nSELECT encryption_key FROM locker -> fetch one"]:::process
  ReadKey --> LoadFernet["Load encryption_key -> fer = Fernet(key)"]:::secure

  LoadFernet --> DefineFunctions["Define GUI functions:\nmasterpass(), checkmasterpass(), menu(), addpass(), viewpass(), dellpass()"]:::process

  DefineFunctions --> MainLoop["Main control loop:\nWHILE true -> SELECT master_password FROM locker\nIF exists -> checkmasterpass()\nELSE -> masterpass()"]:::process

  %% Master password exists branch
  MainLoop -->|master exists| CheckMasterPass
  MainLoop -->|no master| MasterPass

  subgraph MASTER_SET [Master password exists]
    style MASTER_SET fill:#ffffff,stroke:#1a73e8,stroke-width:1px
    CheckMasterPass["checkmasterpass() -- Open Tk window\nPrompt user for master password"]:::process
    CheckMasterPass --> PasswordMatch{"Does entered password\nmatch hashed value?"}:::decision
    PasswordMatch -->|yes| SuccessMsg["Show success\nDestroy check window"]:::success --> MenuCall["Call menu()"]:::process
    PasswordMatch -->|no| IncAttempts["Increment attempts\n(if <5 -> show error and allow retry)"]:::warning
    IncAttempts --> PasswordMatch
    IncAttempts -->|reach 5| DropDB["Show error 'Too many failed attempts'\nDROP DATABASE password_manager\nExit process"]:::danger
  end

  subgraph MASTER_NOT_SET [No master password set]
    style MASTER_NOT_SET fill:#ffffff,stroke:#1a73e8,stroke-width:1px
    MasterPass["masterpass() -- Open Tk window\nPrompt user to create master password"]:::process
    MasterPass --> StoreHash["Hash entered password using bcrypt\nINSERT INTO locker(master_password)"]:::secure
    StoreHash --> SuccessStored["Show success\nDestroy masterpass window"]:::success
    SuccessStored --> EndAfterSet["(code breaks out of while loop after calling masterpass())"]:::process
  end

  MenuCall --> MENU["menu() -- Main GUI\nButtons: Add Password, View Passwords, Delete Password"]:::process

  %% Add password
  MENU -->|Add Password| AddPass["addpass() -- Open add window\nUser enters username & password"]:::process
  AddPass --> EncryptStore["Encrypt password with fer.encrypt()\nINSERT INTO passwords(username, encrypted_password)"]:::secure
  EncryptStore --> AddSuccess["Show success; clear fields"]:::success

  %% View passwords
  MENU -->|View Passwords| ViewPass["viewpass() -- Open view window\nSELECT * FROM passwords"]:::process
  ViewPass --> DecryptList["For each row: fer.decrypt() -> display 'username | password' in text widget"]:::secure

  %% Delete password
  MENU -->|Delete Password| DelPass["dellpass() -- Open delete window\nUser enters username to delete"]:::process
  DelPass --> DeleteRow["DELETE FROM passwords WHERE username = %s\nCommit; show success"]:::success

  MENU -->|Quit GUI| QuitGUI["User closes menu window(s)"]:::process

  EndAfterSet --> CloseDB["mydb.close()\nProgram exits"]:::process
  DropDB --> CloseDB
  AddSuccess --> MENU
  DecryptList --> MENU
  DeleteRow --> MENU
  QuitGUI --> CloseDB

  %% Legend for visual clarity
  subgraph LEGEND [Legend]
    direction LR
    L_start([Start/End]):::startEnd
    L_proc([Process]):::process
    L_secure([Encryption / Sensitive]):::secure
    L_db([(Database)]):::db
    L_ok([Success]):::success
    L_warn([Warning]):::warning
    L_err([Error / Danger]):::danger
  end

  %% Classes (colors & styling)
  classDef startEnd fill:#1a73e8,stroke:#0b57d0,color:#ffffff,stroke-width:2px;
  classDef process fill:#eef6ff,stroke:#90b7ff,color:#022c43,stroke-width:1px;
  classDef secure fill:#fff8e1,stroke:#ffcc66,color:#6b4b00,stroke-width:1px;
  classDef db fill:#f1f3f5,stroke:#adb5bd,color:#222,stroke-width:1px;
  classDef success fill:#d4edda,stroke:#28a745,color:#155724,stroke-width:1px;
  classDef warning fill:#fff3cd,stroke:#f0ad4e,color:#856404,stroke-width:1px;
  classDef danger fill:#f8d7da,stroke:#dc3545,color:#721c24,stroke-width:1px;
  classDef decision fill:#ffffff,stroke:#343a40,color:#343a40,stroke-width:1.5px,stroke-dasharray: 3 2;

  %% Assign classes explicitly where needed (redundant safe-guard)
  class Start startEnd;
  class LoadModules,DecryptGPG,DBSetup,WriteKey,ReadKey,DefineFunctions,MainLoop,CheckMasterPass,MasterPass,MenuCall,MENU,AddPass,ViewPass,DelPass,QuitGUI process;
  class SetPassword,SuccessMsg,SuccessStored,AddSuccess,DeleteRow success;
  class PrintError,DropDB danger;
  class LoadFernet,StoreHash,EncryptStore,DecryptList secure;
  class DBConnect,LEGEND db;
  class PasswordMatch decision;
  class IncAttempts warning;
```
