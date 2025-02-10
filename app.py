from flask import Flask, request, jsonify, render_template, session, redirect, url_for
import mysql.connector
import bcrypt
import functools
import requests
from config import DEEPSEEK_API_KEY

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # 设置 session secret key

# 数据库连接配置
db_config = {
    "host": "1.1.1.8",
    "user": "notes_user",   # 你的 MySQL 用户名
    "password": "mydAFwXbxkydeM6B",  # 你的 MySQL 密码
    "database": "notes_app"
}

# 连接数据库
def get_db_connection():
    return mysql.connector.connect(**db_config)

# 登录验证装饰器
def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if session.get('user_id') is None:
            return redirect(url_for('login'))
        return view(**kwargs)
    return wrapped_view

@app.route("/test_db", methods=["GET"])
def test_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DATABASE();")
        db_name = cursor.fetchone()
        return jsonify({"status": "success", "database": db_name[0]})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.json.get('username')
        password = request.json.get('password')

        # 密码加密
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            sql = "INSERT INTO users (username, password) VALUES (%s, %s)"
            val = (username, hashed_password)
            cursor.execute(sql, val)
            conn.commit()

            # 获取用户ID
            user_id = cursor.lastrowid

            # 设置session
            session['user_id'] = user_id
            session['username'] = username

            return jsonify({'status': 'success', 'message': 'User registered successfully'})
        except Exception as e:
            conn.rollback()
            return jsonify({'status': 'error', 'message': str(e)})
        finally:
            cursor.close()
            conn.close()
    else:
        return render_template("register.html")

@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.json.get('username')
        password = request.json.get('password')

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            sql = "SELECT * FROM users WHERE username = %s"
            val = (username,)
            cursor.execute(sql, val)
            user = cursor.fetchone()

            if user:
                stored_password = user[2]  # 假设密码在第三列
                if bcrypt.checkpw(password.encode('utf-8'), stored_password.encode('utf-8')):
                    # 设置session
                    session['user_id'] = user[0]  # 假设用户ID在第一列
                    session['username'] = username
                    return jsonify({'status': 'success', 'message': 'Logged in successfully'})
                else:
                    return jsonify({'status': 'error', 'message': 'Invalid credentials'})
            else:
                return jsonify({'status': 'error', 'message': 'User not found'})
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)})
        finally:
            cursor.close()
            conn.close()
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    return redirect(url_for('index'))

@app.route("/add_memo", methods=['POST'])
@login_required
def add_memo():
    if request.method == 'POST':
        memo_title = request.json.get('memoTitle')
        memo_type = request.json.get('memoType')
        memo_date = request.json.get('memoDate')
        memo_remind_days = request.json.get('memoRemindDays')
        memo_content = request.json.get('memoContent')
        user_id = session.get('user_id')

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            sql = "INSERT INTO memos (memo_title, memo_type, memo_date, memo_remind_days, memo_content, user_id) VALUES (%s, %s, %s, %s, %s, %s)"
            val = (memo_title, memo_type, memo_date, memo_remind_days, memo_content, user_id)
            print(val)  # 打印 SQL 插入语句的值
            cursor.execute(sql, val)
            conn.commit()
            # 不再使用重定向，而是返回 JSON 响应
            return jsonify({'status': 'success', 'message': '备忘添加成功'})
        except Exception as e:
            conn.rollback()
            return jsonify({'status': 'error', 'message': str(e)})
        finally:
            cursor.close()
            conn.close()
    else:
        return jsonify({'status': 'error', 'message': 'Method not allowed'})

