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
from auth_middleware import *

electrical_root = Blueprint("electrical", __name__, url_prefix="/api/v1/electrical")

# lấy toàn bộ dữ liệu electrical real time
@electrical_root.get('')
@swag_from('./docs/Electrical/electrical.yaml')
@token_required_and_permissions
def electrical(role, permissions):
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
        id_permission = 2
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

        print("select * from [QC].[dbo].[Electrical]")
        cursor.execute("select * from [QC].[dbo].[Electrical]")
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
        ret = {
                'status':True,
                'message':'Success',
                'data':[]
            }
        
        for item in all_records:
            area_name, average, u_ab, u_bc, u_ac, total, status = item
            ret['data'].append({
                'area':area_name.strip(),
                'average':average,
                'uAB':u_ab,
                'uBC':u_bc,
                'uAC':u_ac,
                'total':total,
            })
        return jsonify(ret)
    
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        return jsonify(ret),500
    
# api update electrical
@electrical_root.put('/update_cost')
@swag_from('./docs/Electrical/electrical_cost_update.yaml')
@token_required_and_permissions
def electrical_cost_update(role, permissions):
    try:
        # Check xem có phải Manager không?
        if role < 100:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 4
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

        off_peak_hour = request.json['off_peak_hour']
        normal_hour = request.json['normal_hour']
        rush_hour = request.json['rush_hour']
        
        # update electrical cost for each type
        cursor.execute("update [Electric].[dbo].[Elec_Cost] set cost = '" + off_peak_hour + "' where etype = 1")
        cursor.execute("update [Electric].[dbo].[Elec_Cost] set cost = '" + normal_hour + "' where etype = 2")
        cursor.execute("update [Electric].[dbo].[Elec_Cost] set cost = '" + rush_hour + "' where etype = 3")
        
        conn.commit()

        # if insert data to Vending table successfully
        ret = {
            'status':True,
            'message':'Update Data Successfully'
        }
        return jsonify(ret), HTTP_201_CREATED
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        Systemp_log1(str(e), "electrical_cost_update").append_new_line()
        return jsonify(ret), 500
    
@electrical_root.get('/cost')
@swag_from('./docs/Electrical/electrical_cost.yaml')
@token_required
def electrical_cost():
    try:
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234;Database=QC; Trusted_Connection=No;',timeout=1)
        cursor = conn.cursor()

        cursor.execute("select etype, cost from [Electric].[dbo].[Elec_Cost] order by etype")
        electrical_cost = cursor.fetchall()

        # Nếu lấy dữ liệu ra trống
        if electrical_cost == None:
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

        # Nếu lấy dữ liệu ra trống
        if len(electrical_cost) == 0:
            ret['data'] = None
            return jsonify(ret)
        
        for item in electrical_cost:
            etype, cost = item
            ret['data'].append({
                'etype': etype,
                'cost': cost
            })
        
        return jsonify(ret)
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        Systemp_log1(str(e), "electrical_cost").append_new_line()
        return jsonify(ret), 500
    
