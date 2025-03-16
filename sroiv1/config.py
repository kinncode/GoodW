import os

class Config:
    # 其他配置...
    OPENAI_API_KEY = 'your-openai-api-key'
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY') 