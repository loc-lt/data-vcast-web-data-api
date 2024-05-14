from os import access
from constants.http_status_code import HTTP_200_OK, HTTP_201_CREATED, HTTP_400_BAD_REQUEST, HTTP_401_UNAUTHORIZED, HTTP_409_CONFLICT
from flask import Blueprint, app, request, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from flask_jwt_extended import jwt_required, create_access_token, create_refresh_token, get_jwt_identity
from flasgger import swag_from
from database import *
from ERROR import *
import hashlib
import bcrypt
import jwt
from flask import * 
from flask import current_app, session
import traceback
from auth_middleware import *

users = Blueprint("users", __name__, url_prefix="/api/v1/users")

def check_exist(username):
    conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234; Database=QC; Trusted_Connection=No;', timeout=1)
    cursor = conn.cursor()

    query = "SELECT * FROM [QC].[dbo].[Web_Data_User] WHERE Username =  '" +username+ "'"
    
    cursor.execute(query)
    user_list =  cursor.fetchall()
    
    if len(user_list) > 0:
        return True
    return False

def add_user(username, password, display_name):
    conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234; Database=QC; Trusted_Connection=No;', timeout=1)
    cursor = conn.cursor()

    query = "INSERT INTO [QC].[dbo].[Web_Data_User](Username, DisplayName, HashPassword, Role) VALUES('"+username+"', N'"+display_name+"', '"+password+"', 0)"
    try:
        cursor.execute(query)
        conn.commit()
        return True
    except pyodbc.IntegrityError:
        return False
    
@users.post("/register")
@swag_from("./docs/user/register.yaml")
def register():
    try:
        username = request.json['userName']
        display_name = request.json['displayName']

        if check_exist(username):
            ret = {
                    'status': False,
                    'message':'This username already exists!'
                }
            return jsonify(ret), 400

        # converting password to array of bytes 
        bytes = request.json["password"].encode('utf-8') 

        # generating the salt 
        salt = bcrypt.gensalt() 
        
        # Hashing the password 
        hash_password = bcrypt.hashpw(bytes, salt)

        if add_user(username, hash_password.decode('utf-8'), display_name):
            ret = {
                    'status': True,
                    'message':'Register new account successfully!'
                }
            return jsonify(ret), 200
        
        ret = {
                'status': False,
                
                'message':'Register new account failed!'
            }
        return jsonify(ret), 400
    
    except Exception as e:
        ret = {
            'status': False,
            'message': str(e)
        }
        return jsonify(ret), 500
    
@users.put("/update")
@swag_from("./docs/user/update_role.yaml")
@token_required_and_permissions
def update_role(role, permissions):
    try:
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234; Database=QC; Trusted_Connection=No;', timeout=1)
        cursor = conn.cursor()

        # Check xem có phải Admin không?
        if role < 9000:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 45
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

        username = request.json['userName']
        display_name = request.json['displayName']
        role = request.json['role']

        if not check_exist(username):
            ret = {
                    'status': False,
                    'message':'This username not exists!'
                }
            return jsonify(ret), 400

        cursor.execute("update [QC].[dbo].[Web_Data_User] set DisplayName = N'"+ display_name +"', Role = '"+ str(role) +"' where Username = '"+ username +"'")
        conn.commit()

        ret = {
                'status': True,
                'message':'Update user successfully!',
                'data': {'userName': username, 'displayName': display_name, 'role': role}
            }
        return jsonify(ret), 200

    except Exception as e:
        ret = {
            'status': False,
            'message': str(e)
        }
        return jsonify(ret), 500
    
@users.post("/login")
@swag_from("./docs/user/login.yaml")
def login():
    try:
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234; Database=QC; Trusted_Connection=No;', timeout=1)
        cursor = conn.cursor()

        # xử lý dữ liệu đầu vào 
        username = request.json["userName"]

        if not check_exist(username):
            ret = {
                    'status': False,
                    'message':'Username or password is incorrect!'
                }
            return jsonify(ret), 400

        # encoding user password 
        hash_password = request.json["password"].encode('utf-8')

        # từ username lấy lên hashword từ database
        print("select HashPassword, Role from [QC].[dbo].[Web_Data_User] where Username = '"+ username +"'")
        cursor.execute("select HashPassword, Role, DisplayName from [QC].[dbo].[Web_Data_User] where Username = '"+ username +"'")
        hash_pw_role = cursor.fetchone()

        if len(hash_pw_role) > 0:
            hash_password_db, role, display_name = hash_pw_role
        else:
            return jsonify({
                            'status':False,
                            'message':'Username or password is incorrect!'
                            }), 400 

        # checking password
        result = bcrypt.checkpw(hash_password, hash_password_db.encode('utf-8'))
        
        if result:
            session['logged_in'] = True
            
            # if check passwork successfully -> get permissions
            cursor.execute("select Permissions from [QC].[dbo].[Permission_Users] where Role = '"+str(role)+"'")
            permissions = cursor.fetchone()
            print(permissions)

            token = jwt.encode({
                'user': username,
                'role': role,
                'expiration': (datetime.datetime.now() + datetime.timedelta(hours=12)).timestamp(),
                'permissions': permissions[0].strip()
            }, current_app.config['SECRET_KEY'], algorithm="HS256")

            # Lưu token vào Redis
            redis_client.set(username, token)
            
            print(token)
            print(redis_client.keys())

            ret = {
                    'status': True,
                    'message':'Login New successfully!',
                    'token': token
                }
            
            return jsonify(ret), 200

        return jsonify({
                        'status':False,
                        'message':'Username or password is incorrect!'
                        }), 400 
    except Exception as e:
        ret = {
            'status': False,
            'message': str(e)
        }
        Systemp_log1(traceback.format_exc(), "login").append_new_line()
        return jsonify(ret), 500
    
