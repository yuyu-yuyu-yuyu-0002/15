from flask import Flask, request, jsonify
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, firestore
import os
import hashlib

app = Flask(__name__)
CORS(app)

# Firebase 配置字典 (簡化版本)
FIREBASE_CONFIGS = {}
FIREBASE_APPS = {}

# 初始化多個 Firebase 應用
def init_firebase_apps():
    for i in range(100):  # 100個分片
        app_name = f"ai-card-{i}"
        # 實際部署時需要每個專案的 service account key
        # 這裡用環境變數或配置檔案
        try:
            cred = credentials.Certificate({
                "type": "service_account",
                "project_id": f"ai-card-{i}",
                # ... 其他憑證資訊
            })
            firebase_app = firebase_admin.initialize_app(cred, name=app_name)
            FIREBASE_APPS[i] = firebase_app
        except:
            pass  # 跳過未配置的分片

# 獲取分片索引
def get_shard_index(user_id):
    return user_id // 10000

# 獲取 Firestore 客戶端
def get_firestore_client(shard_index):
    if shard_index in FIREBASE_APPS:
        return firestore.client(FIREBASE_APPS[shard_index])
    return None

@app.route('/api/register', methods=['POST'])
def register_user():
    data = request.get_json()
    user_id = data.get('user_id')
    user_data = data.get('user_data')
    
    # 計算分片
    shard_index = get_shard_index(user_id)
    
    # 獲取對應的 Firestore 客戶端
    db = get_firestore_client(shard_index)
    if not db:
        return jsonify({'error': 'Database not available'}), 500
    
    try:
        # 儲存用戶資料
        doc_ref = db.collection('users').document(str(user_id))
        doc_ref.set(user_data)
        
        return jsonify({
            'success': True,
            'shard_index': shard_index,
            'user_id': user_id
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/user/<int:user_id>', methods=['GET'])
def get_user(user_id):
    shard_index = get_shard_index(user_id)
    db = get_firestore_client(shard_index)
    
    if not db:
        return jsonify({'error': 'Database not available'}), 500
    
    try:
        doc = db.collection('users').document(str(user_id)).get()
        if doc.exists:
            return jsonify({
                'success': True,
                'data': doc.to_dict(),
                'shard_index': shard_index
            })
        else:
            return jsonify({'error': 'User not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/search', methods=['GET'])
def search_users():
    query = request.args.get('q', '')
    results = []
    
    # 搜尋所有分片 (簡化版本，實際可優化)
    for shard_index in range(100):
        db = get_firestore_client(shard_index)
        if db:
            try:
                docs = db.collection('users').where('name', '>=', query).limit(10).stream()
                for doc in docs:
                    data = doc.to_dict()
                    data['user_id'] = doc.id
                    data['shard_index'] = shard_index
                    results.append(data)
            except:
                continue
    
    return jsonify({'results': results})

@app.route('/api/shard-info/<int:user_id>', methods=['GET'])
def get_shard_info(user_id):
    shard_index = get_shard_index(user_id)
    return jsonify({
        'user_id': user_id,
        'shard_index': shard_index,
        'firebase_project': f'ai-card-{shard_index}',
        'mega_account': f'mega-{shard_index}'
    })

if __name__ == '__main__':
    init_firebase_apps()
    app.run(debug=True, port=5000)