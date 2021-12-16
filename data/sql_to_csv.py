import re
import os
import pandas as pd

def get_collaborations_from_sql(filename):
    collaborations =[]
    with open(filename) as f:
        data = f.readlines()
        for i in range(0,len(data)):
            if "INSERT INTO `collaboration`" in data[i]:
                i+=1
                while data[i]!='\n' :
                    collaboration = data[i].replace('(','').replace('),','').replace(');','').split(',')
                    name = re.search(r"'(.*?)'",collaboration[1]).group(1)
                    collaborations.append(name)
                    i+=1
    return collaborations

def get_users_from_sql(filename):
    collaborations = get_collaborations_from_sql(filename)
    users = []
    with open(filename) as f:
        data = f.readlines()

        for i in range(0,len(data)):
            if "INSERT INTO `users`" in data[i]:
                i+=1
                while data[i]!='\n' :
                    isAdmin = False
                    user_data = data[i].replace('(','').replace('),','').replace(');','').split(',')
                    if re.search(r"'(.*?)'",user_data[1]).group(1) == '':
                        temp = re.search(r"'(.*?)'",user_data[2]).group(1).split()
                        temp = (temp[0][0] + temp[1]).lower()
                        username = temp
                    else:
                        username = re.search(r"'(.*?)'",user_data[1]).group(1)
                    temp = re.search(r"'(.*?)'",user_data[2]).group(1).split()
                    first_name = temp[0]
                    last_name = ''
                    if len(temp) > 2:
                        for j in temp[1:]:
                            last_name += j + ' '
                        last_name = last_name[:-1]
                    else:
                        last_name = temp[1]
                    contact_email = re.search(r"'(.*?)'",user_data[5]).group(1)
                    oauth_uid = re.search(r"'(.*?)'",user_data[7]).group(1)
                    contact_phone = re.search(r"'(.*?)'",user_data[6]).group(1)
                    if (int(user_data[12]) - 1 < 0) or (int(user_data[12]) - 1 > len(collaborations) - 1):
                        collaboration = None
                    else:
                        collaboration = collaborations[int(user_data[12]) - 1]
                    if int(user_data[11]) == 1:
                        isAdmin = True
                    users.append([username, first_name, last_name, contact_email, oauth_uid, contact_phone, collaboration, isAdmin])
                    i+=1
    return users

def save_collaborations_to_csv(collaborations, echo=True):
    csvDir =  os.getcwd()+"/csv"
    if not os.path.isdir(csvDir):
        os.makedirs(csvDir)
    df = pd.DataFrame(collaborations, columns =['name'])
    df.index+=1
    df.to_csv(csvDir+"/grandma_collaborations.csv", index=True)
    if echo:
        print("successfully saved grandma collaborations in csv format")
        print("in directory : {}\n".format(csvDir+"/grandma_collaborations.csv"))

def save_users_to_csv(users, echo=True):
    csvDir =  os.getcwd()+"/csv"
    if not os.path.isdir(csvDir):
        os.makedirs(csvDir)
    #df = pd.DataFrame(users, columns =['username','first_name','last_name','contact_email','oauth_uid','contact_phone','collaboration','admin'])
    df = pd.DataFrame(users, columns =['username', 'first_name', 'last_name', 'contact_email', 'oauth_uid', 'contact_phone','collaboration','admin'])
    df.index+=1
    df.to_csv(csvDir+"/grandma_users.csv", index=True)
    if echo:
        print("successfully saved grandma users in csv format")
        print("in directory : {}\n".format(csvDir+"/grandma_users.csv"))

def save_collaborations_from_sql_to_csv(filename, echo=True):
    save_collaborations_to_csv(get_collaborations_from_sql(filename),echo)

def save_users_sql_from_to_csv(filename, echo=True):
    save_users_to_csv(get_users_from_sql(filename),echo)

################################## TESTS ###################################

filename = 'grandma.sql'
#users = get_users_from_sql(filename)
#print(users)
#colab = get_collaborations_from_sql(filename)
#print(colab[0])
#save_collaborations_to_csv(colab)
#save_users_to_csv(users)

save_users_sql_from_to_csv(filename)
save_collaborations_from_sql_to_csv(filename)