# Vẽ điều bồ miền khi nhấn vô từng location trong real_time 
# Cần time_start, time_end, location_name -> trả về một bộ số liệu gồm: tổng, các biến là list thời gian, thông số theo thời gian để vẽ biểu đồ
@electrical_root.post('/area_chart') 
@swag_from('./docs/Electrical/area_chart_data.yaml')
@token_required_and_permissions
def domain_chart_data(role, permissions):
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
        id_permission = 3
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

        # Lấy dữ liệu location
        location = request.json['location']

        print("SELECT * FROM [Electric].[dbo].[ELec_main] where Name_Area = '"+location+"' and Time_get > '"+day_start+"' and Time_get < '"+day_end+"' order by Time_get")
        cursor.execute("SELECT * FROM [Electric].[dbo].[ELec_main] where Name_Area = '"+location+"' and Time_get > '"+day_start+"' and Time_get < '"+day_end+"' order by Time_get")
        all_records = cursor.fetchall() # là dữ liệu của bảng ELec_main
        print("select * from [Electric].[dbo].[Elec_Cost] order by etype")
        cursor.execute("select * from [Electric].[dbo].[Elec_Cost] order by etype")
        elec_cost = cursor.fetchall() # là dữ liệu giá điện ở 3 mức -> giờ thấp điểm, giờ bình thường, giờ cao điểm

        # lấy ra 1 dict gồm etype và giá
        elect_cost_dict = {}
        for item in elec_cost:
            etype_elec, descript_elec, cost_elec = item
            elect_cost_dict[etype_elec] = cost_elec

        # Khởi tạo 3 list chứa 3 danh sách các giá trị qua thời gian của Time_get, Value(Số Kwhs điện), Money(Tiền điện)
        time_list = []
        total_kwh_list = []
        total_money_list = []

        # Khởi tạo 2 biến chứa tổng số ký điện và tổng số tiền điện
        total_kwh = 0
        total_money  = 0

        # Nếu lấy dữ liệu ra trống
        if all_records == None:
            ret = {
                'status':False,
                'message':'Not Exist Data'
            }
            return jsonify(ret),400
        
        '''
        - Nếu search trong khoảng tg đó có dữ liệu: lúc này có 3 TH
            1. Số ngày search >= 30 ngày -> trục thời gian lấy đơn vị là ngày (khoảng cách giữa 2 điểm là 1 ngày)
            2. Số ngày search thuộc (1, 30) -> ...
            3. Só ngày search <= 1 -> ...
        '''

        # Nếu có dữ liệu
        ret = {
                'status':True,
                'message':'Success',
                'data':[]
            }
        
        if len(all_records) == 0:
            ret['data'] = None
            return jsonify(ret)
        
        fID, fName, fTimeGet, fVolTage, fL_Avg, fPower, fPowerF, fTotal, fCost, fUab, fUbc, fUac, fla, flb, flc, fEaSub, fCostSub, fEtype = all_records[0]
        lID, lName, lTimeGet, lVolTage, lL_Avg, lPower, lPowerF, lTotal, lCost, lUab, lUbc, lUac, lla, llb, llc, lEaSub, lCostSub, lEtype = all_records[-1]

        # TH1: số ngày search >= 30 ngày: vẽ biểu đồ với đơn vị kỳ (10 ngày)
        if (lTimeGet - fTimeGet).days >= 30:
            print("Vô TH1")
            time_temp = 0
            sum_value = 0
            sum_money = 0
            
            # khởi tạo để khởi chạy dòng đầu tiên
            time_temp = '....'

            for idx in range(len(all_records)):
                ID, Name, TimeGet, VolTage, L_Avg, Power, PowerF, Total, Cost, Uab, Ubc, Uac, la, lb, flc, EaSub, CostSub, Etype = all_records[idx]

                # biến period là kỳ trong 1 tháng, trong đó: per1 là kỳ 1 (từ ngày 1 tới ngày 10), per2 từ ngày 11 tới 20, per3 từ 21 trở đi
                if TimeGet.day <= 10:
                    period = 'per1'
                elif TimeGet.day > 20:
                    period = 'per3'
                else:
                    period = 'per2'

                # time_temp có dạng YYYY-mm-kn, ky có dạng km
                # nếu mà km và kn thay đổi sau mỗi vòng lặp mà khác nhau
                if period != time_temp[-4:]:
                    # total_kwh_list và total_money_list được append sum_value và sum_money
                    total_kwh_list.append(round(sum_value,2))
                    total_money_list.append(round(sum_money))
                    time_list.append(time_temp)
                    
                    # total_kwh và total_money được cộng dồn qua từng vòng lặp 
                    total_kwh += sum_value
                    total_money += sum_money
                    time_temp = TimeGet.strftime("%Y-%m-") + period

                    # sum_value và sum_money thay đổi qua từng vòng lặp
                    sum_value = EaSub
                    sum_money = EaSub * elect_cost_dict[Etype]
                # còn km  và kn giống mãi thì cứ cộng dồn lên (cùng 1 ngày thì cứ cộng dồn lên?)
                else:
                    sum_value += EaSub
                    sum_money += EaSub * elect_cost_dict[Etype]

            total_kwh_list.append(round(sum_value,2))
            total_kwh_list = total_kwh_list[1:]

            total_money_list.append(round(sum_money))
            total_money_list = total_money_list[1:]

            time_list.append(time_temp)
            time_list = time_list[1:]
            
            total_kwh += sum_value
            total_money += sum_money

        # TH2: số ngày search thuộc (1, 30): vẽ biểu đồ miền với đơn vị ngày
        elif len(all_records) > 48:
            time_temp = 0
            sum_value = 0
            sum_money = 0

            for idx in range(len(all_records)):
                ID, Name, TimeGet, VolTage, L_Avg, Power, PowerF, Total, Cost, Uab, Ubc, Uac, la, lb, flc, EaSub, CostSub, Etype = all_records[idx]
                
                if TimeGet.strftime("%Y-%m-%d") != time_temp:
                    total_kwh_list.append(round(sum_value,2))
                    total_money_list.append(round(sum_money))
                    time_list.append(time_temp)
                    total_kwh += sum_value
                    total_money += sum_money
                    time_temp = TimeGet.strftime("%Y-%m-%d")
                    sum_value = EaSub
                    sum_money = sum_value * elect_cost_dict[Etype]
                else:
                    sum_value += EaSub
                    sum_money += sum_value * elect_cost_dict[Etype]

            total_kwh_list.append(round(sum_value,2))
            total_kwh_list = total_kwh_list[1:]
            
            total_money_list.append(round(sum_money))
            total_money_list = total_money_list[1:]
            
            time_list.append(time_temp)
            time_list = time_list[1:]
            
            total_kwh += sum_value
            total_money += sum_money

        # TH3: số ngày search <= 1: vẽ biểu đồ miền với đơn vị là 30p 
        else:
            for idx in range(len(all_records)):
                ID, Name, TimeGet, VolTage, L_Avg, Power, PowerF, Total, Cost, Uab, Ubc, Uac, la, lb, flc, EaSub, CostSub, Etype = all_records[idx]

                total_kwh_list.append(round(EaSub,2))
                total_money_list.append(round(EaSub * elect_cost_dict[Etype]))
                time_list.append(TimeGet.strftime("%Hh%Mm"))
                total_kwh += EaSub
                total_money += EaSub * elect_cost_dict[Etype]

        ret['data'] = {
            'name': location,
            'labels': time_list,
            'totalKwh': total_kwh,
            'totalMoney': total_money,
            'kwh': total_kwh_list,
            'money': total_money_list
        }   
         
        return jsonify(ret)
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        Systemp_log1(traceback.format_exc(), "electrical_cost_update").append_new_line()
        return jsonify(ret), 500
    
