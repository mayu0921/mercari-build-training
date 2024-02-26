import os
import logging
import pathlib
import json
import hashlib
from fastapi import FastAPI, Form, HTTPException, File, UploadFile, Path
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
logger = logging.getLogger("uvicorn")
logger.level = logging.INFO
images = pathlib.Path(__file__).parent.resolve() / "image"
images.mkdir(exist_ok=True)  # imagesフォルダがなければ作成
origins = [ os.environ.get('FRONT_URL', 'http://localhost:3000') ]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET","POST","PUT","DELETE"],
    allow_headers=["*"],
)

# 参考：https://docs.datadoghq.com/ja/continuous_integration/static_analysis/rules/python-django/http-response-with-json-dumps/


# ファイルの作成
file_path = 'items.json'
# JSONファイルがない場合は空のリストで初期化
if not pathlib.Path(file_path).exists():
    with open(file_path, 'w') as file:
        json.dump([], file)

@app.get("/")
def root():
    return {"message": "Hello, world!"}


@app.get("/items")
def get_items():
    # ファイルの読み込み
    with open(file_path, 'r') as file:
        items_data = json.load(file)

    logger.info(f"Receive items: {items_data}")
    return JSONResponse(content=items_data)

@app.post("/items")
async def add_item(name: str = Form(...), category: str = Form(...), image: UploadFile = File(...)):
    # 画像のファイル名の取得
    image_contents = await image.read()
    image_hash = hashlib.sha256(image_contents).hexdigest()
    image_filename = f"{image_hash}.jpg"
    with open(images / image_filename, 'wb') as file:
        file.write(image_contents)

    # 新しい商品をJSONに追加
    new_item = {"name":name, "category":category, "image_name":image_filename}
    try:
    with open(file_path, 'r+') as file:
        items_data = json.load(file)
        items_data.append(new_item)
        file.seek(0)
        json.dump(items_data, file, indent=4)
        file.truncate()
    except Exception as e:
    logger.info(f"Receive item: {name}, {category}")
    return {"message": f"item received: {name}, {category}"} # ちょっと形式違うけどこれでいいのかな？



@app.get("/image/{image_filename}")
async def get_image(image_filename: str):
    # Create image path
    image_path = images / image_filename

    if not image_filename.endswith(".jpg"):
        raise HTTPException(status_code=400, detail="Image path does not end with .jpg")

    # ファイルが存在しない場合はデフォルト画像を使用
    if not image_path.exists():
        logger.debug(f"Image not found: {image_path}")  # 修正された参照
        image_path = images / "default.jpg"  # default.jpgにフォールバック

    # FileResponseの引数はstr型である必要がある
    return FileResponse(str(image_path))


# import os
# import logging
# import pathlib
# from fastapi import FastAPI, Form, HTTPException
# from fastapi.responses import FileResponse
# from fastapi.middleware.cors import CORSMiddleware

# app = FastAPI()
# logger = logging.getLogger("uvicorn")
# logger.level = logging.INFO
# images = pathlib.Path(__file__).parent.resolve() / "images"
# origins = [os.environ.get("FRONT_URL", "http://localhost:3000")]
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=origins,
#     allow_credentials=False,
#     allow_methods=["GET", "POST", "PUT", "DELETE"],
#     allow_headers=["*"],
# )


# @app.get("/")
# def root():
#     return {"message": "Hello, world!"}


# @app.post("/items")
# def add_item(name: str = Form(...)):
#     logger.info(f"Receive item: {name}")
#     return {"message": f"item received: {name}"}


# @app.get("/image/{image_name}")
# async def get_image(image_name):
#     # Create image path
#     image = images / image_name

#     if not image_name.endswith(".jpg"):
#         raise HTTPException(status_code=400, detail="Image path does not end with .jpg")

#     if not image.exists():
#         logger.debug(f"Image not found: {image}")
#         image = images / "default.jpg"

#     return FileResponse(image)
