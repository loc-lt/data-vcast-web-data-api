from os import access
from constants.http_status_code import HTTP_200_OK, HTTP_201_CREATED, HTTP_400_BAD_REQUEST, HTTP_401_UNAUTHORIZED, HTTP_409_CONFLICT
from flask import Blueprint, app, request, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from flask_jwt_extended import jwt_required, create_access_token, create_refresh_token, get_jwt_identity
from flasgger import swag_from
from database import *
from ERROR import *
import traceback
from flask import session
from auth_middleware import *

lwm = Blueprint("lwm", __name__, url_prefix="/api/v1/lwm")

@lwm.get('/file_names') # cần time_start, time_end, day_start, day_end, code -> trả về một bộ số liệu gồm: tổng, các biến là list thời gian, thông số theo thời gian để vẽ biểu đồ
@swag_from('./docs/LWM/file_list.yaml')
@token_required_and_permissions
def file_list(role, permissions):
    try:
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234;Database=LWM; Trusted_Connection=No;',timeout=1)
        cursor = conn.cursor()

        # Check xem có phải Manager không?
        if role < 100:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 15
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

        cursor.execute("select dmc_product, getdatetime from datalwm order by id desc")
        dmc_products_list = cursor.fetchall()

        # Nếu lấy dữ liệu ra trống
        if dmc_products_list == None:
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
        
        if len(dmc_products_list) == 0:
            ret['data'] = None                  
            return jsonify(ret)
        
        file_list = [{'dmc': row.dmc_product, 'datetime': row.getdatetime.strftime("%Y-%m-%d %H:%M:%S")} for row in dmc_products_list]

        ret['data'] = file_list

        return jsonify(ret)
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        Systemp_log1(traceback.format_exc(), "file_list").append_new_line()
        return jsonify(ret),500
    
@lwm.get('/charts/<string:fileName>') # cần time_start, time_end, day_start, day_end, code -> trả về một bộ số liệu gồm: tổng, các biến là list thời gian, thông số theo thời gian để vẽ biểu đồ
@swag_from('./docs/LWM/file_name.yaml')
@token_required
def file_name(role, permissions, fileName):
    try:
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234;Database=LWM; Trusted_Connection=No;',timeout=1)
        cursor = conn.cursor()

        # Check xem có phải Manager không?
        if role < 100:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 15
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
        
        cursor.execute("SELECT TimeLine1, TimeLine2, Plasma1, Plasma2, Temp1, Temp2, Refl1, Refl2, Laser1, Laser2 FROM [LWM].[dbo].[DataLWM] where dmc_product = '"+fileName+"'")
        data_lwm_record = cursor.fetchone()

        # Nếu lấy dữ liệu ra trống
        if data_lwm_record == None:
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
        
        if len(data_lwm_record) == 0:
            ret['data'] = None                  
            return jsonify(ret)
        
        time_line_list = [float(val) for val in (data_lwm_record[0] + data_lwm_record[1]).split(';')] # x_axis  

        plasma_list = [float(val) for val in (data_lwm_record[2] + data_lwm_record[3]).split(';')]
        temp_list = [float(val) for val in (data_lwm_record[4] + data_lwm_record[5]).split(';')]
        refl_list = [float(val) for val in (data_lwm_record[6] + data_lwm_record[7]).split(';')]
        laser_list = [float(val) for val in (data_lwm_record[8] + data_lwm_record[9]).split(';')]

        tolerance_percent = 0.2  # 20%
        jitter_percent = 40     # 40%

        upper_limit0 = []
        lower_limit0 = []
        upper_limit1 = []
        lower_limit1 = []
        upper_limit2 = []
        lower_limit2 = []
        upper_limit3 = []
        lower_limit3 = []

        count = 99999999

        for idx in range(len(time_line_list)):
            tolerance0 = plasma_list[idx] * tolerance_percent
            tolerance1 = temp_list[idx] * tolerance_percent
            tolerance2 = refl_list[idx] * tolerance_percent
            tolerance3 = laser_list[idx] * tolerance_percent

            if count > jitter_percent:
                lower_bound0 = plasma_list[idx] - tolerance0
                upper_bound0 = plasma_list[idx] + tolerance0
                lower_bound1 = temp_list[idx] - tolerance1
                upper_bound1 = temp_list[idx] + tolerance1
                lower_bound2 = refl_list[idx] - tolerance2
                upper_bound2 = refl_list[idx] + tolerance2
                lower_bound3 = laser_list[idx] - tolerance3
                upper_bound3 = laser_list[idx] + tolerance3

                count = 0
            
            # Thêm giới hạn vào danh sách
            lower_limit0.append(lower_bound0)
            upper_limit0.append(upper_bound0)
            lower_limit1.append(lower_bound1)
            upper_limit1.append(upper_bound1)
            lower_limit2.append(lower_bound2)
            upper_limit2.append(upper_bound2)
            lower_limit3.append(lower_bound3)
            upper_limit3.append(upper_bound3)

            count += 1

        ret['data']['plasmaList'] = {'value': plasma_list, 'lowerValue': lower_limit0, 'upperValue': upper_limit0}
        ret['data']['tempList'] = {'value': temp_list, 'lowerValue': lower_limit1, 'upperValue': upper_limit1}
        ret['data']['reflList'] = {'value': refl_list, 'lowerValue': lower_limit2, 'upperValue': upper_limit2}
        ret['data']['laserList'] = {'value': laser_list, 'lowerValue': lower_limit3, 'upperValue': upper_limit3}

        return jsonify(ret)
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        Systemp_log1(traceback.format_exc(), "file_list").append_new_line()
        return jsonify(ret),500