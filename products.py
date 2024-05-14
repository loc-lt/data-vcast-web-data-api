from os import access
from constants.http_status_code import HTTP_200_OK, HTTP_201_CREATED, HTTP_400_BAD_REQUEST, HTTP_401_UNAUTHORIZED, HTTP_409_CONFLICT
from flask import Blueprint, app, request, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from flask_jwt_extended import jwt_required, create_access_token, create_refresh_token, get_jwt_identity
from flasgger import swag_from
from database import *
from ERROR import *
import pandas as pd
import traceback
from flask import session
from flask import *
import io
from auth_middleware import *
import cv2
import numpy as np

products = Blueprint("products", __name__, url_prefix="/api/v1/products")

# COATING
@products.post('/coating')
@swag_from('./docs/products/coating/coating_data.yaml')
@token_required_and_permissions
def get_coating_data(role, permissions):
    try:
        # Tạo cusor để kết nối với database
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234; Database=Auto; Trusted_Connection=No;', timeout=1)
        cursor = conn.cursor()

        # Check xem có phải Manager không?
        if role < 100:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 19
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

        # Lấy dữ liệu coat_name
        coat_name = request.json['coatName']

        # Lấy dữ liệu datetime_start, datetime_end, location
        day_start = request.json['dayStart']
        day_end = request.json['dayEnd']
        time_start = request.json['timeStart']
        time_end = request.json['timeEnd']  

        datetime_start = day_start + " " + time_start
        datetime_end = day_end + " " + time_end

        cursor.execute("SELECT Top(15000)* FROM [Auto].[dbo].[Product_Quantity_W5_"+coat_name+"] where DateTime >'"+datetime_start+"' and DateTime <'"+datetime_end+"'")
        all_records = cursor.fetchall()

        # Lấy số dượng lượng record
        num_records = len(all_records)

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
                'data':{}
            }
        
        if num_records == 0:
            ret['data'] = None
            return jsonify(ret)
        
        # Khởi tạo để lấy dữ liệu cho chart và table 
        ret['data']['chart'] = {}
        ret['data']['table'] = []

        # Lấy dữ liệu cho bảng
        for item in all_records:
            order_number1, order_number2, product_name, date_time, datetime_ms = item
            ret['data']['table'].append({
                'orderNumber1': order_number1,
                'orderNumber2': order_number2,
                'productName': product_name,
                'datetime': date_time
            })

        # Khởi tạo các list dữ liệu cần thiết để vẽ chart
        ret['data']['chart']['datetimeList'] = []
        ret['data']['chart']['tempList'] = []
        ret['data']['chart']['humidList'] = []

        # Lấy averageTempList, averageHumidList
        cursor.execute("select Datetime, average_temp1, average_humid1 from data_"+coat_name+"_W5 where Datetime >'"+datetime_start+"' and Datetime <'"+datetime_end+"' order by Datetime desc")
        temp_humid_average_data = cursor.fetchall()

        for item in temp_humid_average_data:
            datetime_data, average_temp, average_humid = item
            
            ret['data']['chart']['datetimeList'].append(datetime_data.strftime("%Y-%m-%d %H:%M:%S.%f"))
            ret['data']['chart']['tempList'].append(average_temp)
            ret['data']['chart']['humidList'].append(average_humid)

        # Lấy các biến temp_min, temp_max, humid_min, humid_max
        cursor.execute("select * from [Auto].[dbo].[Settinglimitcoatingx5] where Coating = '"+coat_name+"'")
        figues = cursor.fetchone()

        print(figues)

        coating_name, temp_min, temp_max, humid_min, humid_max, layer = figues

        ret['data']['chart']['tempMin'] = temp_min
        ret['data']['chart']['tempMax'] = temp_max
        ret['data']['chart']['humidMin'] = humid_min
        ret['data']['chart']['humidMax'] = humid_max

        return jsonify(ret)
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        Systemp_log1(traceback.format_exc(), "dmc_data").append_new_line()
        return jsonify(ret),500
    
@products.post('/coating/download')
@swag_from('./docs/products/coating/coating_download.yaml')
@token_required_and_permissions
def download_coating_data(role, permissions):
    try:
        # Tạo cusor để kết nối với database
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234; Database=Auto; Trusted_Connection=No;', timeout=1)
        cursor = conn.cursor()

        # Check xem có phải Manager không?
        if role < 100:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 19
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

        datetime_start = day_start + " " + time_start
        datetime_end = day_end + " " + time_end

        df1 = pd.read_sql("SELECT * FROM [Auto].[dbo].[Product_Quantity_W5_Coating1] where DateTime >'"+datetime_start+"' and DateTime <'"+datetime_end+"'", conn)
        df2 = pd.read_sql("SELECT * FROM [Auto].[dbo].[Product_Quantity_W5_Coating2] where DateTime >'"+datetime_start+"' and DateTime <'"+datetime_end+"'", conn)
        df3 = pd.read_sql("SELECT * FROM [Auto].[dbo].[Product_Quantity_W5_Coating3] where DateTime >'"+datetime_start+"' and DateTime <'"+datetime_end+"'", conn)
        df4 = pd.read_sql("SELECT * FROM [Auto].[dbo].[Product_Quantity_W5_Coating4] where DateTime >'"+datetime_start+"' and DateTime <'"+datetime_end+"'", conn)
        df5 = pd.read_sql("SELECT * FROM [Auto].[dbo].[Product_Quantity_W5_Coating5] where DateTime >'"+datetime_start+"' and DateTime <'"+datetime_end+"'", conn)
        df6 = pd.read_sql("SELECT * FROM [Auto].[dbo].[Product_Quantity_W5_Coating6] where DateTime >'"+datetime_start+"' and DateTime <'"+datetime_end+"'", conn)

        # Nếu lấy dữ liệu ra trống
        if len(df1) == 0 and len(df2) == 0 and len(df3) == 0 and len(df4) == 0 and len(df5) == 0 and len(df6) == 0:
            ret = {
                'status':False,
                'message':'Not Exist Data'
            }
            return jsonify(ret),400

        output = io.BytesIO()
        writer = pd.ExcelWriter(
            output,
            engine='xlsxwriter')    # add a sheet
        
        df1.index+=1
        df2.index+=1
        df3.index+=1
        df4.index+=1
        df5.index+=1
        df6.index+=1
        df1.to_excel(writer, sheet_name='layer1')
        df2.to_excel(writer, sheet_name='layer2')
        df3.to_excel(writer, sheet_name='layer3')
        df4.to_excel(writer, sheet_name='layer4')
        df5.to_excel(writer, sheet_name='layer5')
        df6.to_excel(writer, sheet_name='layer6')

        # add headers
        writer.close()
        output.seek(0)
        
        return Response(output, mimetype="application/ms-excel",
                    headers={"Content-Disposition": "attachment;filename=Coating_Data.xls"})
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        Systemp_log1(traceback.format_exc(), "dmc_data").append_new_line()
        return jsonify(ret),500
    
@products.post('/coating/temp_humid_download')
@swag_from('./docs/products/coating/temp_humid_download.yaml')
@token_required_and_permissions
def download_temp_humid_data(role, permissions):
    global coat_name
    try:
        # Tạo cusor để kết nối với database
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234; Database=Auto; Trusted_Connection=No;', timeout=1)
        cursor = conn.cursor()

        # Check xem có phải Manager không?
        if role < 100:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 19
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

        datetime_start = day_start + " " + time_start
        datetime_end = day_end + " " + time_end

        # Lấy dữ liệu coat_name
        coat_name = request.json['coatName']

        # Lấy coat_data
        cursor.execute("select * from data_"+coat_name+"_W5 where Datetime >'"+datetime_start+"' and Datetime <'"+datetime_end+"'")
        coat_data = cursor.fetchall()

        # Lấy coat_data_sorted
        cursor.execute("select Datetime, average_temp1, average_humid1 from data_"+coat_name+"_W5 where Datetime >'"+datetime_start+"' and Datetime <'"+datetime_end+"' order by Datetime desc")
        coat_data_sorted = cursor.fetchall()

        # Nếu lấy dữ liệu ra trống
        if coat_data == None:
            ret = {
                'status':False,
                'message':'Not Exist Data'
            }
            return jsonify(ret),400
        
        # Lấy df để lưu dữ liệu vô worksheet
        df_coat_data = pd.read_sql("select * from data_"+coat_name+"_W5 where Datetime >'"+datetime_start+"' and Datetime <'"+datetime_end+"'", conn)

        # Nếu có máy
        ret = {
                'status':True,
                'message':'Success',
                'data':{}
            }
        
        # Nếu dữ liệu rỗng
        if len(coat_data) == 0:
            ret['data'] = None
            return jsonify(ret)

        # Khởi tạo các list dữ liệu cần thiết để vẽ chart
        ret['data']['datetime'] = []
        ret['data']['averageTempList'] = []
        ret['data']['averageHumidList'] = []

        for item in coat_data_sorted:
            datetime_data, average_temp, average_humid = item
            
            ret['data']['datetime'].append(datetime_data.strftime("%Y-%m-%d %H:%M:%S.%f"))
            ret['data']['averageTempList'].append(average_temp)
            ret['data']['averageHumidList'].append(average_humid)

        # Lấy các biến temp_min, temp_max, humid_min, humid_max
        cursor.execute("select * from [Auto].[dbo].[Settinglimitcoatingx5] where Coating = '"+coat_name+"'")
        figues = cursor.fetchone()

        coating_name, temp_min, temp_max, humid_min, humid_max, layer = figues

        ret['data']['tempMin'] = temp_min
        ret['data']['tempMax'] = temp_max
        ret['data']['humidMin'] = humid_min
        ret['data']['humidMax'] = humid_max

        image_path = 'static/images/'+coat_name+'.png'
                             
        output = io.BytesIO()
        writer = pd.ExcelWriter(output,engine='xlsxwriter')    # add a sheet
        df_coat_data.index+=1
        df_coat_data.to_excel(writer, sheet_name=str(coat_name))
        worksheet = writer.book.add_worksheet("Chart")

        # Get the xlsxwriter workbook and worksheet objects for the new sheet.
        worksheet.insert_image('A1', image_path, {'x_offset': 15, 'y_offset': 10})

        # add headers
        writer.close()
        output.seek(0)
        
        return Response(output, mimetype="application/ms-excel",
                        headers={"Content-Disposition": "attachment;filename=Temp_Humid_Coating.xls"})
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        Systemp_log1(traceback.format_exc(), "temp_humid_download").append_new_line()
        return jsonify(ret),500
    
def isNaN(num):
    return num != num

# SHOT BLASING
@products.post('/shot_blasting')
@swag_from('./docs/products/shot_blasting/shot_blasting_data.yaml')
@token_required_and_permissions
def get_shot_blasting_data(role, permissions):
    try:
        # Tạo cusor để kết nối với database
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234; Database=Auto; Trusted_Connection=No;', timeout=1)
        cursor = conn.cursor()

        # Check xem có phải Manager không?
        if role < 100:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 20
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

        datetime_start = day_start + " " + time_start
        datetime_end = day_end + " " + time_end

        # Lấy dữ liệu bảng ShotBlasting
        cursor.execute("SELECT Top(15000)* FROM [Auto].[dbo].[ShotBlasting] where Time_Take_out >'"+datetime_start+"' and Time_Take_out <'"+datetime_end+"'")
        all_records = cursor.fetchall()

        # Lấy số dượng lượng record
        num_records = len(all_records)

        # Nếu lấy dữ liệu ra trống
        if all_records == None:
            ret = {
                'status':False,
                'message':'Not Exist Data'
            }
            return jsonify(ret),400

        # Nếu có máy
        ret = {
                'status':True,
                'message':'Success',
                'data':{}
            }
        
        if num_records == 0:
            ret['data'] = None
            return jsonify(ret)
        
        # Nếu lấy dữ liệu không trống        
        # Khởi tạo 2 list dữ liệu cần thiết show bảng dữ liệu và dữ liệu đã qua xử lý để vẽ chart
        ret['data']['table'] = []
        ret['data']['chart'] = {}

        # Lấy dữ liệu để show bảng
        for item in all_records:
            id, machine_no, face, time_set, time_put_into, time_start_temp, time_finish_temp, time_take_out = item
            
            ret['data']['table'].append({
                'id': id,
                'machineNo': machine_no,
                'face': face,
                'timeSet': time_set,
                'timePutInto': time_put_into,
                'timeStart': time_start_temp,
                'timeFinish': time_finish_temp,
                'timeTakeOut': time_take_out
            })

        # Lấy dữ liệu để vẽ chart
        shot_blasting_df = pd.read_sql("SELECT left(Time_Take_out,11) as 'Time', MachineNo, COUNT(MachineNo) AS 'Count'FROM [Auto].[dbo].[ShotBlasting] where Time_Take_out >'"+datetime_start+"' and Time_Take_out <'"+datetime_end+"' GROUP BY left(Time_Take_out,11),MachineNo order by left(Time_Take_out,11) desc", conn)
        
        shot_blasting_df = shot_blasting_df.pivot_table(index='Time', columns='MachineNo')

        # Khảo sát dữ liệu trong df
        print(shot_blasting_df.head(10))
        print(shot_blasting_df.columns.to_list())
        print(shot_blasting_df.values)
        print(shot_blasting_df.index.to_list())

        # Khởi tạo các list dữ liệu để vẽ chart
        ret['data']['chart']['machineNo'] = []
        ret['data']['chart']['timeIndex'] = []
        ret['data']['chart']['machineNoData'] = {}

        # Lấy dữ liệu machine_no
        for item in shot_blasting_df.columns.to_list():
            ret['data']['chart']['machineNo'].append(item[1])

        # Lấy dữ liệu timeIndex
        ret['data']['chart']['timeIndex'] = shot_blasting_df.index.to_list()

        # Lấy dữ liệu machineNoData
        # Khởi tạo các list chứa dữ liệu 
        machine_no_list = ret['data']['chart']['machineNo']
        for item in machine_no_list:
            ret['data']['chart']['machineNoData'][item] = []

        # Add data
        for row_data in shot_blasting_df.values:
            for idx, element in enumerate(row_data):
                if isNaN(element):
                    ret['data']['chart']['machineNoData'][machine_no_list[idx]].append(0)
                else:
                    ret['data']['chart']['machineNoData'][machine_no_list[idx]].append(element)          

        return jsonify(ret)
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        Systemp_log1(traceback.format_exc(), "shot_blasting_data").append_new_line()
        return jsonify(ret),500
    
@products.post('/shot_blasting/download')
@swag_from('./docs/products/shot_blasting/shot_blasting_download.yaml')
@token_required_and_permissions
def download_shot_blasting_data(role, permissions):
    try:
        # Tạo cusor để kết nối với database
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234; Database=Auto; Trusted_Connection=No;', timeout=1)

        # Check xem có phải Manager không?
        if role < 100:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 20
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

        datetime_start = day_start + " " + time_start
        datetime_end = day_end + " " + time_end

        print("SELECT*From[Auto].[dbo].[ShotBlasting] where Time_Take_out >'"+datetime_start+"' and Time_Take_out <'"+datetime_end+"'")
        shot_blasting_df = pd.read_sql("SELECT*From[Auto].[dbo].[ShotBlasting] where Time_Take_out >'"+datetime_start+"' and Time_Take_out <'"+datetime_end+"'", conn)

        # Nếu lấy dữ liệu ra trống
        if len(shot_blasting_df) == 0:
            ret = {
                'status':False,
                'message':'Not Exist Data'
            }
            return jsonify(ret),400

        output = io.BytesIO()
        writer = pd.ExcelWriter(
            output,
            engine='xlsxwriter')    # add a sheet
        
        shot_blasting_df.to_excel(writer, sheet_name='ShotBlasting', index=False)

        # add headers
        writer.close()
        output.seek(0)
        
        return Response(output, mimetype="application/ms-excel",
                        headers={"Content-Disposition": "attachment;filename=ShotBlasting_Data.xls"})
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        Systemp_log1(traceback.format_exc(), "shot_blasting_download").append_new_line()
        return jsonify(ret),500
    
# LASER
@products.post('/laser')
@swag_from('./docs/products/laser/laser_data.yaml')
@token_required_and_permissions
def get_laser_data(role, permissions):
    try:
        # Tạo cusor để kết nối với database
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234;Database=QC; Trusted_Connection=No;',timeout=1)
        cursor = conn.cursor()

        # Check xem có phải Manager không?
        if role < 100:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 21
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

        datetime_start = day_start + " " + time_start
        datetime_end = day_end + " " + time_end

        cursor.execute("SELECT Id, MachineNo, NameOperator, NameProduct, DMCin, TimeInDMC, TimeOutDMC, TimeOutBarcode, Result, Status From [QC].[dbo].[Laser] where TimeOutBarcode >'"+datetime_start+"' and TimeOutBarcode <'"+datetime_end+"'")
        all_records = cursor.fetchall()

        # Lấy số dượng lượng record
        num_records = len(all_records)

        # Nếu lấy dữ liệu ra trống
        if all_records == None:
            ret = {
                'status':False,
                'message':'Not Exist Data'
            }
            return jsonify(ret),400

        # Nếu có máy
        ret = {
                'status':True,
                'message':'Success',
                'data':{}
            }
        
        if num_records == 0:
            ret['data'] = None
            return jsonify(ret)
        
        # Khởi tạo để lấy dữ liệu cho chart và table 
        ret['data']['chart'] = {}
        ret['data']['table'] = []

        # Lấy dữ liệu cho bảng
        for item in all_records:
            id, machine_no, name_operator, name_product, dmc, time_start, time_end, time_scan, result, status = item
            ret['data']['table'].append({
                'id': id,
                'machine': machine_no,
                'operator': name_operator,
                'product': name_product,
                'dmc': dmc,
                'timeStart': time_start,
                'timeEnd': time_end,
                'timeScan': time_scan,
                'result': result,
                'status': status
            })

        # Lấy dữ liệu để vẽ chart
        laser_df = pd.read_sql("SELECT left(TimeInDMC, 11) as Time, Quality, COUNT(Quality) AS 'Count' FROM [QC].[dbo].[Laser] where TimeInDMC > '"+ datetime_start +"' and TimeInDMC < '"+ datetime_end +"' GROUP BY left(TimeInDMC, 11), Quality order by left(TimeInDMC, 11)", conn)
        
        laser_df = laser_df.pivot_table(index='Time', columns='Quality')

        # Khảo sát dữ liệu trong df
        print(laser_df.head(10))
        print(laser_df.columns.to_list())
        print(laser_df.values)
        print(laser_df.index.to_list())

        # Khởi tạo các list dữ liệu để vẽ chart
        ret['data']['chart']['timeIndex'] = []
        ret['data']['chart']['countList'] = []

        # Lấy dữ liệu timeIndex
        ret['data']['chart']['timeIndex'] = laser_df.index.to_list()  

        # Lấy dữ liệu count
        for item in laser_df.values:
            ret['data']['chart']['countList'].append(item[0])

        return jsonify(ret)
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        Systemp_log1(traceback.format_exc(), "laser_data").append_new_line()
        return jsonify(ret),500
    
@products.post('/laser/download')
@swag_from('./docs/products/laser/laser_download.yaml')
@token_required_and_permissions
def download_laser_data(role, permissions):
    try:
        # Tạo cusor để kết nối với database
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234;Database=QC; Trusted_Connection=No;',timeout=1)

        # Check xem có phải Manager không?
        if role < 100:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 21
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

        datetime_start = day_start + " " + time_start
        datetime_end = day_end + " " + time_end

        print("SELECT * From[QC].[dbo].[Laser] where TimeOutBarcode >'"+datetime_start+"' and TimeOutBarcode <'"+datetime_end+"'")
        laser_df = pd.read_sql("SELECT * From[QC].[dbo].[Laser] where TimeOutBarcode >'"+datetime_start+"' and TimeOutBarcode <'"+datetime_end+"'", conn)

        # Nếu lấy dữ liệu ra trống
        if len(laser_df) == 0:
            ret = {
                'status':False,
                'message':'Not Exist Data'
            }
            return jsonify(ret),400

        output = io.BytesIO()
        writer = pd.ExcelWriter(
            output,
            engine='xlsxwriter')    # add a sheet
        
        laser_df.to_excel(writer, sheet_name='layer1', index=False)

        # add headers
        writer.close()
        output.seek(0)
        
        return Response(output, mimetype="application/ms-excel",
                        headers={"Content-Disposition": "attachment;filename=Laser_Data.xls"})
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        Systemp_log1(traceback.format_exc(), "laser_download").append_new_line()
        return jsonify(ret),500
    
