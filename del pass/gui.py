from pathlib import Path

from tkinter import Tk, Canvas, Entry, Text, Button, PhotoImage,Toplevel
import os


OUTPUT_PATH = Path(__file__).parent
# Use os.path.dirname to get the directory and os.path.join to create the full path
ASSETS_PATH = os.path.join(OUTPUT_PATH, "del pass", "del pass assets", "frame0")
ASSETS_PATH = Path(ASSETS_PATH)  # Convert back to Path object for consistency

def relative_to_assets(path: str) -> Path:
        return ASSETS_PATH / Path(path)



window4 = Toplevel()

window4.geometry("702x417")
window4.configure(bg = "#FFFFFF")


canvas = Canvas(
    window4,
    bg = "#FFFFFF",
    height = 417,
    width = 702,
    bd = 0,
    highlightthickness = 0,
    relief = "ridge"
)


canvas.place(x = 0, y = 0)
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
    command=lambda:window4.destroy(),
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
    command=lambda: print("button_2 clicked"),
    relief="flat"
)
button_2.place(
    x=271.0,
    y=224.0,
    width=166.0,
    height=38.0
)

e3 = Entry(window4, text='enter username to delete the password')
e3.place(x=124, y=122, width=452, height=45)
e3.insert(0,"enter username to delete the password")
                                                                     


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
