from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import uvicorn
from risk_strategy import MultimodalRiskJudge

app = FastAPI(title="风控多模态大模型API", description="端到端直播内容安全策略")
judge = MultimodalRiskJudge()

# 定义请求模型
class RiskCheckRequest(BaseModel):
    image_url: Optional[str] = Field(None, description="视频关键帧URL")
    image_description: Optional[str] = Field(None, description="图片内容文本描述（若无法传图则使用此字段）")
    audio_transcript: Optional[str] = Field("", description="直播音频转写文本")
    comment_text: Optional[str] = Field("", description="用户评论文本")
    user_behavior_sequence: Optional[str] = Field("", description="用户行为序列描述")
    user_profile: Optional[Dict[str, Any]] = Field({}, description="用户画像，如信用分、注册时长等")

class RiskCheckResponse(BaseModel):
    risk_type: str
    risk_level: str
    confidence: float
    evidence_chain: list
    suggestion: str

@app.post("/v1/risk_judge", response_model=RiskCheckResponse)
async def risk_judge(request: RiskCheckRequest):
    """多模态风险识别接口"""
    try:
        input_data = request.dict()
        # 若提供了image_url但没有description，可在此调用图片理解模型补充（这里简化）
        result = judge.judge(input_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"判官模型出错: {str(e)}")

@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)