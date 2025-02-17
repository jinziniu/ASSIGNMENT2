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
app.config['SECRET_KEY'] = 'supersecretkey'
db.init_app(app)

with app.app_context():
    db.create_all()

def verify_jwt_remote(token):
    try:
        auth_url = "http://localhost:8001/users/verify"
        response = requests.post(auth_url, json={"token": token})
        if response.status_code == 200:
            return response.json()
        else:
            app.logger.error(f"Auth service verification failed: {response.text}")
            return None
    except requests.RequestException as e:
        app.logger.error(f"Error contacting auth service: {str(e)}")
        return None


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

        return jsonify({"error": "Internal Server Error"}), 500


    return '', 404


@app.route('/<short_id>', methods=['GET'])
def get_long_url(short_id):
    try:
        mapping = URLMapping.query.filter_by(shortid=short_id).first()
        if not mapping:
            return jsonify({"error": "Not found"}), 404

        return jsonify({"value": mapping.long_url}), 301
    except Exception as e:
        app.logger.error(f"Error in get_long_url for {short_id}: {e}")
        return jsonify({"error": "Internal Server Error"}), 500



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

       
        data = request.get_json(force=True, silent=True) or request.form


        new_url = data.get("url") or data.get("value")
        if not new_url:
            return jsonify({"error": "Invalid request data"}), 400


        if not (new_url.startswith("http://") or new_url.startswith("https://")):
            return jsonify({"error": "Invalid URL"}), 400

        mapping.long_url = new_url
        db.session.commit()
        return jsonify({"message": "Updated"}), 200
    except Exception as e:
        app.logger.error(f"Error updating URL {short_id}: {e}")
        return jsonify({"error": "Internal Server Error"}), 500





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
