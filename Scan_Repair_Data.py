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

Scan_Repair_Data = Blueprint("Scan_Repair_Data", __name__, url_prefix="/api/v1/Scan_Repair_Data")

# Nếu hàng từ CNC qua: Thì mình chỉ việc sửa nếu sửa đc rồi đưa lại bên gia công tiếp tục gia công
@Scan_Repair_Data.post('/Insert_Scan_Repair_Data')
@swag_from('./docs/Scan_Repair_Data/Insert_Scan_Repair_Data.yaml')
def Insert_Scan_Repair_Data():
    try:
        MSNV = request.json['MSNV']
        KhuVuc = request.json['KhuVuc']
        Tram = request.json['Tram']
        DMC_Product = request.json['DMC_Product']
        Product_Type = request.json['Product_Type']
        
        # Thay vì chỉ lưu vô bảng dữ chính, mình sẽ lưu các bảng tạm của từng trạm
        print("insert into [QC].[dbo].[Scan_Repair_Test] values ('"+ MSNV +"', N'"+ KhuVuc +"', '"+ Tram +"', '"+ DMC_Product +"', '"+ Product_Type +"', '"+datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')+"')")
        cursor.execute("insert into [QC].[dbo].[Scan_Repair_Test] values ('"+ MSNV +"', N'"+ KhuVuc +"', '"+ Tram +"', '"+ DMC_Product +"', '"+ Product_Type +"', '"+datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')+"')")
        
        tail_table_names = {"Ngoại Quan": "NQ", "Pin Ren": "PR", "Kiểm Tra Ren": "KTR", "Gá Tổng Hợp": "GTH", "Kích Thước Khác": "KTK"}
        print("insert into [QC].[dbo].[Scan_Repair_"+tail_table_names[KhuVuc]+"] values ('"+ MSNV +"', '"+ Tram +"', '"+ DMC_Product +"', '"+ Product_Type +"', '"+datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')+"')")
        cursor.execute("insert into [QC].[dbo].[Scan_Repair_"+tail_table_names[KhuVuc]+"] values ('"+ MSNV +"', '"+ Tram +"', '"+ DMC_Product +"', '"+ Product_Type +"', '"+datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')+"')")

        conn.commit()
    except Exception as e:
        Systemp_log1(str(e), "Insert_Scan_Repair_Data").append_new_line()
        return jsonify({"Error": "Invalid request, please try again."})
    return jsonify('OK'), HTTP_201_CREATED

@Scan_Repair_Data.post('/Insert_Scan_Repair_Data_With_DateTime')
@swag_from('./docs/Scan_Repair_Data/Insert_Scan_Repair_Data_With_DateTime.yaml')
def Insert_Scan_Repair_Data_With_DateTime():
    try:
        MSNV = request.json['MSNV']
        KhuVuc = request.json['KhuVuc']
        Tram = request.json['Tram']
        DMC_Product = request.json['DMC_Product']
        Product_Type = request.json['Product_Type']
        DateTime = request.json['DateTime']

        print("insert into [QC].[dbo].[Scan_Repair_Test] values ('"+ MSNV +"', N'"+ KhuVuc +"', '"+ Tram +"', '"+ DMC_Product +"', '"+ Product_Type +"', '"+DateTime+"')")
        cursor.execute("insert into [QC].[dbo].[Scan_Repair_Test] values ('"+ MSNV +"', N'"+ KhuVuc +"', '"+ Tram +"', '"+ DMC_Product +"', '"+ Product_Type +"', '"+DateTime+"')")
        conn.commit()
    except Exception as e:
        Systemp_log1(str(e), "Insert_Scan_Repair_Data_With_DateTime").append_new_line()
        return jsonify({"Error": "Invalid request, please try again."})
    return jsonify('OK'), HTTP_201_CREATED

