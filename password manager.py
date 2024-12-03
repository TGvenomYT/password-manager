

from cryptography.fernet import Fernet
key=Fernet.generate_key()
fer=Fernet(key)


def add():
    e=open('test.txt','a')
    acc=input('enter account name:')
    pwd=input('enter password:')
    encrypted_file=fer.encrypt(pwd.encode()).decode()
    e.write(acc +"|" +encrypted_file+ "\n")
    e.close()


def view():
     e=open('test.txt','r')
     for i in e.readlines():
         data=i.rstrip()
         acc,pwd=data.split('|')
         decrypted_token=fer.decrypt(pwd.encode()).decode()
         print(acc+'|'+decrypted_token)
         e.close()
add()
view()
