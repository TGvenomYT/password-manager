from cryptography.fernet import Fernet

def write_key():
    file=open('key.key','wb')
    key = Fernet.generate_key()
    file.write(key)
    file.close()


def read_key():
    file=open('key.key','rb')
    key=file.read()
    print('returned key=')
    return key
    file.close()



key=read_key()
fer=Fernet(key)



def view():
      with open('text.txt','r')as f:
         for lines in f.readlines():
           data=lines.rstrip()
           uname,pwd=data.split('|')
           decrypted_pwd=fer.decrypt(pwd.encode()).decode()
           print(uname,'|',decrypted_pwd)



def add():
    uname=str(input('enter username'))
    pwd = str(input('enter password'))
    with open('text.txt', 'a') as f:
          encrypted_file = fer.encrypt(pwd.encode()).decode()
          f.write(uname + '|' + encrypted_file + '\n')




while True:
    mode = input(
        "Would you like to add a new password or view existing ones (view, add), press q to quit? ").lower()
    if mode == "q":
        break

    if mode == "view":
        view()
    elif mode == "add":
        add()
    else:
        print("Invalid mode.")
        continue