# SCANQR
@products.post('/scanqr')
@swag_from('./docs/products/scanqr/scanqr_data.yaml')
@token_required_and_permissions
def get_scanqr_data(role, permissions):
    try:
        # Tạo cusor để kết nối với database
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234; Database=Auto; Trusted_Connection=No;', timeout=1)
        cursor = conn.cursor()

        # Check xem có phải Manager không?
        if role < 100:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 22
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

        datetime_start = day_start + " " + time_start
        datetime_end = day_end + " " + time_end

        # Lấy dữ liệu bảng ShotBlasting
        cursor.execute("SELECT Top(15000)* FROM [QC].[dbo].[ScanQR] where Time_scan_tray >'"+datetime_start+"' and Time_scan_tray <'"+datetime_end+"'")
        all_records = cursor.fetchall()

        # Lấy số dượng lượng record
        num_records = len(all_records)

        # Nếu lấy dữ liệu ra trống
        if all_records == None:
            ret = {
                'status':False,
                'message':'Not Exist Data'
            }
            return jsonify(ret),400

        # Nếu có máy
        ret = {
                'status':True,
                'message':'Success',
                'data':{}
            }
        
        if num_records == 0:
            ret['data'] = None
            return jsonify(ret)
        
        # Nếu lấy dữ liệu không trống        
        # Khởi tạo 2 list dữ liệu cần thiết show bảng dữ liệu và dữ liệu đã qua xử lý để vẽ chart
        ret['data']['table'] = []
        ret['data']['chart'] = {}

        # Lấy dữ liệu để show bảng
        for item in all_records:
            id, product, time_scan_product, time_scan_tray, dmc_product, dmc_tray, compare = item
            
            ret['data']['table'].append({
                'id': id,
                'product': product,
                'timeScanProduct': time_scan_product,
                'timeScanTray': time_scan_tray,
                'dmcProduct': dmc_product,
                'dmcTray': dmc_tray,
                'compare': compare
            })

        # Lấy dữ liệu để vẽ chart
        scanqr_df = pd.read_sql("select left(Time_scan_tray, 11) as 'Time', Compare, Count(compare) as 'Count' from [QC].[dbo].[ScanQR] where Time_scan_tray > '"+ datetime_start +"' and Time_scan_tray <'"+ datetime_end +"' GROUP BY left(Time_scan_tray, 11), Compare order by left(Time_scan_tray, 11) desc", conn)
        
        scanqr_df = scanqr_df.pivot_table(index='Time', columns='Compare')

        # Khảo sát dữ liệu trong df
        print(scanqr_df.head(10))
        print(scanqr_df.columns.to_list())
        print(scanqr_df.values.tolist())
        print(scanqr_df.index.to_list())

        # Khởi tạo các list dữ liệu để vẽ chart
        ret['data']['chart']['timeIndex'] = []
        ret['data']['chart']['okNgData'] = []

        # Lấy dữ liệu timeIndex
        ret['data']['chart']['timeIndex'] = scanqr_df.index.to_list()

        # Lấy dữ liệu count OK và count NG của mỗi timeIndex
        for idx in range(len(scanqr_df.index.tolist())):
            ret['data']['chart']['okNgData'].append({'NG': scanqr_df.values.tolist()[idx][0], 'OK': scanqr_df.values.tolist()[idx][1]}) 

        return jsonify(ret)
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        Systemp_log1(traceback.format_exc(), "scanqr_data").append_new_line()
        return jsonify(ret),500
    
@products.post('/scanqr/download')
@swag_from('./docs/products/scanqr/scanqr_download.yaml')
@token_required_and_permissions
def download_scanqr_data(role, permissions):
    try:
        # Tạo cusor để kết nối với database
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234;Database=QC; Trusted_Connection=No;',timeout=1)

        # Check xem có phải Manager không?
        if role < 100:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 22
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

        datetime_start = day_start + " " + time_start
        datetime_end = day_end + " " + time_end

        print("SELECT * From [QC].[dbo].[ScanQR] where Time_scan_tray > '"+ datetime_start +"' and Time_scan_tray < '"+ datetime_end +"'")
        scanqr_df = pd.read_sql("SELECT * From [QC].[dbo].[ScanQR] where Time_scan_tray > '"+ datetime_start +"' and Time_scan_tray < '"+ datetime_end +"'", conn)

        # Nếu lấy dữ liệu ra trống
        if len(scanqr_df) == 0:
            ret = {
                'status':False,
                'message':'Not Exist Data'
            }
            return jsonify(ret),400

        output = io.BytesIO()
        writer = pd.ExcelWriter(
            output,
            engine='xlsxwriter')    # add a sheet
        
        scanqr_df.to_excel(writer, sheet_name='ScanQR', index=False)

        # add headers
        writer.close()
        output.seek(0)
        
        return Response(output, mimetype="application/ms-excel",
                        headers={"Content-Disposition": "attachment;filename=ScanQR_Data.xls"})
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        Systemp_log1(traceback.format_exc(), "scanqr_download").append_new_line()
        return jsonify(ret),500
    
# MAUNAL SCAN   
@products.post('/manual_scan')
@swag_from('./docs/products/manual_scan/manual_scan_data.yaml')
@token_required_and_permissions
def get_manual_scan_data(role, permissions):
    try:
        # Tạo cusor để kết nối với database
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234;Database=QC; Trusted_Connection=No;',timeout=1)
        cursor = conn.cursor()

        # Check xem có phải Manager không?
        if role < 100:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 23
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
        
        # Lấy dữ liệu Khu Vực
        area_scan = request.json['areaScan']

        # Lấy dữ liệu datetime_start, datetime_end, location
        day_start = request.json['dayStart']
        day_end = request.json['dayEnd']
        time_start = request.json['timeStart']
        time_end = request.json['timeEnd']

        datetime_start = day_start + " " + time_start
        datetime_end = day_end + " " + time_end

        # Lấy dữ liệu bảng Scan_Repair_Data
        if area_scan == 'All':
            cursor.execute("select * FROM [QC].[dbo].[Scan_Repair_Data] where TimeSave >='"+ datetime_start +"' and TimeSave <='"+ datetime_end +"' order by TimeSave asc")
            all_records = cursor.fetchall()
        else:
            cursor.execute("select * FROM [QC].[dbo].[Scan_Repair_Data] where KhuVuc like N'%"+ area_scan +"%' and TimeSave >='"+ datetime_start +"' and TimeSave <='"+ datetime_end +"' order by TimeSave asc")
            all_records = cursor.fetchall()

        # Lấy số dượng lượng record
        num_records = len(all_records)

        # Nếu lấy dữ liệu ra trống
        if all_records == None:
            ret = {
                'status':False,
                'message':'Not Exist Data'
            }
            return jsonify(ret),400

        # Nếu có máy
        ret = {
                'status':True,
                'message':'Success',
                'data':{}
            }
        
        if num_records == 0:
            ret['data'] = None
            return jsonify(ret)
        
        # Nếu lấy dữ liệu không trống        
        # Khởi tạo 2 list dữ liệu cần thiết show bảng dữ liệu và dữ liệu đã qua xử lý để vẽ chart
        ret['data']['table'] = []
        ret['data']['chart'] = {}

        # Lấy dữ liệu để show bảng
        for item in all_records:
            id, msnv, station, station_no, dmc, product_type, time_save = item
            
            ret['data']['table'].append({
                'id': id,
                'msnv': msnv,
                'station': station,
                'stationNo': station_no,
                'dmc': dmc,
                'productType': product_type,
                'timeSave': time_save
            })

        # Lấy dữ liệu để vẽ chart
        if area_scan == 'All':
            manual_scan_df = pd.read_sql("SELECT left(TimeSave, 11) as 'Time', KhuVuc, COUNT(DMC) AS 'Count' FROM [QC].[dbo].[Scan_Repair_Data] where TimeSave >='"+datetime_start+"' and TimeSave <='"+datetime_end+"' GROUP BY left(TimeSave, 11), KhuVuc order by left(TimeSave, 11) asc", conn)
        else:
            manual_scan_df = pd.read_sql("SELECT left(TimeSave, 11) as 'Time', KhuVuc, COUNT(DMC) AS 'Count' FROM [QC].[dbo].[Scan_Repair_Data] where KhuVuc like N'%"+area_scan+"%' and TimeSave >='"+datetime_start+"' and TimeSave <='"+datetime_end+"' GROUP BY left(TimeSave, 11), KhuVuc order by left(TimeSave,11) asc", conn)

        manual_scan_df = manual_scan_df.pivot_table(index='Time', columns=['KhuVuc'], values='Count', aggfunc='sum', fill_value=0)

        # Khảo sát dữ liệu trong df
        print(manual_scan_df)
        print(manual_scan_df.columns.to_list())
        print(manual_scan_df.values.tolist())
        print(manual_scan_df.index.to_list())

        # Khởi tạo các list dữ liệu để vẽ chart
        ret['data']['chart']['timeIndex'] = []
        ret['data']['chart']['manualScanData'] = []

        # Lấy dữ liệu timeIndex
        ret['data']['chart']['timeIndex'] = manual_scan_df.index.to_list()
        
        # Lấy dữ liệu count OK và count NG của mỗi timeIndex
        for count_list in manual_scan_df.values.tolist(): # Duyệt qua từng count_list -> [1232, 117, 1659, 1676, 162]
            station_dict = {}
            for station_idx, station in enumerate(manual_scan_df.columns.to_list()): # Duyệt qua toàn bộ các trạm -> ['Gá Tổng Hợp', 'Kích Thước Khác', 'Ngoại Quan', 'Pin Ren', 'Ren Tay']
                station_dict[station] = count_list[station_idx]
                
            ret['data']['chart']['manualScanData'].append(station_dict) 

        return jsonify(ret)
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        Systemp_log1(traceback.format_exc(), "scanqr_data").append_new_line()
        return jsonify(ret),500
    
@products.post('/manual_scan/download')
@swag_from('./docs/products/manual_scan/manual_scan_download.yaml')
@token_required_and_permissions
def download_manual_scan_data(role, permissions):
    try:
        # Tạo cusor để kết nối với database
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234;Database=QC; Trusted_Connection=No;',timeout=1)

        # Check xem có phải Manager không?
        if role < 100:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 23
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
        
        # Lấy dữ liệu Khu Vực
        area_scan = request.json['areaScan']

        # Lấy dữ liệu datetime_start, datetime_end, location
        day_start = request.json['dayStart']
        day_end = request.json['dayEnd']
        time_start = request.json['timeStart']
        time_end = request.json['timeEnd']  

        datetime_start = day_start + " " + time_start
        datetime_end = day_end + " " + time_end

        if area_scan =='All':
            print("select * FROM [QC].[dbo].[Scan_Repair_Data] where TimeSave >='"+datetime_start+"' and TimeSave <='"+datetime_end+"' order by TimeSave asc")
            manual_scan_df = pd.read_sql("select * FROM [QC].[dbo].[Scan_Repair_Data] where TimeSave >='"+datetime_start+"' and TimeSave <='"+datetime_end+"' order by TimeSave asc", conn)
        else:
            print("select * FROM [QC].[dbo].[Scan_Repair_Data] where KhuVuc like N'%"+area_scan+"%'and TimeSave >='"+datetime_start+"' and TimeSave <='"+datetime_end+"' order by TimeSave asc")
            manual_scan_df = pd.read_sql("select * FROM [QC].[dbo].[Scan_Repair_Data] where KhuVuc like N'%"+area_scan+"%'and TimeSave >='"+datetime_start+"' and TimeSave <='"+datetime_end+"' order by TimeSave asc", conn)

        # Nếu lấy dữ liệu ra trống
        if len(manual_scan_df) == 0:
            ret = {
                'status':False,
                'message':'Not Exist Data'
            }
            return jsonify(ret),400

        output = io.BytesIO()
        writer = pd.ExcelWriter(
            output,
            engine='xlsxwriter')    # add a sheet
        
        manual_scan_df.to_excel(writer, sheet_name='c', index=False)

        # add headers
        writer.close()
        output.seek(0)
        
        return Response(output, mimetype="application/ms-excel",
                        headers={"Content-Disposition": "attachment;filename=ManualScan_Data.xls"})
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        Systemp_log1(traceback.format_exc(), "scanqr_download").append_new_line()
        return jsonify(ret),500
    
# TiltMeasurement
@products.post('/tilt_measurement')
@swag_from('./docs/products/tilt_measurement/tilt_measurement_data.yaml')
@token_required_and_permissions
def get_tilt_measurement_data(role, permissions):
    try:
        # Tạo cusor để kết nối với database
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234;Database=QC; Trusted_Connection=No;',timeout=1)
        cursor = conn.cursor()

        # Check xem có phải Manager không?
        if role < 100:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 24
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

        datetime_start = day_start + " " + time_start
        datetime_end = day_end + " " + time_end

        # Lấy dữ liệu bảng ShotBlasting
        cursor.execute("SELECT Top(15000) * FROM [QC].[dbo].[TiltMeasurement] where Time_finish >'"+datetime_start+"' and Time_finish <'"+datetime_end+"'")
        all_records = cursor.fetchall()

        # Lấy số lượng record
        num_records = len(all_records)

        # Nếu lấy dữ liệu ra trống
        if all_records == None:
            ret = {
                'status':False,
                'message':'Not Exist Data'
            }
            return jsonify(ret),400

        # Nếu có máy
        ret = {
                'status':True,
                'message':'Success',
                'data':{}
            }
        
        if num_records == 0:
            ret['data'] = None
            return jsonify(ret)
        
        # Nếu lấy dữ liệu không trống        
        # Khởi tạo 2 list dữ liệu cần thiết show bảng dữ liệu và dữ liệu đã qua xử lý để vẽ chart
        ret['data']['table'] = []
        ret['data']['chart'] = {}

        # Lấy dữ liệu để show bảng
        for item in all_records:
            id, id_operator, machine_no, name_product, qr_tray, dmc, time_start_temp, time_finish_temp, total_deviation_height, distance, angle_of_part_vs_master, height_1, height_2, height_3, height_4, height_5, result, status, picture, note = item
            
            ret['data']['table'].append({
                'id': id,
                'operator': id_operator,
                'machine': machine_no,
                'qr_tray': qr_tray,
                'dataMatrixCode': dmc,
                'timeStart': time_start_temp,
                'timeFinish': time_finish_temp,
                'result': result,
                'status': status,
                'note': note,
                'total_deviation': total_deviation_height,
                'pin_distance': distance,
                'angle': angle_of_part_vs_master,
                'height_1': height_1,
                'height_2': height_2,
                'height_3': height_3,
                'height_4': height_4,
                'height_5': height_5
            })

        # Lấy dữ liệu để vẽ chart
        tilt_measurement_df = pd.read_sql("SELECT left(Time_finish, 11) as Time, Result, COUNT(Result) AS 'Count' FROM [QC].[dbo].[TiltMeasurement] where Time_finish >'"+datetime_start+"' and Time_finish < '"+datetime_end+"' GROUP BY left(Time_finish, 11), Result order by left(Time_finish, 11)", conn)
        
        tilt_measurement_df = tilt_measurement_df.pivot_table(index='Time', columns='Result')

        # Khảo sát dữ liệu trong df
        print(tilt_measurement_df.head(10))
        print(tilt_measurement_df.columns.to_list())
        print(tilt_measurement_df.values.tolist())
        print(tilt_measurement_df.index.to_list())

        # Khởi tạo các list dữ liệu để vẽ chart
        ret['data']['chart']['timeIndex'] = []
        ret['data']['chart']['okNgData'] = []

        # Lấy dữ liệu timeIndex
        ret['data']['chart']['timeIndex'] = tilt_measurement_df.index.to_list()

        # Lấy dữ liệu count OK và count NG của mỗi timeIndex
        for idx in range(len(tilt_measurement_df.index.tolist())):
            ret['data']['chart']['okNgData'].append({'NG': tilt_measurement_df.values.tolist()[idx][0], 'OK': tilt_measurement_df.values.tolist()[idx][1]}) 

        return jsonify(ret)
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        Systemp_log1(traceback.format_exc(), "tilt_measurement_data").append_new_line()
        return jsonify(ret),500
    
@products.post('/tilt_measurement/download')
@swag_from('./docs/products/tilt_measurement/tilt_measurement_download.yaml')
@token_required_and_permissions
def download_tilt_measurement_data(role, permissions):
    try:
        # Tạo cusor để kết nối với database
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234;Database=QC; Trusted_Connection=No;',timeout=1)

        # Check xem có phải Manager không?
        if role < 100:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 24
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

        datetime_start = day_start + " " + time_start
        datetime_end = day_end + " " + time_end

        print("SELECT Top(15000) * FROM [QC].[dbo].[TiltMeasurement] where Time_finish >'"+datetime_start+"' and Time_finish <'"+datetime_end+"'")
        tilt_measurement_df = pd.read_sql("SELECT Top(15000) * FROM [QC].[dbo].[TiltMeasurement] where Time_finish >'"+datetime_start+"' and Time_finish <'"+datetime_end+"'", conn)

        # Nếu lấy dữ liệu ra trống
        if len(tilt_measurement_df) == 0:
            ret = {
                'status':False,
                'message':'Not Exist Data'
            }
            return jsonify(ret),400

        output = io.BytesIO()
        writer = pd.ExcelWriter(
            output,
            engine='xlsxwriter')    # add a sheet
        
        tilt_measurement_df.to_excel(writer, sheet_name='layer1', index=False)

        # add headers
        writer.close()
        output.seek(0)
        
        return Response(output, mimetype="application/ms-excel",
                        headers={"Content-Disposition": "attachment;filename=TiltMeasurement_Data.xls"})
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        Systemp_log1(traceback.format_exc(), "scanqr_download").append_new_line()
        return jsonify(ret),500
    
# CNC
@products.post('/cnc')
@swag_from('./docs/products/cnc/cnc_data.yaml')
@token_required_and_permissions
def get_cnc_data(role, permissions):
    try:
        # Tạo cusor để kết nối với database
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234;Database=QC; Trusted_Connection=No;',timeout=1)
        cursor = conn.cursor()

        # Check xem có phải Manager không?
        if role < 100:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 25
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

        datetime_start = day_start + " " + time_start
        datetime_end = day_end + " " + time_end

        # Lấy dữ liệu bảng CNC
        temp_data = pd.read_sql("SELECT MIN(id) AS MinId, MAX(id) AS MaxId FROM [QC].[dbo].[CNC] WHERE TimeoutCNC2 >= '"+datetime_start+"' and TimeoutCNC2 <= '"+datetime_end+"'", conn)
        id_min = str(temp_data.loc[0,'MinId'])
        id_max = str(temp_data.loc[0,'MaxId'])

        # Lấy dữ liệu bảng
        cursor.execute("SELECT Top(15000) * From[QC].[dbo].[CNC] where id >='"+id_min+"' and id <='"+id_max+"'")
        all_records = cursor.fetchall()

        # Lấy số lượng record
        num_records = len(all_records)

        # Nếu lấy dữ liệu ra trống
        if all_records == None:
            ret = {
                'status':False,
                'message':'Not Exist Data'
            }
            return jsonify(ret),400

        # Nếu tồn tại dữ liệu
        ret = {
                'status':True,
                'message':'Success',
                'data':{}
            }
        
        # Nếu số lượng dòng = 0
        if num_records == 0:
            ret['data'] = None
            return jsonify(ret)
        
        # Nếu lấy dữ liệu không trống        
        # Khởi tạo 2 list dữ liệu cần thiết show bảng dữ liệu và dữ liệu đã qua xử lý để vẽ chart
        ret['data']['table'] = []
        ret['data']['chart'] = {}

        # Lấy dữ liệu để show bảng
        for item in all_records:
            id, machine_no, position_product, name_product, dmc_fixture, dmc_product, position1, time_in_op1, time_out_op1, position2, time_in_op2, time_out_op2, status = item
            ret['data']['table'].append({
                'id': id,
                'machineNo': machine_no,
                'position': position_product,
                'dmcFixture': dmc_fixture,
                'dmcProduct': dmc_product,
                'timeInOP1': time_in_op1,
                'timeOutOP1': time_out_op1,
                'timeInOP2': time_in_op2,
                'timeOutOP2': time_out_op2
            })

        # Lấy dữ liệu để vẽ chart
        cnc_df = pd.read_sql("SELECT left(TimeinCNC1, 11) as Time, Machineno as SetNo, sum(case when Position1 is not null then 1 else 0 end) as Qty_OP1, sum(case when Position2 is not null then 1 else 0 end) as Qty_OP2 FROM [QC].[dbo].[CNC] where  TimeinCNC1 >='"+datetime_start+"' and TimeinCNC1 <= '"+datetime_end+"' group by Machineno, left(TimeinCNC1, 11)", conn)
        cnc_df['SetNo'] = cnc_df['SetNo'].apply(lambda x:int(x[3:]))
        cnc_df = cnc_df.pivot_table(index='Time', columns='SetNo')

        # Khảo sát dữ liệu trong cnc_df
        print(cnc_df.head(10))
        print(cnc_df.columns.to_list())
        print(cnc_df.values.tolist())
        print(cnc_df.index.to_list())

        # Lọc ra các tên cột chỉ giữ lại phần không có chỉ số SetNo 
        column_names_filtered = [col[0] for col in cnc_df.columns.to_list()]
        unique_column_names = list(set(column_names_filtered))
        print(unique_column_names)

        # Khởi tạo các list dữ liệu để vẽ chart
        ret['data']['chart']['opQuantityIndex'] = ["OP1_Quantity", "OP2_Quantity"]
        ret['data']['chart']['opQuantityData']   = []

        for column in unique_column_names: # Với mỗi OP Quantity
            op_data_dict = {}

            # Lấy dữ liệu timeIndex
            op_data_dict['timeIndex'] = cnc_df.index.to_list()

            # Lấy dữ liệu count cho mỗi OP Quantity
            op_quantity_list = []

            # Lấy dữ liệu của toàn bộ các time Index
            for time_idx, time_value in enumerate(op_data_dict['timeIndex']):
                time_data_list = []
                for idx in range(13):
                    time_data_list.append(cnc_df[(column, idx+1)].loc[time_value])
                
                op_quantity_list.append(time_data_list)

            op_data_dict['timeData'] = op_quantity_list

            ret['data']['chart']['opQuantityData'].append(op_data_dict)
        
        return jsonify(ret)
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }   
        Systemp_log1(traceback.format_exc(), "cnc_data").append_new_line()
        return jsonify(ret),500
    