@app.route("/memo/<int:memo_id>")
@login_required
def memo(memo_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = "SELECT * FROM memos WHERE id = %s AND user_id = %s"
        val = (memo_id, session.get('user_id'))
        cursor.execute(sql, val)
        memo = cursor.fetchone()

        if memo:
            memo = {
                'id': memo[0],
                'memo_title': memo[1],
                'memo_type': memo[2],
                'memo_date': memo[3],
                'memo_remind_days': memo[4],
                'memo_content': memo[5]
            }
            return render_template("memo.html", memo=memo)
        else:
            return render_template("error.html", message="备忘不存在")
    except Exception as e:
        print(str(e))
        return render_template("error.html", message="发生错误")
    finally:
        cursor.close()
        conn.close()

@app.route("/memo/edit/<int:memo_id>")
@login_required
def edit_memo(memo_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = "SELECT * FROM memos WHERE id = %s AND user_id = %s"
        val = (memo_id, session.get('user_id'))
        cursor.execute(sql, val)
        memo = cursor.fetchone()

        if memo:
            memo = {
                'id': memo[0],
                'memo_title': memo[1],
                'memo_type': memo[2],
                'memo_date': memo[3],
                'memo_remind_days': memo[4],
                'memo_content': memo[5]
            }
            return render_template("edit_memo.html", memo=memo)
        else:
            return render_template("error.html", message="备忘不存在")
    except Exception as e:
        print(str(e))
        return render_template("error.html", message="发生错误")
    finally:
        cursor.close()
        conn.close()

@app.route("/memo/update/<int:memo_id>", methods=['POST'])
@login_required
def update_memo(memo_id):
    try:
        memo_title = request.form.get('memoTitle')
        memo_type = request.form.get('memoType')
        memo_date = request.form.get('memoDate')
        memo_remind_days = request.form.get('memoRemindDays')
        memo_content = request.form.get('memoContent')
        user_id = session.get('user_id')

        conn = get_db_connection()
        cursor = conn.cursor()
        sql = """
            UPDATE memos 
            SET memo_title = %s, memo_type = %s, memo_date = %s, 
                memo_remind_days = %s, memo_content = %s 
            WHERE id = %s AND user_id = %s
        """
        val = (memo_title, memo_type, memo_date, memo_remind_days, 
               memo_content, memo_id, user_id)
        cursor.execute(sql, val)
        conn.commit()
        
        return redirect(url_for('memo', memo_id=memo_id))
    except Exception as e:
        print(str(e))
        return render_template("error.html", message="更新失败")
    finally:
        cursor.close()
        conn.close()

@app.route("/memo/delete/<int:memo_id>")
@login_required
def delete_memo(memo_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = "DELETE FROM memos WHERE id = %s AND user_id = %s"
        val = (memo_id, session.get('user_id'))
        cursor.execute(sql, val)
        conn.commit()
        return redirect(url_for('index'))
    except Exception as e:
        print(str(e))
        return "发生错误"
    finally:
        cursor.close()
        conn.close()

@app.route("/analyze_memos", methods=['POST'])
@login_required
def analyze_memos():
    memo_ids = request.json.get('memo_ids')
    
    try:
        # 获取选中的备忘录内容
        conn = get_db_connection()
        cursor = conn.cursor()
        placeholders = ','.join(['%s'] * len(memo_ids))
        sql = f"SELECT memo_title, memo_content FROM memos WHERE id IN ({placeholders}) AND user_id = %s"
        val = memo_ids + [session.get('user_id')]
        cursor.execute(sql, val)
        memos = cursor.fetchall()
        
        # 准备发送给 Deepseek API 的内容
        memo_texts = [f"标题：{memo[0]}\n内容：{memo[1]}" for memo in memos]
        combined_text = "\n\n".join(memo_texts)
        
        # 调用 Deepseek API
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {
                    "role": "user",
                    "content": f"请分析以下备忘录内容，并提供见解：\n\n{combined_text}"
                }
            ]
        }
        
        response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            json=payload,
            headers=headers
        )
        
        if response.status_code == 200:
            analysis = response.json()["choices"][0]["message"]["content"]
            return jsonify({"status": "success", "analysis": analysis})
        else:
            return jsonify({"status": "error", "message": "API 调用失败"})
            
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})
    finally:
        cursor.close()
        conn.close()

@app.route("/")
def index():
    user_id = session.get('user_id')
    if user_id:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            sql = "SELECT * FROM memos WHERE user_id = %s"
            val = (user_id,)
            cursor.execute(sql, val)
            memos = cursor.fetchall()
            # 将查询结果转换为字典列表
            memos = [
                {
                    'id': memo[0],
                    'memo_title': memo[1],
                    'memo_type': memo[2],
                    'memo_date': memo[3],
                    'memo_remind_days': memo[4],
                    'memo_content': memo[5]
                }
                for memo in memos
            ]
        except Exception as e:
            memos = []
            print(str(e))
        finally:
            cursor.close()
            conn.close()
    else:
        memos = []
    return render_template("index.html", memos=memos)

if __name__ == "__main__":
    app.run(debug=True)
