import pymysql
try:
    print("before connecting")
    connection = pymysql.connect(
        host="192.168.10.143",
        user="root",
        password="Agnext@123",
        database="mnir_ag001",
        port=3310,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor
    )
    print("after connecting", connection)
    print("Connection successful!")
except Exception as e:
    print(" Connection failed:", e) 


cursor=connection.cursor()
query = "SELECT * FROM mnir_ag001.model_data LIMIT 1;"
cursor.execute(query)
results = cursor.fetchall()
for row in results:
    print(row)





    