@products.post('/cnc/download')
@swag_from('./docs/products/cnc/cnc_download.yaml')
@token_required_and_permissions
def download_cnc_data(role, permissions):
    try:
        # Tạo cusor để kết nối với database
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234;Database=QC; Trusted_Connection=No;',timeout=1)

        # Check xem có phải Manager không?
        if role < 100:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 25
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

        datetime_start = day_start + " " + time_start
        datetime_end = day_end + " " + time_end

        print("SELECT*From[QC].[dbo].[CNC] where Timeoutcnc2 >= '"+datetime_start+"' and Timeoutcnc2 <= '"+datetime_end+"'")
        cnc_df = pd.read_sql("SELECT*From[QC].[dbo].[CNC] where Timeoutcnc2 >= '"+datetime_start+"' and Timeoutcnc2 <= '"+datetime_end+"'", conn)

        # Nếu lấy dữ liệu ra trống
        if len(cnc_df) == 0:
            ret = {
                'status':False,
                'message':'Not Exist Data'
            }
            return jsonify(ret),400

        output = io.BytesIO()
        writer = pd.ExcelWriter(
            output,
            engine='xlsxwriter')    # add a sheet
        
        cnc_df.to_excel(writer, sheet_name='layer1', index=False)

        # add headers
        writer.close()
        output.seek(0)
        
        return Response(output, mimetype="application/ms-excel",
                        headers={"Content-Disposition": "attachment;filename=CNC_Data.xls"})
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        Systemp_log1(traceback.format_exc(), "cnc_download").append_new_line()
        return jsonify(ret),500
    
@products.get('/cnc/search/<string:dmc>')
@swag_from('./docs/products/cnc/cnc_search.yaml')
@token_required_and_permissions
def search_cnc_data(role, permissions, dmc):
    try:
        # Tạo cusor để kết nối với database
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234;Database=QC; Trusted_Connection=No;',timeout=1)
        cursor = conn.cursor()

        # Check xem có phải Manager không?
        if role < 100:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 25
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

        cursor.execute("SELECT * From [QC].[dbo].[ScanQR] where DMC_product = '"+dmc+"'")
        scanqr_data = cursor.fetchall()

        cursor.execute("SELECT * From [QC].[dbo].[TiltMeasurement] where DMC = '"+dmc+"'")
        tilt_measurement_data = cursor.fetchall()

        cursor.execute("SELECT * From [QC].[dbo].[CNC] where DMC_product like '%"+dmc+"%'")
        cnc_data = cursor.fetchall()

        # Lấy số lượng record
        num_scanqr_records = len(scanqr_data)
        num_tilt_measurement_records = len(tilt_measurement_data)
        num_cnc_records = len(cnc_data)

        # Nếu lấy dữ liệu ra trống
        if scanqr_data == None and tilt_measurement_data == None and cnc_data == None:
            ret = {
                'status':False,
                'message':'Not Exist Data'
            }
            return jsonify(ret),400

        # Nếu tồn tại dữ liệu
        ret = {
                'status':True,
                'message':'Success',
                'data':{}
            }
        
        # Nếu số lượng dòng = 0
        if num_cnc_records == 0 and num_scanqr_records == 0 and num_tilt_measurement_records == 0:
            ret['data'] = None
            return jsonify(ret)
        
        # Khởi tạo các bộ dữ liệu
        ret['data']['scanqrData'] = []
        ret['data']['tiltMeasurementData'] = []
        ret['data']['cncData'] = []

        # Lấy dữ liệu từ bảng ScanQR
        for item in scanqr_data:
            id, product, time_scan_product, time_scan_tray, dmc_product, dmc_tray, compare = item
            
            ret['data']['scanqrData'].append({
                'id': id,
                'product': product,
                'timeScanProduct': time_scan_product,
                'timeScanTray': time_scan_tray,
                'dmcProduct': dmc_product,
                'dmcTray': dmc_tray,
                'compare': compare
            })

        # Lấy dữ liệu từ bảng TiltMeasurement
        for item in tilt_measurement_data:
            id, id_operator, machine_no, name_product, qr_tray, dmc, time_start_temp, time_finish_temp, total_deviation_height, distance, angle_of_part_vs_master, height_1, height_2, height_3, height_4, height_5, result, status, picture, note = item
            
            ret['data']['tiltMeasurementData'].append({
                'id': id,
                'operator': id_operator,
                'machine': machine_no,
                'qr_tray': qr_tray,
                'dataMatrixCode': dmc,
                'timeStart': time_start_temp,
                'timeFinish': time_finish_temp,
                'result': result,
                'status': status,
                'note': note,
                'total_deviation': total_deviation_height,
                'pin_distance': distance,
                'angle': angle_of_part_vs_master,
                'height_1': height_1,
                'height_2': height_2,
                'height_3': height_3,
                'height_4': height_4,
                'height_5': height_5
            })

        # Lấy dữ liệu từ bảng CNC
        for item in cnc_data:
            id, machine_no, position_product, name_product, dmc_fixtrue, dmc_product, position1, time_in_op1, time_out_op1, position2, time_in_op2, time_out_op2, status = item
            ret['data']['cncData'].append({
                'id': id,
                'machineNo': machine_no,
                'position': position_product,
                'dmcFixtrue': dmc_fixtrue,
                'dmcProduct': dmc_product,
                'timeInOP1': time_in_op1,
                'timeOutOP1': time_out_op1,
                'timeInOP2': time_in_op2,
                'timeOutOP2': time_out_op2
            })

        return jsonify(ret)
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        Systemp_log1(traceback.format_exc(), "cnc_search").append_new_line()
        return jsonify(ret),500

# CNC_X4
@products.post('/cnc_x4')
@swag_from('./docs/products/cnc/cnc_x4_data.yaml')
@token_required_and_permissions
def get_cnc_x4_data(role, permissions):
    try:
        # Tạo cusor để kết nối với database
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234;Database=GC; Trusted_Connection=No;',timeout=1)
        cursor = conn.cursor()

        # Check xem có phải Manager không?
        if role < 100:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 27
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

        datetime_start = day_start + " " + time_start
        datetime_end = day_end + " " + time_end

        # Lấy dữ liệu bảng
        cursor.execute("SELECT Top(15000) * From [GC].[dbo].[ProductControl] where TimeScan >='"+datetime_start+"' and TimeScan <='"+datetime_end+"'")
        all_records = cursor.fetchall()

        # Lấy số lượng record
        num_records = len(all_records)

        # Nếu lấy dữ liệu ra trống
        if all_records == None:
            ret = {
                'status':False,
                'message':'Not Exist Data'
            }
            return jsonify(ret),400

        # Nếu tồn tại dữ liệu
        ret = {
                'status':True,
                'message':'Success',
                'data':[]
            }
        
        # Nếu số lượng dòng = 0
        if num_records == 0:
            ret['data'] = None
            return jsonify(ret)

        # Lấy dữ liệu để show bảng
        for item in all_records:
            id, name_operator, product_name, dmc, line, time_scan = item
            ret['data'].append({
                'id': id,
                'nameOperator': name_operator,
                'productName': product_name,
                'dmc': dmc,
                'line': line,
                'timeScan': time_scan
            })
        
        return jsonify(ret)
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }   
        Systemp_log1(traceback.format_exc(), "cnc_x4_data").append_new_line()
        return jsonify(ret),500

@products.post('/cnc_x4/download')
@swag_from('./docs/products/cnc/cnc_x4_download.yaml')
@token_required_and_permissions
def download_cnc_x4_data(role, permissions):
    try:
        # Tạo cusor để kết nối với database
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234;Database=GC; Trusted_Connection=No;',timeout=1)

        # Check xem có phải Manager không?
        if role < 100:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 27
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

        datetime_start = day_start + " " + time_start
        datetime_end = day_end + " " + time_end

        print("SELECT Top(15000) * From [GC].[dbo].[ProductControl] where TimeScan >='"+datetime_start+"' and TimeScan <='"+datetime_end+"'")
        cnc_x4_df = pd.read_sql("SELECT Top(15000) * From[GC].[dbo].[ProductControl] where TimeScan >='"+datetime_start+"' and TimeScan <='"+datetime_end+"'", conn)

        # Nếu lấy dữ liệu ra trống
        if len(cnc_x4_df) == 0:
            ret = {
                'status':False,
                'message':'Not Exist Data'
            }
            return jsonify(ret),400

        output = io.BytesIO()
        writer = pd.ExcelWriter(
            output,
            engine='xlsxwriter')    # add a sheet
        
        cnc_x4_df.to_excel(writer, sheet_name='layer1', index=False)

        # add headers
        writer.close()
        output.seek(0)
        
        return Response(output, mimetype="application/ms-excel",
                        headers={"Content-Disposition": "attachment;filename=CNCX4_Data.xls"})
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        Systemp_log1(traceback.format_exc(), "cnc_x4_download").append_new_line()
        return jsonify(ret),500
    
# AIR GUAGE GC
@products.post('/air_gauge_gc')
@swag_from('./docs/products/air_guage/air_guage_gc_data.yaml')
@token_required_and_permissions
def get_air_guage_gc_data(role, permissions):
    try:
        # Tạo cusor để kết nối với database
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234;Database=GC; Trusted_Connection=No;',timeout=1)
        cursor = conn.cursor()

        # Check xem có phải Manager không?
        if role < 100:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 28
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

        datetime_start = day_start + " " + time_start
        datetime_end = day_end + " " + time_end

        # Lấy dữ liệu bảng ShotBlasting
        cursor.execute("SELECT Top(15000) * FROM [GC].[dbo].[Measure_Diameter] where Time_finish >'"+datetime_start+"' and Time_finish <'"+datetime_end+"'")
        all_records = cursor.fetchall()

        # Lấy số lượng record
        num_records = len(all_records)

        # Nếu lấy dữ liệu ra trống
        if all_records == None:
            ret = {
                'status':False,
                'message':'Not Exist Data'
            }
            return jsonify(ret),400

        # Nếu có máy
        ret = {
                'status':True,
                'message':'Success',
                'data':{}
            }
        
        if num_records == 0:
            ret['data'] = None
            return jsonify(ret)
        
        # Nếu lấy dữ liệu không trống        
        # Khởi tạo 2 list dữ liệu cần thiết show bảng dữ liệu và dữ liệu đã qua xử lý để vẽ chart
        ret['data']['table'] = []
        ret['data']['chart'] = {}

        # Lấy dữ liệu để show bảng
        for item in all_records:
            id, product_name, time_scan_dmc, dmc, a_min, a_max, b_min, b_max, time_finish, result = item
            
            ret['data']['table'].append({
                'id': id,
                'productName': product_name,
                'timeScanDMC': time_scan_dmc,
                'dmc': dmc,
                'aMin': a_min,
                'aMax': a_max,
                'bMin': b_min,
                'bMax': b_max,
                'timeFinish': time_finish,
                'result': result
            })

        # Lấy dữ liệu để vẽ chart
        air_gauge_gc_df = pd.read_sql("SELECT left(Time_finish,11) as 'Time', Result, COUNT(Result) AS 'Count'FROM [GC].[dbo].[Measure_Diameter] where Time_finish >'"+datetime_start+"' and Time_finish <'"+datetime_end+"' GROUP BY left(Time_finish, 11), Result order by left(Time_finish, 11) desc",conn)
        air_gauge_gc_df = air_gauge_gc_df.pivot_table(index='Time', columns='Result')

        # Khảo sát dữ liệu trong df
        print(air_gauge_gc_df.head(10))
        print(air_gauge_gc_df.columns.to_list())
        print(air_gauge_gc_df.values.tolist())
        print(air_gauge_gc_df.index.to_list())

        # Khởi tạo các list dữ liệu để vẽ chart
        ret['data']['chart']['timeIndex'] = []
        ret['data']['chart']['okNgData'] = []

        # Lấy dữ liệu timeIndex
        ret['data']['chart']['timeIndex'] = air_gauge_gc_df.index.to_list()

        # Lấy dữ liệu count OK và count NG của mỗi timeIndex
        for idx in range(len(air_gauge_gc_df.index.tolist())):
            if len(air_gauge_gc_df.values.tolist()[idx]) > 1:
                if isNaN(air_gauge_gc_df.values.tolist()[idx][0]):
                    ret['data']['chart']['okNgData'].append({'NG': 0, 'OK': air_gauge_gc_df.values.tolist()[idx][1]}) 
                else:
                    ret['data']['chart']['okNgData'].append({'NG': air_gauge_gc_df.values.tolist()[idx][0], 'OK': air_gauge_gc_df.values.tolist()[idx][1]})
            else: 
                ret['data']['chart']['okNgData'].append({'NG': 0, 'OK': air_gauge_gc_df.values.tolist()[idx][0]})

        return jsonify(ret)
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        Systemp_log1(traceback.format_exc(), "air_guage_gc_data").append_new_line()
        return jsonify(ret),500
    
@products.post('/air_guage_gc/download')
@swag_from('./docs/products/air_guage/air_guage_gc_download.yaml')
@token_required_and_permissions
def download_air_guage_gc_data(role, permissions):
    try:
        # Tạo cusor để kết nối với database
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234;Database=GC; Trusted_Connection=No;',timeout=1)

        # Check xem có phải Manager không?
        if role < 100:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 28
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

        datetime_start = day_start + " " + time_start
        datetime_end = day_end + " " + time_end

        print("SELECT * FROM [GC].[dbo].[Measure_Diameter] where Time_finish >'"+datetime_start+"' and Time_finish <'"+datetime_end+"'")
        air_guage_gc_df = pd.read_sql("SELECT * FROM [GC].[dbo].[Measure_Diameter] where Time_finish >'"+datetime_start+"' and Time_finish <'"+datetime_end+"'", conn)
        
        # Nếu lấy dữ liệu ra trống
        if len(air_guage_gc_df) == 0:
            ret = {
                'status':False,
                'message':'Not Exist Data'
            }
            return jsonify(ret),400

        output = io.BytesIO()
        writer = pd.ExcelWriter(
            output,
            engine='xlsxwriter')    # add a sheet
        
        air_guage_gc_df.to_excel(writer, sheet_name='layer1', index=False)

        # add headers
        writer.close()
        output.seek(0)
        
        return Response(output, mimetype="application/ms-excel",
                        headers={"Content-Disposition": "attachment;filename=AirGuageGC_Data.xls"})
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        Systemp_log1(traceback.format_exc(), "air_guage_gc_download").append_new_line()
        return jsonify(ret),500

# AIR GUAGE QC
@products.post('/air_gauge_qc')
@swag_from('./docs/products/air_guage/air_guage_qc_data.yaml')
@token_required_and_permissions
def get_air_guage_qc_data(role, permissions):
    try:
        # Tạo cusor để kết nối với database
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234;Database=QC; Trusted_Connection=No;',timeout=1)
        cursor = conn.cursor()

        # Check xem có phải Manager không?
        if role < 100:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 29
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

        datetime_start = day_start + " " + time_start
        datetime_end = day_end + " " + time_end

        # Lấy dữ liệu bảng ShotBlasting
        cursor.execute("SELECT Top(15000)[ID],[Machine],[Product_Name],[Time_ScanDMC],[TimeFinish],[DMC],[1_Title] ,[1_Type],[1_Min] as A_Min,[1_Max] as A_Max,[2_Title],[2_Type] ,[2_Min] as B_Min,[2_Max] as B_Max,[3_Title],[3_Type],[3_Min] as C_Min,[3_Max] as C_Max,[4_Title],[4_Type],[4_Min] as D_Min,[4_Max] as D_Max,[Result],[PinRing] FROM [QC].[dbo].[airgauge] where TimeFinish >'"+datetime_start+"' and TimeFinish <'"+datetime_end+"'")
        all_records = cursor.fetchall()

        # Lấy số lượng record
        num_records = len(all_records)

        # Nếu lấy dữ liệu ra trống
        if all_records == None:
            ret = {
                'status':False,
                'message':'Not Exist Data'
            }
            return jsonify(ret),400

        # Nếu có máy
        ret = {
                'status':True,
                'message':'Success',
                'data':{}
            }
        
        if num_records == 0:
            ret['data'] = None
            return jsonify(ret)
        
        # Nếu lấy dữ liệu không trống        
        # Khởi tạo 2 list dữ liệu cần thiết show bảng dữ liệu và dữ liệu đã qua xử lý để vẽ chart
        ret['data']['table'] = []
        ret['data']['chart'] = {}

        # Lấy dữ liệu để show bảng
        for item in all_records:
            # [ID],[Machine],[Product_Name],[Time_ScanDMC],[TimeFinish],[DMC],[1_Title] ,[1_Type],[1_Min] as A_Min,[1_Max] as A_Max,[2_Title],[2_Type] ,[2_Min] as B_Min,[2_Max] as B_Max,[3_Title],[3_Type],[3_Min] as C_Min,[3_Max] as C_Max,[4_Title],[4_Type],[4_Min] as D_Min,[4_Max] as D_Max,[Result],[PinRing]
            id, machine, product_name, time_scan_dmc, time_finish, dmc, title_1, type_1, a_min, a_max, title_2, type_2, b_min, b_max, title_3, type_3, c_min, c_max, title_4, type_4, d_min, d_max, result, pinring = item
            
            ret['data']['table'].append({
                'id': id,
                'machine': machine,
                'productName': product_name,
                'timeScanDMC': time_scan_dmc,
                'timeFinish': time_finish,
                'dmc': dmc,
                'title1': title_1,
                'type1': type_1,
                'aMin': a_min,
                'aMax': a_max,
                'title2': title_2,
                'type2': type_2,
                'bMin': b_min,
                'bMax': b_max,
                'title3': title_3,
                'type3': type_3,
                'cMin': c_min,
                'cMax': c_max,
                'title4': title_4,
                'type4': type_4,
                'dMin': d_min,
                'dMax': d_max,
                'result': result,
                'pinring': pinring
            })

        # Lấy dữ liệu để vẽ chart
        air_gauge_qc_df = pd.read_sql("SELECT left(Time_finish, 11) as 'Time', Result, COUNT(Result) AS 'Count' FROM [QC].[dbo].[Measure_Diameter] where Time_finish >'"+datetime_start+"' and Time_finish <'"+datetime_end+"' GROUP BY left(Time_finish, 11), Result order by left(Time_finish, 11) desc", conn)
        air_gauge_qc_df = air_gauge_qc_df.pivot_table(index='Time', columns='Result')

        # Khảo sát dữ liệu trong df
        print(air_gauge_qc_df.head(10))
        print(air_gauge_qc_df.columns.to_list())
        print(air_gauge_qc_df.values.tolist())
        print(air_gauge_qc_df.index.to_list())

        # Khởi tạo các list dữ liệu để vẽ chart
        ret['data']['chart']['timeIndex'] = []
        ret['data']['chart']['okNgData'] = []

        # Lấy dữ liệu timeIndex
        ret['data']['chart']['timeIndex'] = air_gauge_qc_df.index.to_list()

        # Lấy dữ liệu count OK và count NG của mỗi timeIndex
        for idx in range(len(air_gauge_qc_df.index.tolist())):

            ret['data']['chart']['okNgData'].append({'NG': 0 if isNaN(air_gauge_qc_df.values.tolist()[idx][0]) else air_gauge_qc_df.values.tolist()[idx][0], 'OK': 0 if isNaN(air_gauge_qc_df.values.tolist()[idx][1]) else air_gauge_qc_df.values.tolist()[idx][1], 'Return': 0 if isNaN(air_gauge_qc_df.values.tolist()[idx][2]) else air_gauge_qc_df.values.tolist()[idx][2], 'Special': 0 if isNaN(air_gauge_qc_df.values.tolist()[idx][3]) else air_gauge_qc_df.values.tolist()[idx][3]}) 
        
        return jsonify(ret)
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        Systemp_log1(traceback.format_exc(), "air_guage_qc_data").append_new_line()
        return jsonify(ret),500
    
