from cryptography.fernet import Fernet
K=Fernet.generate_key()
f=Fernet(K)



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
         acc,pwd=data.split('|')
         print(acc,'|',f.decrypt(pwd.encode()).decode())
        
view()

