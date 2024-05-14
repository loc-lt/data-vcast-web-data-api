from functools import wraps
import jwt
from flask import request, abort
from flask.json import jsonify
from flask import current_app 
from ERROR import *
from fakeredis import FakeStrictRedis
import traceback

# Kết nối tới Redis server
redis_client = FakeStrictRedis()

def token_required(func):
    @wraps(func)
    def decorated(*args, **kwargs):
        # Lấy token từ request.header
        token = None
        if "Authorization" in request.headers:
            token = request.headers["Authorization"].split(" ")[1]
        
        # Kiểm tra xem token có tồn tại
        if not token:
            ret = {
                'status':False,
                'message':'Sorry, token is missing!'
            }
            return jsonify(ret),403

        try:
            # In ra token và secret key
            print(token)
            print(current_app.config['SECRET_KEY'])

            if len(token.split('.')) == 1:
                ret = {
                    'status':False,
                    'message':'Sorry, invalid token!'
                }
                return jsonify(ret),403

            payload = jwt.decode(token, current_app.config['SECRET_KEY'],algorithms=["HS256"])

            # In ra payload sau khi decode
            print(payload)
            
            # Kiểm tra xem payload lấy vê có None hay không?
            if payload is not None:
                if datetime.datetime.now().timestamp() <= payload['expiration']:
                    # Trả về func với dữ liệu được truyền vào
                    return func(*args, **kwargs)
                elif datetime.datetime.now().timestamp() > payload['expiration']:
                    ret = {
                        'status':False,
                        'message':'Sorry, token expired!'
                    }
                    return jsonify(ret),403
                else:
                    keys = redis_client.keys('*')
                
                    # Lấy lại giá trị cho mỗi khóa
                    data = {}

                    for key in keys:
                        data[key.decode('utf-8')] = redis_client.get(key).decode('utf-8')

                    if token not in data.values():
                        ret = {
                            'status':False,
                            'message':'Sorry, token is not exist!'
                        }
                        return jsonify(ret),403

            else:
                ret = {
                    'status':False,
                    'message':'Sorry, invalid token!'
                }
                return jsonify(ret),403
        except Exception as e:
            ret = {
                'status':False,
                'message':str(e)
            }
            Systemp_log1(traceback.format_exc(), "token_required").append_new_line()
            return jsonify(ret),500
        
    return decorated

def token_required_and_admin(func):
    @wraps(func)
    def decorated(*args, **kwargs):
        # Lấy token từ request.header
        token = None
        if "Authorization" in request.headers:
            token = request.headers["Authorization"].split(" ")[1]
        
        # Kiểm tra xem token có tồn tại
        if not token:
            ret = {
                'status':False,
                'message':'Sorry, token is missing!'
            }
            return jsonify(ret),403

        try:
            # In ra token và secret key
            print(token)
            print(current_app.config['SECRET_KEY'])

            payload = jwt.decode(token, current_app.config['SECRET_KEY'],algorithms=["HS256"])

            # In ra payload sau khi decode
            print(payload)
            
            # Kiểm tra xem payload lấy vê có None hay không?
            if payload is not None:
                if datetime.datetime.now().timestamp() <= payload['expiration']:
                    # Trả về func với dữ liệu được truyền vào
                    return func(*args, **kwargs, role = payload['role'])
                elif datetime.datetime.now().timestamp() > payload['expiration']:
                    ret = {
                        'status':False,
                        'message':'Sorry, token expired!'
                    }
                    return jsonify(ret),403
                else:
                    keys = redis_client.keys('*')
                
                    # Lấy lại giá trị cho mỗi khóa
                    data = {}

                    for key in keys:
                        data[key.decode('utf-8')] = redis_client.get(key).decode('utf-8')

                    if token not in data.values():
                        ret = {
                            'status':False,
                            'message':'Sorry, token is not exist!'
                        }
                        return jsonify(ret),403
            else:
                ret = {
                    'status':False,
                    'message':'Sorry, invalid token!'
                }
                return jsonify(ret),403
        except Exception as e:
            ret = {
                'status':False,
                'message':str(e)
            }
            Systemp_log1(traceback.format_exc(), "token_required").append_new_line()
            return jsonify(ret),500
        
    return decorated

def token_required_and_permissions(func):
    @wraps(func)
    def decorated(*args, **kwargs):
        # Lấy token từ request.header
        token = None
        if "Authorization" in request.headers:
            token = request.headers["Authorization"].split(" ")[1]
        
        # Kiểm tra xem token có tồn tại
        if not token:
            ret = {
                'status':False,
                'message':'Sorry, token is missing!'
            }
            return jsonify(ret),403

        try:
            # In ra token và secret key
            print(token)
            print(current_app.config['SECRET_KEY'])

            payload = jwt.decode(token, current_app.config['SECRET_KEY'],algorithms=["HS256"])

            # In ra payload sau khi decode
            print(payload)
            
            # Kiểm tra xem payload lấy vê có None hay không?
            if payload is not None:
                if datetime.datetime.now().timestamp() <= payload['expiration']:
                    # Trả về func với dữ liệu được truyền vào
                    return func(*args, **kwargs, role = payload['role'], permissions = payload['permissions'])
                elif datetime.datetime.now().timestamp() > payload['expiration']:
                    ret = {
                        'status':False,
                        'message':'Sorry, token expired!'
                    }
                    return jsonify(ret),403
                else:
                    keys = redis_client.keys('*')
                
                    # Lấy lại giá trị cho mỗi khóa
                    data = {}

                    for key in keys:
                        data[key.decode('utf-8')] = redis_client.get(key).decode('utf-8')

                    if token not in data.values():
                        ret = {
                            'status':False,
                            'message':'Sorry, token is not exist!'
                        }
                        return jsonify(ret),403
            else:
                ret = {
                    'status':False,
                    'message':'Sorry, invalid token!'
                }
                return jsonify(ret),403
        except Exception as e:
            ret = {
                'status':False,
                'message':str(e)
            }
            Systemp_log1(traceback.format_exc(), "token_required_and_permissions").append_new_line()
            return jsonify(ret),500
        
    return decorated