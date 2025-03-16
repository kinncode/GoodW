CREATE TABLE users (
    id INT PRIMARY KEY IDENTITY(1,1),
    username NVARCHAR(50) NOT NULL UNIQUE,
    password NVARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    role NVARCHAR(20) NOT NULL DEFAULT 'user',
    created_at DATETIME NOT NULL DEFAULT GETDATE(),
    account_expires DATETIME2 NULL,
    is_active BIT DEFAULT 1,
    last_login DATETIME2 NULL,
    login_count INT DEFAULT 0,
    password_expires DATETIME2 NULL,
    failed_login_attempts INT DEFAULT 0,
    locked_until DATETIME2 NULL,
    session_token VARCHAR(100) NULL,
    ip_address VARCHAR(45) NULL,
    login_time DATETIME NULL,
    last_activity DATETIME NULL,    
    CONSTRAINT UQ_users_username UNIQUE (username),
    CONSTRAINT UQ_users_email UNIQUE (email)
);


CREATE TABLE myprojects (
    id INT PRIMARY KEY IDENTITY(1,1),
    user_id INT NOT NULL, -- 關聯 users 資料表
    organization_name NVARCHAR(255) NOT NULL,
    project_name NVARCHAR(255) NOT NULL,
    project_activity NVARCHAR(MAX) NULL,
    project_goal NVARCHAR(MAX) NULL,
    project_attribute NVARCHAR(50) NOT NULL CHECK (project_attribute IN ('contract', 'funding', 'partOfOrg')),
    project_start_date DATE NOT NULL,
    project_end_date DATE NULL,
    analysis_start_date DATE NULL,
    analysis_end_date DATE NULL,
    analysis_nature NVARCHAR(50) NOT NULL CHECK (analysis_nature IN ('evaluation', 'prediction')),
    created_at DATETIME DEFAULT GETDATE() NOT NULL,
    updated_at DATETIME DEFAULT GETDATE() NOT NULL,
    sroi_score NCHAR(10) NULL, -- 新增這行
    FOREIGN KEY (user_id) REFERENCES users(id) -- 外鍵關聯
);
CREATE TABLE stakeholders (
    id INT PRIMARY KEY IDENTITY(1,1), -- 自動增長主鍵
    project_id INT NOT NULL, -- 外鍵，關聯到 myprojects 表的 id
    stakeholder_name NVARCHAR(255) NOT NULL, -- 主要利害關係者名稱
    stakeholder_group NVARCHAR(255) NOT NULL, -- 組群名稱
    stakeholder_reason NVARCHAR(MAX) NOT NULL, -- 納入理由
    created_at DATETIME DEFAULT GETDATE() NOT NULL, -- 記錄建立時間
    updated_at DATETIME DEFAULT GETDATE() NOT NULL, -- 記錄最後更新時間
    FOREIGN KEY (project_id) REFERENCES myprojects(id) ON DELETE CASCADE
);
CREATE TABLE contributions (-- 投入與產出
    id INT PRIMARY KEY IDENTITY(1,1), -- 自動增長主鍵
    project_id INT NOT NULL, -- 關聯到 myprojects 表的專案
    stakeholder_id INT NOT NULL, -- 關聯到 stakeholders 表的利害關係者
    resource_type NVARCHAR(50) NOT NULL CHECK (resource_type IN ('money', 'time')), -- 投入類型
    resource_amount FLOAT NOT NULL, -- 投入數量
    output_description NVARCHAR(MAX) NOT NULL, -- 產出描述
    created_at DATETIME DEFAULT GETDATE() NOT NULL, -- 建立時間
    updated_at DATETIME DEFAULT GETDATE() NOT NULL, -- 最後更新時間
    FOREIGN KEY (project_id) REFERENCES myprojects(id) ON DELETE NO ACTION, 
    FOREIGN KEY (stakeholder_id) REFERENCES stakeholders(id) ON DELETE CASCADE
);
--------------------------
CREATE TABLE results (
    id INT PRIMARY KEY IDENTITY(1,1), -- 成果ID
    project_id INT NOT NULL, -- 關聯到 myprojects 表的專案ID
    stakeholder_id INT NOT NULL, -- 關聯到 stakeholders 表
    result_description NVARCHAR(MAX) NOT NULL, -- 成果描述(成果網頁上)
    event_chain NVARCHAR(MAX) NULL, -- 成果事件鏈（可選，允許空白）
    created_at DATETIME DEFAULT GETDATE() NOT NULL, -- 建立時間
    updated_at DATETIME DEFAULT GETDATE() NOT NULL, -- 更新時間
    FOREIGN KEY (project_id) REFERENCES myprojects(id) ON DELETE NO ACTION,
    FOREIGN KEY (stakeholder_id) REFERENCES stakeholders(id) ON DELETE CASCADE
);