@products.post('/air_guage_qc/download')
@swag_from('./docs/products/air_guage/air_guage_qc_download.yaml')
@token_required_and_permissions
def download_air_guage_qc_data(role, permissions):
    try:
        # Tạo cusor để kết nối với database
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234;Database=QC; Trusted_Connection=No;',timeout=1)

        # Check xem có phải Manager không?
        if role < 100:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 29
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

        datetime_start = day_start + " " + time_start
        datetime_end = day_end + " " + time_end

        print("SELECT * FROM [GC].[dbo].[Measure_Diameter] where Time_finish >'"+datetime_start+"' and Time_finish <'"+datetime_end+"'")
        air_guage_qc_df = pd.read_sql("SELECT * FROM [QC].[dbo].[Measure_Diameter] where Time_finish >'"+datetime_start+"' and Time_finish <'"+datetime_end+"'", conn)
        
        # Nếu lấy dữ liệu ra trống
        if len(air_guage_qc_df) == 0:
            ret = {
                'status':False,
                'message':'Not Exist Data'
            }
            return jsonify(ret),400

        output = io.BytesIO()
        writer = pd.ExcelWriter(
            output,
            engine='xlsxwriter')    # add a sheet
        
        air_guage_qc_df.to_excel(writer, sheet_name='layer1', index=False)

        # add headers
        writer.close()
        output.seek(0)
        
        return Response(output, mimetype="application/ms-excel",
                        headers={"Content-Disposition": "attachment;filename=AirGuageQC_Data.xls"})
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        Systemp_log1(traceback.format_exc(), "air_guage_qc_download").append_new_line()
        return jsonify(ret),500
    
# search cho từng nhóm 

# search cho nhóm optical_division & laser
@products.get('/search_1/<string:dmc>')
@swag_from('./docs/products/search_data_1.yaml')
@token_required_and_permissions
def search_data_1(role, permissions, dmc):
    try:
        # Tạo cusor để kết nối với database
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234;Database=QC; Trusted_Connection=No;',timeout=1)
        cursor = conn.cursor()

        # Check xem có phải Manager không?
        if role < 100:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 1
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

        if len(dmc) == 29:
            ctc = dmc[21:28]
            if ctc[1] == 'X':
                mathang = '10'
            elif ctc[1] == 'Y':
                mathang = '11'
            elif ctc[1] == 'Z':
                mathang = '12'
            else:
                mathang = '0'+ctc[1]
            casting_code = '202' + ctc[0] + '.' + mathang + '.' + ctc[2:4] + '-' + ctc[4:]
        elif len(dmc) == 25:
            ctc = dmc[17:24]
            if ctc[1] == 'X':
                mathang = '10'
            elif ctc[1] == 'Y':
                mathang = '11'
            elif ctc[1] == 'Z':
                mathang = '12'
            else:
                mathang = '0'+ctc[1]
            casting_code = '202' + ctc[0] + '.' + mathang + '.' + ctc[2:4] + '-' + ctc[4:]
        else:
            casting_code = 'xxxxxx'

        cursor.execute("SELECT * From [SPC].[dbo].newoptical1() where CastingNo = '"+casting_code+"'")
        opticaldivision_data = cursor.fetchall()

        cursor.execute("SELECT top (1) Id, MachineNo, NameOperator, NameProduct, DMCin, TimeInDMC, TimeOutDMC, TimeOutBarcode, Result, Status From [QC].[dbo].[Laser] where DMCout = '"+dmc+"' order by id desc")
        laser_data = cursor.fetchall()

        # Lấy số lượng record
        num_records = len(opticaldivision_data)

        # Nếu lấy dữ liệu ra trống
        if opticaldivision_data == None:
            ret = {
                'status':False,
                'message':'Not Exist Data'
            }
            return jsonify(ret),400

        # Nếu tồn tại dữ liệu
        ret = {
                'status':True,
                'message':'Success',
                'data':{}
            }
        
        # Nếu số lượng dòng = 0
        if num_records == 0:
            ret['data'] = None
            return jsonify(ret)

        # Lấy dữ liệu để show bảng Optical Division
        ret['data']['opticalDivision'] = None
        for optical_divisiom_item in opticaldivision_data:
            vctrlid, datetime_create, c, si, mn, p, s, ni, cr, mo, cu, ti, v, pb, w, ai, co, nb, a_s, sn, sb, b, bi, ca, zn, n, ce, mg, ta, zr, ti_nb, fe_percent, cef, other, a1_appearance, vctrlid_c, casting_no = optical_divisiom_item
            ret["data"]["opticalDivision"] = {
                'vctrlid': vctrlid,
                'datetimeCreate': datetime_create.strftime('%Y-%m-%d %H:%M:%S') if datetime_create is not None else datetime_create,
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
                'a1Appearance': a1_appearance,
                'vctrlidC': vctrlid_c,
                'castingNo': casting_no
            }

        # Lấy dữ liệu để show bảng Laser
        ret['data']['laser'] = None
        for laser_item in laser_data:
            id, machine_no, name_operator, name_product, dmc, time_start, time_end, time_scan, result, status = laser_item
            ret['data']['laser'] = {
                'id': id,
                'machine': machine_no,
                'operator': name_operator,
                'product': name_product,
                'dmc': dmc,
                'timeStart': time_start.strftime('%Y-%m-%d %H:%M:%S') if time_start is not None else time_start,
                'timeEnd': time_end.strftime('%Y-%m-%d %H:%M:%S') if time_end is not None else time_end,
                'timeScan': time_scan.strftime('%Y-%m-%d %H:%M:%S') if time_scan is not None else time_scan,
                'result': result,
                'status': status
            }

        return jsonify(ret)
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }   
        Systemp_log1(traceback.format_exc(), "search_data_1").append_new_line()
        return jsonify(ret),500
    
# search cho nhóm scanqr & manual scan & tilt_measurement
@products.get('/search_2/<string:dmc>')
@swag_from('./docs/products/search_data_2.yaml')
@token_required
def search_data_2(role, permissions, dmc):
    try:
        # Tạo cusor để kết nối với database
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234;Database=QC; Trusted_Connection=No;',timeout=1)
        cursor = conn.cursor()

        # Check xem có phải Manager không?
        if role < 100:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 1
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
        
        cursor.execute("SELECT top (1) * From [QC].[dbo].[ScanQR] where DMC_product = '"+dmc+"' order by id desc")
        scanqr_data = cursor.fetchall()

        # Dữ liệu của mình
        cursor.execute("SELECT top (1) * From [QC].[dbo].[Scan_Repair_Data] where KhuVuc = N'Ngoại Quan' and DMC = '"+dmc+"' order by id desc")
        ngoaiquan_data = cursor.fetchall()

        cursor.execute("SELECT top (1) * From [QC].[dbo].[Scan_Repair_Data] where KhuVuc = N'Pin Ren' and DMC = '"+dmc+"' order by id desc")
        pinren_data = cursor.fetchall()

        cursor.execute("SELECT top (1) * From [QC].[dbo].[Scan_Repair_Data] where KhuVuc = N'Kiểm Tra Ren' and DMC = '"+dmc+"' order by id desc")
        kiemtraren_data = cursor.fetchall()

        cursor.execute("SELECT top (1) * From [QC].[dbo].[Scan_Repair_Data] where KhuVuc = N'Gá Tổng Hợp' and DMC = '"+dmc+"' order by id desc")
        gatonghop_data = cursor.fetchall()

        cursor.execute("SELECT top (1) * From [QC].[dbo].[Scan_Repair_Data] where KhuVuc = N'Kích Thước Khác' and DMC = '"+dmc+"' order by id desc")
        kichthuockhac_data = cursor.fetchall()

        # ================

        cursor.execute("SELECT top (1) * From [QC].[dbo].[TiltMeasurement] where DMC = '"+dmc+"' order by id desc")
        tilt_measurement_data = cursor.fetchall()

        # Lấy số lượng record
        num_records = len(scanqr_data)

        # Nếu lấy dữ liệu ra trống
        if scanqr_data == None:
            ret = {
                'status':False,
                'message':'Not Exist Data'
            }
            return jsonify(ret),400

        # Nếu tồn tại dữ liệu
        ret = {
                'status':True,
                'message':'Success',
                'data':{}
            }
        
        # Nếu số lượng dòng = 0
        if num_records == 0:
            ret['data'] = None
            return jsonify(ret)
        
        # Lấy dữ liệu để show bảng ScanQR
        ret['data']['scanQR'] = None
        for item in scanqr_data:
            id, product, time_scan_product, time_scan_tray, dmc_product, dmc_tray, compare = item
            
            ret['data']['scanQR'] = {
                'id': id,
                'product': product,
                'timeScanProduct': time_scan_product.strftime('%Y-%m-%d %H:%M:%S') if time_scan_product is not None else time_scan_product,
                'timeScanTray': time_scan_tray.strftime('%Y-%m-%d %H:%M:%S') if time_scan_tray is not None else time_scan_tray,
                'dmcProduct': dmc_product,
                'dmcTray': dmc_tray,
                'compare': compare
            }
        # Lấy dữ liệu Manual Scan

        # Ngoại Quan
        ret['data']['visualInspection'] = None
        for item in ngoaiquan_data:
            id, msnv, station, station_no, dmc, product_type, time_save = item
            
            ret['data']['visualInspection'] = {
                'id': id,
                'msnv': msnv,
                'station': station,
                'stationNo': station_no,
                'dmc': dmc,
                'productType': product_type,
                'timeSave': time_save.strftime('%Y-%m-%d %H:%M:%S') if time_save is not None else time_save
            }

        # Pin Ren
        ret['data']['pinInspection'] = None
        for item in pinren_data:
            id, msnv, station, station_no, dmc, product_type, time_save = item
            
            ret['data']['pinInspection'] = {
                'id': id,
                'msnv': msnv,
                'station': station,
                'stationNo': station_no,
                'dmc': dmc,
                'productType': product_type,
                'timeSave': time_save.strftime('%Y-%m-%d %H:%M:%S') if time_save is not None else time_save
            }

        # Kiểm Tra Ren
        ret['data']['threadInspection'] = None
        for item in kiemtraren_data:
            id, msnv, station, station_no, dmc, product_type, time_save = item
            
            ret['data']['threadInspection'] = {
                'id': id,
                'msnv': msnv,
                'station': station,
                'stationNo': station_no,
                'dmc': dmc,
                'productType': product_type,
                'timeSave': time_save.strftime('%Y-%m-%d %H:%M:%S') if time_save is not None else time_save
            }

        # Gá Tổng Hợp
        ret['data']['totalFixtureInspection'] = None
        for item in gatonghop_data:
            id, msnv, station, station_no, dmc, product_type, time_save = item
            ret['data']['totalFixtureInspection'] = {
                'id': id,
                'msnv': msnv,
                'station': station,
                'stationNo': station_no,
                'dmc': dmc,
                'productType': product_type,
                'timeSave': time_save.strftime('%Y-%m-%d %H:%M:%S') if time_save is not None else time_save
            }

        # Kích Thước Khác
        ret['data']['dimensionInspection'] = None
        for item in kichthuockhac_data:
            id, msnv, station, station_no, dmc, product_type, time_save = item
            
            ret['data']['dimensionInspection'] = {
                'id': id,
                'msnv': msnv,
                'station': station,
                'stationNo': station_no,
                'dmc': dmc,
                'productType': product_type,
                'timeSave': time_save.strftime('%Y-%m-%d %H:%M:%S') if time_save is not None else time_save
            }

        # Lấy dữ liệu để show bảng Ngoại Quan, Pin Ren, Kiểm Tra Ren, Gá Tổng Hợp, Kích Thước Khác

        # Lấy dữ liệu để show bảng Tilt Measurement
        ret['data']['tiltMeasurement'] = None
        for item in tilt_measurement_data:
            id, id_operator, machine_no, name_product, qr_tray, dmc, time_start_temp, time_finish_temp, total_deviation_height, distance, angle_of_part_vs_master, height_1, height_2, height_3, height_4, height_5, result, status, picture, note = item
            
            ret['data']['tiltMeasurement'] = {
                'id': id,
                'operator': id_operator,
                'machine': machine_no,
                'qr_tray': qr_tray,
                'dataMatrixCode': dmc,
                'timeStart': time_start_temp.strftime('%Y-%m-%d %H:%M:%S') if time_start_temp is not None else time_start_temp,
                'timeFinish': time_finish_temp.strftime('%Y-%m-%d %H:%M:%S') if time_finish_temp is not None else time_finish_temp,
                'result': result,
                'status': status,
                'note': note,
                'total_deviation': total_deviation_height,
                'pin_distance': distance,
                'angle': angle_of_part_vs_master,
                'height_1': height_1,
                'height_2': height_2,
                'height_3': height_3,
                'height_4': height_4,
                'height_5': height_5
            }

        return jsonify(ret)
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }   
        Systemp_log1(traceback.format_exc(), "search_data_2").append_new_line()
        return jsonify(ret),500
    
# search cho nhóm cnc va cnc_x4

@products.get('/search_3/<string:dmc>')
@swag_from('./docs/products/search_data_3.yaml')
@token_required
def search_data_3(role, permissions, dmc):
    try:
        # Tạo cusor để kết nối với database
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234;Database=QC; Trusted_Connection=No;',timeout=1)
        cursor = conn.cursor()

        # Check xem có phải Manager không?
        if role < 100:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 1
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

        cursor.execute("SELECT top (1) * From [QC].[dbo].[CNC] where DMC_product like '%"+dmc+"%' order by id desc")
        cnc_data = cursor.fetchall()

        cursor.execute("SELECT top (1) * From [GC].[dbo].[ProductControl] where DMC like '%"+dmc+"%' order by id desc")
        cnc_x4_data = cursor.fetchall()

        # Lấy số lượng record
        num_records = len(cnc_data)

        # Nếu lấy dữ liệu ra trống
        if cnc_data == None:
            ret = {
                'status':False,
                'message':'Not Exist Data'
            }
            return jsonify(ret),400

        # Nếu tồn tại dữ liệu
        ret = {
                'status':True,
                'message':'Success',
                'data':{}
            }
        
        # Nếu số lượng dòng = 0
        if num_records == 0:
            ret['data'] = None
            return jsonify(ret)

        # Lấy dữ liệu để show bảng CNC
        ret['data']['cnc'] = None
        for item in cnc_data:
            id, machine_no, position_product, name_product, dmc_fixtrue, dmc_product, position1, time_in_op1, time_out_op1, position2, time_in_op2, time_out_op2, status = item
            ret['data']['cnc'] = {
                'id': id,
                'machineNo': machine_no,
                'position': position_product,
                'productName': name_product,
                'dmcFixture': dmc_fixtrue,
                'dmcProduct': dmc_product,
                'timeInOP1': time_in_op1.strftime('%Y-%m-%d %H:%M:%S') if time_in_op1 is not None else time_in_op1,
                'timeOutOP1': time_out_op1.strftime('%Y-%m-%d %H:%M:%S') if time_out_op1 is not None else time_out_op1,
                'timeInOP2': time_in_op2.strftime('%Y-%m-%d %H:%M:%S') if time_in_op2 is not None else time_in_op2,
                'timeOutOP2': time_out_op2.strftime('%Y-%m-%d %H:%M:%S') if time_out_op2 is not None else time_out_op2
            }

        # Lấy dữ liệu để show bảng CNCX4
        ret['data']['cncX4'] = None
        for item in cnc_x4_data:
            id, name_operator, product_name, dmc, line, time_scan = item
            ret['data']['cncX4'] = {
                'id': id,
                'nameOperator': name_operator,
                'productName': product_name,
                'dmc': dmc,
                'line': line,
                'timeScan': time_scan.strftime('%Y-%m-%d %H:%M:%S') if time_scan is not None else time_scan
            }

        return jsonify(ret)
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }   
        Systemp_log1(traceback.format_exc(), "search_data_3").append_new_line()
        return jsonify(ret),500

# search cho nhóm thread_verification & air_guage_qc & air_guage_gc

@products.get('/search_4/<string:dmc>')
@swag_from('./docs/products/search_data_4.yaml')
@token_required
def search_data_4(role, permissions, dmc):
    try:
        # Tạo cusor để kết nối với database
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234;Database=QC; Trusted_Connection=No;',timeout=1)
        cursor = conn.cursor()

        # Check xem có phải Manager không?
        if role < 100:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 1
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
        
        cursor.execute("SELECT top (1) * From[QC].[dbo].[ThreadVerification] where DMC_product = '"+dmc+"' order by id desc")
        thread_verification_data = cursor.fetchall()

        cursor.execute("SELECT top (1) * From[QC].[dbo].[Measure_Diameter] where DMC = '"+dmc+"' order by id desc")
        airguage_qc_data = cursor.fetchall()

        cursor.execute("SELECT top (1) * From[GC].[dbo].[Measure_Diameter] where DMC = '"+dmc+"' order by id desc")
        airguage_gc_data = cursor.fetchall()

        # Lấy số lượng record
        num_records = len(airguage_qc_data)
        num_records_1 = len(airguage_gc_data)

        # Nếu lấy dữ liệu ra trống
        if airguage_qc_data == None and airguage_gc_data == None:
            ret = {
                'status':False,
                'message':'Not Exist Data'
            }
            return jsonify(ret),400

        # Nếu tồn tại dữ liệu
        ret = {
                'status':True,
                'message':'Success',
                'data':{}
            }
        
        # Nếu số lượng dòng = 0
        if num_records == 0 and num_records_1 == 0:
            ret['data'] = None
            return jsonify(ret)

        # Lấy dữ liệu để show bảng ThreadVerification
        ret['data']['threadVerification'] = None
        for item in thread_verification_data:
            id, op_name, machine, product_name, dmc_product, time_start, time_finish, quality, status, actual_measured_value, setting_value, thread_gauge_code, life_time, note_life_time, torque_h1, torque_h2, torque_h3, torque_h4, torque_h5, torque_h6, torque_h7, torque_h8, torque_h9, torque_h10, torque_h11 = item
            ret['data']['threadVerification'] = {
                'id': id,
                'opName': op_name,
                'machine': machine,
                'dmcProduct': dmc_product,
                'timeStart': time_start.strftime('%Y-%m-%d %H:%M:%S') if time_start is not None else time_start,
                'timeFinish': time_finish.strftime('%Y-%m-%d %H:%M:%S') if time_finish is not None else time_finish,
                'quality': quality,
                'status': status
            }

        # Lấy dữ liệu Airguage QC Data
        ret['data']['airguageQCData'] = None
        for item in airguage_qc_data:
            id, product_name, time_scan_dmc, dmc, a_min, a_max, b_min, b_max, time_finish, result = item
            ret['data']['airguageQCData'] = {
                'id': id,
                'productName': product_name,
                'timeScanDMC': time_scan_dmc.strftime('%Y-%m-%d %H:%M:%S') if time_scan_dmc is not None else time_scan_dmc,
                'dmc': dmc,
                'aMin': a_min,
                'aMax': a_max,
                'bMin': b_min,
                'bMax': b_max,
                'timeFinish': time_finish.strftime('%Y-%m-%d %H:%M:%S') if time_finish is not None else time_finish,
                'result': result
            }

        # Lấy dữ liệu Airguage GC Data
        ret['data']['airguageGCData'] = None
        for item in airguage_gc_data:
            id, product_name, time_scan_dmc, dmc, a_min, a_max, b_min, b_max, time_finish, result = item
            ret['data']['airguageGCData'] = {
                'id': id,
                'productName': product_name,
                'timeScanDMC': time_scan_dmc.strftime('%Y-%m-%d %H:%M:%S') if time_scan_dmc is not None else time_scan_dmc,
                'dmc': dmc,
                'aMin': a_min,
                'aMax': a_max,
                'bMin': b_min,
                'bMax': b_max,
                'timeFinish': time_finish.strftime('%Y-%m-%d %H:%M:%S') if time_finish is not None else time_finish,
                'result': result
            }

        return jsonify(ret)
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }   
        Systemp_log1(traceback.format_exc(), "search_data_4").append_new_line()
        return jsonify(ret),500

