import cv2
import pyodbc
import json
import time
import pandas as pd
import warnings
warnings.filterwarnings("ignore")
with open("pointmap.json", 'r') as json_file:
    points = json.load(json_file)
conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; Database=QC; UID=sa; PWD=1234; Trusted_Connection=No;')
stt_2d = {}
def update2D(machine):
    global stt_2d    
    data = pd.read_sql("select * from [2D_Thread] where machineno = '"+machine+"'",conn)
    try:
        stt_2d[machine] != None
    except:
        stt_2d[machine] = 0
    if stt_2d[machine] != data.loc[0,"Hole_no"]:   
        mahang = data.loc[0,"Product_type"]  
        
        # if data.loc[0,"Hole_no"] != 1:
        #     img = cv2.imread(machine+'.jpg')
        # else:
        img = cv2.imread(mahang+'.png')
        cv2.putText(img,data.loc[0,"DMC"],(int(img.shape[1]/2)-200,100),cv2.FONT_HERSHEY_SIMPLEX,1,(0,0,0),2,cv2.LINE_AA)  
        for i in range(data.loc[0,"Hole_no"]):
            point = points[mahang][i]            
            if data.loc[0,"Hole_stt"+str(i+1)] == 1:
                color = (0,255,0)
            else:
                color = (0,0,255)  
            cv2.circle(img,(point["position"][0],point["position"][1]),point["radius"],color,3)
            cv2.putText(img,str(round(data.loc[0,"Hole_tor"+str(i+1)],4)),(point["position"][0]-50,point["position"][1]-20),cv2.FONT_HERSHEY_SIMPLEX,0.5,color,2,cv2.LINE_AA)  
        cv2.imwrite(machine+".png",img)
        stt_2d[machine] = data.loc[0,"Hole_no"]
while True:
    update2D("Machine1")
    time.sleep(1)