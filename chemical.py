from os import access
from constants.http_status_code import HTTP_200_OK, HTTP_201_CREATED, HTTP_400_BAD_REQUEST, HTTP_401_UNAUTHORIZED, HTTP_409_CONFLICT
from flask import Blueprint, app, request, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
import validators
from flask_jwt_extended import jwt_required, create_access_token, create_refresh_token, get_jwt_identity
from flasgger import swag_from
from database import *
from ERROR import *
import datetime
from threading import Thread
import pandas as pd
import traceback
from flask import session
import numpy as np
import math
import requests
import traceback
from auth_middleware import *

chemical = Blueprint("chemical", __name__, url_prefix="/api/v1/chemical")

@chemical.get('/file_names/<string:fileGroup>') # cần time_start, time_end, day_start, day_end, code -> trả về một bộ số liệu gồm: tổng, các biến là list thời gian, thông số theo thời gian để vẽ biểu đồ
@swag_from('./docs/chemical/file_names.yaml')
@token_required
def get_file_names(fileGroup):
    try:
        # Tạo cusor để kết nối với database
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234;Database=SPC; Trusted_Connection=No;',timeout=1)
        cursor = conn.cursor()

        cursor.execute("select FileName FROM FileName where FileGroup = '"+fileGroup+"'")
        file_names = cursor.fetchall()

        # Nếu lấy dữ liệu ra trống
        if file_names == None:
            ret = {
                'status':False,
                'message':'Not Exist Data'
            }
            return jsonify(ret),400

        # Nếu all_records được truy vấn thành công
        ret = {
                'status':True,
                'message':'Success',
                'data': []
            }
        
        if len(file_names) == 0:
            ret['data'] = None                  
            return jsonify(ret)
    

        for item in file_names:
            file_name = item
            ret["data"].append(file_name[0])
        
        return jsonify(ret)
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        Systemp_log1(traceback.format_exc(), "file_names").append_new_line()
        return jsonify(ret),500

def calculate_standard_deviation(K107):
    sqrt_term = math.sqrt(2 / (K107 - 1))
    gamma_ln1 = math.lgamma(K107 / 2)
    gamma_ln2 = math.lgamma((K107 - 1) / 2)
    result = math.exp(math.log(sqrt_term) + gamma_ln1 - gamma_ln2)

def get_data_filed(filegroup, filename):
    conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.9.246; uid=sa; pwd=saa;Database=SPC; Trusted_Connection=No;',timeout=1)
    cursor = conn.cursor()
    
    cursor.execute("select FileID From FileName where FileGroup = '"+filegroup+"' and  FileName='"+filename+"'")
    fileidname= cursor.fetchall()

    list_ids = []
    for item in fileidname:
        list_ids.append(item[0])

    datafileid = {"data": list_ids}

    return datafileid

def isNaN(num):
    return num != num

