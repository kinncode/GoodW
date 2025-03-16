from sqlalchemy import create_engine

engine = create_engine('mssql+pyodbc://@DESKTOP-DDIAQJQ\SQLEXPRESS/SROIV2?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes')
try:
    connection = engine.connect()
    print("連線成功！")
    connection.close()
except Exception as e:
    print(f"連線失敗：{e}")
