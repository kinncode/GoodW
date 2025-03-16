# SROI分析系統

## 專案概述

SROI分析系統是一個專為社會投資回報率(Social Return on Investment)分析設計的網頁應用程式。此系統幫助組織和個人評估社會項目的影響力，量化社會價值，並計算社會投資回報率。

## 主要功能

- **用戶管理**：註冊、登入、權限控制和帳戶安全管理
- **專案管理**：創建、編輯和刪除SROI分析專案
- **利害關係人分析**：識別和管理專案的利害關係人
- **投入與產出追蹤**：記錄和分析專案的資源投入和產出
- **結果指標設定**：定義和測量專案的社會影響指標
- **影響因素評估**：評估死重量(Deadweight)、替代性(Displacement)、歸因度(Attribution)和衰減率(Drop-off)等因素
- **SROI計算與報告**：自動計算SROI比率並生成分析報告
- **AI輔助分析**：利用人工智能協助SROI評估和建議

## 技術架構

- **後端**：Python Flask框架
- **前端**：HTML, CSS, JavaScript
- **數據庫**：SQL Server (支援其他SQL數據庫)
- **認證**：Flask-Login, JWT
- **安全性**：密碼加密、會話管理、防止SQL注入
- **AI整合**：Google Generative AI

## 安裝指南

### 前置需求

- Python 3.8+
- SQL Server或其他SQL數據庫
- pip (Python包管理器)

### 安裝步驟

1. 克隆此儲存庫
   ```
   git clone https://github.com/yourusername/sroiv1.git
   cd sroiv1
   ```

2. 創建並啟動虛擬環境
   ```
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # Linux/Mac
   source venv/bin/activate
   ```

3. 安裝依賴項
   ```
   pip install -r requirements.txt
   ```

4. 配置環境變數
   - 複製`.env.example`為`.env`
   - 編輯`.env`文件，設置數據庫連接和其他配置

5. 初始化數據庫
   ```
   # 使用SROIdata.sql腳本創建數據庫結構
   ```

6. 啟動應用程式
   ```
   python app.py
   ```

7. 訪問應用程式
   ```
   http://localhost:50
   ```

## 使用指南

1. **註冊/登入**：創建帳戶或使用現有帳戶登入
2. **創建專案**：填寫專案基本信息
3. **添加利害關係人**：識別並記錄專案的利害關係人
4. **記錄投入與產出**：添加專案的資源投入和直接產出
5. **設定結果指標**：定義專案的社會影響指標和價值
6. **評估影響因素**：設定影響評估參數
7. **生成SROI分析**：計算並查看SROI分析結果

## 系統截圖

*[ ]*

## 開發者指南

### 專案結構

```
sroiv1/
├── app/                    # 主應用程式目錄
│   ├── __init__.py         # 應用程式初始化
│   ├── models.py           # 數據模型
│   ├── routes.py           # 路由和視圖函數
│   ├── admin_routes.py     # 管理員路由
│   ├── ai_service.py       # AI服務整合
│   ├── analysis.py         # SROI分析邏輯
│   ├── project.py          # 專案相關功能
│   ├── forms.py            # 表單定義
│   ├── mailconfig.py       # 郵件配置
│   ├── static/             # 靜態文件(CSS, JS, 圖片)
│   └── templates/          # HTML模板
├── app.py                  # 應用程式入口點
├── config.py               # 配置文件
├── requirements.txt        # 依賴項列表
├── SROIdata.sql            # 數據庫結構
└── README.md               # 專案文檔
```

### 擴展開發

1. **添加新功能**：在routes.py中添加新路由和視圖函數
2. **修改數據模型**：更新models.py和相應的數據庫結構
3. **自定義分析邏輯**：在analysis.py中修改SROI計算方法
4. **增強AI功能**：擴展ai_service.py中的AI輔助功能

## 貢獻指南

1. Fork此儲存庫
2. 創建您的功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交您的更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 開啟Pull Request

## 授權

此專案採用 [MIT 授權](LICENSE)。

## 聯絡方式

- 專案維護者：[YU Hsiang]
- 電子郵件：[4B190011@stust.edu.tw]


## 致謝

- 感謝所有為此專案做出貢獻的開發者
- 特別感謝[相關組織或個人]的支持和幫助 