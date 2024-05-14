from os import access
from constants.http_status_code import HTTP_200_OK, HTTP_201_CREATED, HTTP_400_BAD_REQUEST, HTTP_401_UNAUTHORIZED, HTTP_409_CONFLICT
from flask import Blueprint, app, request, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from flask_jwt_extended import jwt_required, create_access_token, create_refresh_token, get_jwt_identity
from flasgger import swag_from
from database import *
from ERROR import *
import traceback
from auth_middleware import *

heat_treatment = Blueprint("heat_treatment", __name__, url_prefix="/api/v1/heat_treatment")
    
@heat_treatment.post('') # cần time_start, time_end, day_start, day_end, code -> trả về một bộ số liệu gồm: tổng, các biến là list thời gian, thông số theo thời gian để vẽ biểu đồ
@swag_from('./docs/Heat_Treatment/search_data.yaml')
@token_required_and_permissions
def search_data(role, permissions):
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
        id_permission = 18
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

        code = request.json['code']

        if len(code) == 8:
            try:
                ccode = ma[-3:]
                ctime = ma[:-4]

                if ctime[1].upper() == 'X':
                    cmonth = 10
                elif ctime[1].upper() == 'Y':
                    cmonth = 11
                elif ctime[1].upper() == 'Z':
                    cmonth = 12
                else:
                    cmonth = '0' + ctime[1]

                rtime = f'202{ctime[0]}-{cmonth}-{ctime[-2:]}'
                print(rtime)

                print("SELECT * FROM [SPC].[dbo].[HXL_HeatTreatment_Furnance] where Furnance_Code = '"+ccode+"' and TimeSet = '"+rtime+"'")
                cursor.execute("SELECT * FROM [SPC].[dbo].[HXL_HeatTreatment_Furnance] where Furnance_Code = '"+ccode+"' and TimeSet = '"+rtime+"'")
                
                temp_data = cursor.fetchone()
                hcode = temp_data[1]
            except:
                hcode = 'nocode'

            cursor.execute("SELECT Top(15000)* From [SPC].[dbo].[HXL_HeatTreatment_FileCode] where HeatTreatment_Code like '%"+hcode+"%'")
        else:
            cursor.execute("SELECT Top(15000)* From [SPC].[dbo].[HXL_HeatTreatment_FileCode] where Time_Out >'"+datetime_start+"' and Time_In <'"+datetime_end+"'")
        
        all_records = cursor.fetchall()

        # Nếu lấy dữ liệu ra trống
        if all_records == None:
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
        
        if len(all_records) == 0:
            ret['data'] = None
            return jsonify(ret)
            
        for item in all_records:
            id, heat_treatment_code, time_create, material, time_in, temp_in, operator1, time_indicated, temp_design, operator2, time_out, temp_out, operator3, machine, note = item
            ret['data'].append({
                'heatTreatmentCode':heat_treatment_code.strip(),
                'timeCreate':time_create,
                'material':material.strip(),
                'timeIn':time_in,
                'tempIn':temp_in,
                'operator1':operator1.strip(),
                'timeIndicated':time_indicated,
                'tempDesign': temp_design,
                'operator2': operator2.strip(),
                'timeOut': time_out,
                'tempOut': temp_out,
                'operator3': operator3.strip(),
                'machine': machine.strip(),
                'note': note.strip()
            })

        return jsonify(ret)
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        Systemp_log1(traceback.format_exc(), "search_data").append_new_line()
        return jsonify(ret),500
    
@heat_treatment.get('/line_chart/<string:heatTreatmentCode>') 
@swag_from('./docs/Heat_Treatment/line_chart.yaml')
@token_required_and_permissions
def line_chart(role, permissions ,heatTreatmentCode):
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
        id_permission = 18
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
        
        # Truy cập Database để lấy dữ liệu
        cursor.execute("SELECT Time_In, Time_Indicated, Time_Out, Machine FROM [SPC].[dbo].[HXL_HeatTreatment_FileCode] where HeatTreatment_Code like '%"+heatTreatmentCode+"%'")
        record_infor = cursor.fetchone()

        # Nếu lấy dữ liệu ra trống
        if record_infor == None:
            ret = {
                'status':False,
                'message':'Not Exist Data'
            }
            return jsonify(ret),400
        
        print("SELECT * FROM [SPC].[dbo].[HXL_HeatTreatment_Data] where DateTimeData > '"+str(record_infor[0])+"' and DateTimeData < '"+str(record_infor[2])+"' and Machine = '"+record_infor[3]+"' order by id desc")
        cursor.execute("SELECT * FROM [SPC].[dbo].[HXL_HeatTreatment_Data] where DateTimeData > '"+str(record_infor[0])+"' and DateTimeData < '"+str(record_infor[2])+"' and Machine = '"+record_infor[3]+"' order by id desc" )
        all_records = cursor.fetchall()

        print('test', all_records)
        # Nếu lấy dữ liệu ra trống
        if all_records == None:
            ret = {
                'status':False,
                'message':'Not Exist Data'
            }
            return jsonify(ret),400

        # Nếu fetch dữ liệu thành công
        ret = {
                'status':True,
                'message':'Success',
                'data': {}
            }
        
        # Nếu không có dòng dữ liệu nào thì trả về luôn        
        if len(all_records) == 0:
            ret['data'] = None
            return jsonify(ret)
        
        # Khởi tạo các biến để 
        main_temp_list = []
        over_temp_list = []
        cooling_water_list = []
        time_list = []
    
        # Lưu dữ liệu vô các list
        for item in all_records:
            id, machine, datetime_data, main_temp, over_temp, cooling_water = item
            
            main_temp_list.append(round(main_temp))
            over_temp_list.append(round(over_temp))
            cooling_water_list.append(round(cooling_water))
            # time_list.append(datetime_data.strftime("%Y-%m-%D %H:%M:%S"))
            time_list.append(int(datetime_data.timestamp()*1000))

        # Khởi tạo các list trong 'data' để chứa dữ liệu
        ret['data']['timeList'] = time_list

        ret['data']['mainTempList'] = main_temp_list
        ret['data']['overTempList'] = over_temp_list
        ret['data']['coolingWaterList'] = cooling_water_list
        
        # ret['data']['indicated'] = record_infor[1].strftime("%Y-%m-%D %H:%M:%S")
        ret['data']['indicated'] = int(record_infor[1].timestamp()*1000)

        return jsonify(ret)
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        Systemp_log1(traceback.format_exc(), "line_chart").append_new_line()
        return jsonify(ret), 500