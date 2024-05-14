from os import access
from constants.http_status_code import HTTP_200_OK, HTTP_201_CREATED, HTTP_400_BAD_REQUEST, HTTP_401_UNAUTHORIZED, HTTP_409_CONFLICT
from flask import Blueprint, app, request, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from flask_jwt_extended import jwt_required, create_access_token, create_refresh_token, get_jwt_identity
from flasgger import swag_from
from database import *
from ERROR import *
from auth_middleware import *

permissions = Blueprint("permissions", __name__, url_prefix="/api/v1/permissions")

# get all permissions
@permissions.get('')
@swag_from('./docs/permissions/permissions.yaml')
@token_required_and_permissions
def get_permissions(role, permissions):
    try:
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234;Database=QC; Trusted_Connection=No;',timeout=1)
        cursor = conn.cursor()

        # Check xem có phải Developer không?
        if role < 9999:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 46
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

        print("select * from [QC].[dbo].[Permission_Name]")
        cursor.execute("select * from [QC].[dbo].[Permission_Name]")
        all_records =cursor.fetchall()

        # Nếu lấy dữ liệu ra trống
        if all_records == None:
            ret = {
                'status':False,
                'message':'Not exist data!'
            }
            return jsonify(ret),400
        
        # Nếu có máy
        ret = {
                'status':True,
                'message':'Success',
                'data':[]
            }
        
        for item in all_records:
            id, permission_name = item
            ret['data'].append({
                'id':id,
                'permissionName': permission_name
            })

        ret['data'].sort(key=lambda item:item['id'], reverse=False)

        return jsonify(ret)
    
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        Systemp_log1(traceback.format_exc(), "get_permissions").append_new_line()
        return jsonify(ret),500

# get all roles
@permissions.get('/roles')
@swag_from('./docs/permissions/roles.yaml')
@token_required_and_permissions
def get_roles(role, permissions):
    try:
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234;Database=QC; Trusted_Connection=No;',timeout=1)
        cursor = conn.cursor()

        # Check xem có phải Developer không?
        if role < 9999:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 46
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

        print("select * from [QC].[dbo].[Permission_Users]")
        cursor.execute("select * from [QC].[dbo].[Permission_Users]")
        all_records =cursor.fetchall()

        # Nếu lấy dữ liệu ra trống
        if all_records == None:
            ret = {
                'status':False,
                'message':'Not exist data!'
            }
            return jsonify(ret),400
        
        # Nếu có máy
        ret = {
                'status':True,
                'message':'Success',
                'data':[]
            }
        
        for item in all_records:
            role, role_name, group, permissions = item
            ret['data'].append({
                'role':role,
                'roleName': role_name,
                'group': group,
                'permissions': permissions
            })

        ret['data'].sort(key=lambda item:item['role'], reverse=False)

        return jsonify(ret)
    
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        Systemp_log1(traceback.format_exc(), "get_roles").append_new_line()
        return jsonify(ret),500
    
# add new permission
@permissions.post('/add')
@swag_from('./docs/permissions/add_new_permission.yaml')
@token_required_and_permissions
def add_new_permission(role, permissions):
    try:
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234;Database=QC; Trusted_Connection=No;',timeout=1)
        cursor = conn.cursor()

        # Check xem có phải Manager không?
        if role < 9999:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 46
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

        permission_name = request.json['permissionName']

        # check if permission name is duplicated
        cursor.execute("select * from [QC].[dbo].[Permission_Name] where PermissionName = '" + permission_name + "'")
        count_record_dups = cursor.fetchall()

        if len(count_record_dups) > 0:
            return jsonify({
                        'status':False,
                        'message':'This permission already exists!'
                    })

        # get biggest id in permission table
        cursor.execute("select top(1) id from [QC].[dbo].[Permission_Name] order by id desc")
        biggest_id = cursor.fetchone()

        if biggest_id is None or len(biggest_id) == 0:
            biggest_id = [0]
        biggest_id = biggest_id[0]

        print("insert into [QC].[dbo].[Permission_Name]"
            " values ('" + str(biggest_id + 1) + "', '" + permission_name + "')")
        cursor.execute("insert into [QC].[dbo].[Permission_Name]"
            " values ('" + str(biggest_id + 1) + "', '" + permission_name + "')")
        
        # commit
        conn.commit()

        # if add new permission is ok
        ret = {
            'status':True,
            'message':'Add new permission successfully!',
            'data': []
        }

        # show all permission after add a new
        cursor.execute("select * from [QC].[dbo].[Permission_Name]")
        permission_name_updated = cursor.fetchall()

        for item in permission_name_updated:
            id, permission_name = item
            ret['data'].append({
                'id':id,
                'permissionName': permission_name
            })

        ret['data'].sort(key=lambda item:item['id'], reverse=False)

        return jsonify(ret), HTTP_201_CREATED
    except Exception as e:
        ret = {
            'status':False,
            'message':'Failed to add new permission!'
        }
        Systemp_log1(str(e), "add_new_permission").append_new_line()
        return jsonify(ret),400
    
