from pathlib import Path
from tkinter import Tk, Canvas, Entry, Text, Button, PhotoImage,Label
from cryptography.fernet import Fernet
import mysql.connector as mysql
from tkinter import messagebox


OUTPUT_PATH = Path(__file__).parent
ASSETS_PATH = OUTPUT_PATH / Path(r"/home/niranjan/Documents/python/work in progress/Password manager gui MARK-III/password manager/login page/login page assets/frame0")


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
    command=lambda: print("button_2 clicked"),
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
    text='Quit',
    compound='center',
    image=button_image_3,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: print("button_3 clicked"),
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
