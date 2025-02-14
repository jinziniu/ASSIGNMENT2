from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class URLMapping(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    shortid = db.Column(db.String(64), unique=True, nullable=False)
    long_url = db.Column(db.String(2048), nullable=False)
    user_id = db.Column(db.Integer, nullable=False)  # 绑定到用户
