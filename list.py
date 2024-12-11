lst=eval(input('enter a list :'))
a=[]
b=[]
for i in lst:
    if (lst.count(i)>=2 and i not in a ):
        a.append(i)
    else:
        b.append(i)

print('duplicate items in the list:',a)
print('unique items in the list:',b)