# search cho nhóm air_tight & air_tight_chamfer & air_tight_window

@products.get('/search_5/<string:dmc>')
@swag_from('./docs/products/search_data_5.yaml')
@token_required
def search_data_5(role, permissions, dmc):
    try:
        # Tạo cusor để kết nối với database
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234;Database=QC; Trusted_Connection=No;',timeout=1)
        cursor = conn.cursor()

        # Check xem có phải Manager không?
        if role < 100:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 1
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

        cursor.execute("select top (1) * from  [QC].[dbo].[air_tight] WHERE barcode = '"+dmc+"' order by id desc")
        airtight_data = cursor.fetchall()
        print(len(airtight_data))
        
        cursor.execute("select top (1) * from  [QC].[dbo].[air_tight_chamfer] WHERE barcode = '"+dmc+"' order by id desc")
        airtight_chamfer_data = cursor.fetchall()

        cursor.execute("select top (1) * from  [QC].[dbo].[air_tight_window] WHERE barcode = '"+dmc+"' order by id desc")
        airtight_window_data = cursor.fetchall()

        # Lấy số lượng record
        num_records = len(airtight_data)

        # Nếu lấy dữ liệu ra trống
        if airtight_data == None:
            ret = {
                'status':False,
                'message':'Not Exist Data'
            }
            return jsonify(ret),400

        # Nếu tồn tại dữ liệu
        ret = {
                'status':True,
                'message':'Success',
                'data':{}
            }
        
        # Nếu số lượng dòng = 0
        if num_records == 0:
            ret['data'] = None
            return jsonify(ret)

        #  Lấy dữ liệu để show bảng air_tight
        ret['data']['airTight'] = None
        for item in airtight_data:
            id, machine, prodcut_type, barcode, position, air_value, time_start_air_tight, time_finish_air_tight, quality, note = item
            ret['data']['airTight'] = {
                'id': id,
                'machine': machine,
                'productType': prodcut_type,
                'barcode': barcode,
                'position': position,
                'airValue': air_value,
                'timeStart': time_start_air_tight.strftime('%Y-%m-%d %H:%M:%S') if time_start_air_tight is not None else time_start_air_tight,
                'timeFinish': time_finish_air_tight.strftime('%Y-%m-%d %H:%M:%S') if time_finish_air_tight is not None else time_finish_air_tight,
                'quality': quality,
                'note': note
            }


        # Lấy dữ liệu để show bảng air_tight_chamfer
        ret['data']['airTightChamfer'] = None
        for item in airtight_chamfer_data:
            id, machine, prodcut_type, barcode, position, air_value, time_start_air_tight_chamfer, time_finish_air_tight_chamfer, quality, note = item
            ret['data']['airTightChamfer'] = {
                'id': id,
                'machine': machine,
                'productType': prodcut_type,
                'barcode': barcode,
                'position': position,
                'airValue': air_value,
                'timeStart': time_start_air_tight_chamfer.strftime('%Y-%m-%d %H:%M:%S') if time_start_air_tight_chamfer is not None else time_start_air_tight_chamfer,
                'timeFinish': time_finish_air_tight_chamfer.strftime('%Y-%m-%d %H:%M:%S') if time_finish_air_tight_chamfer is not None else time_finish_air_tight_chamfer,
                'quality': quality,
                'note': note
            }

        # Lấy dữ liệu để show bảng air_tight_window
        ret['data']['airTightWindow'] = None
        for item in airtight_window_data:
            id, product_name, barcode, air_value1, status_position1, time_start_1, time_finish_1, air_value2, status_position2, time_start2, time_finish2, note = item
            ret['data']['airTightWindow'] = {
                'id': id,
                'productName': product_name,
                'barcode': barcode,
                'airValue1': air_value1,
                'statusPosition1': status_position1,
                'timeStart1': time_start_1.strftime('%Y-%m-%d %H:%M:%S') if time_start_1 is not None else time_start_1,
                'timeFinish1': time_finish_1.strftime('%Y-%m-%d %H:%M:%S') if time_finish_1 is not None else time_finish_1,
                'airValue2': air_value2,
                'statusPosition2': status_position2,
                'timeStart2': time_start2.strftime('%Y-%m-%d %H:%M:%S') if time_start2 is not None else time_start2,
                'timeFinish2': time_finish2.strftime('%Y-%m-%d %H:%M:%S') if time_finish2 is not None else time_finish2,
                'note': note
            }

        return jsonify(ret)
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }   
        Systemp_log1(traceback.format_exc(), "search_data_5").append_new_line()
        return jsonify(ret),500

# search cho classification
@products.get('/search_6/<string:dmc>')
@swag_from('./docs/products/search_data_6.yaml')
@token_required
def search_data_6(role, permissions, dmc):
    try:
        # Tạo cusor để kết nối với database
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234;Database=QC; Trusted_Connection=No;',timeout=1)
        cursor = conn.cursor()

        # Check xem có phải Manager không?
        if role < 100:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 1
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

        cursor.execute("SELECT top (1) b.SPLR_LOT_NO, a.id, a.lazer_machine, a.Time_check, a.pallet_num, a.Num, a.name, a.total_code, a.dmc_was_replace, a.total_quality, a.dataman_total_quality, a.camera_product_shape, a.error_code, a.error_detail From [QC].[dbo].[Classification] a left join [QC].[dbo].[Pallet] b on a.pallet_num = b.Pallet_Name where total_code = '"+dmc+"' order by id desc")
        classification_data = cursor.fetchall()

        # Lấy số lượng record
        num_records = len(classification_data)

        # Nếu lấy dữ liệu ra trống
        if classification_data == None:
            ret = {
                'status':False,
                'message':'Not Exist Data'
            }
            return jsonify(ret),400

        # Nếu tồn tại dữ liệu
        ret = {
                'status':True,
                'message':'Success',
                'data':{}
            }
        
        # Nếu số lượng dòng = 0
        if num_records == 0:
            ret['data'] = None
            return jsonify(ret)

        # Lấy dữ liệu Classification
        ret['data']['classification'] = None
        for item in classification_data:
            splr_lot_no, id, lazer_machine, time_check, pallet_num, num, name, total_code, dmc_was_replace,  total_quality, dataman_total_quality, camera_product_shape, error_code, error_detail = item
            ret['data']['classification'] = {
                'splrLotNo': splr_lot_no,
                'id': id,
                'lazerMachine': lazer_machine,
                'timeCheck': time_check.strftime('%Y-%m-%d %H:%M:%S') if time_check is not None else time_check,
                'palletNum': pallet_num,
                'num': num,
                'name': name,
                'totalCode': total_code,
                'dmcWasReplace': dmc_was_replace,
                'totalQuality': total_quality,
                'datamanTotalQuality': dataman_total_quality,
                'cameraProductShape': camera_product_shape,
                'errorCode': error_code,
                'errorDetail': error_detail
            }

        return jsonify(ret)
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }   
        Systemp_log1(traceback.format_exc(), "search_data_6").append_new_line()
        return jsonify(ret),500
    
# Air Tight
@products.post('/air_tight')
@swag_from('./docs/products/air_tight/air_tight_data.yaml')
@token_required_and_permissions
def get_air_tight_data(role, permissions):
    try:
        # Tạo cusor để kết nối với database
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234;Database=QC; Trusted_Connection=No;',timeout=1)
        cursor = conn.cursor()

        # Check xem có phải Manager không?
        if role < 100:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 33
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

        datetime_start = day_start + " " + time_start
        datetime_end = day_end + " " + time_end

        cursor.execute("SELECT TOP(15000) * FROM [QC].[dbo].[air_tight] WHERE Time_Start >'"+datetime_start+"' and Time_Start <'"+datetime_end+"'")
        all_records = cursor.fetchall()

        # Lấy số dượng lượng record
        num_records = len(all_records)

        # Nếu lấy dữ liệu ra trống
        if all_records == None:
            ret = {
                'status':False,
                'message':'Not Exist Data'
            }
            return jsonify(ret),400

        # Nếu có máy
        ret = {
                'status':True,
                'message':'Success',
                'data':{}
            }
        
        if num_records == 0:
            ret['data'] = None
            return jsonify(ret)
        
        # Khởi tạo để lấy dữ liệu cho chart và table 
        ret['data']['chart'] = {}
        ret['data']['table'] = []

        # Lấy dữ liệu cho bảng
        for item in all_records:
            id, machine, prodcut_type, barcode, position, air_value, time_start_air_tight, time_finish_air_tight, quality, note = item
            ret['data']['table'].append({
                'id': id,
                'machine': machine,
                'productType': prodcut_type,
                'barcode': barcode,
                'position': position,
                'airValue': air_value,
                'timeStart': time_start_air_tight,
                'timeFinish': time_finish_air_tight,
                'quality': quality,
                'note': note
            })

        # Lấy dữ liệu để vẽ chart
        air_tight_df = pd.read_sql("SELECT left(Time_Start, 11) as 'Time', Quality, COUNT(Quality) AS 'Count' FROM  [QC].[dbo].[air_tight] WHERE Time_Start >'"+datetime_start+"' and Time_Start <'"+datetime_end+"' GROUP BY left(Time_Start, 11), Quality order by left(Time_Start, 11) desc", conn)
        
        air_tight_df = air_tight_df.pivot_table(index='Time', columns='Quality')

        # Khảo sát dữ liệu trong df
        print(air_tight_df.head(10))
        print(air_tight_df.columns.to_list())
        print(air_tight_df.values)
        print(air_tight_df.index.to_list())

        # Khởi tạo các list dữ liệu để vẽ chart
        ret['data']['chart']['timeIndex'] = []
        ret['data']['chart']['okNgData'] = []

        # Lấy dữ liệu timeIndex
        ret['data']['chart']['timeIndex'] = air_tight_df.index.to_list()  

        # Lấy dữ liệu count
        # for item in air_tight_df.values:
        #     ret['data']['chart']['countList'].append(item[0])

        for idx, item in enumerate(air_tight_df.values):
            ret['data']['chart']['okNgData'].append({'NG': 0 if isNaN(air_tight_df.values.tolist()[idx][0]) else air_tight_df.values.tolist()[idx][0], 'OK': 0 if isNaN(air_tight_df.values.tolist()[idx][1]) else air_tight_df.values.tolist()[idx][1]})

        return jsonify(ret)
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        Systemp_log1(traceback.format_exc(), "air_tight_data").append_new_line()
        return jsonify(ret),500
    
@products.post('/air_tight/download')
@swag_from('./docs/products/air_tight/air_tight_download.yaml')
@token_required_and_permissions
def download_air_tight_data(role, permissions):
    try:
        # Tạo cusor để kết nối với database
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234;Database=QC; Trusted_Connection=No;',timeout=1)

        # Check xem có phải Manager không?
        if role < 100:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 33
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

        datetime_start = day_start + " " + time_start
        datetime_end = day_end + " " + time_end

        print("SELECT * FROM [QC].[dbo].[air_tight] WHERE Time_Start >'"+datetime_start+"' and Time_Start <'"+datetime_end+"'")
        air_tight_df = pd.read_sql("SELECT * FROM [QC].[dbo].[air_tight] WHERE Time_Start >'"+datetime_start+"' and Time_Start <'"+datetime_end+"'", conn)

        # Nếu lấy dữ liệu ra trống
        if len(air_tight_df) == 0:
            ret = {
                'status':False,
                'message':'Not Exist Data'
            }
            return jsonify(ret),400

        output = io.BytesIO()
        writer = pd.ExcelWriter(
            output,
            engine='xlsxwriter')    # add a sheet
        
        air_tight_df.to_excel(writer, sheet_name='layer1', index=False)

        # add headers
        writer.close()
        output.seek(0)
        
        return Response(output, mimetype="application/ms-excel",
                        headers={"Content-Disposition": "attachment;filename=Airtight_Data.xls"})
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        Systemp_log1(traceback.format_exc(), "air_tight_download").append_new_line()
        return jsonify(ret),500
    
# Air Tight Chamfer
@products.post('/air_tight_chamfer')
@swag_from('./docs/products/air_tight/air_tight_chamfer_data.yaml')
@token_required_and_permissions
def get_air_tight_chamfer_data(role, permissions):
    try:
        # Tạo cusor để kết nối với database
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234;Database=QC; Trusted_Connection=No;',timeout=1)
        cursor = conn.cursor()

        # Check xem có phải Manager không?
        if role < 100:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 35
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

        datetime_start = day_start + " " + time_start
        datetime_end = day_end + " " + time_end

        cursor.execute("SELECT TOP(15000) * FROM [QC].[dbo].[air_tight_chamfer] WHERE Time_Start >='"+datetime_start+"' and Time_Start <='"+datetime_end+"'")
        all_records = cursor.fetchall()

        # Lấy số dượng lượng record
        num_records = len(all_records)

        # Nếu lấy dữ liệu ra trống
        if all_records == None:
            ret = {
                'status':False,
                'message':'Not Exist Data'
            }
            return jsonify(ret),400

        # Nếu có máy
        ret = {
                'status':True,
                'message':'Success',
                'data':{}
            }
        
        if num_records == 0:
            ret['data'] = None
            return jsonify(ret)
        
        # Khởi tạo để lấy dữ liệu cho chart và table 
        ret['data']['chart'] = {}
        ret['data']['table'] = []

        # Lấy dữ liệu cho bảng
        for item in all_records:
            id, machine, prodcut_type, barcode, position, air_value, time_start_air_tight_chamfer, time_finish_air_tight_chamfer, quality, note = item
            ret['data']['table'].append({
                'id': id,
                'machine': machine,
                'productType': prodcut_type,
                'barcode': barcode,
                'position': position,
                'airValue': air_value,
                'timeStart': time_start_air_tight_chamfer,
                'timeFinish': time_finish_air_tight_chamfer,
                'quality': quality,
                'note': note
            })

        # Lấy dữ liệu để vẽ chart
        air_tight_chamfer_df = pd.read_sql("SELECT left(Time_Start, 11) as 'Time', Quality, COUNT(Quality) AS 'Count' FROM [QC].[dbo].[air_tight_chamfer] WHERE Time_Start >='"+datetime_start+"' and Time_Start <='"+datetime_end+"' GROUP BY left(Time_Start, 11), Quality order by left(Time_Start, 11) desc", conn)
        
        air_tight_chamfer_df = air_tight_chamfer_df.pivot_table(index='Time', columns='Quality')

        # Khảo sát dữ liệu trong df
        print(air_tight_chamfer_df.head(10))
        print(air_tight_chamfer_df.columns.to_list())
        print(air_tight_chamfer_df.values)
        print(air_tight_chamfer_df.index.to_list())

        # Khởi tạo các list dữ liệu để vẽ chart
        ret['data']['chart']['timeIndex'] = []
        ret['data']['chart']['okNgData'] = []

        # Lấy dữ liệu timeIndex
        ret['data']['chart']['timeIndex'] = air_tight_chamfer_df.index.to_list()  

        # Lấy dữ liệu count
        for idx, item in enumerate(air_tight_chamfer_df.values):
            ret['data']['chart']['okNgData'].append({'NG': 0 if isNaN(air_tight_chamfer_df.values.tolist()[idx][0]) else air_tight_chamfer_df.values.tolist()[idx][0], 'OK': 0 if isNaN(air_tight_chamfer_df.values.tolist()[idx][1]) else air_tight_chamfer_df.values.tolist()[idx][1]})

        return jsonify(ret)
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        Systemp_log1(traceback.format_exc(), "air_tight_chamfer_data").append_new_line()
        return jsonify(ret),500
    
@products.post('/air_tight_chamfer/download')
@swag_from('./docs/products/air_tight/air_tight_chamfer_download.yaml')
@token_required_and_permissions
def download_air_tight_chamfer_data(role, permissions):
    try:
        # Tạo cusor để kết nối với database
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234;Database=QC; Trusted_Connection=No;',timeout=1)

        # Check xem có phải Manager không?
        if role < 100:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 35
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

        datetime_start = day_start + " " + time_start
        datetime_end = day_end + " " + time_end

        print("SELECT * FROM [QC].[dbo].[air_tight_chamfer] WHERE Time_Start >'"+datetime_start+"' and Time_Start <'"+datetime_end+"'")
        air_tight_chamfer_df = pd.read_sql("SELECT * FROM [QC].[dbo].[air_tight_chamfer] WHERE Time_Start >'"+datetime_start+"' and Time_Start <'"+datetime_end+"'", conn)
        
        # Nếu lấy dữ liệu ra trống
        if len(air_tight_chamfer_df) == 0:
            ret = {
                'status':False,
                'message':'Not Exist Data'
            }
            return jsonify(ret),400

        output = io.BytesIO()
        writer = pd.ExcelWriter(
            output,
            engine='xlsxwriter')    # add a sheet
        
        air_tight_chamfer_df.to_excel(writer, sheet_name='layer1', index=False)

        # add headers
        writer.close()
        output.seek(0)
        
        return Response(output, mimetype="application/ms-excel",
                        headers={"Content-Disposition": "attachment;filename=Airtight_Chamfer_Data.xls"})
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        Systemp_log1(traceback.format_exc(), "air_tight_chamfer_download").append_new_line()
        return jsonify(ret),500
    
# Air Tight Window
@products.post('/air_tight_window')
@swag_from('./docs/products/air_tight/air_tight_window_data.yaml')
@token_required_and_permissions
def get_air_tight_window_data(role, permissions):
    try:
        # Tạo cusor để kết nối với database
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234;Database=QC; Trusted_Connection=No;',timeout=1)
        cursor = conn.cursor()

        # Check xem có phải Manager không?
        if role < 100:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 37
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

        datetime_start = day_start + " " + time_start
        datetime_end = day_end + " " + time_end

        cursor.execute("SELECT TOP(15000) * FROM [QC].[dbo].[air_tight_window] WHERE Time_Finish_2 >='"+datetime_start+"' and Time_Finish_2 <='"+datetime_end+"'")
        all_records = cursor.fetchall()

        # Lấy số dượng lượng record
        num_records = len(all_records)

        # Nếu lấy dữ liệu ra trống
        if all_records == None:
            ret = {
                'status':False,
                'message':'Not Exist Data'
            }
            return jsonify(ret),400

        # Nếu có máy
        ret = {
                'status':True,
                'message':'Success',
                'data':{}
            }
        
        if num_records == 0:
            ret['data'] = None
            return jsonify(ret)
        
        # Khởi tạo để lấy dữ liệu cho chart và table 
        ret['data']['chart'] = {}
        ret['data']['table'] = []

        # Lấy dữ liệu cho bảng
        for item in all_records:
            id, product_name, barcode, air_value1, status_position1, time_start_1, time_finish_1, air_value2, status_position2, time_start2, time_finish2, note = item
            ret['data']['table'].append({
                'id': id,
                'productName': product_name,
                'barcode': barcode.strip(),
                'airValue1': air_value1,
                'statusPosition1': status_position1,
                'timeStart1': time_start_1,
                'timeFinish1': time_finish_1,
                'airValue2': air_value2,
                'statusPosition2': status_position2,
                'timeStart2': time_start2,
                'timeFinish2': time_finish2,
                'note': note
            })

        # Lấy dữ liệu để vẽ chart
        air_tight_window_df = pd.read_sql("SELECT left(Time_Finish_2, 11) as 'Time', Status_Position_2 as Quality, COUNT(Status_Position_2) AS 'Count' FROM [QC].[dbo].[air_tight_window] WHERE Time_Finish_2 >='"+datetime_start+"' and Time_Finish_2 <='"+datetime_end+"' GROUP BY left(Time_Finish_2, 11), Status_Position_2 order by left(Time_Finish_2, 11) desc", conn)

        air_tight_window_df = air_tight_window_df.pivot_table(index='Time', columns='Quality')
        
        # Khảo sát dữ liệu trong df
        print(air_tight_window_df.head(10))
        print(air_tight_window_df.columns.to_list())
        print(air_tight_window_df.values)
        print(air_tight_window_df.index.to_list())

        # Khởi tạo các list dữ liệu để vẽ chart
        ret['data']['chart']['timeIndex'] = []
        ret['data']['chart']['okNgData'] = []

        # Lấy dữ liệu timeIndex
        ret['data']['chart']['timeIndex'] = air_tight_window_df.index.to_list()  

        # Lấy dữ liệu count
        for idx, item in enumerate(air_tight_window_df.values):
            ret['data']['chart']['okNgData'].append({'NG': 0 if isNaN(air_tight_window_df.values.tolist()[idx][0]) else air_tight_window_df.values.tolist()[idx][0], 'OK': 0 if isNaN(air_tight_window_df.values.tolist()[idx][1]) else air_tight_window_df.values.tolist()[idx][1]})

        return jsonify(ret)
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        Systemp_log1(traceback.format_exc(), "air_tight_window_data").append_new_line()
        return jsonify(ret),500
    
