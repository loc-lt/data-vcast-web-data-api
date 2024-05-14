# # # import binascii
# # # list1=[]
# # # th="MAN-A2012003"
# # # t=th[-8:]
# # # print(t)
# # # i0 = binascii.hexlify(t[1:2].encode() + t[0:1].encode())
# # # i1 = binascii.hexlify(t[3:4].encode() + t[2:3].encode())
# # # i2 = binascii.hexlify(t[5:6].encode() + t[4:5].encode())
# # # i3 = binascii.hexlify(t[7:8].encode() + t[6:7].encode())
# # # encod=[i0,i1,i2,i3]
# # # for j in encod:
# # #     t = int(j, 16)
# # #     list1.append((t))

# # a = {1: 'a', 2: 'b'}
# # for item in a.items():
# #     print(item[0])

# # # list1 = [{1, 'a'}, {2, 'b'}]
# # # list1.sort(key=lambda item:item[1], reverse=False)

# def check_null(string_value):
#     # print(type(string_value))
#     if string_value == None:
#         return 'NULL'
#     return "'" +str(string_value) +"'"
# print(check_null('abc'))
import cx_Oracle

# Replace 'your_username', 'your_password', 'your_host:port/service' with your actual database information
dsn_tns = cx_Oracle.makedsn('192.168.0.211', '1521', service_name='topprod')
connection = cx_Oracle.connect(user='app', password='app#22979313', dsn=dsn_tns)

# Create a cursor
cursor = connection.cursor()

# Example SELECT query
query = "SELECT TRIM(IMB01),SUM(TRIM(CASE WHEN IMB218 = 0 THEN IMB118 ELSE IMB218 END )),SUM(TRIM(IMG10)) FROM vc.IMB_FILE IMB LEFT JOIN vc.IMG_FILE IMG ON IMB.IMB01 = IMG.IMG01 WHERE (IMB01 like 'FGB%' OR IMB01 ='FGDB04-VBMT110304HQ')  GROUP BY IMB01"
cursor.execute(query)

a = [
          "FGBA10-10.0X90",
          "FGBD01-4EN-D090-L075",
          "FGBD04-SCET050204",
          "FGBA05-4X60",
          "FGBD01-4EN-EL20-8.0",
          "FGBDA1-PR1535NA",
          "FGBDA2-TPGH-090204L",
          "WNMX060308-SR LP1080",
          "FGBD01-4EN-4.02X0.2R",
          "FGBA01-D5.558X35XD6",
          "FGBD01-D2076R.045D12",
          "FGBD01-4EN-60X8.6X75",
          "FGBD04-XPET0502AP",
          "FGBA01-D8.8X75XSD10",
          "FGBD01-4EN-4X90X110",
          "FGBD01-4EN-0.2R10D75",
          "FGBDA2-SNMG-120408N",
          "FGBE07-D5.99X12X40",
          "FGBA05-3X90",
          "FGBB09-M4X0.7-E",
          "FGBE07-9.03X36X125L",
          "FGBB09-M8-ISO2/6H",
          "FGBEE11-16.5X90",
          "FGBD04-ONMU050410",
          "FGBE07-10.15",
          "FGBD01-4EN-D52050L",
          "FGBDA2-SPMG-050204",
          "FGBA03-6.8X34X79",
          "FGBA01-3.445X66L",
          "FGBA03-3.8X23X4DX74L",
          "FGBD01-10X35X75/4-R",
          "FGBE07-6.06",
          "FGBD01-4EN-9X10X75",
          "FGBA03-5.5X28X66L",
          "FGBD01-4EN-0.2R11D80",
          "FGBE10-D10R1-75L",
          "FGBDA2-WDXT042004G",
          "FGBA05-3X90X100L",
          "FGBD01-4EN-45-60L",
          "FGBDA2-WNMX060308"
        ]

my_dict = {}

# Fetch and print results
for row in cursor.fetchall():
    my_dict[row[0]] = row[1]

for item in a:
    if item in list(my_dict.keys()):
        
        print(True)
    else:
        print(item)
        print(False)

# Close the cursor and connection
cursor.close()
connection.close()