from tkinter import *
from tkinter import messagebox
from cryptography.fernet import Fernet
import os

# Get the current user's home directory
home_directory = os.path.expanduser('~')

# Specify the directory within the user's home directory
directory = os.path.join(home_directory, 'password_manager')

# Ensure the directory exists
if not os.path.exists(directory):
    os.makedirs(directory)

# Specify the full path to the key file
key_file_path = os.path.join(directory, 'key.key')

def write_key():
    with open(key_file_path, 'ab') as file:
        key = Fernet.generate_key()
        file.write(key)

write_key()

def read_key():
    with open(key_file_path, 'rb') as file:
        key = file.read()
    return key

key = read_key()
fer = Fernet(key)
root = Tk()
root.title('Password Manager')
root.geometry('1920x1080')
root.configure(bg='black')

def quit():
    root.destroy()

def view():
    root4 = Tk()
    root4.title('View Passwords')
    root4.geometry('1920x1080')
    root4.configure(bg='black')

    text_file_path = os.path.join(directory, 'text.txt')
    with open(text_file_path, 'r') as f:
        for lines in f.readlines():
            data = lines.rstrip()
            uname, pwd = data.split('|')
            decrypted_pwd = fer.decrypt(pwd.encode()).decode()
            Label(root4, text=uname + '|' + decrypted_pwd, font=('Bold', 20), bg='black', fg='white', bd=5).pack()
    root4.mainloop()

def add():
    root2 = Tk()
    root2.title('Add Password')
    root2.geometry('1920x1080')
    root2.configure(bg='black')

    def add2():
        uname = e.get()
        pwd = e2.get()
        text_file_path = os.path.join(directory, 'text.txt')
        with open(text_file_path, 'a') as f:
            encrypted_file = fer.encrypt(pwd.encode()).decode()
            f.write(uname + '|' + encrypted_file + '\n')

        messagebox.showinfo('Success', 'Password Added Successfully')
        e.delete(0, END)
        e2.delete(0, END)

    Label(root2,
          text='Enter Username:',
          font=('Bold', 20),
          bg='black',
          fg='red',
          bd=5).grid(row=0,
                     column=0,
                     padx=0,
                     pady=100)
    e = Entry(root2,
              font=('Bold', 20),
              bg='black',
              fg='white',
              bd=5)
    e.grid(row=0,
           column=1,
           padx=0,
           pady=100)
    Label(root2,
          text='Enter Password:',
          font=('Bold', 20),
          bg='black',
          fg='red',
          bd=5).grid(row=1,
                     column=0,
                     padx=0,
                     pady=100)
    e2 = Entry(root2,
               font=('Bold', 20),
               bg='black',
               fg='white',
               bd=5,
               show='*')
    e2.grid(row=1,
            column=1,
            padx=0,
            pady=100)
    button = Button(root2,
                    text='Add Password',
                    font=('Bold', 20),
                    bg='black',
                    fg='red',
                    bd=5,
                    command=add2)
    button.grid(row=2,
                column=1,
                padx=0,
                pady=100)
    root2.mainloop()

Label(root,
      text=' Main Menu',
      font=('Bold', 20),
      bg='black',
      fg='white',
      bd=5).grid(row=0,
                 column=3,
                 padx=884,
                 pady=0)
Button(root,
       text='Add Password',
       font=('Bold', 25), bg='black',
       fg='white',
       bd=5,
       command=add).grid(row=3,
                         column=3,
                         padx=870,
                         pady=100)
Button(root,
       text='View Passwords',
       font=('Bold', 25),
       bg='black',
       fg='white',
       bd=5,
       command=view).grid(row=4,
                          column=3,
                          padx=870,
                          pady=0)
Button(root,
       text='Quit',
       font=('Bold', 25),
       bg='black',
       fg='white',
       bd=5,
       command=quit).grid(row=5,
                          column=3,
                          padx=870,
                          pady=100)
root.mainloop()