@products.post('/air_tight_window/download')
@swag_from('./docs/products/air_tight/air_tight_window_download.yaml')
@token_required_and_permissions
def download_air_tight_window_data(role, permissions):
    try:
        # Tạo cusor để kết nối với database
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234;Database=QC; Trusted_Connection=No;',timeout=1)

        # Check xem có phải Manager không?
        if role < 100:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 37
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

        datetime_start = day_start + " " + time_start
        datetime_end = day_end + " " + time_end

        print("SELECT * FROM [QC].[dbo].[air_tight_window] WHERE Time_Finish_2 >='"+datetime_start+"' and Time_Finish_2 <='"+datetime_end+"'")
        air_tight_window_df = pd.read_sql("SELECT * FROM [QC].[dbo].[air_tight_window] WHERE Time_Finish_2 >='"+datetime_start+"' and Time_Finish_2 <='"+datetime_end+"'", conn)
        
        # Nếu lấy dữ liệu ra trống
        if len(air_tight_window_df) == 0:
            ret = {
                'status':False,
                'message':'Not Exist Data'
            }
            return jsonify(ret),400

        output = io.BytesIO()
        writer = pd.ExcelWriter(
            output,
            engine='xlsxwriter')    # add a sheet
        
        air_tight_window_df.to_excel(writer, sheet_name='layer1', index=False)

        # add headers
        writer.close()
        output.seek(0)
        
        return Response(output, mimetype="application/ms-excel",
                        headers={"Content-Disposition": "attachment;filename=Airtight_Window_Data.xls"})
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        Systemp_log1(traceback.format_exc(), "air_tight_window_download").append_new_line()
        return jsonify(ret),500
    
# CLASSIFICATION
@products.post('/classification')
@swag_from('./docs/products/classification/classification_data.yaml')
@token_required_and_permissions
def get_classification_data(role, permissions):
    try:
        # Tạo cusor để kết nối với database
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234;Database=QC; Trusted_Connection=No;',timeout=1)
        cursor = conn.cursor()

        # Check xem có phải Manager không?
        if role < 100:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 39
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

        datetime_start = day_start + " " + time_start
        datetime_end = day_end + " " + time_end

        print("SELECT top (15000) b.SPLR_LOT_NO, a.id, a.lazer_machine, a.Time_check, a.pallet_num, a.Num, a.name, a.total_code, a.dmc_was_replace, a.total_quality, a.dataman_total_quality, a.camera_product_shape, a.error_code, a.error_detail From [QC].[dbo].[Classification] a left join [QC].[dbo].[Pallet] b on a.pallet_num = b.Pallet_Name where a.Time_check >'"+datetime_start+"' and a.Time_check <'"+datetime_end+"'")
        cursor.execute("SELECT top (15000) b.SPLR_LOT_NO, a.id, a.lazer_machine, a.Time_check, a.pallet_num, a.Num, a.name, a.total_code, a.dmc_was_replace, a.total_quality, a.dataman_total_quality, a.camera_product_shape, a.error_code, a.error_detail From [QC].[dbo].[Classification] a left join [QC].[dbo].[Pallet] b on a.pallet_num = b.Pallet_Name where a.Time_check >'"+datetime_start+"' and a.Time_check <'"+datetime_end+"'")
        all_records = cursor.fetchall()

        # Lấy số dượng lượng record
        num_records = len(all_records)

        # Nếu lấy dữ liệu ra trống
        if all_records == None:
            ret = {
                'status':False,
                'message':'Not Exist Data'
            }
            return jsonify(ret),400

        # Nếu có máy
        ret = {
                'status':True,
                'message':'Success',
                'data':{}
            }
        
        if num_records == 0:
            ret['data'] = None
            return jsonify(ret)
        
        # Khởi tạo để lấy dữ liệu cho chart và table 
        ret['data']['chart'] = {}
        ret['data']['table'] = []

        # Lấy dữ liệu cho bảng
        for item in all_records:
            splr_lot_no, id, lazer_machine, time_check, pallet_num, num, name, total_code, dmc_was_replace,  total_quality, dataman_total_quality, camera_product_shape, error_code, error_detail = item
            ret['data']['table'].append({
                'splrLotNo': splr_lot_no,
                'id': id,
                'lazerMachine': lazer_machine,
                'timeCheck': time_check,
                'palletNum': pallet_num,
                'num': num,
                'name': name,
                'totalCode': total_code,
                'dmcWasReplace': dmc_was_replace,
                'totalQuality': total_quality,
                'datamanTotalQuality': dataman_total_quality,
                'cameraProductShape': camera_product_shape,
                'errorCode': error_code,
                'errorDetail': error_detail
            })

        # Lấy dữ liệu để vẽ chart
        print("SELECT left(Time_check,11) as 'Time', dataman_total_quality, COUNT(dataman_total_quality) AS 'Count' FROM [QC].[dbo].[Classification] where Time_check >'"+datetime_start+"' and Time_check <'"+datetime_end+"' GROUP BY left(Time_check, 11), dataman_total_quality order by left(Time_check, 11) desc")
        classification_df = pd.read_sql("SELECT left(Time_check,11) as 'Time', dataman_total_quality, COUNT(dataman_total_quality) AS 'Count' FROM [QC].[dbo].[Classification] where Time_check >'"+datetime_start+"' and Time_check <'"+datetime_end+"' GROUP BY left(Time_check, 11), dataman_total_quality order by left(Time_check, 11) desc", conn)
        
        classification_df = classification_df.pivot_table(index='Time', columns='dataman_total_quality')
        
        # Khảo sát dữ liệu trong df
        print(classification_df.head(10))
        print(classification_df.columns.to_list())
        print(classification_df.values)
        print(classification_df.index.to_list())

        # Khởi tạo các list dữ liệu để vẽ chart
        ret['data']['chart']['timeIndex'] = []
        ret['data']['chart']['countData'] = []

        # Lấy dữ liệu timeIndex
        ret['data']['chart']['timeIndex'] = classification_df.index.to_list()  

        # Lấy dữ liệu count
        for count_list in classification_df.values:
            count_data_list = []
            for count_idx, count_name in enumerate(classification_df.columns.to_list()):
                count_data_dict = {}

                count_data_dict['countName'] = list(count_name)[0] + ", " + list(count_name)[1]
                count_data_dict['countValue'] = 0 if isNaN(count_list[count_idx]) else count_list[count_idx]

                count_data_list.append(count_data_dict)
            
            ret['data']['chart']['countData'].append(count_data_list)
            
        return jsonify(ret)
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        Systemp_log1(traceback.format_exc(), "classification_data").append_new_line()
        return jsonify(ret),500
    
@products.post('/classification/download')
@swag_from('./docs/products/classification/classification_download.yaml')
@token_required_and_permissions
def download_classification_data(role, permissions):
    try:
        # Tạo cusor để kết nối với database
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234;Database=QC; Trusted_Connection=No;',timeout=1)

        # Check xem có phải Manager không?
        if role < 100:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 39
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

        datetime_start = day_start + " " + time_start
        datetime_end = day_end + " " + time_end

        print("SELECT [Pallet].[SPLR_LOT_NO], [Classification].* From [Classification] left join [Pallet] on [Classification].pallet_num= [Pallet].Pallet_Name where [Classification].Time_check >='"+datetime_start+"' and [Classification].Time_check <='"+datetime_end+"'")
        classification_df = pd.read_sql("SELECT [Pallet].[SPLR_LOT_NO], [Classification].* From [Classification] left join [Pallet] on [Classification].pallet_num= [Pallet].Pallet_Name where [Classification].Time_check >='"+datetime_start+"' and [Classification].Time_check <='"+datetime_end+"'", conn)
        
        # Nếu lấy dữ liệu ra trống
        if len(classification_df) == 0:
            ret = {
                'status':False,
                'message':'Not Exist Data'
            }
            return jsonify(ret),400

        output = io.BytesIO()
        writer = pd.ExcelWriter(
            output,
            engine='xlsxwriter')    # add a sheet
        
        classification_df.to_excel(writer, sheet_name='layer1', index=False)

        # add headers
        writer.close()
        output.seek(0)
        
        return Response(output, mimetype="application/ms-excel",
                        headers={"Content-Disposition": "attachment;filename=Classification_Data.xls"})
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        Systemp_log1(traceback.format_exc(), "classification_download").append_new_line()
        return jsonify(ret),500
    
# CUTTING MACHINE
@products.post('/cutting')
@swag_from('./docs/products/cutting/cutting_data.yaml')
@token_required_and_permissions
def get_cutting_data(role, permissions):
    try:
        # Tạo cusor để kết nối với database
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234;Database=QC; Trusted_Connection=No;',timeout=1)
        cursor = conn.cursor()

        # Check xem có phải Manager không?
        if role < 100:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 42
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

        datetime_start = day_start + " " + time_start
        datetime_end = day_end + " " + time_end
    
        cursor.execute("SELECT Top(15000)* FROM [HXL].[dbo].[DSA_cutting] where [Time] >'"+datetime_start+"' and [Time] <'"+datetime_end+"'")
        all_records = cursor.fetchall()

        # Lấy số dượng lượng record
        num_records = len(all_records)

        # Nếu lấy dữ liệu ra trống
        if all_records == None:
            ret = {
                'status':False,
                'message':'Not Exist Data'
            }
            return jsonify(ret),400

        # Nếu có máy
        ret = {
                'status':True,
                'message':'Success',
                'data':{}
            }
        
        if num_records == 0:
            ret['data'] = None
            return jsonify(ret)
        
        # Khởi tạo để lấy dữ liệu cho chart và table 
        ret['data']['chart'] = {}
        ret['data']['table'] = []

        # Lấy dữ liệu cho bảng
        for item in all_records:
            id, time, cutting_name, product_id, product_name, hmi_count, cutting_time, vfd_speed, robot_speed = item
            ret['data']['table'].append({
                'id': id,
                'time': time,
                'cuttingName': cutting_name,
                'productId': product_id,
                'productName': product_name,
                'productName': product_name,
                'hmiCount': hmi_count,
                'cuttingTime': cutting_time,
                'vfdSpeed': vfd_speed,
                'robotSpeed': robot_speed
            })

        # Lấy dữ liệu để vẽ chart
        cutting_df = pd.read_sql("SELECT left(Time, 11) as 'Time', cutting_name, COUNT(cutting_name) AS 'Count' FROM [HXL].[dbo].[DSA_cutting] where Time >'"+datetime_start+"' and Time <'"+datetime_end+"' GROUP BY left(Time, 11), cutting_name order by left(Time, 11) desc", conn)
        
        cutting_df = cutting_df.pivot_table(index='Time', columns='cutting_name')
        
        # Khảo sát dữ liệu trong df
        print(cutting_df.head(10))
        print(cutting_df.columns.to_list())
        print(cutting_df.values)
        print(cutting_df.index.to_list())

        # Khởi tạo các list dữ liệu để vẽ chart
        ret['data']['chart']['timeIndex'] = []
        ret['data']['chart']['dsaData'] = []

        # Lấy dữ liệu timeIndex
        ret['data']['chart']['timeIndex'] = cutting_df.index.to_list()  

        # Lấy dữ liệu count
        list_dsa_values = [list(item)[1] for item in cutting_df.columns.to_list()]
        for item in cutting_df.values:
            dsa_dict = {}
            for idx, dsa in enumerate(list_dsa_values):
                if isNaN(item[idx]):
                    dsa_dict[dsa] = 0
                else:
                    dsa_dict[dsa] = item[idx]
            ret['data']['chart']['dsaData'].append(dsa_dict)

        return jsonify(ret)
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        Systemp_log1(traceback.format_exc(), "cutting_data").append_new_line()
        return jsonify(ret),500
    
@products.post('/cutting/download')
@swag_from('./docs/products/cutting/cutting_download.yaml')
@token_required_and_permissions
def download_cutting_data(role, permissions):
    try:
        # Tạo cusor để kết nối với database
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234;Database=QC; Trusted_Connection=No;',timeout=1)

        # Check xem có phải Manager không?
        if role < 100:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 42
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

        datetime_start = day_start + " " + time_start
        datetime_end = day_end + " " + time_end

        print("SELECT * FROM [HXL].[dbo].[DSA_cutting] where Time >'"+datetime_start+"' and Time <'"+datetime_end+"'")
        cutting_df = pd.read_sql("SELECT * FROM [HXL].[dbo].[DSA_cutting] where Time >'"+datetime_start+"' and Time <'"+datetime_end+"'", conn)

        # Nếu lấy dữ liệu ra trống
        if len(cutting_df) == 0:
            ret = {
                'status':False,
                'message':'Not Exist Data'
            }
            return jsonify(ret),400

        output = io.BytesIO()
        writer = pd.ExcelWriter(
            output,
            engine='xlsxwriter')    # add a sheet
        
        cutting_df.to_excel(writer, sheet_name='layer1', index=False)

        # add headers
        writer.close()
        output.seek(0)
        
        return Response(output, mimetype="application/ms-excel",
                        headers={"Content-Disposition": "attachment;filename=Cutting_Data.xls"})
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        Systemp_log1(traceback.format_exc(), "cutting_download").append_new_line()
        return jsonify(ret),500
    
# Làm thêm cho mã hàng 004
# Air Tight Spain
@products.post('/air_tight_spain')
@swag_from('./docs/products/air_tight/air_tight_spain_data.yaml')
@token_required_and_permissions
def get_air_tight_spain_data(role, permissions):
    try:
        # Tạo cusor để kết nối với database
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234;Database=QC; Trusted_Connection=No;',timeout=1)
        cursor = conn.cursor()

        # Check xem có phải Manager không?
        if role < 100:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 36
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

        datetime_start = day_start + " " + time_start
        datetime_end = day_end + " " + time_end
    
        cursor.execute("SELECT TOP(15000) * FROM [QC].[dbo].[air_tight_spain] WHERE Time_Start >='"+datetime_start+"' and Time_Start <='"+datetime_end+"'")
        all_records = cursor.fetchall()

        # Lấy số dượng lượng record
        num_records = len(all_records)

        # Nếu lấy dữ liệu ra trống
        if all_records == None:
            ret = {
                'status':False,
                'message':'Not Exist Data'
            }
            return jsonify(ret),400

        # Nếu có máy
        ret = {
                'status':True,
                'message':'Success',
                'data':{}
            }
        
        if num_records == 0:
            ret['data'] = None
            return jsonify(ret)
        
        # Khởi tạo để lấy dữ liệu cho chart và table 
        ret['data']['chart'] = {}
        ret['data']['table'] = []

        # Lấy dữ liệu cho bảng
        for item in all_records:
            id, machine, product_type, barcode, position, air_value, time_start, time_finish, quality, note = item
            ret['data']['table'].append({
                'id': id,
                'machine': machine,
                'productType': product_type,
                'barcode': barcode,
                'position': position,
                'airValue': air_value,
                'timeStart': time_start,
                'timeFinish': time_finish,
                'quality': quality,
                'note': note
            })

        # Lấy dữ liệu để vẽ chart
        air_tight_spain_df = pd.read_sql("SELECT left(Time_Start, 11) as 'Time', Quality, COUNT(Quality) AS 'Count' FROM [QC].[dbo].[air_tight_spain] WHERE Time_Start >='"+datetime_start+"' and Time_Start <='"+datetime_end+"' GROUP BY left(Time_Start, 11), Quality order by left(Time_Start, 11) desc", conn)
        
        air_tight_spain_df = air_tight_spain_df.pivot_table(index='Time', columns='Quality')
        
        # Khảo sát dữ liệu trong df
        print(air_tight_spain_df.head(10))
        print(air_tight_spain_df.columns.to_list())
        print(air_tight_spain_df.values)
        print(air_tight_spain_df.index.to_list())

        # Khởi tạo các list dữ liệu để vẽ chart
        ret['data']['chart']['timeIndex'] = []
        ret['data']['chart']['okNgData'] = []

        # Lấy dữ liệu timeIndex
        ret['data']['chart']['timeIndex'] = air_tight_spain_df.index.to_list()  

        # Lấy dữ liệu count
        for idx, item in enumerate(air_tight_spain_df.values):
            ret['data']['chart']['okNgData'].append({'NG': 0 if isNaN(air_tight_spain_df.values.tolist()[idx][0]) else air_tight_spain_df.values.tolist()[idx][0], 'OK': 0 if isNaN(air_tight_spain_df.values.tolist()[idx][1]) else air_tight_spain_df.values.tolist()[idx][1]})

        return jsonify(ret)
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        Systemp_log1(traceback.format_exc(), "air_tight_spain_data").append_new_line()
        return jsonify(ret),500
    
@products.post('/air_tight_spain/download')
@swag_from('./docs/products/air_tight/air_tight_spain_download.yaml')
@token_required_and_permissions
def download_air_tight_spain_data(role, permissions):
    try:
        # Tạo cusor để kết nối với database
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234;Database=QC; Trusted_Connection=No;',timeout=1)

        # Check xem có phải Manager không?
        if role < 100:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 36
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

        datetime_start = day_start + " " + time_start
        datetime_end = day_end + " " + time_end

        print("SELECT * FROM [QC].[dbo].[air_tight_spain] WHERE Time_Start >='"+datetime_start+"' and Time_Start <='"+datetime_end+"'")
        air_tight_spain_df = pd.read_sql("SELECT * FROM [QC].[dbo].[air_tight_spain] WHERE Time_Start >='"+datetime_start+"' and Time_Start <='"+datetime_end+"'", conn)

        # Nếu lấy dữ liệu ra trống
        if len(air_tight_spain_df) == 0:
            ret = {
                'status':False,
                'message':'Not Exist Data'
            }
            return jsonify(ret),400

        output = io.BytesIO()
        writer = pd.ExcelWriter(
            output,
            engine='xlsxwriter')    # add a sheet
        
        air_tight_spain_df.to_excel(writer, sheet_name='layer1', index=False)

        # add headers
        writer.close()
        output.seek(0)
        
        return Response(output, mimetype="application/ms-excel",
                        headers={"Content-Disposition": "attachment;filename=Airtight_Spain_Data.xls"})
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        Systemp_log1(traceback.format_exc(), "air_tight_spain_download").append_new_line()
        return jsonify(ret),500
    
# 036
# Classification036
@products.post('/classification_036')
@swag_from('./docs/products/classification/classification036_data.yaml')
@token_required_and_permissions
def get_classification036_data(role, permissions):
    try:
        # Tạo cusor để kết nối với database
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234;Database=QC; Trusted_Connection=No;',timeout=1)
        cursor = conn.cursor()

        # Check xem có phải Manager không?
        if role < 100:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 40
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

        datetime_start = day_start + " " + time_start
        datetime_end = day_end + " " + time_end
    
        cursor.execute("SELECT Top(15000) * FROM [QC].[dbo].[AirGauge036_Classification] where TimeDMC >'"+datetime_start+"' and TimeDMC <'"+datetime_end+"'")
        all_records = cursor.fetchall()

        # Lấy số dượng lượng record
        num_records = len(all_records)

        # Nếu lấy dữ liệu ra trống
        if all_records == None:
            ret = {
                'status':False,
                'message':'Not Exist Data'
            }
            return jsonify(ret),400

        # Nếu có máy
        ret = {
                'status':True,
                'message':'Success',
                'data':{}
            }
        
        if num_records == 0:
            ret['data'] = None
            return jsonify(ret)
        
        # Khởi tạo để lấy dữ liệu cho chart và table 
        ret['data']['chart'] = {}
        ret['data']['table'] = []

        # Lấy dữ liệu cho bảng
        for item in all_records:
            id, time_dmc, code_furnace, dmc, replace_dmc, pallet_code, draw_id, draw_version, num, note = item
            ret['data']['table'].append({
                'id': id,
                'time_dmc': time_dmc.strftime('%Y-%m-%d %H:%M:%S') if time_dmc is not None else time_dmc,
                'code_furnace': code_furnace,
                'dmc': dmc,
                'replace_dmc': replace_dmc,
                'pallet_code': pallet_code,
                'draw_id': draw_id,
                'draw_version': draw_version,
                'num': num,
                'note': note
            })

        # Lấy dữ liệu để vẽ chart
        classification036_df = pd.read_sql("SELECT CAST(TimeDMC AS DATE) as Time, COUNT(DMC) AS 'Quantity' FROM [QC].[dbo].[AirGauge036_Classification] where TimeDMC >'"+datetime_start+"' and TimeDMC <'"+datetime_end+"' GROUP BY CAST(TimeDMC AS DATE) order by CAST(TimeDMC AS DATE)", conn)
        
        classification036_df['Time'] = pd.to_datetime(classification036_df['Time'])
        
        # Khảo sát dữ liệu trong df
        print(classification036_df)
        print(classification036_df.head(10))
        print(classification036_df.columns.to_list())
        print(classification036_df.values)
        print(classification036_df.index.to_list())

        # Khởi tạo các list dữ liệu để vẽ chart
        ret['data']['chart']['timeIndex'] = []
        ret['data']['chart']['countList'] = []

        # Lấy dữ liệu timeIndex
        for idx, row_data in classification036_df.iterrows():
            ret['data']['chart']['timeIndex'].append(row_data['Time'].strftime('%Y-%m-%d'))
            ret['data']['chart']['countList'].append(row_data['Quantity'])

        return jsonify(ret)
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        Systemp_log1(traceback.format_exc(), "classification036_data").append_new_line()
        return jsonify(ret),500
    