# Vẽ biểu đồ tròn trong trang chart
# Cần time_start, time_end -> trả về một bộ số liệu gồm: tổng, các biến là list thời gian, thông số theo thời gian để vẽ biểu đồ
@electrical_root.post('/pie_chart') 
@swag_from('./docs/Electrical/pie_chart_data.yaml')
@token_required
def pie_chart_data(role, permissions):
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
        id_permission = 3
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

        cursor.execute("select * from [Electric].[dbo].[Elec_Cost] order by etype")
        elec_cost = cursor.fetchall()

        print("select distinct(Name_Area) from [Electric].[dbo].[ELec_main] where Name_Area not like '%All%' and Time_get > '"+day_start+"' and Time_get < '"+day_end+"'")
        cursor.execute("select distinct(Name_Area) from [Electric].[dbo].[ELec_main] where Name_Area not like '%All%' and Time_get > '"+day_start+"' and Time_get < '"+day_end+"'")
        area_names = cursor.fetchall()

        # lấy ra 1 dict gồm etype và giá
        elect_cost_dict = {}
        for item in elec_cost:
            etype_elec, descript_elec, cost_elec = item
            elect_cost_dict[etype_elec] = cost_elec

        # Nếu lấy dữ liệu ra trống
        if area_names == None:
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
        if len(area_names) == 0:
            ret['data'] = None
            return jsonify(ret)

        # Khởi tạo các list trong 'data' để chứa dữ liệu
        ret['data']['labels'] = []
        ret['data']['kwh'] = []
        ret['data']['money'] = []
        
        # 2 biến chứa tổng số lượng kWh điện, tổng số tiền điện
        all_kwh = 0
        all_money = 0

        # Còn nếu không thì tiếp tục triển khai
        print(len(area_names))

        for idx in range(len(area_names)):
            AreaName = area_names[idx][0]
            print(AreaName)

            cursor.execute("SELECT Ea_Sub, etype FROM [Electric].[dbo].[ELec_main] where Name_Area = '"+AreaName+"' and Time_get > '"+day_start+"' and Time_get < '"+day_end+"' order by Time_get")
            all_records = cursor.fetchall()

            total_kwh = 0
            total_money = 0
            
            for idx1 in range(len(all_records)):
                Ea_Sub, etype = all_records[idx1]

                total_kwh += Ea_Sub
                total_money += Ea_Sub * elect_cost_dict[etype]
            
            all_kwh += total_kwh
            all_money += total_money
            
            # Append dữ liệu mới vào 4 list đã khởi tạo ở trên
            ret['data']["kwh"].append(round(total_kwh,2))
            ret['data']['money'].append(round(total_money))
            ret['data']['labels'].append(AreaName)

        ret['data']['totalKwh'] = all_kwh
        ret['data']['totalMoney'] = all_money

        return jsonify(ret)
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        Systemp_log1(traceback.format_exc(), "electrical_cost_update").append_new_line()
        return jsonify(ret), 500