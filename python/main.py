import os
import logging
import pathlib
import json
import hashlib
import sqlite3
from fastapi import FastAPI, Form, HTTPException, File, UploadFile, Path
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlite3 import Connection

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
    conn = get_db_connection()
    items = conn.execute('''SELECT items.id, items.name, categories.name AS category, items.image_name
                            FROM items
                            JOIN categories ON items.category_id = categories.id''').fetchall()
    conn.close()
    return {"items": [dict(item) for item in items]}

    # ファイルの読み込み
    # with open(file_path, 'r') as file:
    #     items_data = json.load(file)

    # logger.info(f"Receive items: {items_data}")
    # return JSONResponse(content=items_data)

@app.post("/items")
async def add_item(name: str = Form(...), category: str = Form(...), image: UploadFile = File(...)):
    conn = get_db_connection()
    # カテゴリが存在するか確認し、なければ追加
    category_id = conn.execute('SELECT id FROM categories WHERE name = ?', (category,)).fetchone()
    if category_id is None:
        conn.execute('INSERT INTO categories (name) VALUES (?)', (category,))
        category_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
    else:
        category_id = category_id['id']
    
    # 画像の処理
    image_contents = await image.read()
    image_hash = hashlib.sha256(image_contents).hexdigest()
    image_filename = f"{image_hash}.jpg"
    with open(images / image_filename, 'wb') as file:
        file.write(image_contents)
    
    # 商品情報をデータベースに保存
    conn.execute('INSERT INTO items (name, category_id, image_name) VALUES (?, ?, ?)',
                 (name, category_id, image_filename))
    conn.commit()
    conn.close()
    return {"message": f"Item received: {name}", "category": category, "image_name": image_filename}

@app.get("/search")
def search_items(keyword: str):
    conn = get_db_connection()
    items = conn.execute('''SELECT items.name, categories.name AS category, items.image_name
                            FROM items
                            JOIN categories ON items.category_id = categories.id
                            WHERE items.name LIKE ?''', ('%' + keyword + '%',)).fetchall()
    conn.close()
    return {"items": [dict(item) for item in items]}

    
    # # 画像のファイル名の取得
    # image_contents = await image.read()
    # image_hash = hashlib.sha256(image_contents).hexdigest()
    # image_filename = f"{image_hash}.jpg"
    # with open(images / image_filename, 'wb') as file:
    #     file.write(image_contents)

    # # 新しい商品をJSONに追加
    # new_item = {"name":name, "category":category, "image_name":image_filename}
    # with open(file_path, 'r+') as file:
    #     items_data = json.load(file)
    #     items_data.append(new_item)
    #     file.seek(0)
    #     json.dump(items_data, file, indent=4)


    logger.info(f"Receive item: {name}, {category}")
    return {"message": f"item received: {name}, {category}"} # ちょっと形式違うけどこれでいいのかな？



@app.get("/image/{image_filename}")
async def get_image(image_filename: str):
    # Create image path
    image_path = images / image_filename

    if not image_filename.endswith(".jpg"):
        raise HTTPException(status_code=400, detail="Image path does not end with .jpg")

    if not image_path.exists():
        logger.debug(f"Image not found: {image_filename}")
        image = images / "default.jpg"

    return FileResponse(image)


# データベース接続用の関数
def get_db_connection() -> Connection:
    conn = sqlite3.connect('mercari.sqlite3')
    conn.row_factory = sqlite3.Row  # 辞書形式で結果を取得できるようにする
    return conn

# データベースとテーブルの初期設定
def initialize_db():
    conn = get_db_connection()
    conn.execute('''CREATE TABLE IF NOT EXISTS categories (
                        id INTEGER PRIMARY KEY,
                        name TEXT UNIQUE NOT NULL
                    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS items (
                        id INTEGER PRIMARY KEY,
                        name TEXT NOT NULL,
                        category_id INTEGER NOT NULL,
                        image_name TEXT,
                        FOREIGN KEY (category_id) REFERENCES categories(id)
                    )''')
    conn.commit()
    conn.close()

# アプリ起動時にデータベースを初期化
@app.on_event("startup")
def startup_event():
    initialize_db()