@chemical.post('') # cần time_start, time_end, day_start, day_end, code -> trả về một bộ số liệu gồm: tổng, các biến là list thời gian, thông số theo thời gian để vẽ biểu đồ
@swag_from('./docs/chemical/chemical_data.yaml')
@token_required_and_permissions
def search_data(role, permissions):
    try:
        # Tạo cusor để kết nối với database
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234;Database=SPC; Trusted_Connection=No;',timeout=1)
        cursor = conn.cursor()

        # Check xem có phải Manager không?
        if role < 100:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 5
        binary_number = bin(int(permissions, 16))[2:]

        cursor.execute("select count(*) from [QC].[dbo].[Permission_Name]")
        num_permissions = cursor.fetchone()

        binary_number = binary_number.zfill(num_permissions[0])
        permission_value = binary_number[-id_permission]

        if not int(permission_value):
            ret = {
                'status':False,
                'message':'Sorry, your role does not have this permission!'
            }
            return jsonify(ret),401

        # Lấy dữ liệu datetime_start, datetime_end, location
        day_start = request.json['dayStart']
        day_end = request.json['dayEnd']
        time_start = request.json['timeStart']
        time_end = request.json['timeEnd']

        # Lấy datetime_start
        datetime_start = day_start + " " + time_start
        if day_start == '':
            datetime_start = '1900-01-01' + datetime_start        
        
        # Lấy datetime_end
        datetime_end = day_end + " " + time_end
        if day_start == '':
            datetime_end = '2100-01-01' + datetime_end        

        # Lấy group và file_name
        file_group = request.json['groupName']
        filename = request.json['fileName']

        cursor.execute("select GroupName from FileGroup_V WHERE GroupName ='DC10200-Casting'")
        group_names = cursor.fetchall()

        datafileid_str = get_data_filed(file_group, filename)["data"][0]
        
        if file_group =='DS50000-Heat-Treatment':
            cmdtorque = "select * from SPCtorque() where FileID = '"+datafileid_str+"' and VCTRLID in (SELECT [VCTRLID] FROM [SPC].[dbo].[HeatTreament_Info]) and DateTimeCreate >'"+datetime_start+"' and DateTimeCreate <'"+datetime_end+"'"
            cursor.execute(cmdtorque)
            opticaldivision_data = cursor.fetchall()
        elif file_group =='DC10200-Casting':  
            cmd = "SELECT * FROM dbo.newoptical("+str(datafileid_str)+", '"+datetime_start+"', '"+datetime_end+"')"
            print(cmd)
            cursor.execute(cmd)
            opticaldivision_data = cursor.fetchall()

        # Nếu lấy dữ liệu ra trống
        if opticaldivision_data == None:
            ret = {
                'status':False,
                'message':'Not Exist Data'
            }
            return jsonify(ret),400
            
        # Nếu all_records được truy vấn thành công
        ret = {
                'status':True,
                'message':'Success',
                'data': {}
            }
        # Khởi tạo 2 list dữ liệu
        ret["data"]["table1"] = []
        ret["data"]["table2"] = []

        # Lấy dữ liệu từ opticaldivision_data
        
        for optical_divisiom_item in opticaldivision_data:
            datetime_create, c, si, mn, p, s, ni, cr, mo, cu, ti, v, pb, w, ai, co, nb, a_s, sn, sb, b, bi, ca, zn, n, ce, mg, ta, zr, ti_nb, fe_percent, cef, other, a1_appearance = optical_divisiom_item
            ret["data"]["table2"].append({
                'datetimeCreate': datetime_create,
                'c': c,
                'si': si,
                'mn': mn,
                'p': p,
                's': s,
                'ni': ni,
                'cr': cr,
                'mo': mo,
                'cu': cu,
                'ti':  ti,
                'v': v,
                'pb': pb,
                'w': w,
                'ai': ai,
                'co': co,
                'nb': nb,
                'a_s': a_s,
                'sn': sn,
                'sb': sb,
                'b': b,
                'bi': bi,
                'ca': ca,
                'zn': zn,
                'n': n,
                'ce': ce,
                'mg': mg,
                'ta': ta,
                'zr': zr,
                'tiNb': ti_nb,
                'fePercent': fe_percent,
                'cef': cef,
                'other': other,
                'a1Appearance': a1_appearance
            })
        if len(opticaldivision_data) == 0:
            ret['data'] = None
            return jsonify(ret)
        
        # In thử
        print('torque_data',opticaldivision_data)

        if file_group == 'DS50000-Heat-Treatment':
            data1 = pd.read_sql("SELECT * FROM GetControltorque() where fileid = "+str(datafileid_str)+"", conn)
            data2 = pd.read_sql("select * from spc.dbo.getcontrol821_torque("+str(datafileid_str)+", '"+datetime_start+"', '"+datetime_end+"')", conn)
            data3 = pd.read_sql("SELECT * FROM spctorque() where fileid = "+str(datafileid_str)+" and DateTimeCreate >'"+datetime_start+"' and DateTimeCreate <'"+datetime_end+"'", conn)
            post = 0
        elif file_group == 'DC10200-Casting':
            data1 = pd.read_sql("SELECT * FROM GetControl3() where fileid = "+str(datafileid_str)+"",conn)
            dff=pd.read_sql("SELECT * FROM dbo.newoptical("+str(datafileid_str)+", '"+datetime_start+"', '"+datetime_end+"')",conn)
            df = dff.drop('DateTimeCreate', axis=1)
            df1 = df.agg(['max', 'min', 'mean'])
            df2 = pd.DataFrame(df1, index=['max', 'min', 'mean'])
            df2['Control_Item'] = df2.index
            data2 = df2[['Control_Item'] + [col for col in df2.columns if col != 'Control_Item']]
            data3 = pd.read_sql("SELECT * FROM dbo.newoptical("+str(datafileid_str)+", '"+datetime_start+"', '"+datetime_end+"')",conn)
            post = 1

        common_columns = data1.columns.intersection(data2.columns)
        rs = pd.concat([data1[common_columns], data2[common_columns]])
        newdata = {}

        try:
            for col in rs.columns[1:]:
                newdata[col] = []
                splqlt = len(data3) -1
                sps = int(rs.loc[4,col])

                if sps == 1:
                    try:
                        for i in range(splqlt):
                            test += abs(data3.loc[i+1,col] - data3.loc[i,col])
                        dev = test/splqlt/1.128
                        newdata[col].append(round(dev,4))
                        newdata[col].append(int(splqlt+1))
                    except:
                        newdata[col].append('--')
                        newdata[col].append(int(splqlt+1))
                else:   
                    try:
                        k107 = 0
                        for i in range(0,splqlt+1,sps):
                            savg = np.average(data3.loc[i:i+sps-1,col])
                            sumd = 0
                            for j in data3.loc[i:i+sps-1,col]:
                                sumd += (float(j)-savg)**2
                            test += sumd
                            k107 += len(data3.loc[i:i+sps-1,col]) - 1
                        k107 = k107+1 
                        l108 = math.sqrt(test/(k107-1))
                        k109 = calculate_standard_deviation(k107)
                        dev = l108/k109
                        newdata[col].append(round(dev,4))
                        newdata[col].append(int(splqlt+1))
                    except:
                        newdata[col].append('--')
                        newdata[col].append(int(splqlt+1))
                #Ca
                try:        
                    newdata[col].append(round((2*float(rs.loc[5,col]) - float(rs.loc[1,col]) - float(rs.loc[2,col]))/(float(rs.loc[1,col]) - float(rs.loc[2,col])),4)) #ca=2avg-usl-lsl/usl-lsl
                except:
                    newdata[col].append('--')
                
                #Cp       
                try:        
                    newdata[col].append(round((float(rs.loc[1,col]) - float(rs.loc[2,col]))/(6*dev),4)) #cp=(usl-lsl)/6*dev   USL, LSL != '--'
                except:
                    try:        
                        newdata[col].append(round(abs((float(rs.loc[5,col]) - float(rs.loc[1,col])))/(3*dev),4)) # cp = |avg-usl|/3.dev USL != '--'
                    except:
                        try:
                            newdata[col].append(round(abs((float(rs.loc[5,col]) - float(rs.loc[2,col])))/(3*dev),4)) # cp = |avg-lsl|/3.dev LSL != '--'
                        except:
                            newdata[col].append('--') #LSL = USL = '--'

                try:        
                    newdata[col].append(round(((float(rs.loc[1,col]) - float(rs.loc[2,col]))/(6*dev))*(1-abs((2*float(rs.loc[5,col]) - float(rs.loc[1,col]) - float(rs.loc[2,col]))/(float(rs.loc[1,col]) - float(rs.loc[2,col])))),4)) #Cpk = ((usl-lsl)/6*dev) * (1-|2avg-usl-lsl/usl-lsl|)
                except:
                    try:        
                        newdata[col].append(round(abs((float(rs.loc[5,col]) - float(rs.loc[1,col])))/(3*dev),4)) # cpk = |avg-usl|/3.dev USL != '--'
                    except:
                        try:
                            newdata[col].append(round(abs((float(rs.loc[5,col]) - float(rs.loc[2,col])))/(3*dev),4)) # cpk = |avg-lsl|/3.dev LSL != '--'
                        except:
                            newdata[col].append('--') #LSL = USL = '--'
                
                # P
                count = 0
                for x in range(splqlt):
                    try:
                        if float(data3.loc[x,col]) > float(data1.loc[1,col]):
                            print(col, data3.loc[x,col])
                            count += 1       
                    except:
                        pass

                    try:
                        if float(data3.loc[x,col]) < float(data1.loc[2,col]):
                            print(col, data3.loc[x,col])
                            count += 1     
                    except:
                        pass

                print(col, count)

                try:
                    newdata[col].append(str(round(100*count/len(data3),2))+'%') 
                except:
                    newdata[col].append('--')

            newdata['Control_Item'] = ['Std.Dev', 'Qty', 'Ca', 'Cp', 'Cpk', 'P']
            newdata['FileID'] = [datafileid_str] * 6

            print(newdata)

            dt1 = pd.DataFrame(newdata)
            rs2_list = pd.concat([rs, dt1], ignore_index=True)
            rs3 = []

            if file_group == 'DS50000-Heat-Treatment':
                for index, row in rs2_list.iterrows():
                    item = {
                        "Control_Item": row["Control_Item"],
                        "1_Yield Strength": row["1_Yield Strength"],
                        "2_Tensile Strength": row["2_Tensile Strength"],
                        "3_Elongation": row["3_Elongation"],
                        "4_Cross-Sectional Area": row["4_Cross-Sectional Area"],
                        "5_Hardness": row["5_Hardness"],
                        "A1_Appearance": row["A1_Appearance"]      
                    }

                    rs3.append(item)
            elif file_group =='DC10200-Casting':
                for index, row in rs2_list.iterrows():
                    item = {
                        "controlItem": row["Control_Item"],
                        "c": row["C"],
                        "si": row["Si"],
                        "mn": row["Mn"],
                        "p": row["P"],
                        "s": row["S"],
                        "ni": row["Ni"],
                        "cr": row["Cr"],
                        "mo": row["Mo"],
                        "cu": row["Cu"],
                        "ti": row["Ti"],
                        "v": row["V"],
                        "pb": row["Pb"],
                        "w": row["W"],
                        "al": row["Al"],
                        "co": row["Co"],
                        "nb": row["Nb"],
                        "as": row["As"],
                        "sn": row["Sn"],
                        "sb": row["Sb"],
                        "b": row["B"],
                        "bi": row["Bi"],
                        "ca": row["Ca"],
                        "zn": row["Zn"],
                        "n": row["N"],
                        "ce": row["Ce"],
                        "mg": row["Mg"],
                        "ta": row["Ta"],
                        "zr": row["Zr"],
                        "tiNb": row["Ti+Nb"],
                        "fePercent": row["Fe%"],
                        "cef": row["CEF"],
                        "other": row["Other"],
                        "a1Appearance": row["A1_Appearance"],
                    }

                    for record in item.items():                        
                        if isNaN(record[1]):
                            item[record[0]] = None

                    rs3.append(item)
        except Exception:
            pass

        ret["data"]["table1"] = rs3

        return jsonify(ret)
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        Systemp_log1(traceback.format_exc(), "file_names1").append_new_line()
        return jsonify(ret),500

