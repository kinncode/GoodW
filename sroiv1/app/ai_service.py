import google.generativeai as genai
from flask import current_app

class AIService:
    @staticmethod
    def generate_response(prompt, context='general'):
        """
        根據提示和上下文生成 AI 回應
        :param prompt: 用戶輸入的提示
        :param context: 上下文（如 'analysis'）
        :return: AI 生成的回應
        """
        # 配置 Gemini API
        genai.configure(api_key=current_app.config['GEMINI_API_KEY'])
        
        # 根據上下文生成系統提示
        if context == 'analysis':
            system_prompt = """
            你是一個 SROI 分析專家，請根據用戶的問題提供專業的分析建議。
            回答時請注意：
            1. 使用專業術語但解釋清楚
            2. 提供具體的改進建議
            3. 必要時使用數據支持你的觀點
            """
        else:
            system_prompt = "你是一個 AI 助理，請根據用戶的問題提供幫助。"

        # 初始化 Gemini 模型
        model = genai.GenerativeModel('gemini-2.0-flash')
        chat = model.start_chat(history=[])

        # 生成回應
        try:
            response = chat.send_message(f"{system_prompt}\n\n{prompt}")
            return response.text
        except Exception as e:
            raise Exception(f"Gemini API 錯誤: {str(e)}")

    @staticmethod
    def evaluate_project(project_data):
        """
        根據專案數據進行 AI 評估
        :param project_data: 專案數據字典
        :return: AI 生成的回應
        """
        # 建立評估提示
        prompt = f"""
        請根據以下專案數據進行評估：
        專案名稱：{project_data['project_name']}
        總影響力價值：{project_data['total_impact']} 元
        總投入成本：{project_data['total_input']} 元
        總 SROI：{project_data['project_sroi']}
        利害關係人數：{len(project_data['stakeholder_metrics'])}

        請提供：
        1. 專案整體評估
        2. 主要優點
        3. 改進建議
        4. 未來發展方向
        """

        return AIService.generate_response(prompt, context='analysis') 