from pathlib import Path
from tkinter import Tk, Canvas, Entry, Text, Button, PhotoImage,Label, Toplevel
from cryptography.fernet import Fernet
import mysql.connector as mysql
from tkinter import messagebox
import os

OUTPUT_PATH = Path(__file__).parent
# Use os.path.dirname to get the directory and os.path.join to create the full path
ASSETS_PATH = os.path.join(OUTPUT_PATH, "view pass", "view password assets", "frame0")
ASSETS_PATH = Path(ASSETS_PATH)  # Convert back to Path object for consistency

def relative_to_assets(path: str) -> Path:
        return ASSETS_PATH / Path(path)


window = Toplevel()

window.geometry("1020x606")
window.configure(bg = "#EBD971")
window.title('')

canvas = Canvas(
    window,
    bg = "#EBD971",
    height = 606,
    width = 1020,
    bd = 0,
    highlightthickness = 0,
    relief = "ridge"
)

canvas.place(x = 0, y = 0)
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
    window,
    text='Quit',
    image=button_image_1,
    compound='center',
    borderwidth=0,
    highlightthickness=0,
    command=lambda: print("button_1 clicked"),
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
window.resizable(False, False)
window.mainloop()
