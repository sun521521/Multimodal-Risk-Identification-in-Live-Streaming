import json
import base64
import requests
from typing import Dict, Any, List, Optional
from config import OPENAI_API_KEY, OPENAI_MODEL, ENABLE_MOCK_MODE, USE_COST_SAVING_ROUTING

class MultimodalRiskJudge:
    """风控多模态大模型 - 策略产品核心类"""

    def __init__(self):
        self.client = None
        if not ENABLE_MOCK_MODE and OPENAI_API_KEY and OPENAI_API_KEY != "your-api-key-here":
            from openai import OpenAI
            self.client = OpenAI(api_key=OPENAI_API_KEY)

    # ---------- 1. 轻量模型快速预筛选（策略路由）----------
    def _quick_prefilter(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用轻量规则/小模型判断是否明显安全或高风险。
        返回：{"need_large_model": bool, "pre_risk_level": str, "reason": str}
        """
        # 简单示例：包含明显敏感词或异常行为序列
        risk_score = 0
        reasons = []

        # 检查文本（评论文本、音频转文本）
        text_data = input_data.get("comment_text", "") + input_data.get("audio_transcript", "")
        high_risk_keywords = ["微信", "加群", "转账", "赌博", "色情", "暴利"]
        for kw in high_risk_keywords:
            if kw in text_data:
                risk_score += 20
                reasons.append(f"文本含敏感词'{kw}'")

        # 检查行为序列（例如：账号长时间静默，异地异设备开直播，无浏览观看行为）
        behavior = input_data.get("user_behavior_sequence", "")
        if "静默后异地异设备开播" in behavior or "短时间刷屏" in behavior:
            risk_score += 30
            reasons.append("用户行为异常：低价值账号异地异设备")

        # 用户画像风险
        user_profile = input_data.get("user_profile", {})
        if user_profile.get("credit_score", 100) < 60:
            risk_score += 25
            reasons.append("用户信用分低")

        if risk_score >= 50:
            return {"need_large_model": True, "pre_risk_level": "high", "reason": "; ".join(reasons)}
        elif risk_score >= 20:
            return {"need_large_model": True, "pre_risk_level": "medium", "reason": "; ".join(reasons)}
        else:
            return {"need_large_model": False, "pre_risk_level": "low", "reason": "无明显风险信号"}

    # ---------- 2. 构建多模态大模型输入提示词（结构化、证据链）----------
    def _build_prompt(self, input_data: Dict[str, Any], prefilter_result: Dict[str, Any]) -> str:
        """
        构建详细的系统提示和用户消息，强制要求输出JSON格式 + 证据链。
        """
        system_prompt = """
你是一个直播平台内容安全策略专家。你的任务是基于给定的多模态数据（图像描述、文本、用户行为、用户画像），判断是否存在违规风险。

**输出要求（严格JSON格式）**：
{
  "risk_type": "低俗色情 | 欺诈引流 | 违规营销 | 正常",
  "risk_level": "高 | 中 | 低",
  "confidence": 0.0~1.0,
  "evidence_chain": [
    {"modal": "image", "description": "图片内发现赌博水印", "location": "右下角"},
    {"modal": "text", "description": "评论文本包含'加微信领红包'"}
  ],
  "suggestion": "具体处置建议（如：断流、降流、人工复核、加强监控）"
}

注意：
- 只输出JSON，不要有其他解释。
- 证据链必须基于给出的信息，不可凭空捏造。
- 处置建议需对应风险等级：高风险→自动断流 + 人工核验；中风险→限流、弹窗警告 + 人工核验；低风险→打标监控暂不处置。
"""
        user_content = f"""
### 输入数据 ###
1. 视频关键帧描述（AI分析）：{input_data.get('image_description', '无图片')}
2. 直播音频转录文本：{input_data.get('audio_transcript', '无音频')}
3. 用户评论文本：{input_data.get('comment_text', '无评论')}
4. 用户行为序列：{input_data.get('user_behavior_sequence', '无行为')}
5. 用户画像：{json.dumps(input_data.get('user_profile', {}), ensure_ascii=False)}

### 预检信息（来自小模型） ###
{prefilter_result.get('reason', '无预检')}

请输出风险判定结果。
"""
        return system_prompt, user_content

    # ---------- 3. 调用多模态大模型（支持图片URL或Base64）----------
    def _call_large_model(self, system_prompt: str, user_content: str, image_url: Optional[str] = None) -> str:
        """调用多模态模型（OpenAI GPT-4V示例）"""
        if ENABLE_MOCK_MODE or self.client is None:
            # 模拟返回（用于测试）
            return self._mock_response()

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": []}
        ]
        # 文本部分
        messages[1]["content"].append({"type": "text", "text": user_content})
        # 如果有图片，附加图片（单张示例）
        if image_url:
            messages[1]["content"].append({
                "type": "image_url",
                "image_url": {"url": image_url}
            })

        response = self.client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            max_tokens=500,
            temperature=0.2
        )
        return response.choices[0].message.content

    def _mock_response(self) -> str:
        """模拟大模型输出"""
        return json.dumps({
            "risk_type": "欺诈引流",
            "risk_level": "高",
            "confidence": 0.92,
            "evidence_chain": [
                {"modal": "image", "description": "图片包含二维码及'加微信返现'文字"},
                {"modal": "text", "description": "评论文本中有'加微信领礼物'"}
            ],
            "suggestion": "立即断流，通知风控团队溯源"
        })

    # ---------- 4. 解析大模型输出并加固（保证格式正确）----------
    def _parse_output(self, raw_output: str) -> Dict[str, Any]:
        try:
            # 去除可能的Markdown代码块标记
            clean = raw_output.strip().strip('```json').strip('```')
            result = json.loads(clean)
            # 确保关键字段存在
            default = {
                "risk_type": "正常",
                "risk_level": "低",
                "confidence": 0.5,
                "evidence_chain": [],
                "suggestion": "无动作"
            }
            default.update(result)
            return default
        except:
            return {
                "risk_type": "未知",
                "risk_level": "中",
                "confidence": 0.5,
                "evidence_chain": [{"modal": "system", "description": "模型输出解析失败，请人工审核"}],
                "suggestion": "转人工复审"
            }

    # ---------- 5. 端到端执行入口 ----------
    def judge(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        input_data 结构示例：
        {
            "image_url": "https://xxx.jpg",  # 可选，视频关键帧
            "image_description": "系统生成或用户提供的图片文本描述",
            "audio_transcript": "音频转写文本",
            "comment_text": "评论文本",
            "user_behavior_sequence": "用户行为描述，如 '过去5分钟: 开播2次, 发评论10条'",
            "user_profile": {"credit_score": 85, "account_age_days": 30}
        }
        """
        # Step1: 小模型预筛选
        prefilter = self._quick_prefilter(input_data)
        if not USE_COST_SAVING_ROUTING or not prefilter["need_large_model"]:
            # 直接返回低风险结论（节省成本）
            return {
                "risk_type": "正常",
                "risk_level": "低",
                "confidence": 0.6,
                "evidence_chain": [{"modal": "prefilter", "description": prefilter["reason"]}],
                "suggestion": "仅记录日志，无需干预",
                "from_large_model": False
            }

        # Step2: 调用大模型
        system_prompt, user_content = self._build_prompt(input_data, prefilter)
        image_url = input_data.get("image_url", None)
        raw_output = self._call_large_model(system_prompt, user_content, image_url)
        final_result = self._parse_output(raw_output)
        final_result["from_large_model"] = True
        final_result["prefilter_reason"] = prefilter["reason"]
        return final_result

# 测试
if __name__ == "__main__":
    judge = MultimodalRiskJudge()
    test_data = {
        "image_description": "直播间背景有二维码，写有'加微信送红包'",
        "audio_transcript": "家人们点击下方链接领取福利",
        "comment_text": "已加微信，谢谢",
        "user_behavior_sequence": "用户5分钟内连续开播3次",
        "user_profile": {"credit_score": 30, "account_age_days": 1}
    }
    result = judge.judge(test_data)
    print(json.dumps(result, ensure_ascii=False, indent=2))