@chemical.get('/sixpack/<string:groupName>/<string:fileName>')
@swag_from('./docs/chemical/spc_sixpack_form.yaml')
@token_required
def spc_sixpack_form(groupName, fileName):
    try:
        # Tạo cusor để kết nối với database
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234;Database=SPC; Trusted_Connection=No;',timeout=1)
        cursor = conn.cursor()

        cursor.execute("SELECT distinct(CTRLITEM) as CTRLITEM FROM [SPC].[dbo].[VCTRL] where [FileID]= (select FileID From FileName where FileGroup = '"+groupName+"' and  FileName='"+fileName+"')")
        data = cursor.fetchall()

        # Nếu lấy dữ liệu ra trống
        if data == None:
            ret = {
                'status':False,
                'message':'Not Exist Data'
            }
            return jsonify(ret),400

        # Nếu all_records được truy vấn thành công
        ret = {
                'status':True,
                'message':'Success',
                'data':[]
            }
        
        if len(data) == 0:
            ret['data'] = None                  
            return jsonify(ret)
    

        for item in data:
            file_name = item
            ret["data"].append({
                'cmm': item[0],
                'name': item[0]
            })
        
        return jsonify(ret)
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        Systemp_log1(traceback.format_exc(), "spc_sixpack_form").append_new_line()
        return jsonify(ret),500