@products.post('/classification_036/download')
@swag_from('./docs/products/classification/classification036_download.yaml')
@token_required_and_permissions
def download_classification036_data(role, permissions):
    try:
        # Tạo cusor để kết nối với database
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234;Database=QC; Trusted_Connection=No;',timeout=1)

        # Check xem có phải Manager không?
        if role < 100:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 40
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

        datetime_start = day_start + " " + time_start
        datetime_end = day_end + " " + time_end

        print("SELECT * FROM [QC].[dbo].[AirGauge036_Classification] where [TimeDMC] >'"+datetime_start+"' and [TimeDMC] <'"+datetime_end+"'")
        classification036 = pd.read_sql("SELECT * FROM [QC].[dbo].[AirGauge036_Classification] where [TimeDMC] >'"+datetime_start+"' and [TimeDMC] <'"+datetime_end+"'", conn)
        
        # Nếu lấy dữ liệu ra trống
        if len(classification036) == 0:
            ret = {
                'status':False,
                'message':'Not Exist Data'
            }
            return jsonify(ret),400

        output = io.BytesIO()
        writer = pd.ExcelWriter(
            output,
            engine='xlsxwriter')    # add a sheet
        
        classification036.to_excel(writer, sheet_name='layer1', index=False)

        # add headers
        writer.close()
        output.seek(0)
        
        return Response(output, mimetype="application/ms-excel",
                        headers={"Content-Disposition": "attachment;filename=Classification036_Data.xls"})
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        Systemp_log1(traceback.format_exc(), "classification036_download").append_new_line()
        return jsonify(ret),500
    
# Airgauge036
@products.post('/air_gauge_036')
@swag_from('./docs/products/air_guage/airgauge036_data.yaml')
@token_required_and_permissions
def get_airgauge036_data(role, permissions):
    try:
        # Tạo cusor để kết nối với database
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234;Database=QC; Trusted_Connection=No;',timeout=1)
        cursor = conn.cursor()

        # Check xem có phải Manager không?
        if role < 100:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 30
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

        datetime_start = day_start + " " + time_start
        datetime_end = day_end + " " + time_end
    
        cursor.execute("SELECT Top(15000) * FROM [QC].[dbo].[AirGauge036] where TimeFinish >'"+datetime_start+"' and TimeFinish <'"+datetime_end+"'")
        all_records = cursor.fetchall()

        # Lấy số dượng lượng record
        num_records = len(all_records)

        # Nếu lấy dữ liệu ra trống
        if all_records == None:
            ret = {
                'status':False,
                'message':'Not Exist Data'
            }
            return jsonify(ret),400

        # Nếu có máy
        ret = {
                'status':True,
                'message':'Success',
                'data':{}
            }
        
        if num_records == 0:
            ret['data'] = None
            return jsonify(ret)
        
        # Khởi tạo để lấy dữ liệu cho chart và table 
        ret['data']['chart'] = {}
        ret['data']['table'] = []

        # Lấy dữ liệu cho bảng
        for item in all_records:
            id, machine, product_name, time_scan_dmc, time_finish, furnace, dmc, machining_station, operator, p6_min, p6_max, p10_1_min, p10_1_max, p10_2_min, p10_2_max, p13_min, p13_max, p18_1_min, p18_1_max, p18_2_min, p18_2_max, p53_min, p53_max, result, pin_ring, note = item
            ret['data']['table'].append({
                'id': id,
                'machine': machine,
                'product_name': product_name,
                'time_scan_dmc': time_scan_dmc.strftime('%Y-%m-%d %H:%M:%S') if time_scan_dmc is not None else time_scan_dmc,
                'time_finish': time_finish.strftime('%Y-%m-%d %H:%M:%S') if time_finish is not None else time_finish,
                'furnace': furnace,
                'dmc': dmc,
                'machining_station': machining_station,
                'operator': operator,
                'p6_min': p6_min,
                'p6_max': p6_max,
                'p10_1_min': p10_1_min,
                'p10_1_max': p10_1_max,
                'p10_2_min': p10_2_min,
                'p10_2_max': p10_2_max,
                'p13_min': p13_min,
                'p13_max': p13_max,
                'p18_1_min': p18_1_min,
                'p18_1_max': p18_1_max,
                'p18_2_min': p18_2_min,
                'p18_2_max': p18_2_max,
                'p53_min': p53_min,
                'p53_max': p53_max,
                'result': result,
                'pin_ring': pin_ring,
                'note': note
            })

        # Lấy dữ liệu để vẽ chart
        airgauge036_df = pd.read_sql("SELECT left(TimeFinish, 11) as Time, Result, COUNT(Result) AS 'Count' FROM [QC].[dbo].[AirGauge036] where TimeFinish >'"+datetime_start+"' and TimeFinish <'"+datetime_end+"'GROUP BY left(TimeFinish, 11), Result order by left(TimeFinish, 11)", conn)
        
        airgauge036_df = airgauge036_df.pivot_table(index='Time', columns='Result')

        # Khảo sát dữ liệu trong df
        print(airgauge036_df.head(10))
        print(airgauge036_df.columns.to_list())
        print(airgauge036_df.values)
        print(airgauge036_df.index.to_list())

        # Khởi tạo các list dữ liệu để vẽ chart
        ret['data']['chart']['timeIndex'] = []
        ret['data']['chart']['okNgData'] = []

        # Lấy dữ liệu timeIndex
        ret['data']['chart']['timeIndex'] = airgauge036_df.index.to_list()  

        # Lấy dữ liệu count
        for idx in range(len(airgauge036_df.index.tolist())):
            ret['data']['chart']['okNgData'].append({'NG': 0 if isNaN(airgauge036_df.values.tolist()[idx][0]) else airgauge036_df.values.tolist()[idx][0], 'OK': 0 if isNaN(airgauge036_df.values.tolist()[idx][1]) else airgauge036_df.values.tolist()[idx][1], 'Return': 0 if isNaN(airgauge036_df.values.tolist()[idx][2]) else airgauge036_df.values.tolist()[idx][2], 'Special': 0 if isNaN(airgauge036_df.values.tolist()[idx][3]) else airgauge036_df.values.tolist()[idx][3]}) 

        return jsonify(ret)
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        Systemp_log1(traceback.format_exc(), "airgauge036_data").append_new_line()
        return jsonify(ret),500
    
@products.post('/air_gauge_036/download')
@swag_from('./docs/products/air_guage/airgauge036_download.yaml')
@token_required_and_permissions
def download_airgauge036_data(role, permissions):
    try:
        # Tạo cusor để kết nối với database
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234;Database=QC; Trusted_Connection=No;',timeout=1)

        # Check xem có phải Manager không?
        if role < 100:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 30
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

        datetime_start = day_start + " " + time_start
        datetime_end = day_end + " " + time_end

        print("SELECT * FROM [QC].[dbo].[AirGauge036] where TimeFinish >'"+datetime_start+"' and TimeFinish <'"+datetime_end+"'")
        airgauge036_df = pd.read_sql("SELECT * FROM [QC].[dbo].[AirGauge036] where TimeFinish >'"+datetime_start+"' and TimeFinish <'"+datetime_end+"'", conn)
        
        # Nếu lấy dữ liệu ra trống
        if len(airgauge036_df) == 0:
            ret = {
                'status':False,
                'message':'Not Exist Data'
            }
            return jsonify(ret),400

        output = io.BytesIO()
        writer = pd.ExcelWriter(
            output,
            engine='xlsxwriter')    # add a sheet
        
        airgauge036_df.to_excel(writer, sheet_name='layer1', index=False)

        # add headers
        writer.close()
        output.seek(0)
        
        return Response(output, mimetype="application/ms-excel",
                        headers={"Content-Disposition": "attachment;filename=Airgauge036_Data.xls"})
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        Systemp_log1(traceback.format_exc(), "airgauge036_download").append_new_line()
        return jsonify(ret),500
    
# Airtight036
@products.post('/air_tight_036')
@swag_from('./docs/products/air_tight/airtight036_data.yaml')
@token_required_and_permissions
def get_airtight036_data(role, permissions):
    try:
        # Tạo cusor để kết nối với database
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234;Database=QC; Trusted_Connection=No;',timeout=1)
        cursor = conn.cursor()

        # Check xem có phải Manager không?
        if role < 100:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 34
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

        datetime_start = day_start + " " + time_start
        datetime_end = day_end + " " + time_end
    
        cursor.execute("SELECT TOP(15000) * FROM [QC].[dbo].[AirTight036] WHERE TimeFinish >='"+datetime_start+"' and TimeFinish <='"+datetime_end+"'")
        all_records = cursor.fetchall()

        # Lấy số dượng lượng record
        num_records = len(all_records)

        # Nếu lấy dữ liệu ra trống
        if all_records == None:
            ret = {
                'status':False,
                'message':'Not Exist Data'
            }
            return jsonify(ret),400

        # Nếu có máy
        ret = {
                'status':True,
                'message':'Success',
                'data':{}
            }
        
        if num_records == 0:
            ret['data'] = None
            return jsonify(ret)
        
        # Khởi tạo để lấy dữ liệu cho chart và table 
        ret['data']['chart'] = {}
        ret['data']['table'] = []

        # Lấy dữ liệu cho bảng
        for item in all_records:
            id, time_start, time_finish, machine, dmc, airvalue_1, result_station_1, airvalue_2, result_station_2, total_quantity, note, note1, note2, note3, note4, note5 = item
            ret['data']['table'].append({
                'id': id,
                'machine': machine,
                'time_start': time_start.strftime('%Y-%m-%d %H:%M:%S') if time_start is not None else time_start,
                'time_finish': time_finish.strftime('%Y-%m-%d %H:%M:%S') if time_finish is not None else time_finish,
                'dmc': dmc,
                'airvalue_1': airvalue_1,
                'result_station_1': result_station_1,
                'airvalue_2': airvalue_2,
                'result_station_2': result_station_2,
                'total_quantity': total_quantity,
                'note': note
            })

        # Lấy dữ liệu để vẽ chart    
        airtight036_df = pd.read_sql("SELECT left(TimeFinish, 11) as 'Time', Total_Quality as Quality , COUNT(Total_Quality) AS 'Total' FROM [QC].[dbo].[AirTight036] WHERE TimeFinish >='"+datetime_start+"' and [TimeFinish] <='"+datetime_end+"' GROUP BY left(TimeFinish, 11), Total_Quality order by left(TimeFinish, 11) desc", conn)
        
        airtight036_df = airtight036_df.pivot_table(index='Time', columns='Quality')
        
        # Khảo sát dữ liệu trong df
        print(airtight036_df.head(10))
        print(airtight036_df.columns.to_list())
        print(airtight036_df.values)
        print(airtight036_df.index.to_list())

        # Khởi tạo các list dữ liệu để vẽ chart
        ret['data']['chart']['timeIndex'] = []
        ret['data']['chart']['okNgData'] = []

        # Lấy dữ liệu timeIndex
        ret['data']['chart']['timeIndex'] = airtight036_df.index.to_list()  

        # Lấy dữ liệu count
        for idx, item in enumerate(airtight036_df.values):
            ret['data']['chart']['okNgData'].append({'NG': 0 if isNaN(airtight036_df.values.tolist()[idx][0]) else airtight036_df.values.tolist()[idx][0], 'OK': 0 if isNaN(airtight036_df.values.tolist()[idx][1]) else airtight036_df.values.tolist()[idx][1]})

        return jsonify(ret)
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        Systemp_log1(traceback.format_exc(), "airtight036_data").append_new_line()
        return jsonify(ret),500
    
@products.post('/air_tight_036/download')
@swag_from('./docs/products/air_tight/airtight036_download.yaml')
@token_required_and_permissions
def download_airtight036_data(role, permissions):
    try:
        # Tạo cusor để kết nối với database
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234;Database=QC; Trusted_Connection=No;',timeout=1)

        # Check xem có phải Manager không?
        if role < 100:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 34
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

        datetime_start = day_start + " " + time_start
        datetime_end = day_end + " " + time_end

        print("SELECT * FROM [QC].[dbo].[AirTight036] WHERE TimeFinish >'"+datetime_start+"' and TimeFinish <'"+datetime_end+"'")
        airtight036_df = pd.read_sql("SELECT * FROM [QC].[dbo].[AirTight036] WHERE TimeFinish >'"+datetime_start+"' and TimeFinish <'"+datetime_end+"'", conn)
        
        # Nếu lấy dữ liệu ra trống
        if len(airtight036_df) == 0:
            ret = {
                'status':False,
                'message':'Not Exist Data'
            }
            return jsonify(ret),400

        output = io.BytesIO()
        writer = pd.ExcelWriter(
            output,
            engine='xlsxwriter')    # add a sheet
        
        airtight036_df.to_excel(writer, sheet_name='layer1', index=False)

        # add headers
        writer.close()
        output.seek(0)
        
        return Response(output, mimetype="application/ms-excel",
                        headers={"Content-Disposition": "attachment;filename=Airtight036_Data.xls"})
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        Systemp_log1(traceback.format_exc(), "airtight036_download").append_new_line()
        return jsonify(ret),500
    
# Classification3123
@products.post('/classification_3123')
@swag_from('./docs/products/classification/classification3123_data.yaml')
@token_required_and_permissions
def get_classification3123_data(role, permissions):
    try:
        # Tạo cusor để kết nối với database
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234;Database=QC; Trusted_Connection=No;',timeout=1)
        cursor = conn.cursor()

        # Check xem có phải Manager không?
        if role < 100:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 41
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

        datetime_start = day_start + " " + time_start
        datetime_end = day_end + " " + time_end
    
        cursor.execute("SELECT Top(15000) * FROM [QC].[dbo].[Classification_A2303123] where TimeSave >='"+datetime_start+"' and TimeSave <='"+datetime_end+"'")
        all_records = cursor.fetchall()

        # Lấy số dượng lượng record
        num_records = len(all_records)

        # Nếu lấy dữ liệu ra trống
        if all_records == None:
            ret = {
                'status':False,
                'message':'Not Exist Data'
            }
            return jsonify(ret),400

        # Nếu có máy
        ret = {
                'status':True,
                'message':'Success',
                'data':{}
            }
        
        if num_records == 0:
            ret['data'] = None
            return jsonify(ret)
        
        # Khởi tạo để lấy dữ liệu cho chart và table 
        ret['data']['chart'] = {}
        ret['data']['table'] = []

        # Lấy dữ liệu cho bảng
        for item in all_records:
            id, time_save, dmc_scan, dmc_internal, dmc_original, replace_dmc, pallet_code, draw_id, draw_version, num, result, status = item
            ret['data']['table'].append({
                'id': id,
                'time_save': time_save.strftime('%Y-%m-%d %H:%M:%S') if time_save is not None else time_save,
                'dmc_scan': dmc_scan,
                'dmc_internal': dmc_internal,
                'dmc_original': dmc_original,
                'replace_dmc': replace_dmc,
                'pallet_code': pallet_code,
                'draw_id': draw_id,
                'draw_version': draw_version,
                'num': num,
                'result': result,
                'status': status
            })

        # Lấy dữ liệu để vẽ chart    
        classification3123_df = pd.read_sql("SELECT CAST(TimeSave AS DATE) as Time, COUNT(DMC_Scan) AS 'Quantity' FROM [QC].[dbo].[Classification_A2303123] where TimeSave >='"+datetime_start+"' and TimeSave<='"+datetime_end+"' GROUP BY CAST(TimeSave AS DATE) order by CAST(TimeSave AS DATE)", conn)
        
        classification3123_df['Time'] = pd.to_datetime(classification3123_df['Time'])
        
        # Khảo sát dữ liệu trong df
        print(classification3123_df.head(10))
        print(classification3123_df.columns.to_list())
        print(classification3123_df.values)
        print(classification3123_df.index.to_list())

        # Khởi tạo các list dữ liệu để vẽ chart
        ret['data']['chart']['timeIndex'] = []
        ret['data']['chart']['countList'] = []

        # Lấy dữ liệu count
        for idx, row_data in classification3123_df.iterrows():
            ret['data']['chart']['timeIndex'].append(row_data['Time'].strftime('%Y-%m-%d'))
            ret['data']['chart']['countList'].append(row_data['Quantity'])

        return jsonify(ret)
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        Systemp_log1(traceback.format_exc(), "classification3123_data").append_new_line()
        return jsonify(ret),500
    
@products.post('/classification_3123/download')
@swag_from('./docs/products/classification/classification3123_download.yaml')
@token_required_and_permissions
def download_classification3123_data(role, permissions):
    try:
        # Tạo cusor để kết nối với database
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234;Database=QC; Trusted_Connection=No;',timeout=1)

        # Check xem có phải Manager không?
        if role < 100:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 41
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

        datetime_start = day_start + " " + time_start
        datetime_end = day_end + " " + time_end

        print("SELECT * FROM [QC].[dbo].[Classification_A2303123] where TimeSave >='"+datetime_start+"' and TimeSave <='"+datetime_end+"'")
        classification3123_df = pd.read_sql("SELECT * FROM [QC].[dbo].[Classification_A2303123] where TimeSave >='"+datetime_start+"' and TimeSave <='"+datetime_end+"'", conn)

        # Nếu lấy dữ liệu ra trống
        if len(classification3123_df) == 0:
            ret = {
                'status':False,
                'message':'Not Exist Data'
            }
            return jsonify(ret),400

        output = io.BytesIO()
        writer = pd.ExcelWriter(
            output,
            engine='xlsxwriter')    # add a sheet
        
        classification3123_df.to_excel(writer, sheet_name='layer1', index=False)

        # add headers
        writer.close()
        output.seek(0)
        
        return Response(output, mimetype="application/ms-excel",
                        headers={"Content-Disposition": "attachment;filename=Classification3123_Data.xls"})
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        Systemp_log1(traceback.format_exc(), "classification3123_download").append_new_line()
        return jsonify(ret),500