@Scan_Repair_Data.get("/Get_KhuVuc_OK_Product_TheoCa_New")
@swag_from("./docs/Scan_Repair_Data/Get_KhuVuc_OK_Product_TheoCa_New.yaml")
def Get_KhuVuc_OK_Product_TheoCa_New():
    try:
        result = None
        today = datetime.datetime.now()
        ytday = today - datetime.timedelta(days=1)
        if today.hour < 8 or today.hour >= 20:
            if today.hour < 8:
                print("select KhuVuc, Tram, count(distinct(DMC)) as count from [QC].[dbo].[Scan_Repair_Test] where TimeSave > '" + ytday.strftime("%Y-%m-%d 20:00:00'") + " group by KhuVuc, Tram")
                cursor.execute("select KhuVuc, Tram, count(distinct(DMC)) as count from [QC].[dbo].[Scan_Repair_Test] where TimeSave > '" + ytday.strftime("%Y-%m-%d 20:00:00'") + " group by KhuVuc, Tram")
                result = cursor.fetchall()
            elif today.hour >= 20:
                print("select KhuVuc, Tram, count(distinct(DMC)) as count from [QC].[dbo].[Scan_Repair_Test] where TimeSave > '" + today.strftime("%Y-%m-%d 20:00:00'") + " group by KhuVuc, Tram")
                cursor.execute("select KhuVuc, Tram, count(distinct(DMC)) as count from [QC].[dbo].[Scan_Repair_Test] where TimeSave > '" + today.strftime("%Y-%m-%d 20:00:00'") + " group by KhuVuc, Tram")
                result = cursor.fetchall()  
        else:
            print("select KhuVuc, Tram, count(distinct(DMC)) as count from [QC].[dbo].[Scan_Repair_Test] where TimeSave > '" + today.strftime("%Y-%m-%d 08:00:00'") + " group by KhuVuc, Tram")
            cursor.execute("select KhuVuc, Tram, count(distinct(DMC)) as count from [QC].[dbo].[Scan_Repair_Test] where TimeSave > '" + today.strftime("%Y-%m-%d 08:00:00'") + " group by KhuVuc, Tram")
            result = cursor.fetchall()

        # Đưa result về dạng json
        json_result = {}

        for idx in range(len(result)):
            if result[idx][0] != "Kiểm Tra Ren":
                json_result[result[idx][0]+' '+result[idx][1].strip()] = result[idx][2]
            else:
                if result[idx][0] not in json_result:
                    json_result[result[idx][0]] = result[idx][2]
                else:
                    json_result[result[idx][0]] = json_result[result[idx][0]] + result[idx][2]

        print(json_result)

        # Cập nhật sự thay đổi của table
        cursor.commit()

    except Exception as e:
        Systemp_log1(str(e), "Get_KhuVuc_OK_Product_TheoCa_New").append_new_line()
        return jsonify({"Error": "Invalid request, please try again."})
    return jsonify(json_result), HTTP_200_OK

@Scan_Repair_Data.post('/Check_DMC_In_Previous_Stage')
@swag_from('./docs/Scan_Repair_Data/Check_DMC_In_Previous_Stage.yaml')
def Check_DMC_In_Previous_Stage():
    try:
        StageName = request.json['StageName']
        DMC = request.json['DMC']

        result = {'count': 0}

        if StageName == 'Kín Khí Chamfer':
            print("select COUNT(DISTINCT barcode) AS NUM_DMC from [QC].[dbo].[air_tight_chamfer] where barcode ='" + DMC + "'")
            cursor.execute("select COUNT(DISTINCT barcode) AS NUM_DMC from [QC].[dbo].[air_tight_chamfer] where barcode ='" + DMC + "'")
            result = cursor.fetchone()
        elif StageName == 'Air Gauge':
            print("select COUNT(DISTINCT DMC) AS NUM_DMC from [QC].[dbo].[airgauge] where DMC ='" + DMC + "'")
            cursor.execute("select COUNT(DISTINCT DMC) AS NUM_DMC from [QC].[dbo].[airgauge] where DMC ='" + DMC + "'")
            result = cursor.fetchone()
        else:
            tail_table_names = {"Ngoại Quan": "NQ", "Pin Ren": "PR", "Kiểm Tra Ren": "KTR", "Gá Tổng Hợp": "GTH", "Kích Thước Khác": "KTK"}
            # Thưc thi câu lệnh
            print("select COUNT(DISTINCT DMC) AS NUM_DMC from [QC].[dbo].[Scan_Repair_"+tail_table_names[StageName]+"] where DMC  = '" + DMC + "'")
            cursor.execute("select COUNT(DISTINCT DMC) AS NUM_DMC from [QC].[dbo].[Scan_Repair_"+tail_table_names[StageName]+"] where DMC  = '" + DMC + "'")
            result = cursor.fetchone()
            
        count = result[0]

        # Cập nhật sự thay đổi của table
        cursor.commit()
    except Exception as e:
        Systemp_log1(str(e), "Check_DMC_In_Previous_Stage").append_new_line()
        return jsonify({"Error": "Invalid request, please try again."})
    return jsonify({'count': count}), HTTP_201_CREATED