# add new roles
@permissions.post('/roles/add')
@swag_from('./docs/permissions/add_new_roles.yaml')
@token_required_and_permissions
def add_new_roles(role, permissions):
    try:
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234;Database=QC; Trusted_Connection=No;',timeout=1)
        cursor = conn.cursor()

        # Check xem có phải Developer không?
        if role < 9999:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 46
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

        roleName = request.json['roleName']
        group = request.json['group']

        # check if role name is duplicated
        cursor.execute("select * from [QC].[dbo].[Permission_Users] where RoleName = '" + roleName + "'")
        count_record_dups = cursor.fetchall()

        if len(count_record_dups) > 0:
            return jsonify({
                        'status':False,
                        'message':'This role already exists!'
                    })

        # get biggest id in permission user table
        print("select top(1) Role from [QC].[dbo].[Permission_Users] where [Group] = '"+ group +"' order by Role desc")
        cursor.execute("select top(1) Role from [QC].[dbo].[Permission_Users] where [Group] = '"+ group +"' order by Role desc")
        biggest_id = cursor.fetchone()

        if biggest_id is None or len(biggest_id) == 0:
            biggest_id = [0]
        biggest_id = biggest_id[0]
        
        cursor.execute("insert into [QC].[dbo].[Permission_Users] values (?,?,?,?)",
                        str(biggest_id + 1),
                        roleName,
                        group,
                        None)
        
        # commit
        conn.commit()

        # if add new permission is ok
        ret = {
            'status':True,
            'message':'Add new role successfully!',
            'data': []
        }

        # show all permission after add a new
        cursor.execute("select * from [QC].[dbo].[Permission_Users]")
        role_name_updated = cursor.fetchall()

        for item in role_name_updated:
            id, role_name, group, permissions = item
            ret['data'].append({
                'role':id,
                'roleName': role_name,
                'group': group,
                'permissions': permissions
            })

        ret['data'].sort(key=lambda item:item['role'], reverse=False)

        return jsonify(ret), HTTP_201_CREATED
    except Exception as e:
        ret = {
            'status':False,
            'message':'Failed to add new role!'
        }
        11(str(e), "add_new_role").append_new_line()
        return jsonify(ret),400