CREATE TABLE result_indicators (
    id INT PRIMARY KEY IDENTITY(1,1), -- 指標ID
    result_id INT NOT NULL, -- 關聯到 results 表
    indicator_name NVARCHAR(255) NOT NULL, -- 指標名稱
    scale_population INT NOT NULL, -- 成果人數
    duration INT NOT NULL CHECK (duration BETWEEN 1 AND 4), -- 持續時間 (1~4)
    weight INT NOT NULL CHECK (weight BETWEEN 1 AND 10), -- 權重 (一般版使用)
    pricing_variable NVARCHAR(255) NULL, -- 財務代理變數（高級版使用，允許空白）
    pricing_amount FLOAT NULL, -- 定價（高級版使用，允許空白）
    data_source NVARCHAR(MAX) NULL, -- 資料來源備註（高級版使用，允許空白）
    created_at DATETIME DEFAULT GETDATE() NOT NULL, -- 建立時間
    updated_at DATETIME DEFAULT GETDATE() NOT NULL, -- 更新時間
    FOREIGN KEY (result_id) REFERENCES results(id) ON DELETE CASCADE -- 外鍵約束，並設置級聯刪除
);

CREATE TABLE impact_factors (
    id INT PRIMARY KEY IDENTITY(1,1), -- 影響力因子ID
    result_id INT NOT NULL, -- 關聯到 results 表
    deadweight FLOAT NOT NULL CHECK (deadweight BETWEEN 0 AND 100), -- 無謂因子 (0~100%)
    displacement FLOAT NOT NULL CHECK (displacement BETWEEN 0 AND 100), -- 移轉因子 (0~100%)
    attribution FLOAT NOT NULL CHECK (attribution BETWEEN 0 AND 100), -- 歸因因子 (0~100%)
    drop_off FLOAT NOT NULL CHECK (drop_off BETWEEN 0 AND 100), -- 衰減因子 (0~100%)
    created_at DATETIME DEFAULT GETDATE() NOT NULL, -- 建立時間
    updated_at DATETIME DEFAULT GETDATE() NOT NULL, -- 更新時間
    FOREIGN KEY (result_id) REFERENCES results(id) ON DELETE CASCADE -- 外鍵約束，並設置級聯刪除
);



-- 創建系統設定表
CREATE TABLE system_settings (
    id INT IDENTITY(1,1) PRIMARY KEY,
    system_name NVARCHAR(100) NOT NULL,
    maintenance_mode BIT DEFAULT 0,
    allow_registration BIT DEFAULT 1,
    [version] NVARCHAR(20),  -- 使用方括號因為 version 是保留字
    last_update DATETIME2 DEFAULT GETDATE(),
    max_projects_per_user INT DEFAULT 10,
    default_project_visibility NVARCHAR(20) DEFAULT N'private',
    enable_email_notifications BIT DEFAULT 1,
    backup_frequency NVARCHAR(20) DEFAULT N'daily',
    session_timeout INT DEFAULT 30
);
GO




--管理員--
-- 創建系統日誌表
CREATE TABLE system_log (
    id INT IDENTITY(1,1) PRIMARY KEY,
    [timestamp] DATETIME2 DEFAULT GETDATE(),  -- 使用方括號因為 timestamp 是保留字
    [level] NVARCHAR(20),
    username NVARCHAR(80),
    ip_address NVARCHAR(45),
    [action] NVARCHAR(255),
    details NVARCHAR(MAX),
    created_at DATETIME2 DEFAULT GETDATE()
);
GO

-- 插入預設系統設定
INSERT INTO system_settings (
    system_name,
    maintenance_mode,
    allow_registration,
    [version],
    last_update
) VALUES (
    N'SROI 管理系統',
    0,
    1,
    N'1.0.0',
    GETDATE()
);
GO
-- 創建 AI 模型表
CREATE TABLE ai_models (
    id INT PRIMARY KEY IDENTITY(1,1),
    name NVARCHAR(100) NOT NULL,
    description NVARCHAR(MAX),
    model_type NVARCHAR(50),
    api_endpoint NVARCHAR(255),
    api_key NVARCHAR(255),
    is_active BIT DEFAULT 1,
    created_at DATETIME DEFAULT GETDATE(),
    last_updated DATETIME,
    usage_count INT DEFAULT 0,
    last_used DATETIME
);

-- 創建 AI 模型使用日誌表
CREATE TABLE ai_model_usage_logs (
    id INT PRIMARY KEY IDENTITY(1,1),
    model_id INT FOREIGN KEY REFERENCES ai_models(id),
    user_id INT FOREIGN KEY REFERENCES users(id),
    timestamp DATETIME DEFAULT GETDATE(),
    input_data NVARCHAR(MAX),
    output_data NVARCHAR(MAX),
    processing_time FLOAT,
    status NVARCHAR(20),
    error_message NVARCHAR(MAX)
);
-- 創建索引
CREATE INDEX IX_system_log_timestamp 
ON system_log([timestamp]);
GO

CREATE INDEX IX_system_log_level 
ON system_log([level]);
GO

CREATE INDEX IX_system_log_username 
ON system_log(username);
GO
CREATE INDEX IX_users_is_active ON users(is_active);
CREATE INDEX IX_users_account_expires ON users(account_expires);
CREATE INDEX IX_users_last_login ON users(last_login);
