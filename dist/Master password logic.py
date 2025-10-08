'''
from bcrypt import hashpw, gensalt

# User's password (convert to bytes)
password = b"MySecurePassword"

# Generate a salt and hash the password
hashed_password = hashpw(password, gensalt())

# Store `hashed_password` in a database
print("Hashed Password:", hashed_password)

from bcrypt import checkpw

# User enters password
user_input = b"MSecurePassword"

# Verify password
if checkpw(user_input, hashed_password):
    print("Login successful!")
else:
    print("Incorrect password.")
'''


from pathlib import Path
from tkinter import Tk, Canvas, Entry, Text, Button, PhotoImage,Label,Toplevel,Frame,Scrollbar
from cryptography.fernet import Fernet
import mysql.connector as mysql
from tkinter import messagebox
import os
from bcrypt import hashpw, gensalt,checkpw


# Database connection
mydb = mysql.connect(
    host="localhost",
    user="root",
    password='Niranjan2022',
    auth_plugin='mysql_native_password',
    unix_socket="/var/run/mysqld/mysqld.sock"
)
cur= mydb.cursor()

cur.execute("CREATE DATABASE IF NOT EXISTS password_manager")
cur.execute("USE password_manager")
cur.execute("CREATE TABLE IF NOT EXISTS passwords (username VARCHAR(255), password VARCHAR(255))")
mydb.commit()
cur.execute("CREATE TABLE IF NOT EXISTS  locker(encryption_key char(255), master_password char(255))")
mydb.commit()


#initialize the key for encryption

def write_key():
    cur.execute("SELECT encryption_key FROM locker LIMIT 1")
    result = cur.fetchone()
    if result:
        print('Key already exists in the database.')
    else:
       key=Fernet.generate_key()
       cur.execute("INSERT INTO locker (encryption_key)  VALUES (%s)", (key.decode(),))
       mydb.commit()

write_key()

def read_key():   
    cur.execute("SELECT encryption_key FROM locker ")
    result = cur.fetchone()
    
read_key()

cur.execute("SELECT encryption_key FROM locker ")
result = cur.fetchone()
keyy= result[0].encode()

fer = Fernet(keyy)

def masterpass():   
    root=Tk()
    root.geometry("570x270")
    root.resizable(False,False)
    root.configure(bg="black")
    root.title('Master Password input')
    messagebox.showinfo('enter the master password', 'Enter the master password correctly as you cannot change it afterwards')
    entry=Entry(root, borderwidth=3,show='*')
    entry.place(x=121,y=72,width=320,height=43)

    def store():
        password = entry.get()
        # Hash the password
        hashed_password = hashpw(password.encode(), gensalt())
        # Store the hashed password in the database
        cur.execute("UPDATE locker SET master_password=%s WHERE encryption_key IS NOT NULL", (hashed_password.decode(),))
        mydb.commit()
        messagebox.showinfo('Success', 'Password Stored Successfully')
        entry.delete(0, 'end')

    button=Button(root,
                  text='Submit',
                  bg='black',
                    fg='white',
                    command=store
    )
    button.place(x=217,y=132,width=147,height=31)
    root.mainloop()


def checkmasterpass():
    root2=Tk()
    root2.geometry("570x270")
    root2.resizable(False,False)
    root2.configure(bg="black")
    root2.title('Master Password input')
    messagebox.showinfo('enter the master password', 'Enter the master password correctly to open the software')
    entry=Entry(root2, borderwidth=3,show='*')
    entry.place(x=121,y=72,width=320,height=43)

    def check():
        root2.withdraw()
        inp = entry.get()
        # Hash the password
        
        # Store the hashed password in the database
        cur.execute("SELECT master_password FROM locker WHERE encryption_key IS NOT NULL")
       
        result = cur.fetchone()
   
        if checkpw(inp.encode(),result[0].encode()):
            messagebox.showinfo('Success', 'Password Matched Successfully')
            entry.delete(0, 'end')
            
        else:
            messagebox.showerror('Error', 'Password Not Matched')

    button=Button(root2,
                  text='Submit',
                  bg='black',
                    fg='white',
                    command=check
    )
    button.place(x=217,y=132,width=147,height=31)
    root2.mainloop()


checkmasterpass()