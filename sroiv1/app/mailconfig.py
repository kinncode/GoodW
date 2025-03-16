from flask_mail import Message
from . import mail

# 存儲驗證碼的字典
verify_codes = {}

# 發送驗證碼郵件的函數
def send_verification_email(email, code):
    msg = Message(
        'SROI評估系統 - 電子郵件驗證',
        sender='sroistust@gmail.com',  # 直接使用設定好的 Gmail
        recipients=[email]
    )
    msg.body = f'''您好！
    
您的驗證碼是：{code}

此驗證碼將在 5 分鐘後失效，請盡快完成驗證。

如果這不是您本人的操作，請忽略此郵件。

此致
SROI評估系統團隊'''
    
    mail.send(msg)