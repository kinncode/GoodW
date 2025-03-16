from app import create_app, db, bcrypt
from app.models import User
    
# 創建 Flask 應用
app = create_app()

# 加密密碼並新增用戶
def add_user(username, password, email, role='user'):
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    new_user = User(username=username, password=hashed_password, email=email, role=role)
    with app.app_context():  # 啟用應用程式上下文
        db.session.add(new_user)
        db.session.commit()
    print(f"User '{username}' with email '{email}' and role '{role}' has been added.")

# 呼叫函數
if __name__ == "__main__":
    username = input("請輸入使用者名稱：")
    password = input("請輸入密碼：")
    email = input("請輸入電子郵件：")
    role = input("請輸入角色（預設為'user'，若新增管理員，請輸入'admin'）：") or 'user'
    add_user(username, password, email, role)
