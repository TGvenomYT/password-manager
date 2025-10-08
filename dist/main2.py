from pathlib import Path
from tkinter import Tk, Canvas, Entry, Text, Button, PhotoImage,Label,Toplevel,Frame,Scrollbar
from cryptography.fernet import Fernet
import mysql.connector as mysql
from tkinter import messagebox
import os
from bcrypt import hashpw, gensalt,checkpw
import subprocess



gpg_file = "passwd.txt.gpg"

result = subprocess.run(
    ["gpg", "-d", gpg_file],
    capture_output=True,
    text=True
)

if result.returncode == 0:
    password = result.stdout.strip()  # Remove whitespace/newlines
  
else:
    print("Decryption failed:", result.stderr)


# Database connection
mydb = mysql.connect(
    host="localhost",
    user="root",
    password='{}'.format( password),
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
    cur.execute("SELECT encryption_key FROM locker where encryption_key IS NOT NULL")
    result = cur.fetchone()
    
read_key()

cur.execute("SELECT encryption_key FROM locker where encryption_key IS NOT NULL")
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
        hashed_password = hashpw(password.encode(), gensalt()).decode()
        # Store the hashed password in the database
        cur.execute("INSERT INTO locker (master_password) VALUES (%s)", (hashed_password,))
        mydb.commit()
        messagebox.showinfo('Success', 'Password Stored Successfully')
        entry.delete(0, 'end')
        root.destroy()

    button=Button(root,
                  text='Submit',
                  bg='black',
                    fg='white',
                    command=store
    )
    button.place(x=217,y=132,width=147,height=31)
    

    root.mainloop()
   



# Function to check the master password




def checkmasterpass():
    root2=Tk()
    root2.geometry("570x270")
    root2.resizable(False,False)
    root2.configure(bg="black")
    root2.title('Master Password input')
    messagebox.showinfo('enter the master password', 'Enter the master password correctly to open the software')
    entry=Entry(root2, borderwidth=3,show='*')
    entry.place(x=121,y=72,width=320,height=43)

    attempts = {'count': 0}

    def check():
        inp = entry.get()
        cur.execute("SELECT master_password FROM locker WHERE master_password IS NOT NULL")
        result = cur.fetchone()
        if result and result[0]:
            if checkpw(inp.encode(), result[0].encode()):
                  messagebox.showinfo('Success', 'Password Matched Successfully')
                  entry.delete(0, 'end')
                  root2.destroy()
                  menu()
            else:
                attempts['count'] += 1
                if attempts['count'] >= 5:
                    messagebox.showerror('Error', 'Too many failed attempts. Database will be dropped.')
                    root2.destroy()
                    cur.execute("DROP DATABASE password_manager")
                    mydb.commit()
                    os._exit(0)     
                else:
                    messagebox.showerror('Error', f'Password Not Matched. Attempt {attempts["count"]}/5')
        
        else:
            messagebox.showerror('Error', 'No master password set.')
        
        
    
    button=Button(root2,
                  text='Submit',
                  bg='black',
                    fg='white',
                    command=check
        
    )
    button.place(x=217,y=132,width=147,height=31)
    
    root2.mainloop()
    





# Function to create the menu window






def menu():
    OUTPUT_PATH = Path(__file__).parent
    # Use os.path.dirname to get the directory and os.path.join to create the full path
    ASSETS_PATH = os.path.join(OUTPUT_PATH, "login page", "login page assets", "frame0")
    ASSETS_PATH = Path(ASSETS_PATH)  # Convert back to Path object for consistency

    def relative_to_assets(path: str) -> Path:
        return ASSETS_PATH / Path(path)
    


    window = Tk()

    window.geometry("981x500")
    window.configure(bg = "#A9CEE9")
    window.title('Menu')

    canvas = Canvas(
        window,
        bg = "#A9CEE9",
        height = 500,
        width = 981,
        bd = 0,
        highlightthickness = 0,
        relief = "ridge"
    )

    canvas.place(x = 0, y = 0)
    image_image_1 = PhotoImage(
        file=relative_to_assets("image_1.png"))
    image_1 = canvas.create_image(
        941.0,
        473.0,
        image=image_image_1
    )

    image_image_2 = PhotoImage(
        file=relative_to_assets("image_2.png"))
    image_2 = canvas.create_image(
        874.0,
        475.0,
        image=image_image_2
    )

    image_image_3 = PhotoImage(
        file=relative_to_assets("image_3.png"))
    image_3 = canvas.create_image(
        798.0,
        471.0,
        image=image_image_3
    )

    image_image_4 = PhotoImage(
        file=relative_to_assets("image_4.png"))
    image_4 = canvas.create_image(
        849.0,
        129.0,
        image=image_image_4
    )

    image_image_5 = PhotoImage(
        file=relative_to_assets("image_5.png"))
    image_5 = canvas.create_image(
        225.0,
        250.0,
        image=image_image_5
    )

    image_image_6 = PhotoImage(
        file=relative_to_assets("image_6.png"))
    image_6 = canvas.create_image(
        572.0,
        373.0,
        image=image_image_6
    )

    button_image_1 = PhotoImage(
        file=relative_to_assets("button_1.png"))
    button_1 = Button(
        window,
        text='Add password',
        image=button_image_1,
        compound='center',
        borderwidth=0,
        highlightthickness=0,
        relief="flat",
        command=addpass


    )
    button_1.place(
        x=515.0,
        y=70.0,
        width=190.0,
        height=48.0
    )

    button_image_2 = PhotoImage(
        file=relative_to_assets("button_2.png"))
    button_2 = Button(
        window,
        text='View Password',
        image=button_image_2,
        compound='center',
        borderwidth=0,
        highlightthickness=0,
        command=lambda: viewpass(), 
        relief="flat"
    )
    button_2.place(
        x=515.0,
        y=163.0,
        width=190.0,
        height=48.0
    )

    button_image_3 = PhotoImage(
        file=relative_to_assets("button_3.png"))
    button_3 = Button(
        window,
        text='Delete Password',
        compound='center',
        image=button_image_3,
        borderwidth=0,
        highlightthickness=0,
        command=dellpass,                           
        relief="flat"
    )

    button_3.place(
        x=753.0,
        y=322.0,
        width=127.0,
        height=37.0
    )

    canvas.create_text(
        540.0,
        88.0,
        anchor="nw",
        text="Add New Password",
        fill="#00517A",
        font=("Inter", 15 * -1)

    )

    canvas.create_text(
        552.0,
        178.0,
        anchor="nw",
        text="View Passwords",
        fill="#60006F",
        font=("Inter", 15 * -1)
    )

    canvas.create_text(
        797.0,
        328.0,
        anchor="nw",
        text="Quit\n",
        fill="#000000",
        font=("Inter", 20 * -1)
    )
    window.resizable(False, False)
    window.mainloop()
   






# Function to add password


 



def addpass():
    OUTPUT_PATH = Path(__file__).parent
    # Use os.path.dirname to get the directory and os.path.join to create the full path
    ASSETS_PATH = os.path.join(OUTPUT_PATH, "add pass", "add password assets", "frame0")
    ASSETS_PATH = Path(ASSETS_PATH)  # Convert back to Path object for consistency

    def relative_to_assets(path: str) -> Path:
        return ASSETS_PATH / Path(path)
  

    window2 = Toplevel()

    window2.geometry("829x506")
    window2.configure(bg = "#69F8B1")
    window2.title('Add Passord')


    canvas = Canvas(
        window2,
        bg = "#69F8B1",
        height = 506,
        width = 829,
        bd = 0,
        highlightthickness = 0,
        relief = "ridge"
    )

    canvas.place(x = 0, y = 0)
    
    window2.image_image_1 = PhotoImage(
        file=relative_to_assets("image_1.png"))
    image_1 = canvas.create_image(
        414.0,
        253.0,
        image=window2.image_image_1
    )

    canvas.create_rectangle(
        100.0,
        84.0,
        442.0,
        131.0,
        fill="#FFFFFF",
        outline="")

    canvas.create_rectangle(
        100.0,
        206.0,
        442.0,
        253.0,
        fill="#FFFFFF",
        outline="")

    canvas.create_text(
        96.0,
        54.0,
        anchor="nw",
        text="Enter Username:",
        fill="#000000",
        font=("Inter", 20 * -1)
    )

    canvas.create_text(
        100.0,
        176.0,
        anchor="nw",
        text="Enter Password:",
        fill="#000000",
        font=("Inter", 20 * -1)
    )

    canvas.create_text(
        385.0,
        368.0,
        anchor="nw",
        text="Quit",
        fill="#FFFFFF",
        font=("Inter", 20 * -1)
    )

    canvas.create_text(
        611.0,
        147.0,
        anchor="nw",
        text="SUBMIT\n",
        fill="#000000",
        font=("Inter", 20 * -1)

    )

    e=Entry(window2, borderwidth=3)
    e.place(x=100,y=84,width=342,height=47)

    e2=Entry(window2, borderwidth=3,show='*')
    e2.place(x=100,y=205,width=342,height=47)

    def add():
        uname = e.get()
        pwd = e2.get()
        encrypted_pwd = fer.encrypt(pwd.encode()).decode()
        cur.execute("insert into passwords (username,password) values (%s,%s)",(uname,encrypted_pwd))
        mydb.commit()
        messagebox.showinfo('Success', 'Password Added Successfully')
        e.delete(0, 'end')
        e2.delete(0, 'end')
         
    button_image_1 = PhotoImage(
        file=relative_to_assets("button_1.png"))
    button_1 = Button(
        window2,
        text='Quit',
        compound='center',
        image=button_image_1,
        borderwidth=0,
        highlightthickness=0,
        command=lambda: window2.destroy(),
        relief="flat"
    )
    button_1.place(
        x=314.0,
        y=359.0,
        width=181.0,
        height=41.0
    )

    window2.button_image_2 = PhotoImage(
        file=relative_to_assets("button_2.png"))
    button_2 = Button(
        window2,
        text='Submit',
        compound='center',
        image= window2.button_image_2,
        borderwidth=0,
        highlightthickness=0,
        relief="flat",
        command=add
    )
        
    button_2.place(
        x=560.0,
        y=136.0,
        width=179.0,
        height=40.0
    )

    window2.image_image_2 = PhotoImage(
        file=relative_to_assets("image_2.png"))
    image_2 = canvas.create_image(
        24.0,
        480.0,
        image= window2.image_image_2
    )

    window2. image_image_3 = PhotoImage(
        file=relative_to_assets("image_3.png"))
    image_3 = canvas.create_image(
        414.0,
        455.0,
        image= window2.image_image_3
    )

    window2.image_image_4 = PhotoImage(
        file=relative_to_assets("image_4.png"))
    image_4 = canvas.create_image(
        178.0,
        243.0,
        image= window2.image_image_4
    )

    window2.image_image_5 = PhotoImage(
        file=relative_to_assets("image_5.png"))
    image_5 = canvas.create_image(
        733.0,
        472.0,
        image= window2.image_image_5
    )

    window2.image_image_6 = PhotoImage(
        file=relative_to_assets("image_6.png"))
    image_6 = canvas.create_image(
        664.0,
        65.0,
        image= window2.image_image_6
    )

    window2.image_image_7 = PhotoImage(
        file=relative_to_assets("image_7.png"))
    image_7 = canvas.create_image(
        797.0,
        474.0,
        image= window2.image_image_7
    )

    window2.image_image_8 = PhotoImage(
        file=relative_to_assets("image_8.png"))
    image_8 = canvas.create_image(
        178.0,
        375.0,
        image= window2.image_image_8
    )

    window2.image_image_9 = PhotoImage(
        file=relative_to_assets("image_9.png"))
    image_9 = canvas.create_image(
        664.0,
        318.0,
        image= window2.image_image_9
    )

    window2.image_image_10 = PhotoImage(
        file=relative_to_assets("image_10.png"))
    image_10 = canvas.create_image(
        534.0,
        474.0,
        image= window2.image_image_10
    )

    window2.image_image_11 = PhotoImage(
        file=relative_to_assets("image_11.png"))
    image_11 = canvas.create_image(
            467.00001096725464,
            203.0,
            image= window2.image_image_11
        )

    window2.image_image_12 = PhotoImage(
            file=relative_to_assets("image_12.png"))
    image_12 = canvas.create_image(
            607.0,
            474.0,
            image= window2.image_image_12
        )

    window2.image_image_13 = PhotoImage(
            file=relative_to_assets("image_13.png"))
    image_13 = canvas.create_image(
            671.0,
            472.0,
            image= window2.image_image_13
        )

    window2.image_image_14 = PhotoImage(
            file=relative_to_assets("image_14.png"))
    image_14 = canvas.create_image(
            40.0,
            172.0,
            image= window2.image_image_14
        )
    window2.resizable(False, False)
    window2.mainloop()
    



#function to view the passwords





def viewpass():
    OUTPUT_PATH = Path(__file__).parent
    # Use os.path.dirname to get the directory and os.path.join to create the full path
    ASSETS_PATH = os.path.join(OUTPUT_PATH, "view pass", "view password assets", "frame0")
    ASSETS_PATH = Path(ASSETS_PATH)  # Convert back to Path object for consistency

    def relative_to_assets(path: str) -> Path:
        return ASSETS_PATH / Path(path)

    window3 = Toplevel()
    window3.geometry("1020x606")
    window3.configure(bg="#EBD971")
    window3.title('')
    canvas = Canvas(
        window3,
        bg="#EBD971",
        height=606,
        width=1020,
        bd=0,
        highlightthickness=0,
        relief="ridge"
    )

    canvas.place(x=0, y=0)
    image_image_1 = PhotoImage(
        file=relative_to_assets("image_1.png"))
    image_1 = canvas.create_image(
        609.0,
        303.0,
        image=image_image_1
    )

    image_image_2 = PhotoImage(
        file=relative_to_assets("image_2.png"))
    image_2 = canvas.create_image(
        95.0,
        303.0,
        image=image_image_2
    )

    image_image_3 = PhotoImage(
        file=relative_to_assets("image_3.png"))
    image_3 = canvas.create_image(
        100,
        513.0,
        image=image_image_3
    )

    image_image_4 = PhotoImage(
        file=relative_to_assets("image_4.png"))
    image_4 = canvas.create_image(
        130.0,
        218.0,
        image=image_image_4
    )

    image_image_5 = PhotoImage(
        file=relative_to_assets("image_5.png"))
    image_5 = canvas.create_image(
        1000.0,
        37.0,
        image=image_image_5
    )

    button_image_1 = PhotoImage(
        file=relative_to_assets("button_1.png"))
    button_1 = Button(
        window3,
        text='Quit',
        image=button_image_1,
        compound='center',
        borderwidth=0,
        highlightthickness=0,
        command=lambda: window3.destroy(),
        relief="flat"
    )
    button_1.place(
        x=800.0,
        y=520.0,
        width=164.0,
        height=36.0
    )

    image_image_6 = PhotoImage(
        file=relative_to_assets("image_6.png"))
    image_6 = canvas.create_image(
        781.0,
        50.0,
        image=image_image_6
    )

    canvas.create_text(
        424.0,
        49.0,
        anchor="nw",
        text="Viewing Passwords",
        fill="#000000",
        font=("Inter", 32 * -1)
    )

    entry_image_1 = PhotoImage(
        file=relative_to_assets("entry_1.png"))
    entry_bg_1 = canvas.create_image(
        609.5,
        314.0,
        image=entry_image_1
    )

    canvas.create_text(
        858.0,
        523.0,
        anchor="nw",
        text="Quit",
        fill="#FFFFFF",
        font=("Inter", 24 * -1)
    )
    frame = Frame(window3, bg="#EBD971")
    frame.place(x=294, y=119, width=632, height=390)

    text_widget = Text(frame, font=('Bold', 16), bg='black', fg='white', bd=5, wrap='none')
    text_widget.pack(side='left', fill='both', expand=True)

    scrollbar = Scrollbar(frame, orient='vertical', command=text_widget.yview)
    scrollbar.pack(side='right', fill='y')
    text_widget.config(yscrollcommand=scrollbar.set)

    def view():
      cur.execute("SELECT *  FROM passwords")
      result = cur.fetchall()
      for row in result:
        user=row[0]
        passwd=row[1]
        decrypted_passwd=fer.decrypt(passwd.encode()).decode()
        text_widget.insert('end', f"{user} | {decrypted_passwd}\n")
      text_widget.config(state='disabled')  # Make read-only
    view()
    window3.resizable(False, False)
    window3.mainloop()





# Function to delete password





def dellpass():
    OUTPUT_PATH = Path(__file__).parent
    # Use os.path.dirname to get the directory and os.path.join to create the full path
    ASSETS_PATH = os.path.join(OUTPUT_PATH, "del pass", "del pass assets", "frame0")
    ASSETS_PATH = Path(ASSETS_PATH)  # Convert back to Path object for consistency

    def relative_to_assets(path: str) -> Path:
        return ASSETS_PATH / Path(path)

    window4 = Toplevel()
    window4.geometry("702x417")
    window4.configure(bg="#FFFFFF")


    def delete():
        uname = e3.get()
        cur.execute("DELETE FROM passwords WHERE username = %s", (uname,))
        mydb.commit()
        messagebox.showinfo('Success', 'Password Deleted Successfully')
        e3.delete(0, 'end')
        window4.destroy()

    canvas = Canvas(
        window4,
        bg="#FFFFFF",
        height=417,
        width=702,
        bd=0,
        highlightthickness=0,
        relief="ridge"
    )

    canvas.place(x=0, y=0)
    image_image_1 = PhotoImage(
        file=relative_to_assets("image_1.png"))
    image_1 = canvas.create_image(
        351.0,
        208.0,
        image=image_image_1
    )

    image_image_2 = PhotoImage(
        file=relative_to_assets("image_2.png"))
    image_2 = canvas.create_image(
        351.0,
        143.0,
        image=image_image_2
    )

    button_image_1 = PhotoImage(
        file=relative_to_assets("button_1.png"))
    button_1 = Button(
        window4,
        text='cancel',
        compound='center',
        image=button_image_1,
        borderwidth=0,
        highlightthickness=0,
        command=lambda: window4.destroy(),
        relief="flat"
    )
    button_1.place(
        x=271.0,
        y=287.0,
        width=166.0,
        height=38.0
    )

    button_image_2 = PhotoImage(
        file=relative_to_assets("button_2.png"))
    button_2 = Button(
        window4,
        text='Delete',
        compound='center',
        image=button_image_2,
        borderwidth=0,
        highlightthickness=0,
        command=delete,
        relief="flat"
    )
    button_2.place(
        x=271.0,
        y=224.0,
        width=166.0,
        height=38.0
    )

    e3 = Entry(window4, borderwidth=3)
    e3.place(x=124, y=122, width=452, height=45)
    e3.insert(0, "enter username to delete the password")


    
    image_image_3 = PhotoImage(
        file=relative_to_assets("image_3.png"))
    image_3 = canvas.create_image(
        351.0,
        43.0,
        image=image_image_3
    )

    canvas.create_text(
        67.0,
        24.0,
        anchor="nw",
        text="You are about to delete the password",
        fill="#000000",
        font=("Inter", 32 * -1)
    )

    image_image_4 = PhotoImage(
        file=relative_to_assets("image_4.png"))
    image_4 = canvas.create_image(
        30.0,
        40.0,
        image=image_image_4
    )

    image_image_5 = PhotoImage(
        file=relative_to_assets("image_5.png"))
    image_5 = canvas.create_image(
        671.0,
        40.0,
        image=image_image_5
    )
    
    window4.resizable(False, False)
    window4.mainloop()
    
    
    

#logic to check if the master password is set or not




while 1:
    cur.execute("SELECT master_password FROM password_manager.locker where master_password IS NOT NULL")
    result = cur.fetchone()
    
    if result is not None :
        checkmasterpass()
        break   
    else:
        masterpass()
        break


mydb.close()


