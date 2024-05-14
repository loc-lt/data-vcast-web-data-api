from os import access
from constants.http_status_code import HTTP_200_OK, HTTP_201_CREATED, HTTP_400_BAD_REQUEST, HTTP_401_UNAUTHORIZED, HTTP_409_CONFLICT
from flask import Blueprint, app, request, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from flask_jwt_extended import jwt_required, create_access_token, create_refresh_token, get_jwt_identity
from flasgger import swag_from
from database import *
from ERROR import *
from auth_middleware import *

temphumid = Blueprint("temp_and_humid", __name__, url_prefix="/api/v1/temp_and_humid")

# lấy toàn bộ dữ liệu temp_and_humid real time
@temphumid.get('')
@swag_from('./docs/temphumid/temp_and_humid.yaml')
@token_required_and_permissions
def temp_and_humid(role, permissions):
    try:
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
        id_permission = 16
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

        print("select b.Area_name, a.Temp, a.Humid, b.Temp_Min, b.Temp_Max, b.Humid_Min, b.Humid_Max from [QC].[dbo].[temp_humid_realtime] a, [QC].[dbo].[temp_humid_setting] b where a.Area = b.Area")
        cursor.execute("select b.Area_name, a.Temp, a.Humid, b.Temp_Min, b.Temp_Max, b.Humid_Min, b.Humid_Max from [QC].[dbo].[temp_humid_realtime] a, [QC].[dbo].[temp_humid_setting] b where a.Area = b.Area")
        all_records =cursor.fetchall()

        # Nếu lấy dữ liệu ra trống
        if all_records == None:
            ret = {
                'status':False,
                'message':'Not Exist Data'
            }
            return jsonify(ret),400
        
        print(all_records[0])
        # Nếu có máy
        ret ={
                'status':True,
                'message':'Success',
                'data':[]
            }
        
        for item in all_records:
            area_name, temp, humid, temp_min, temp_max, humid_min, humid_max = item
            ret['data'].append({
                'name':area_name.strip(),
                'temp':temp,
                'humid':humid,
                'tempMin':temp_min,
                'tempMax':temp_max,
                'humidMin':humid_min,
                'humidMax':humid_max,
            })
        return jsonify(ret)
    
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        return jsonify(ret),500
    
@temphumid.post('') # cần time_start, time_end, location_name -> trả về một bộ số liệu gồm: tổng, các biến là list thời gian, thông số theo thời gian để vẽ biểu đồ
@swag_from('./docs/temphumid/chart_data.yaml')
@token_required_and_permissions
def chart_data(role, permissions):
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
        id_permission = 17
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

        location = request.json['location']

        # Khởi tạo 3 list chứa 3 list các giá trị qua thời gian của Time_get, Temp, Humid
        datetime_list = []
        temp_list = []
        humid_list = []

        print("select top 10000 Area_name, Temp, Humid, Time_get from [Temp_Humid_Factory] left join [temp_humid_setting] on [Temp_Humid_Factory].Area = [temp_humid_setting].Area where Area_name = N'"+location+"' and Time_get >='"+datetime_start+"' and Time_get <='"+datetime_end+"'")
        cursor.execute("select top 10000 Area_name, Temp, Humid, Time_get from [Temp_Humid_Factory] left join [temp_humid_setting] on [Temp_Humid_Factory].Area = [temp_humid_setting].Area where Area_name = N'"+location+"' and Time_get >='"+datetime_start+"' and Time_get <='"+datetime_end+"'")
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
        
        for item in all_records:
            area_name, temp, humid, time_get = item

            # Thêm giá trị vào các list
            datetime_list.append(time_get.strftime('%Y-%m-%d %H:%M:%S'))
            temp_list.append(temp)
            humid_list.append(humid)
            
        # Lấy các thông số ngưỡng trên và ngưỡng dưới của temp_and_humid
        cursor.execute("select * from [QC].[dbo].[temp_humid_setting] where Area_name = N'"+location+"'")
        important_figures = cursor.fetchone()

        area, areaname, temp_min, temp_max, humid_min, humid_max = important_figures

        ret['data'] = {'name': area_name, 'datetimeList': datetime_list, 'tempList': temp_list, 'humidList': humid_list, 'tempMin': temp_min, 'tempMax': temp_max, 'humidMin': humid_min, 'humidMax': humid_max}
            
        return jsonify(ret)
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        return jsonify(ret),500