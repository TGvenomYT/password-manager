from cryptography.fernet import Fernet
K=Fernet.generate_key()
f=Fernet(K)
input('enter master password:')


def add():
    acc=input('enter account name:')
    e=open('text.exe','a')
    pwd=input('enter password:')
    e.write(acc + "|" + f.encrypt(pwd.encode()).decode() + "\n")
    e.close()


def view():
     e=open('test.txt','r')
     for i in e.readlines():
         data=i.rstrip()
         print(data.split('|'))
         acc,pwd=data.split('|')
         print(acc,'|',f.decrypt(pwd.encode()).decode())
        
view()