@chemical.post('/sixpack') # cần time_start, time_end, location_name -> trả về một bộ số liệu gồm: tổng, các biến là list thời gian, thông số theo thời gian để vẽ biểu đồ
@swag_from('./docs/chemical/create_spc_sixpacking.yaml')
@token_required_and_permissions
def chart_data(role, permissions):
    try:
        # Tạo cusor để kết nối với database
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234;Database=SPC; Trusted_Connection=No;',timeout=1)
        cursor = conn.cursor()

        # Check xem có phải Manager không?
        if role < 100:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 6
        binary_number = bin(int(permissions, 16))[2:]

        cursor.execute("select count(*) from [QC].[dbo].[Permission_Name]")
        num_permissions = cursor.fetchone()

        binary_number = binary_number.zfill(num_permissions[0])
        permission_value = binary_number[-id_permission]

        if not int(permission_value):
            ret = {
                'status':False,
                'message':'Sorry, your role does not have this permission!'
            }
            return jsonify(ret),401

        # Lấy dữ liệu group_name, file_name, data, name
        group_name = request.json['groupName']
        file_name = request.json['fileName']
        data = request.json['name']
        name = request.json['name']

        # Lấy dữ liệu datetime_start, datetime_end, location
        day_start = request.json['dayStart']
        day_end = request.json['dayEnd']
        time_start = request.json['timeStart']
        time_end = request.json['timeEnd']

        datetime_start = day_start + " " + time_start
        datetime_end = day_end + " " + time_end

        # url để lấy dữ liệu từ api web của A. Học
        url = 'http://192.168.8.21:5008/six_pack_v2_1'

        print("select VCDATA.VCTRLID, Name, Value, SC, SU, SL from VCDATA left join displayname on VCDATA.Linkname = Displayname.ID left join (SELECT *  FROM [SPC].[dbo].[VCTRL] where [FileID]= (select FileID From FileName where FileGroup = '"+group_name+"' and  FileName='"+file_name+"')) as a on Displayname.Name = a.CTRLITEM   where VCDATA.VCTRLID in (select [VCTRLID] FROM [SPC].[dbo].[FileData] where DateTimeCreate >='"+datetime_start+"' and DateTimeCreate <='"+datetime_end+"' and [FileID]=(select FileID From FileName where FileGroup = '"+group_name+"' and  FileName='"+file_name+"')) and Linkname != 0 and Name = '"+data+"'order by VCDATA.VCTRLID")
        cursor.execute("select VCDATA.VCTRLID, Name, Value, SC, SU, SL from VCDATA left join displayname on VCDATA.Linkname = Displayname.ID left join (SELECT *  FROM [SPC].[dbo].[VCTRL] where [FileID]= (select FileID From FileName where FileGroup = '"+group_name+"' and  FileName='"+file_name+"')) as a on Displayname.Name = a.CTRLITEM   where VCDATA.VCTRLID in (select [VCTRLID] FROM [SPC].[dbo].[FileData] where DateTimeCreate >='"+datetime_start+"' and DateTimeCreate <='"+datetime_end+"' and [FileID]=(select FileID From FileName where FileGroup = '"+group_name+"' and  FileName='"+file_name+"')) and Linkname != 0 and Name = '"+data+"'order by VCDATA.VCTRLID")
        all_records = cursor.fetchall()

        # Nếu lấy dữ liệu ra trống
        if all_records == None:
            ret = {
                'status':False,
                'message':'Not Exist Data'
            }
            return jsonify(ret),400

        # Nếu có máy
        ret ={
                'status':True,
                'message':'Success',
                'data':[]
            }
        
        if len(all_records) == 0:
            ret['data'] = None
            return jsonify(ret)
        
        # Khởi tạo 2 list để lưu dữ liệu sl và su
        sl_list = []
        su_list = []
        data_list = []

        for item in all_records:
            vctrlid, name, value, sc, su, sl = item
            try:
                sl_list.append(float(sl))
            except:
                pass

            try:
                su_list.append(float(su))
            except:
                pass

            data_list.append(value)
            
        if len(sl_list) == 0:
            lsl = None
        else:
            lsl = sum(sl_list) / len(sl_list) 
        
        if len(su_list) == 0:
            usl = None
        else:
            usl = sum(su_list) / len(su_list)
        
        data = {
            "LSL":  lsl,
            "USL": usl,
            "data": data_list,
            "name": name
        }

        print(data)
            
        if len(data['data']) > 0:
            Req = requests.post(url=url,json=data)
            ret["data"] = Req.text
            print(Req.text.find("relative"))
        else:
            ret["data"] = []
            return jsonify(ret), 400

        return jsonify(ret)
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        Systemp_log1(traceback.format_exc(), "sixpack").append_new_line()
        return jsonify(ret),500