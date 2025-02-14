from flask import Flask, request, jsonify
import hashlib
import hmac
import base64
import json
import time
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SECRET_KEY'] = 'supersecretkey'
db = SQLAlchemy(app)


# 用户模型
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


with app.app_context():
    db.create_all()


# **手写 JWT 生成**
def generate_jwt(payload, secret):
    header = {"alg": "HS256", "typ": "JWT"}

    # Base64 编码 Header 和 Payload
    header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")

    # 计算 HMAC-SHA256 签名
    signature = hmac.new(secret.encode(), f"{header_b64}.{payload_b64}".encode(), hashlib.sha256).digest()
    signature_b64 = base64.urlsafe_b64encode(signature).decode().rstrip("=")

    return f"{header_b64}.{payload_b64}.{signature_b64}"


# **手写 JWT 解析**
def verify_jwt(token, secret):
    try:
        header_b64, payload_b64, signature_b64 = token.split(".")

        # 重新计算签名
        signature_check = hmac.new(secret.encode(), f"{header_b64}.{payload_b64}".encode(), hashlib.sha256).digest()
        expected_signature_b64 = base64.urlsafe_b64encode(signature_check).decode().rstrip("=")

        # 验证签名
        if expected_signature_b64 != signature_b64:
            return None

        # 解析 Payload
        payload_json = base64.urlsafe_b64decode(payload_b64 + "==").decode()
        payload = json.loads(payload_json)

        # 验证是否过期
        if payload.get("exp") and payload["exp"] < int(time.time()):
            return None

        return payload
    except Exception as e:
        return None


# **用户注册**
@app.route('/users', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Missing username or password"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "User already exists"}), 409

    user = User(username=username)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    return jsonify({"message": "User created successfully"}), 201


# **用户登录**
@app.route('/users/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid credentials"}), 403

    # 生成 JWT
    payload = {
        "user_id": user.id,
        "exp": int(time.time()) + 3600  # 1 小时有效期
    }
    token = generate_jwt(payload, app.config['SECRET_KEY'])

    return jsonify({"token": token}), 200


@app.route('/users', methods=['PUT'])
def change_password():
    data = request.get_json()
    username = data.get("username")
    old_password = data.get("old_password")  # 确保这里是 old_password，而不是 old-password
    new_password = data.get("new_password")

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(old_password):
        return jsonify({"error": "Invalid credentials"}), 403

    user.set_password(new_password)
    db.session.commit()

    return jsonify({"message": "Password updated successfully"}), 200

@app.route('/users/verify', methods=['POST'])
def verify_token():
    data = request.get_json()
    token = data.get("token")
    if not token:
        return jsonify({"error": "Token is required"}), 400
    try:
        payload = verify_jwt(token, app.config['SECRET_KEY'])
        if payload is None:
            return jsonify({"error": "Invalid token"}), 403
        return jsonify(payload), 200
    except Exception as e:
        app.logger.error(f"Token verification error: {str(e)}")
        return jsonify({"error": "Token verification error"}), 500

if __name__ == '__main__':
    app.run(port=8001, debug=True)