# update permissions
@permissions.put('/roles/update_permissions')
@swag_from('./docs/permissions/update_permissions.yaml')
@token_required_and_permissions
def update_permissions(role, permissions):
    try:
        # Tạo cusor để kết nối với database
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234;Database=QC; Trusted_Connection=No;',timeout=1)
        cursor = conn.cursor()

        # Check xem có phải Developer không?
        if role < 9999:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 46
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
        
        data = request.json['data']

        for item in data:
            print("Update [QC].[dbo].[Permission_Users] set Permissions = '"+item["permissions"]+"' where Role ='"+str(item["role"])+"'")
            cursor.execute("Update [QC].[dbo].[Permission_Users] set Permissions = '"+item["permissions"]+"' where Role ='"+str(item["role"])+"'")
            conn.commit()

        ret = {
            'status':True,
            'message':'Update permissions successfully!',
            'data':[]
        }

        # show all permissions after update
        cursor.execute("select * from [QC].[dbo].[Permission_Users]")
        role_name_updated = cursor.fetchall()

        for item in role_name_updated:
            id, role_name, group, permissions = item
            print(type(permissions))
            ret['data'].append({
                'role': id,
                'roleName': role_name,
                'permissions': permissions if permissions is None else permissions.strip()
            })

        ret['data'].sort(key=lambda item:item['role'], reverse=False)

        return jsonify(ret), HTTP_201_CREATED
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        Systemp_log1(str(e), "update_permissions").append_new_line()
        return jsonify(ret), 500
    
# update role name
@permissions.put('/roles/update_name')
@swag_from('./docs/permissions/update_role_name.yaml')
@token_required_and_permissions
def update_role_name(role, permissions):
    try:
        # Tạo cusor để kết nối với database
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234;Database=QC; Trusted_Connection=No;',timeout=1)
        cursor = conn.cursor()
        
        # Check xem có phải Developer không?
        if role < 9999:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 46
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

        role = request.json['role']
        new_role_name = request.json['newName']

        print("Update [QC].[dbo].[Permission_Users] set RoleName = '"+new_role_name+"' where Role ='"+str(role)+"'")
        cursor.execute("Update [QC].[dbo].[Permission_Users] set RoleName = '"+new_role_name+"' where Role ='"+str(role)+"'")
        
        conn.commit()

        ret = {
            'status':True,
            'message':'Update role name successfully!',
            'data':[]
        }

        # show all permissions after update
        cursor.execute("select * from [QC].[dbo].[Permission_Users]")
        role_name_updated = cursor.fetchall()

        for item in role_name_updated:
            id, role_name, group, permissions = item
            print(type(permissions))
            ret['data'].append({
                'role': id,
                'roleName': role_name if role_name is None else role_name.strip(),
                'permissions': permissions,
            })

        ret['data'].sort(key=lambda item:item['role'], reverse=False)

        return jsonify(ret), HTTP_201_CREATED
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        Systemp_log1(str(e), "update_role_name").append_new_line()
        return jsonify(ret), 500
    
# update permission name
@permissions.put('/update')
@swag_from('./docs/permissions/update_permission_name.yaml')
@token_required_and_permissions
def update_permission_name(role, permissions):
    try:
        # Tạo cusor để kết nối với database
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234;Database=QC; Trusted_Connection=No;',timeout=1)
        cursor = conn.cursor()
        
        # Check xem có phải Developer không?
        if role < 9999:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 46
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

        id = request.json['id']
        new_permission_name = request.json['newName']

        print("Update [QC].[dbo].[Permission_Name] set PermissionName = '"+new_permission_name+"' where Id ='"+str(id)+"'")
        cursor.execute("Update [QC].[dbo].[Permission_Name] set PermissionName = '"+new_permission_name+"' where Id ='"+str(id)+"'")
        
        conn.commit()

        ret = {
            'status':True,
            'message':'Update permission name successfully!',
            'data':[]
        }

        # show all permissions after update
        cursor.execute("select * from [QC].[dbo].[Permission_Name]")
        permission_name_updated = cursor.fetchall()

        for item in permission_name_updated:
            id, permission_name = item
            ret['data'].append({
                'id': id,
                'permissionName': permission_name if permission_name is None else permission_name.strip()
            })

        ret['data'].sort(key=lambda item:item['id'], reverse=False)

        return jsonify(ret), HTTP_201_CREATED
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        Systemp_log1(str(e), "update_permission_name").append_new_line()
        return jsonify(ret), 500
    