@users.get("")
@swag_from("./docs/user/users_infor.yaml")
@token_required_and_permissions
def users_infor(role, permissions):
    try:
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234; Database=QC; Trusted_Connection=No;', timeout=1)
        cursor = conn.cursor()

        # Check xem có phải Admin không?
        if role < 9000:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 45
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

        cursor.execute("select Username, DisplayName, Role from [QC].[dbo].[Web_Data_User]")
        all_users = cursor.fetchall()
        conn.close()
        
        # Neu lay du lieu ra trong
        if all_users == None or len(all_users) == 0:
            ret = {
                'status':False,
                'message':'Not Exist Data!'
            }
            return jsonify(ret),400
        
        # Nếu có máy
        ret = {
                'status':True,
                'message':'Success',
                'data':[]
            }
        
        for item in all_users:
            username, display_name, role = item
            ret['data'].append({
                'userName':username.strip(),
                'displayName':display_name,
                'role':role,
            })

        return jsonify(ret)
    except Exception as e:
        ret = {
            'status': False,
            'message': str(e)
        }
        Systemp_log1(traceback.format_exc(), "get_users_infor").append_new_line()
        return jsonify(ret), 500
    
@users.post("/delete")
@swag_from("./docs/user/delete_user.yaml")
@token_required_and_permissions
def delete_user(role, permissions):
    try:
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234; Database=QC; Trusted_Connection=No;', timeout=1)
        cursor = conn.cursor()

        # Check xem có phải Manager không?
        if role < 9000:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 45
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
        
        username = request.json['userName']

        if not check_exist(username):
            ret = {
                    'status': False,
                    'message':'This username not exists!'
                }
            return jsonify(ret), 400

        cursor.execute("delete from [QC].[dbo].[Web_Data_User] where Username = '"+ username +"'")
        conn.commit()

        ret = {
                'status': True,
                'message':'Delete user successfully!'
            }
        return jsonify(ret), 200

    except Exception as e:
        ret = {
            'status': False,
            'message': str(e)
        }
        Systemp_log1(traceback.format_exc(), "delete_user").append_new_line()
        return jsonify(ret), 500
    
# Hàm logout
@users.post("/logout")
@swag_from("./docs/user/logout.yaml")
def logout():
    try:
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401

        # Giải mã token để lấy username
        decoded_token = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
        username = decoded_token['user']

        # Xóa token từ Redis
        redis_client.delete(username)

        # Xóa session
        session.pop('logged_in', None)

        ret = {
            'status': True,
            'message': 'Logout successfully!'
        }
        return jsonify(ret), 200

    except Exception as e:
        ret = {
            'status': False,
            'message': str(e)
        }
        Systemp_log1(traceback.format_exc(), "logout").append_new_line()
        return jsonify(ret), 500
    
# Hàm validate
@users.get("/validate")
@swag_from("./docs/user/validate.yaml")
def validate():
    try:
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401

        if "Bearer " in token:
            token = token.replace("Bearer ", "")

        # Giải mã token để lấy username
        decoded_token = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
        expired_time = decoded_token['expiration']

        if datetime.datetime.now().timestamp() <= expired_time:
            ret = {
                'status': True,
                'message': 'Validate token successfully!',
                'data': expired_time - datetime.datetime.now().timestamp()
            }
            return jsonify(ret), 200

        ret = {
            'status': False,
            'message': 'Validate token fail!',
            'data': expired_time - datetime.datetime.now().timestamp()
        }
        return jsonify(ret), 403

    except Exception as e:
        ret = {
            'status': False,
            'message': str(e)
        }
        Systemp_log1(traceback.format_exc(), "validate_token").append_new_line()
        return jsonify(ret), 500