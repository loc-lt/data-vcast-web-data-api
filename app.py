from flask.json import jsonify
from constants.http_status_code import HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR
from flask import Flask, config, redirect
import os
from flask_jwt_extended import JWTManager
from flasgger import Swagger, swag_from
from config.swagger import template, swagger_config
from flask_cors import CORS
from database import *
from temphumid import temphumid
from users import users
from CMM import CMM
from electrical import electrical_root
from heat_treatment import heat_treatment
from chemical import chemical
from lwm import lwm
from products import products
from Scan_Repair_Data import Scan_Repair_Data
from permissions import permissions

app = Flask(__name__, instance_relative_config=True)
app.config.from_mapping(
            SECRET_KEY=os.environ.get("SECRET_KEY") or '154281130814958933425240769184967185190',
            JWT_SECRET_KEY=os.environ.get('JWT_SECRET_KEY'),
            SWAGGER={
                'title': "Bookmarks API",
                'uiversion': 3
            }
        )

ma.app=app
ma.init_app(app)
JWTManager(app)
CORS(app)

app.register_blueprint(temphumid)
app.register_blueprint(users)
app.register_blueprint(CMM)
app.register_blueprint(electrical_root)
app.register_blueprint(heat_treatment)
app.register_blueprint(chemical)
app.register_blueprint(lwm)
app.register_blueprint(products)
app.register_blueprint(Scan_Repair_Data)
app.register_blueprint(permissions)

Swagger(app, config=swagger_config, template=template)

@app.errorhandler(HTTP_404_NOT_FOUND)
def handle_404(e):
    return jsonify({'error': 'Not found'}), HTTP_404_NOT_FOUND
@app.errorhandler(HTTP_500_INTERNAL_SERVER_ERROR)
def handle_500(e):
    return jsonify({'error': 'Something went wrong, we are working on it'}), HTTP_500_INTERNAL_SERVER_ERROR

# def create_app(test_config=None):
    # return app
if __name__ == "__main__":
    app.run(host='0.0.0.0',debug=True,port=5000)
