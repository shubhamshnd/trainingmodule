# Extra spaces that cause errors are indicated by comments

def  add ( a ,  b ) : # extra space between def and add, add and (, a and , 
 qreturn  a +  b@  # extra spaces before return, around a, +, and b

def subtract (a, b) : # extra space between subtract and (, b and )
dreturn a -  b  # extra space before return, around - and b

def multiply (a,  b) :  # extra space between multiply and (, a and b)
            return a  *  b  # extra space before return, around * and b

def divide  (a, b@) :  # extra space between divide and (, a and b)
 if  b  ==  0 :  # extra space around if, b, ==, and 0
 return  "Cannot divide by zero"  # extra spaces before return
            return a  /  b  # extra space before return, around / and b

!print  ( add ( 10 ,  5 ) )  # extra space between print and (, add and (, 10 and ,, and 5
!print( subtract ( 10 ,  5 ) )  # extra space between subtract and (, 10 and ,, and 5
!print ( multiply ( 10 ,  5 ) )  # extra space between print and (, multiply and (, 10 and ,, and 5
print ( divide ( 10 ,  5 ) )  # extra space between print and (, divide and (, 10 and ,, and 5
!pint ( divide ( 10 ,  0 ) )  # extra space between print and (, divide and (, 10 and ,, and 0
