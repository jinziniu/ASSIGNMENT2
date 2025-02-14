from flask import Flask, request, jsonify, redirect
import requests
from database import db, URLMapping
import hashlib
import hmac
import base64
import json
import time

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///urls.db'
# 不再使用本地 secret，移除或保留但仅用于内部操作
app.config['SECRET_KEY'] = 'supersecretkey'
db.init_app(app)

with app.app_context():
    db.create_all()

def verify_jwt_remote(token):
    try:
        auth_url = "http://localhost:8001/users/verify"  # 请确保认证服务正在运行
        response = requests.post(auth_url, json={"token": token})
        if response.status_code == 200:
            return response.json()
        else:
            app.logger.error(f"Auth service verification failed: {response.text}")
            return None
    except requests.RequestException as e:
        app.logger.error(f"Error contacting auth service: {str(e)}")
        return None

# 统一处理 '/' 的 POST 和 GET 请求
@app.route('/', methods=['POST', 'GET'])
def handle_urls():
    token = request.headers.get("Authorization")
    user_data = verify_jwt_remote(token)
    if not user_data:
        return jsonify({"error": "Unauthorized"}), 403

    if request.method == 'POST':
        data = request.get_json()
        long_url = data.get("value")
        if not long_url or long_url.strip() == "":
            return jsonify({"error": "Invalid URL"}), 400

        try:
            new_mapping = URLMapping(long_url=long_url, shortid='', user_id=user_data["user_id"])
            db.session.add(new_mapping)
            db.session.commit()

            short_id = str(new_mapping.id)
            new_mapping.shortid = short_id
            db.session.commit()
        except Exception as e:
            app.logger.error(f"Error creating short URL: {e}")
            return jsonify({"error": "Internal Server Error"}), 500

        return jsonify({'id': short_id}), 201

    elif request.method == 'GET':
        try:
            urls = URLMapping.query.filter_by(user_id=user_data["user_id"]).all()
            result = [{"id": url.shortid, "long_url": url.long_url} for url in urls]
            return jsonify({"short_links": result}), 200
        except Exception as e:
            app.logger.error(f"Error fetching URLs: {e}")
            return jsonify({"error": "Internal Server Error"}), 500

# 删除全部短链接，删除后无论是否有数据均返回 404
@app.route('/', methods=['DELETE'])
def delete_all_urls():
    token = request.headers.get("Authorization")
    user_data = verify_jwt_remote(token)
    if not user_data:
        return jsonify({"error": "Unauthorized"}), 403

    try:
        user_id = user_data["user_id"]
        urls_to_delete = URLMapping.query.filter_by(user_id=user_id).all()
        if urls_to_delete:
            for url in urls_to_delete:
                db.session.delete(url)
            db.session.commit()
    except Exception as e:
        app.logger.error(f"Error deleting urls: {e}")
        # 如果删除时出现异常，返回 500
        return jsonify({"error": "Internal Server Error"}), 500

    # 按测试要求，删除后返回 404 表示资源不存在
    return '', 404

# 获取单个短链接的重定向接口
@app.route('/<short_id>', methods=['GET'])
def get_long_url(short_id):
    try:
        mapping = URLMapping.query.filter_by(shortid=short_id).first()
        if not mapping:
            return jsonify({"error": "Not found"}), 404
        # 返回 JSON 响应，并设置状态码为 301
        return jsonify({"value": mapping.long_url}), 301
    except Exception as e:
        app.logger.error(f"Error in get_long_url for {short_id}: {e}")
        return jsonify({"error": "Internal Server Error"}), 500


# 修改短链接的 PUT 接口
@app.route('/<short_id>', methods=['PUT'])
def update_short_url(short_id):
    token = request.headers.get("Authorization")
    user_data = verify_jwt_remote(token)
    if not user_data:
        return jsonify({"error": "Unauthorized"}), 403

    try:
        mapping = URLMapping.query.filter_by(shortid=short_id, user_id=user_data["user_id"]).first()
        if not mapping:
            return jsonify({"error": "Not found or no permission"}), 404

        # 强制解析 JSON 数据
        data = request.get_json(force=True, silent=True) or request.form

        # 接受 "url" 键（也可以同时接受 "value" 以保持与 POST 一致）
        new_url = data.get("url") or data.get("value")
        if not new_url:
            return jsonify({"error": "Invalid request data"}), 400

        # 增加 URL 格式校验
        if not (new_url.startswith("http://") or new_url.startswith("https://")):
            return jsonify({"error": "Invalid URL"}), 400

        mapping.long_url = new_url
        db.session.commit()
        return jsonify({"message": "Updated"}), 200
    except Exception as e:
        app.logger.error(f"Error updating URL {short_id}: {e}")
        return jsonify({"error": "Internal Server Error"}), 500




# 删除单个短链接
@app.route('/<short_id>', methods=['DELETE'])
def delete_short_url(short_id):
    token = request.headers.get("Authorization")
    user_data = verify_jwt_remote(token)
    if not user_data:
        return jsonify({"error": "Unauthorized"}), 403

    try:
        mapping = URLMapping.query.filter_by(shortid=short_id, user_id=user_data["user_id"]).first()
        if not mapping:
            return jsonify({"error": "Not found or no permission"}), 404

        db.session.delete(mapping)
        db.session.commit()
        return '', 204
    except Exception as e:
        app.logger.error(f"Error deleting URL {short_id}: {e}")
        return jsonify({"error": "Internal Server Error"}), 500

if __name__ == '__main__':
    app.run(port=8000, debug=True)
