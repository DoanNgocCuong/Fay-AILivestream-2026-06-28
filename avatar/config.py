import os

# Đường dẫn avatar (video hoặc ảnh tĩnh)
AVATAR_VIDEO_PATH = os.path.join(os.path.dirname(__file__), "assets", "avatar_idle.mp4")
AVATAR_IMAGE_PATH = os.path.join(os.path.dirname(__file__), "assets", "avatar.jpg")

# Đường dẫn Wav2Lip
WAV2LIP_DIR = os.path.join(os.path.dirname(__file__), "Wav2Lip")
WAV2LIP_CHECKPOINT = os.path.join(WAV2LIP_DIR, "checkpoints", "wav2lip_gan.pth")
WAV2LIP_INFERENCE = os.path.join(WAV2LIP_DIR, "inference.py")

# Output
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
LIPSYNC_OUTPUT = os.path.join(OUTPUT_DIR, "lipsync_current.mp4")

# Display
WINDOW_NAME = "Linh - Dr.Bee AI Host"
FPS = 25  # fallback FPS nếu video không đọc được
# WIDTH/HEIGHT: None = tự detect từ video gốc lúc khởi động
# Nếu muốn override cứng thì set số (vd: WIDTH=720, HEIGHT=1280)
WIDTH = None
HEIGHT = None

# OBS Virtual Camera output
# Set True để push mỗi frame lên OBS Virtual Camera (cần pip install pyvirtualcam + OBS Virtual Camera driver)
OBS_VIRTUAL_CAM = False
# Resolution cố định cho virtual cam (Facebook Live yêu cầu 1920x1080 hoặc 1280x720)
OBS_CAM_WIDTH = 1280
OBS_CAM_HEIGHT = 720
OBS_CAM_FPS = 25

# Thư mục output
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(os.path.join(os.path.dirname(__file__), "assets"), exist_ok=True)