@permissions.delete('/delete')
@swag_from('./docs/permissions/delete_permission.yaml')
@token_required_and_permissions
def delete_permission(role, permissions):
    try:
        # Tạo cusor để kết nối với database
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234;Database=QC; Trusted_Connection=No;',timeout=1)
        cursor = conn.cursor()

        # Check xem có phải Developer không?
        if role < 9999:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 46
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
        
        id = request.json['id']

        # check if arbor_code is not exist
        cursor.execute("select * from [QC].[dbo].[Permission_Name] where Id = '" + str(id) + "'")
        count_record_dups = cursor.fetchall()
        if count_record_dups == None or len(count_record_dups) == 0:
            return jsonify({
                        'status':False,
                        'message':'This permission does not exist!'
                    })  
        
        print("delete from [QC].[dbo].[Permission_Name] where Id = '" + str(id) + "'")
        cursor.execute("delete from [QC].[dbo].[Permission_Name] where Id = '" + str(id) + "'")
        
        conn.commit()

        # if insert data to Vending table successfully
        ret = {
            'status':True,
            'message':'Deleted permission successfully!',
            'data': []
        }

        # change ids of table which > id already delete
        print("select * from [QC].[dbo].[Permission_Name] where Id > "+str(id)+"")
        cursor.execute("select * from [QC].[dbo].[Permission_Name] where Id > "+str(id)+"")
        higher_ids = cursor.fetchall()

        for item in higher_ids:
            id_temp, permission_name = item

            cursor.execute("update [QC].[dbo].[Permission_Name] set Id = '"+ str(id_temp - 1) +"' where PermissionName = '"+ permission_name +"'")
            conn.commit()

        # show all permissions after delete
        cursor.execute("select * from [QC].[dbo].[Permission_Name]")
        permission_name_deleted = cursor.fetchall()

        for item in permission_name_deleted:
            id, permission_name = item
            ret['data'].append({
                'id': id,
                'permissionName': permission_name if permission_name is None else permission_name.strip()
            })
        
        ret['data'].sort(key=lambda item:item['id'], reverse=False)

        return jsonify(ret), HTTP_201_CREATED
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        Systemp_log1(str(e), "delete_permission").append_new_line()
        return jsonify(ret), 500
    
@permissions.delete('/roles/delete')
@swag_from('./docs/permissions/delete_role.yaml')
@token_required_and_permissions
def delete_role(role, permissions):
    try:
        # Tạo cusor để kết nối với database
        conn = pyodbc.connect('Driver={SQL Server}; Server=192.168.8.21; uid=sa; pwd=1234;Database=QC; Trusted_Connection=No;',timeout=1)
        cursor = conn.cursor()

        # Check xem có phải Developer không?
        if role < 9999:
            ret = {
                'status':False,
                'message':'Sorry, permission denied!'
            }
            return jsonify(ret),401

        # Check xem có permission không?
        id_permission = 46
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
        
        role_id = request.json['role']

        # check if arbor_code is not exist
        cursor.execute("select * from [QC].[dbo].[Permission_Users] where Role = '" + str(role_id) + "'")
        count_record_dups = cursor.fetchall()
        if count_record_dups == None or len(count_record_dups) == 0:
            return jsonify({
                        'status':False,
                        'message':'This role does not exist!'
                    })  
        
        print("delete from [QC].[dbo].[Permission_Users] where Role = '" + str(role_id) + "'")
        cursor.execute("delete from [QC].[dbo].[Permission_Users] where Role = '" + str(role_id) + "'")
        
        conn.commit()

        # if insert data to Vending table successfully
        ret = {
            'status':True,
            'message':'Deleted role successfully!',
            'data': []
        }

        # show all roles after delete
        cursor.execute("select * from [QC].[dbo].[Permission_Users]")
        role_name_updated = cursor.fetchall()

        for item in role_name_updated:
            id, role_name, group, permissions = item
            ret['data'].append({
                'role': id,
                'group': group,
                'roleName': role_name if role_name is None else role_name.strip(),
                'permissions': permissions,
            })

        return jsonify(ret), HTTP_201_CREATED
    except Exception as e:
        ret = {
            'status':False,
            'message': str(e)
        }
        Systemp_log1(str(e), "delete_role").append_new_line()
        return jsonify(ret), 500