import os

# 使用 OpenAI API（也可以替换为其他多模态模型）
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your-api-key-here")
OPENAI_MODEL = "gpt-4-vision-preview"  # 或 "gpt-4-turbo" 支持多模态

# 策略开关
ENABLE_MOCK_MODE = False   # 若为True，则使用规则模拟，不调用真实模型（用于测试）
USE_COST_SAVING_ROUTING = True   # 是否启用策略路由（小模型预筛选）