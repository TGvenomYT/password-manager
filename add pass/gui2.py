from pathlib import Path
from tkinter import Tk, Canvas, Entry, Text, Button, PhotoImage,Label
from cryptography.fernet import Fernet
import mysql.connector as mysql
from tkinter import messagebox

# Database connection
mydb = mysql.connect(
    host="localhost",
    user="root",
    password="Niranjan2022",
    auth_plugin='mysql_native_password',
    unix_socket="/var/run/mysqld/mysqld.sock"
)
cur= mydb.cursor()
cur.execute("CREATE DATABASE IF NOT EXISTS password_manager")
cur.execute("USE password_manager")
cur.execute("CREATE TABLE IF NOT EXISTS passwords (username VARCHAR(255), password VARCHAR(255))")
mydb.commit()
cur.execute("CREATE TABLE IF NOT EXISTS  locker(encryption_key char(255))")
mydb.commit()


#initialize the key for encryption

def write_key():
    cur.execute("SELECT encryption FROM locker LIMIT 1")
    result = cur.fetchone()
    if result:
        print('Key already exists in the database.')
    else:
       key=Fernet.generate_key()
       cur.execute("INSERT INTO locker (encryption)  VALUES (%s)", (key.decode(),))
       mydb.commit()

write_key()

def read_key():   
    cur.execute("SELECT encryption FROM locker ")
    result = cur.fetchone()
    
read_key()

cur.execute("SELECT encryption FROM locker ")
result = cur.fetchone()
keyy= result[0].encode()

fer = Fernet(keyy)


def addpass():
        OUTPUT_PATH = Path(__file__).parent
        ASSETS_PATH = OUTPUT_PATH / Path(r"/home/niranjan/Documents/python/work in progress/Password manager gui MARK-III/password manager/add pass/add password assets/frame0")

        def relative_to_assets(path: str) -> Path:
            return ASSETS_PATH / Path(path)

        window2 = Tk()

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
        image_image_1 = PhotoImage(
            file=relative_to_assets("image_1.png"))
        image_1 = canvas.create_image(
            414.0,
            253.0,
            image=image_image_1
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

        e2=Entry(window2, borderwidth=3)
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
            command=lambda: print("button_1 clicked"),
            relief="flat"
        )
        button_1.place(
            x=314.0,
            y=359.0,
            width=181.0,
            height=41.0
        )

        button_image_2 = PhotoImage(
            file=relative_to_assets("button_2.png"))
        button_2 = Button(
            window2,
            text='Submit',
             compound='center',
            image=button_image_2,
            borderwidth=0,
            highlightthickness=0,
            relief="flat"
        )
        
        button_2.place(
            x=560.0,
            y=136.0,
            width=179.0,
            height=40.0
        )

        image_image_2 = PhotoImage(
            file=relative_to_assets("image_2.png"))
        image_2 = canvas.create_image(
            24.0,
            480.0,
            image=image_image_2
        )

        image_image_3 = PhotoImage(
            file=relative_to_assets("image_3.png"))
        image_3 = canvas.create_image(
            414.0,
            455.0,
            image=image_image_3
        )

        image_image_4 = PhotoImage(
            file=relative_to_assets("image_4.png"))
        image_4 = canvas.create_image(
            178.0,
            243.0,
            image=image_image_4
        )

        image_image_5 = PhotoImage(
            file=relative_to_assets("image_5.png"))
        image_5 = canvas.create_image(
            733.0,
            472.0,
            image=image_image_5
        )

        image_image_6 = PhotoImage(
            file=relative_to_assets("image_6.png"))
        image_6 = canvas.create_image(
            664.0,
            65.0,
            image=image_image_6
        )

        image_image_7 = PhotoImage(
            file=relative_to_assets("image_7.png"))
        image_7 = canvas.create_image(
            797.0,
            474.0,
            image=image_image_7
        )

        image_image_8 = PhotoImage(
            file=relative_to_assets("image_8.png"))
        image_8 = canvas.create_image(
            178.0,
            375.0,
            image=image_image_8
        )

        image_image_9 = PhotoImage(
            file=relative_to_assets("image_9.png"))
        image_9 = canvas.create_image(
            664.0,
            318.0,
            image=image_image_9
        )

        image_image_10 = PhotoImage(
            file=relative_to_assets("image_10.png"))
        image_10 = canvas.create_image(
            534.0,
            474.0,
            image=image_image_10
        )

        image_image_11 = PhotoImage(
            file=relative_to_assets("image_11.png"))
        image_11 = canvas.create_image(
            467.00001096725464,
            203.0,
            image=image_image_11
        )

        image_image_12 = PhotoImage(
            file=relative_to_assets("image_12.png"))
        image_12 = canvas.create_image(
            607.0,
            474.0,
            image=image_image_12
        )

        image_image_13 = PhotoImage(
            file=relative_to_assets("image_13.png"))
        image_13 = canvas.create_image(
            671.0,
            472.0,
            image=image_image_13
        )

        image_image_14 = PhotoImage(
            file=relative_to_assets("image_14.png"))
        image_14 = canvas.create_image(
            40.0,
            172.0,
            image=image_image_14
        )
        window2.resizable(False, False)
        window2.mainloop()




addpass()