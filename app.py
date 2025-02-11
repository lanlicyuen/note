from flask import Flask, request, jsonify, render_template, session, redirect, url_for
import mysql.connector
import bcrypt
import functools
import requests
from openai import OpenAI
from config import (
    DEEPSEEK_API_KEY, 
    WEATHER_API_KEY, 
    DB_CONFIG, 
    SECRET_KEY
)

app = Flask(__name__)
app.secret_key = SECRET_KEY

# 连接数据库
def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)

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

# 创建 OpenAI 客户端
client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"
)

@app.route("/analyze_memo/<int:memo_id>", methods=['POST'])
@login_required
def analyze_memo(memo_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = "SELECT memo_title, memo_type, memo_date, memo_content FROM memos WHERE id = %s AND user_id = %s"
        val = (memo_id, session.get('user_id'))
        cursor.execute(sql, val)
        memo = cursor.fetchone()
        
        if not memo:
            return jsonify({"status": "error", "message": "备忘不存在"})
        
        # 提取地点信息（简单示例，实际应使用更复杂的NLP）
        content = memo[3].lower()
        location = None
        for city in ["北京", "上海", "广州", "深圳"]:  # 可以扩展城市列表
            if city in content:
                location = city
                break
        
        # 构建提示词
        prompt = f"""
分析以下备忘录内容：
标题：{memo[0]}
类型：{memo[1]}
日期：{memo[2]}
内容：{memo[3]}

请从以下几个方面提供建议：
1. 识别内容中的关键词并提供相关建议
2. 基于日期和类型提供合适的时间建议
"""
        
        # 如果检测到地点，添加地点相关提示
        if location:
            prompt += f"""
3. 针对地点 {location} 的具体建议：
   - 交通方式和路线规划
   - 适合的活动场所和地点
   - 当地特色推荐
   - 需要提前准备的事项
"""
        
        # 构建提示词
        messages = [
            {
                "role": "system", 
                "content": "你是一个专业的备忘录分析助手。请直接分析内容中的关键信息，提供具体且实用的建议，避免笼统的评价。如果发现与时间、地点、人物相关的信息，请给出针对性的详细建议。"
            },
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                stream=False
            )
            analysis = response.choices[0].message.content
            
            # 如果有地点信息，尝试获取天气信息
            if location:
                try:
                    weather_info = get_weather(location, memo[2])
                    if "失败" not in weather_info and "超出" not in weather_info:
                        analysis += f"\n\n当前天气信息：\n{weather_info}"
                    else:
                        analysis += f"\n\n天气信息：{weather_info}"
                except Exception as weather_error:
                    analysis += f"\n\n天气信息：获取失败 ({str(weather_error)})"
            
            return jsonify({"status": "success", "analysis": analysis})
            
        except Exception as api_error:
            print(f"API error: {str(api_error)}")
            return jsonify({
                "status": "error",
                "message": f"AI API 调用失败：{str(api_error)}"
            })
            
    except Exception as e:
        print(f"General error: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"系统错误：{str(e)}"
        })
    finally:
        cursor.close()
        conn.close()

@app.route("/save_analysis", methods=['POST'])
@login_required
def save_analysis():
    try:
        memo_id = request.json.get('memo_id')
        analysis_content = request.json.get('analysis_content')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        sql = "INSERT INTO analysis_records (memo_id, analysis_content) VALUES (%s, %s)"
        val = (memo_id, analysis_content)
        cursor.execute(sql, val)
        conn.commit()
        
        return jsonify({"status": "success", "message": "分析结果已保存"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})
    finally:
        cursor.close()
        conn.close()

@app.route("/analysis_history/<int:memo_id>")
@login_required
def analysis_history(memo_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        sql = """
            SELECT ar.* FROM analysis_records ar
            JOIN memos m ON ar.memo_id = m.id
            WHERE m.id = %s AND m.user_id = %s
            ORDER BY ar.created_at DESC
        """
        val = (memo_id, session.get('user_id'))
        cursor.execute(sql, val)
        records = cursor.fetchall()
        
        formatted_records = [{
            'id': record[0],
            'analysis_content': record[2],
            'created_at': record[3].strftime('%Y-%m-%d %H:%M:%S')
        } for record in records]
        
        return jsonify({
            "status": "success",
            "records": formatted_records
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})
    finally:
        cursor.close()
        conn.close()

def get_weather(city, date):
    try:
        response = requests.get(
            f"https://api.weatherapi.com/v1/forecast.json",
            params={
                "key": WEATHER_API_KEY,
                "q": city,
                "dt": date
            },
            timeout=5  # 设置5秒超时
        )
        print(f"Weather API Response: {response.text}")  # 调试日志
        
        if response.status_code == 200:
            data = response.json()
            if 'forecast' in data and 'forecastday' in data['forecast'] and data['forecast']['forecastday']:
                forecast = data['forecast']['forecastday'][0]['day']
                return f"""
天气：{forecast.get('condition', {}).get('text', '未知')}
温度：{forecast.get('avgtemp_c', '未知')}°C
降水概率：{forecast.get('daily_chance_of_rain', '未知')}%
"""
            else:
                return "暂无该日期天气预报信息"
        elif response.status_code == 400:
            return "日期超出预报范围（最多支持14天预报）"
        else:
            return f"天气信息获取失败（HTTP {response.status_code}：{response.text}）"
    except requests.exceptions.Timeout:
        return "天气 API 连接超时"
    except requests.exceptions.ConnectionError:
        return "天气 API 连接失败，请检查网络"
    except Exception as e:
        print(f"Weather API error: {str(e)}")  # 调试日志
        return f"天气信息获取失败：{str(e)}"

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
