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

@temphumid.get('/realtime_data/term_serch=<string:term>')
@swag_from('./docs/temphumid/realtime_data.yaml')
@token_required
def realtime_data(term):
    try:
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234;Database=QC; Trusted_Connection=No;',timeout=1)
        
        cursor = conn.cursor()

        print("select b.Area_name, a.Temp, a.Humid, b.Temp_Min, b.Temp_Max, b.Humid_Min, b.Humid_Max from [QC].[dbo].[temp_humid_realtime] a, [QC].[dbo].[temp_humid_setting] b where a.Area = b.Area and LOWER(b.Area_name) like N'%'" + term + "'%'")
        cursor.execute("select b.Area_name, a.Temp, a.Humid, b.Temp_Min, b.Temp_Max, b.Humid_Min, b.Humid_Max from [QC].[dbo].[temp_humid_realtime] a, [QC].[dbo].[temp_humid_setting] b where a.Area = b.Area and LOWER(b.Area_name) like N'%" + term + "%'")
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
                'area_name':area_name.strip(),
                'temp':temp,
                'humid':humid,
                'temp_min':temp_min,
                'temp_max':temp_max,
                'humid_min':humid_min,
                'humid_max':humid_max,
            })
        return jsonify(ret)
    
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        return jsonify(ret),500
    
@temphumid.get('/')
@swag_from('./docs/temphumid/temp_and_humid.yaml')
@token_required
def temp_and_humid():
    try:
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234;Database=QC; Trusted_Connection=No;',timeout=1)
        
        cursor = conn.cursor()

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
                'humid_max':humid_max,
            })
        return jsonify(ret)
    
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        return jsonify(ret),500