import requests
import json

# API地址
API_URL = "http://localhost:8000/v1/risk_judge"

# 示例1：高风险欺诈引流
sample_high_risk = {
    "image_url": "https://example.com/malicious_qrcode.jpg",  
    "image_description": "直播间画面中有一个二维码，旁边写着'加微信返现50元'，背景色情低俗",
    "audio_transcript": "兄弟们扫码加微信领红包，名额有限",
    "comment_text": "已加，什么时候发钱？",
    "user_behavior_sequence": "用户近10分钟: 开播1次，但该直播间刚创建，且用户历史信用评分极低",
    "user_profile": {
        "credit_score": 20,
        "account_age_days": 1,
        "device_risk_label": "模拟器"
    }
}

# 示例2：正常直播
sample_normal = {
    "image_description": "主播在唱歌，背景干净，无二维码",
    "audio_transcript": "欢迎大家来到直播间，点个关注吧",
    "comment_text": "唱得真好",
    "user_behavior_sequence": "用户正常评论，无异常行为",
    "user_profile": {"credit_score": 90}
}

def call_demo(data, title):
    print(f"\n========== {title} ==========")
    print("输入:")
    print(json.dumps(data, ensure_ascii=False, indent=2))
    resp = requests.post(API_URL, json=data)
    if resp.status_code == 200:
        print("输出:")
        print(json.dumps(resp.json(), ensure_ascii=False, indent=2))
    else:
        print(f"错误: {resp.status_code}, {resp.text}")

if __name__ == "__main__":
    
    call_demo(sample_high_risk, "高风险欺诈引流案例")
    call_demo(sample_normal, "正常直播案例")