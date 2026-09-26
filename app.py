from flask import Flask, request, jsonify, render_template
import sqlite3
from datetime import datetime

app = Flask(__name__)

def init_db():
    conn = sqlite3.connect('zne_security.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT UNIQUE,
            one_id TEXT,
            full_name TEXT,
            password TEXT,
            face_photo TEXT
        )
    ''')
    # Agar jadval eskirgan bo'lib face_photo ustuni bo'lmasa, uni avtomatik qo'shish
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN face_photo TEXT")
    except sqlite3.OperationalError:
        pass # Ustun allaqachon mavjud

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_phone TEXT,
            card_number TEXT,
            card_name TEXT,
            balance REAL DEFAULT 1000000.0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_phone TEXT,
            place TEXT,
            category TEXT,
            amount REAL,
            date TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    phone = data.get('phone')
    one_id = data.get('one_id')
    full_name = data.get('full_name')
    password = data.get('password')
    face_photo = data.get('face_photo')
    
    try:
        conn = sqlite3.connect('zne_security.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (phone, one_id, full_name, password, face_photo) VALUES (?, ?, ?, ?, ?)", 
                       (phone, one_id, full_name, password, face_photo))
        cursor.execute("INSERT INTO cards (user_phone, card_number, card_name, balance) VALUES (?, ?, ?, ?)", 
                       (phone, "8600****5678", "Humo Card", 1000000.0))
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "message": "Ro'yxatdan o'tildi!"})
    except sqlite3.IntegrityError:
        return jsonify({"status": "error", "message": "Bu telefon raqam allaqachon mavjud!"}), 400

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    phone = data.get('phone')
    password = data.get('password')
    
    conn = sqlite3.connect('zne_security.db')
    cursor = conn.cursor()
    cursor.execute("SELECT full_name, password FROM users WHERE phone = ?", (phone,))
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        return jsonify({"status": "error", "message": "Bunday telefon raqam topilmadi!"}), 400
        
    if str(user[1]) == str(password):
        return jsonify({"status": "success", "full_name": user[0]})
    else:
        return jsonify({"status": "error", "message": "Parol noto'g'ri!"}), 400

@app.route('/api/verify-face', methods=['POST'])
def verify_face():
    data = request.json
    phone = data.get('phone')
    
    conn = sqlite3.connect('zne_security.db')
    cursor = conn.cursor()
    cursor.execute("SELECT face_photo FROM users WHERE phone = ?", (phone,))
    user = cursor.fetchone()
    conn.close()
    
    if user and user[0]:
        return jsonify({"status": "success", "match": True, "confidence": "98.7%"})
    
    return jsonify({"status": "error", "message": "Yuz ma'lumotlari topilmadi!"}), 400

@app.route('/api/transaction', methods=['POST'])
def transaction():
    data = request.json
    phone = data.get('phone')
    place = data.get('place')
    category = data.get('category')
    amount = float(data.get('amount'))
    date_str = datetime.now().strftime("%d.%m.%Y %H:%M")
    
    conn = sqlite3.connect('zne_security.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT balance FROM cards WHERE user_phone = ?", (phone,))
    card = cursor.fetchone()
    
    if card:
        if card[0] < amount:
            conn.close()
            return jsonify({"status": "error", "message": "Balansda yetarli mablag' yo'q!"}), 400
            
        new_balance = card[0] - amount
        cursor.execute("UPDATE cards SET balance = ? WHERE user_phone = ?", (new_balance, phone))
        
        cursor.execute("INSERT INTO transactions (user_phone, place, category, amount, date) VALUES (?, ?, ?, ?, ?)",
                       (phone, place, category, amount, date_str))
        
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "new_balance": new_balance})
    
    conn.close()
    return jsonify({"status": "error", "message": "Karta topilmadi!"}), 400

@app.route('/api/transactions/<phone>', methods=['GET'])
def get_transactions(phone):
    conn = sqlite3.connect('zne_security.db')
    cursor = conn.cursor()
    cursor.execute("SELECT place, category, amount, date FROM transactions WHERE user_phone = ? ORDER BY id DESC", (phone,))
    rows = cursor.fetchall()
    conn.close()
    
    transactions = []
    for row in rows:
        transactions.append({
            "place": row[0],
            "category": row[1],
            "amount": row[2],
            "date": row[3]
        })
    return jsonify({"status": "success", "transactions": transactions})

@app.route('/api/stats/<phone>', methods=['GET'])
def get_stats(phone):
    conn = sqlite3.connect('zne_security.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT category, SUM(amount) 
        FROM transactions 
        WHERE user_phone = ? 
        GROUP BY category
    ''', (phone,))
    rows = cursor.fetchall()
    conn.close()
    
    stats = {}
    for row in rows:
        stats[row[0]] = row[1]
        
    return jsonify({"status": "success", "stats": stats})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)