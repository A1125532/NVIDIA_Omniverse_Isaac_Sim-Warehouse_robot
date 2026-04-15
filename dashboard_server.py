from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from threading import Lock
from typing import Dict

app = FastAPI(title="Isaac Sim Dashboard", description="Simple API for forklift pose + static frontend")


class Pose(BaseModel):
    x: float
    y: float
    yaw: float  # 角度（度）


class Command(BaseModel):
    destination: str
    raw: str


_state_lock = Lock()
_pose: Dict[str, float] = {"x": 0.0, "y": 0.0, "yaw": 0.0}
_start_flag: bool = False  # 是否已收到開始信號
_command: Dict[str, str] = {"destination": "", "raw": ""}  # 儲存指令


@app.post("/api/start")
def start_execution():
    """接收開始執行信號（finish.py 需要手動在 Isaac Sim 環境中啟動）"""
    global _start_flag
    
    with _state_lock:
        # 如果已經在執行，不重複設定
        if _start_flag:
            return {"ok": False, "message": "已在執行中"}
        
        _start_flag = True
        print("✅ 收到開始執行信號（請確保 finish.py 已在 Isaac Sim 環境中運行）")
        return {"ok": True, "message": "開始執行信號已設定"}


@app.get("/api/start")
def get_start_flag():
    """檢查是否已收到開始信號"""
    with _state_lock:
        return {"started": _start_flag}


@app.post("/api/reset")
def reset_start_flag():
    """重置開始標誌，允許重新執行"""
    global _start_flag
    with _state_lock:
        _start_flag = False
    return {"ok": True, "message": "已重置"}


@app.post("/api/pose")
def update_pose(pose: Pose):
    """由 Isaac Sim 腳本呼叫，用來更新目前叉車位置與朝向。"""
    with _state_lock:
        _pose.update(pose.dict())
    return {"ok": True}


@app.get("/api/pose")
def get_pose():
    """前端輪詢這個 API，即時取得叉車位置。"""
    with _state_lock:
        return _pose.copy()


@app.post("/api/command")
def set_command(command: Command):
    """接收前端發送的指令"""
    global _command
    with _state_lock:
        _command.update(command.dict())
    return {"ok": True, "message": "指令已接收"}


@app.get("/api/command")
def get_command():
    """Isaac Sim 腳本可以讀取這個 API 來取得指令"""
    with _state_lock:
        return _command.copy()


# 靜態前端（dashboard），會從 ./frontend/index.html 開始
app.mount(
    "/",
    StaticFiles(directory="frontend", html=True),
    name="frontend",
)


