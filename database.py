from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow,fields
from datetime import datetime
import string
import random
import pyodbc
from pyodbc import Error
import time
ma = Marshmallow()
while True:
    try:
        conn = pyodbc.connect(
            'Driver={SQL Server}; Server=192.168.8.127; uid=sa; pwd=1234;Database=KnifeCNCSystem; Trusted_Connection=No;')
        cursor = conn.cursor()
        break
    except Error as err:
        print(f"Error1: '{err}'")
        time.sleep(0.5)
class KnifeCNCSystem(ma.Schema):
    class Meta:
        fields=('Machine','ToolHolder','Length')
KnifeCNC=KnifeCNCSystem()
Knife_CNC=KnifeCNCSystem(many=True)