def convert_to_json_serializable(data):
    if isinstance(data, dict):
        return {convert_to_json_serializable(k): convert_to_json_serializable(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [convert_to_json_serializable(item) for item in data]
    elif isinstance(data, datetime.datetime):  # Sử dụng datetime.datetime thay vì datetime
        return data.strftime('%Y-%m-%d %H:%M:%S')  # Chuyển đổi datetime thành chuỗi
    elif isinstance(data, (np.int64, np.int32, np.int16, np.int8)):
        return int(data)  # Chuyển đổi int64 thành int
    else:
        return data
    
# Thread Verification
# SEARCH
@products.post('/thread_verification')
@swag_from('./docs/products/thread_verification/thread_verification_data.yaml')
@token_required_and_permissions
def get_thread_verification_data(role, permissions):
    try:
        # Tạo cusor để kết nối với database
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234;Database=QC; Trusted_Connection=No;',timeout=1)
        cursor = conn.cursor()

        # Check xem có phải Manager không?
        if role < 100:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 31
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

        datetime_start = day_start + " " + time_start
        datetime_end = day_end + " " + time_end

        print("SELECT Top(15000) id, OP_name, Machine, ProductName, DMC_product, Timestart, Timefinish, Quality, Status, Note_life_time FROM [QC].[dbo].[ThreadVerification] where Timestart >'"+datetime_start+"' and Timestart <'"+datetime_end+"'")
        cursor.execute("SELECT Top(15000) id, OP_name, Machine, ProductName, DMC_product, Timestart, Timefinish, Quality, Status, Note_life_time FROM [QC].[dbo].[ThreadVerification] where Timestart >'"+datetime_start+"' and Timestart <'"+datetime_end+"'")
        all_records = cursor.fetchall()

        # Lấy số dượng lượng record
        num_records = len(all_records)

        # Nếu lấy dữ liệu ra trống
        if all_records == None:
            ret = {
                'status':False,
                'message':'Not Exist Data'
            }
            return jsonify(ret),400

        # Nếu có máy
        ret = {
                'status':True,
                'message':'Success',
                'data':{}
            }
        
        if num_records == 0:
            ret['data'] = None
            return jsonify(ret)
        
        # Khởi tạo để lấy dữ liệu cho chart và table 
        ret['data']['chart'] = {}
        ret['data']['table'] = []

        # Lấy dữ liệu cho bảng
        for item in all_records:
            id, op_name, machine, product_name, dmc_product, datetime_start_temp, datetime_finish_temp, quality, status, note_life_time = item
            ret['data']['table'].append({
                'id': str(id),
                'opName': op_name,
                'machine': machine,
                'productName': product_name,
                'dmcProduct': dmc_product,
                'timeStart': datetime_start_temp.strftime('%Y-%m-%d %H:%M:%S') if datetime_start_temp is not None else datetime_start_temp,
                'timeFinish': datetime_finish_temp.strftime('%Y-%m-%d %H:%M:%S') if datetime_finish_temp is not None else datetime_finish_temp,
                'quality': quality,
                'status': status,
                'noteLifeTime': note_life_time
            })

        # Lấy dữ liệu để vẽ chart
        print("SELECT left(Timestart, 11) as 'Time', Machine, Quality, COUNT(Quality) AS 'Count' FROM [QC].[dbo].[ThreadVerification] where Timestart >'"+datetime_start+"' and Timestart <'"+datetime_end+"' and Quality != '' GROUP BY left(Timestart, 11), Quality, Machine order by left(Timestart, 11) desc")
        thread_verification_df = pd.read_sql("SELECT left(Timestart, 11) as 'Time', Machine, Quality, COUNT(Quality) AS 'Count' FROM [QC].[dbo].[ThreadVerification] where Timestart >'"+datetime_start+"' and Timestart <'"+datetime_end+"' and Quality != '' GROUP BY left(Timestart, 11), Quality, Machine order by left(Timestart, 11) desc", conn)
        thread_verification_df = thread_verification_df.pivot_table(index='Time', columns=['Machine', 'Quality'], values='Count', aggfunc='sum', fill_value=0)
        
        # Khảo sát dữ liệu trong df
        print(thread_verification_df.head(10))
        print(thread_verification_df.columns.to_list())
        print(thread_verification_df.values)
        print(thread_verification_df.index.to_list())

        # Khởi tạo các list dữ liệu để vẽ chart
        ret['data']['chart']['timeIndex'] = []
        ret['data']['chart']['countData'] = []

        # Lấy dữ liệu timeIndex
        ret['data']['chart']['timeIndex'] = thread_verification_df.index.to_list()  

        # Lấy dữ liệu count
        for count_list in thread_verification_df.values:
            count_data_list = []
            for count_idx, count_name in enumerate(thread_verification_df.columns.to_list()):
                count_data_dict = {}

                count_data_dict['countName'] = "(" + list(count_name)[0] + ", " + list(count_name)[1] + ")"
                count_data_dict['countValue'] = count_list[count_idx]

                count_data_list.append(count_data_dict)
            
            ret['data']['chart']['countData'].append(count_data_list)

        ret = convert_to_json_serializable(ret)

        return jsonify(ret)
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        Systemp_log1(traceback.format_exc(), "thread_verification_data").append_new_line()
        return jsonify(ret),500
    
@products.post('/thread_verification/download')
@swag_from('./docs/products/thread_verification/thread_verification_download.yaml')
@token_required_and_permissions
def download_thread_verification_data(role, permissions):
    try:
        # Tạo cusor để kết nối với database
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234;Database=QC; Trusted_Connection=No;',timeout=1)

        # Check xem có phải Manager không?
        if role < 100:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 31
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

        datetime_start = day_start + " " + time_start
        datetime_end = day_end + " " + time_end

        print("SELECT * From[QC].[dbo].[ThreadVerification] where Timestart >'"+datetime_start+"' and Timestart <'"+datetime_end+"'")
        thread_verification_df = pd.read_sql("SELECT * From[QC].[dbo].[ThreadVerification] where Timestart >'"+datetime_start+"' and Timestart <'"+datetime_end+"'", conn)

        # Nếu lấy dữ liệu ra trống
        if len(thread_verification_df) == 0:
            ret = {
                'status':False,
                'message':'Not Exist Data'
            }
            return jsonify(ret),400

        output = io.BytesIO()
        writer = pd.ExcelWriter(
            output,
            engine='xlsxwriter')    # add a sheet
        
        thread_verification_df.to_excel(writer, sheet_name='ThreadVerification', index=False)

        # add headers
        writer.close()
        output.seek(0)
        
        return Response(output, mimetype="application/ms-excel",
                        headers={"Content-Disposition": "attachment;filename=ThreadVerification_Data.xls"})
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        Systemp_log1(traceback.format_exc(), "thread_verification_download").append_new_line()
        return jsonify(ret),500

# REALTIME
@products.get('/thread_verification/machine=<string:machine_name>')
@swag_from('./docs/products/thread_verification/top_10_thread_verification_data.yaml')
@token_required_and_permissions
def get_top_10_thread_verification_data(role, permissions, machine_name):
    try:
        # Tạo cusor để kết nối với database
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234;Database=QC; Trusted_Connection=No;',timeout=1)
        cursor = conn.cursor()

        # Check xem có phải Manager không?
        if role < 100:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 31
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
        
        print("select top(10) id, OP_name, Machine, ProductName, DMC_product, Timestart, Timefinish, Quality, Status, Note_life_time from [QC].[dbo].[ThreadVerification] where Machine = '"+machine_name+"' order by Timestart desc")
        cursor.execute("select top(10) id, OP_name, Machine, ProductName, DMC_product, Timestart, Timefinish, Quality, Status, Note_life_time from [QC].[dbo].[ThreadVerification] where Machine = '"+machine_name+"' order by Timestart desc")
        all_records = cursor.fetchall()

        # Lấy số dượng lượng record
        num_records = len(all_records)

        # Nếu lấy dữ liệu ra trống
        if all_records == None:
            ret = {
                'status':False,
                'message':'Not Exist Data'
            }
            return jsonify(ret),400

        # Nếu có máy
        ret = {
                'status':True,
                'message':'Success',
                'data':[]
            }
        
        if num_records == 0:
            ret['data'] = None
            return jsonify(ret)

        # Lấy dữ liệu cho bảng
        for item in all_records:
            id, op_name, machine, product_name, dmc_product, datetime_start_temp, datetime_finish_temp, quality, status, note_life_time = item
            ret['data'].append({
                'id': str(id),
                'opName': op_name,
                'machine': machine,
                'productName': product_name,
                'dmcProduct': dmc_product,
                'timeStart': datetime_start_temp.strftime('%Y-%m-%d %H:%M:%S') if datetime_start_temp is not None else datetime_start_temp,
                'timeFinish': datetime_finish_temp.strftime('%Y-%m-%d %H:%M:%S') if datetime_finish_temp is not None else datetime_finish_temp,
                'quality': quality,
                'status': status,
                'noteLifeTime': note_life_time
            })

        return jsonify(ret)
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        Systemp_log1(traceback.format_exc(), "top_10_thread_verification_data").append_new_line()
        return jsonify(ret),500
    
@products.get('/thread_verification/images/machine=<string:machine_name>')
@swag_from('./docs/products/thread_verification/2dimage_thread_verification.yaml')
@token_required_and_permissions
def get_2dimage_thread_verification(role, permissions, machine_name):
    try:
        with open("static/airleakage/pointmap.json", 'r') as json_file:
            points = json.load(json_file)

        # Tạo cusor để kết nối với database
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; Database=QC; UID=sa; PWD=1234; Trusted_Connection=No;')

        # Check xem có phải Manager không?
        if role < 100:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 31
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
        
        threadverification_2d = pd.read_sql("select * from [2D_Thread] where machineno = '"+machine_name+"'",conn)
        dmc = threadverification_2d.loc[0,"Product_type"]  
        img = cv2.imread('static/airleakage/'+dmc+'.png')
        
        dt = pd.read_sql("select top(1) Quality from [QC].[dbo].[ThreadVerification] where [DMC_product] = '"+threadverification_2d.loc[0,"DMC"]+"' order by Timestart desc", conn)
        if len(dt) > 0:
            if dt.loc[0,"Quality"] == "OK":
                cv2.rectangle(img,(int(img.shape[1]/2)-210,70),(int(img.shape[1]/2)+390,110), (0, 255, 0), -1)
            else:
                cv2.rectangle(img,(int(img.shape[1]/2)-210,70),(int(img.shape[1]/2)+390,110), (0, 0, 255), -1)
        else:
            cv2.rectangle(img,(int(img.shape[1]/2)-210,70),(int(img.shape[1]/2)+390,110), (200, 200, 200), -1)

        cv2.putText(img, threadverification_2d.loc[0,"DMC"], (int(img.shape[1]/2)-200,100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,0), 2, cv2.LINE_AA)  
        for i in range(int(threadverification_2d.loc[0, "Hole_no"])):
            point = points[dmc][i]   
                
            if int(threadverification_2d.loc[0,"Hole_stt"+str(i+1)]) == 1:
                color = (0,255,0)
            else:
                color = (0,0,255)  

            cv2.circle(img,(point["position"][0],point["position"][1]),point["radius"],color,3)

            if dmc == 'A2303121':
                if int(threadverification_2d.loc[0,"Hole_no"]) < len(points[dmc]):
                    point2 = points[dmc][int(threadverification_2d.loc[0,"Hole_no"])] 
                    if datetime.datetime.now().second % 2 == 0:
                        cv2.circle(img,(point2["position"][0],point2["position"][1]),point["radius"],(0,255,255),3)
            else:        
                if int(threadverification_2d.loc[0,"Hole_no"]) < len(points[dmc]):
                    point2 = points[dmc][int(threadverification_2d.loc[0,"Hole_no"])] 
                    if datetime.datetime.now().second % 2 == 0:
                        cv2.circle(img,(point2["position"][0],point2["position"][1]),point["radius"],(0,255,255),3)

            cv2.putText(img,str(round(float(threadverification_2d.loc[0,"Hole_tor"+str(i+1)]),4)),(point["position"][0]-50,point["position"][1]-20),cv2.FONT_HERSHEY_SIMPLEX,0.5,(0,0,0),5,cv2.LINE_AA) 
            cv2.putText(img,str(round(float(threadverification_2d.loc[0,"Hole_tor"+str(i+1)]),4)),(point["position"][0]-50,point["position"][1]-20),cv2.FONT_HERSHEY_SIMPLEX,0.5,color,2,cv2.LINE_AA)
        
        filename = 'static/airleakage/'+machine_name+str(threadverification_2d.loc[0,"Hole_no"])+'.png'
        cv2.imwrite(filename,img)

        return send_file(filename, mimetype='image/png')
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        Systemp_log1(traceback.format_exc(), "get_2dimage_thread_verification").append_new_line()
        return jsonify(ret),500
    
@products.get('/thread_verification/images/id=<string:dmc>')
@swag_from('./docs/products/thread_verification/get_info.yaml')
@token_required_and_permissions
def get_info_data(role, permissions, dmc):
    try:
        with open("static/airleakage/pointmap.json", 'r') as json_file:
            points = json.load(json_file)
        
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; Database=QC; UID=sa; PWD=1234; Trusted_Connection=No;')
        
        # Check xem có phải Manager không?
        if role < 100:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 31
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
        
        data = pd.read_sql("select top(1) * from [QC].[dbo].[ThreadVerification] where id = '"+dmc+"' order by id desc",conn)
        mahang = data.loc[0,"ProductName"]  
        img = cv2.imread('static/airleakage/'+mahang+'.png')
        
        if data.loc[0,"Quality"] == "OK":
            cv2.rectangle(img,(int(img.shape[1]/2)-210,70),(int(img.shape[1]/2)+390,110), (0, 255, 0), -1)
        else:
            cv2.rectangle(img,(int(img.shape[1]/2)-210,70),(int(img.shape[1]/2)+390,110), (0, 0, 255), -1)
        
        cv2.putText(img,data.loc[0,"DMC_product"],(int(img.shape[1]/2)-200,100),cv2.FONT_HERSHEY_SIMPLEX,1,(0,0,0),2,cv2.LINE_AA) 
        errorhole = []
        
        if len(data.loc[0,"Status"])> 0:
            err = str(data.loc[0,"Status"]).split("HOLE_")
            for hole in err:
                try:
                    errorhole.append(int(hole.strip()))
                except:
                    print("error",hole)

        if mahang == 'A2303121':
            for i in range(7):
                point = points[mahang][i]   
                
                if (i+1) in errorhole:
                    color = (0,0,255)
                else:
                    color = (0,255,0)  

                cv2.circle(img,(point["position"][0],point["position"][1]),point["radius"],color,3)
                cv2.putText(img,str(round(float(data.loc[0,"Torque_H"+str(i+1)]),4)),(point["position"][0]-50,point["position"][1]-20),cv2.FONT_HERSHEY_SIMPLEX,0.5,(0,0,0),5,cv2.LINE_AA)
                cv2.putText(img,str(round(float(data.loc[0,"Torque_H"+str(i+1)]),4)),(point["position"][0]-50,point["position"][1]-20),cv2.FONT_HERSHEY_SIMPLEX,0.5,color,2,cv2.LINE_AA)  
        else:
            for i in range(11):
                point = points[mahang][i]   
                
                if (i+1) in errorhole:
                    color = (0,0,255)
                else:
                    color = (0,255,0)  

                cv2.circle(img,(point["position"][0],point["position"][1]),point["radius"],color,3)
                cv2.putText(img,str(round(float(data.loc[0,"Torque_H"+str(i+1)]),4)),(point["position"][0]-50,point["position"][1]-20),cv2.FONT_HERSHEY_SIMPLEX,0.5,(0,0,0),5,cv2.LINE_AA)
                cv2.putText(img,str(round(float(data.loc[0,"Torque_H"+str(i+1)]),4)),(point["position"][0]-50,point["position"][1]-20),cv2.FONT_HERSHEY_SIMPLEX,0.5,color,2,cv2.LINE_AA)  
        
        filename = 'static/airleakage/showpic.png'
        cv2.imwrite(filename,img)

        return send_file(filename, mimetype='image/png')
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        Systemp_log1(traceback.format_exc(), "get_2dimage_thread_verification").append_new_line()
        return jsonify(ret),500

@products.put('/thread_verification/update_result')
@swag_from('./docs/products/thread_verification/update_result_data.yaml')
@token_required_and_permissions
def update_result_data(role, permissions):
    try:
        # Tạo cusor để kết nối với database
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234;Database=Auto; Trusted_Connection=No;',timeout=1)
        cursor = conn.cursor()

        # Check xem có phải Manager không?
        if role < 100:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 32
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

        dmc = request.json['dmc']
        result = request.json['result']

        print("Update [QC].[dbo].[ThreadVerification] set Quality = '"+result+"' where DMC_Product ='"+dmc+"'")
        cursor.execute("Update [QC].[dbo].[ThreadVerification] set Quality = '"+result+"' where DMC_Product ='"+dmc+"'")
        
        conn.commit()

        ret = {
            'status':True,
            'message':'Update data successfully!',
            'data': {'dmc': dmc, 'result': result}
        }

        return jsonify(ret), HTTP_201_CREATED
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        Systemp_log1(str(e), "update_result_data").append_new_line()
        return jsonify(ret), 500
    
# Pin Press
@products.post('/pin_press')
@swag_from('./docs/products/pin_press/pin_press_data.yaml')
@token_required_and_permissions
def get_pin_press_data(role, permissions):
    try:
        # Tạo cusor để kết nối với database
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234; Database=Auto; Trusted_Connection=No;', timeout=1)
        cursor = conn.cursor()

        # Check xem có phải Manager không?
        if role < 100:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 44
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

        datetime_start = day_start + " " + time_start
        datetime_end = day_end + " " + time_end

        # Lấy dữ liệu bảng ShotBlasting
        cursor.execute("SELECT Top(15000) * From [QC].[dbo].[DONG_BIN] where TimeFinish >'"+datetime_start+"' and TimeFinish <'"+datetime_end+"'")
        all_records = cursor.fetchall()

        # Lấy số dượng lượng record
        num_records = len(all_records)

        # Nếu lấy dữ liệu ra trống
        if all_records == None:
            ret = {
                'status':False,
                'message':'Not Exist Data'
            }
            return jsonify(ret),400

        # Nếu có máy
        ret = {
                'status':True,
                'message':'Success',
                'data':{}
            }
        
        if num_records == 0:
            ret['data'] = None
            return jsonify(ret)
        
        # Nếu lấy dữ liệu không trống        
        # Khởi tạo 2 list dữ liệu cần thiết show bảng dữ liệu và dữ liệu đã qua xử lý để vẽ chart
        ret['data']['table'] = []
        ret['data']['chart'] = {}

        # Lấy dữ liệu để show bảng
        for item in all_records:
            id, machine_no, dmc_product, motor_current, position, time_start_temp, time_finish_temp, result, thrust = item
            
            ret['data']['table'].append({
                'id': id,
                'machineNo': machine_no,
                'dmcProduct': dmc_product,
                'motorCurrent': motor_current,
                'position': position,
                'timeStart': time_start_temp.strftime('%Y-%m-%d %H:%M:%S') if time_start_temp is not None else time_start_temp,
                'timeFinish': time_finish_temp.strftime('%Y-%m-%d %H:%M:%S') if time_finish_temp is not None else time_finish_temp,
                'result': result,
                'thrust': thrust
            })

        # Lấy dữ liệu để vẽ chart
        pin_press_df = pd.read_sql("SELECT left(TimeFinish,11) as 'Time', Result, COUNT(Result) AS 'Count' FROM [QC].[dbo].[DONG_BIN] where TimeFinish >'"+datetime_start+"' and TimeFinish<'"+datetime_end+"'GROUP BY left(TimeFinish,11), Result order by left(TimeFinish,11)", conn)
        
        pin_press_df = pin_press_df.pivot_table(index='Time', columns='Result')

        # Khảo sát dữ liệu trong df
        print(pin_press_df.head(10))
        print(pin_press_df.columns.to_list())
        print(pin_press_df.values.tolist())
        print(pin_press_df.index.to_list())

        # Khởi tạo các list dữ liệu để vẽ chart
        ret['data']['chart']['timeIndex'] = []
        ret['data']['chart']['okNgData'] = []

        # Lấy dữ liệu timeIndex
        ret['data']['chart']['timeIndex'] = pin_press_df.index.to_list()

        # Lấy dữ liệu count OK và count NG của mỗi timeIndex
        for idx in range(len(pin_press_df.index.tolist())):
            if len(pin_press_df.values.tolist()[idx]) > 1:
                ret['data']['chart']['okNgData'].append({'NG': 0 if isNaN(pin_press_df.values.tolist()[idx][0]) else pin_press_df.values.tolist()[idx][0], 'OK': 0 if isNaN(pin_press_df.values.tolist()[idx][1]) else pin_press_df.values.tolist()[idx][1]}) 
            else:
                ret['data']['chart']['okNgData'].append({'NG': 0, 'OK': 0 if isNaN(pin_press_df.values.tolist()[idx][0]) else pin_press_df.values.tolist()[idx][0]}) 
        
        return jsonify(ret)
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        Systemp_log1(traceback.format_exc(), "pin_press_data").append_new_line()
        return jsonify(ret),500
    
@products.post('/pin_press/download')
@swag_from('./docs/products/pin_press/pin_press_download.yaml')
@token_required_and_permissions
def download_pin_press_data(role, permissions):
    try:
        # Tạo cusor để kết nối với database
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234;Database=QC; Trusted_Connection=No;',timeout=1)

        # Check xem có phải Manager không?
        if role < 100:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 44
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

        datetime_start = day_start + " " + time_start
        datetime_end = day_end + " " + time_end

        print("SELECT * From [QC].[dbo].[DONG_BIN] where TimeFinish >'"+datetime_start+"' and TimeFinish <'"+datetime_end+"'")
        pin_press_df = pd.read_sql("SELECT * From [QC].[dbo].[DONG_BIN] where TimeFinish >'"+datetime_start+"' and TimeFinish <'"+datetime_end+"'", conn)

        # Nếu lấy dữ liệu ra trống
        if len(pin_press_df) == 0:
            ret = {
                'status':False,
                'message':'Not Exist Data'
            }
            return jsonify(ret),400

        output = io.BytesIO()
        writer = pd.ExcelWriter(
            output,
            engine='xlsxwriter')    # add a sheet
        
        pin_press_df.to_excel(writer, sheet_name='PinPress', index=False)

        # add headers
        writer.close()
        output.seek(0)
        
        return Response(output, mimetype="application/ms-excel",
                        headers={"Content-Disposition": "attachment;filename=PinPress_Data.xls"})
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        Systemp_log1(traceback.format_exc(), "pin_press_download").append_new_line()
        return jsonify(ret),500