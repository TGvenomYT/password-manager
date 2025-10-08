**Ensure that the software is set up only on linux PC**
=============================================

Install Mysql
==========
1.Run 
**sudo apt install mysql-server**

in terminal

2.open mysql as root **mysql -u root -p**

3.Create User 
**CREATE USER 'root'@'localhost' IDENTIFIED BY 'your password';**
change the password according to your wish

4.Grant privileges to your user
**GRANT ALL PRIVILEGES ON password_manager.* TO 'root'@'localhost';**

5.Save the privileges
**FLUSH PRIVILEGES;**

6.Add Mysql password to the **passwd.txt** file

7.Encrypt the password:

open password manager file in terminal
```
chmod 600 passwd.txt

gpg -c passwd.txt

shred -u passwd.txt

gpg -d passwd.txt.gpg

```
**NOTE:**
==========
upon using the command  "gpg -c passwd.txt"  you will be asked for a passphrase 

 **PASSPHRASE cannot be changed**
**Give a very strong passphrase for the security of your passwords**
carefully Type the passphrase

        
        
             **After completing all the steps Password Manager is ready to use**
             
                             **Store your passwords securly in this  software**


**THANK YOU FOR USING PASSWORD MANAGER**
