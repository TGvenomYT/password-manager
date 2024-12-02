'''
In Fernet, the signature is a 256-bit HMAC of the concatenated Version, Timestamp, IV, and Ciphertext fields. 
The HMAC is signed using the signing key section of the Fernet key. 
The entire token, including the HMAC, is encoded using Base64'''


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

