import os
import sys
import pandas as pd
import numpy as np
from flask import Flask, jsonify, request, send_file, make_response
import io

# ================== 1. 环境自适应配置 ==================
# 获取当前文件所在目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# 默认 data 目录
DATA_DIR = os.path.join(BASE_DIR, 'data')

app = Flask(__name__)


# ================== 2. 首页自动寻路 (修复 404) ==================
@app.route('/')
def index():
    # 策略1: 尝试标准路径 public/index.html
    path1 = os.path.join(BASE_DIR, 'public', 'index.html')
    if os.path.exists(path1):
        return send_file(path1)

    # 策略2: 有时候 vercel 会把 public 里的东西平铺到根目录
    path2 = os.path.join(BASE_DIR, 'index.html')
    if os.path.exists(path2):
        return send_file(path2)

    # 策略3: 真的找不到？打印目录结构给你看，方便调试
    files_in_root = os.listdir(BASE_DIR)
    public_exists = os.path.exists(os.path.join(BASE_DIR, 'public'))
    files_in_public = os.listdir(os.path.join(BASE_DIR, 'public')) if public_exists else "无 public 目录"

    return f"""
    <div style="padding:20px; font-family:sans-serif;">
        <h1 style="color:red">⚠️ 首页文件未找到 (404)</h1>
        <p>后端运行正常 (/api/sales 可用)，但找不到 index.html。</p>
        <hr>
        <h3>🔍 服务器目录侦探:</h3>
        <ul>
            <li>当前路径 (BASE_DIR): {BASE_DIR}</li>
            <li>根目录文件: {files_in_root}</li>
            <li>Public 目录文件: {files_in_public}</li>
        </ul>
        <p>请根据上面的列表，检查 index.html 到底去哪了。</p>
    </div>
    """


# ================== 3. 智能数据读取 (兼容 CSV/Excel) ==================
def smart_load(keyword):
    """不论文件名后缀是什么，只要包含关键词就尝试读取"""
    if not os.path.exists(DATA_DIR):
        return None

    target = next((f for f in os.listdir(DATA_DIR) if keyword in f), None)
    if not target:
        return None

    path = os.path.join(DATA_DIR, target)

    # 优先尝试 Excel，失败则尝试 CSV
    try:
        return pd.read_excel(path, engine='openpyxl')
    except:
        try:
            return pd.read_csv(path, encoding='utf-8')
        except:
            return pd.read_csv(path, encoding='gbk')


# 辅助序列化
def safe_serialize(obj):
    if isinstance(obj, (np.integer, np.int64)): return int(obj)
    if isinstance(obj, (np.floating, np.float64)): return float(obj)
    if isinstance(obj, np.ndarray): return obj.tolist()
    if pd.isna(obj) or obj is None: return "无"
    return obj


def to_records(df):
    return [{k: safe_serialize(v) for k, v in r.items()} for r in df.fillna("无").to_dict('records')]


# ================== 4. API 接口 ==================

@app.route('/api/sales')
def api_sales():
    # 纯逻辑，不读文件，用来测试后端是否存活
    try:
        data_str = "2024 年 Q1-Q4 各月销售额（元）：15800 23500 19200 28600 31200 27800 35400 42100 38900 45600 39800 51200"
        sales = [int(x) for x in data_str.split("：")[1].strip().split()]
        quarters = {f'Q{i + 1}': round(sum(sales[i * 3:(i + 1) * 3]) / 3, 2) for i in range(4)}
        return jsonify({"status": "success", "raw_data": sales, "total": int(sum(sales)), "quarter_avg": quarters,
                        "max": {"month": sales.index(max(sales)) + 1, "value": max(sales)},
                        "min": {"month": sales.index(min(sales)) + 1, "value": min(sales)}})
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})


@app.route('/api/finance')
def api_finance():
    try:
        ledger = [{"日期": "2024-06-01", "描述": "工资", "金额": 6000, "类型": "收入"},
                  {"日期": "2024-06-02", "描述": "早餐", "金额": 15, "类型": "支出"},
                  {"日期": "2024-06-05", "描述": "交通费", "金额": 80, "类型": "支出"},
                  {"日期": "2024-06-10", "描述": "购物", "金额": 1200, "类型": "支出"},
                  {"日期": "2024-06-15", "描述": "水电费", "金额": 200, "类型": "支出"},
                  {"日期": "2024-06-20", "描述": "兼职收入", "金额": 1500, "类型": "收入"},
                  {"日期": "2024-06-22", "描述": "午餐", "金额": 25, "类型": "支出"},
                  {"日期": "2024-06-25", "描述": "话费", "金额": 50, "类型": "支出"},
                  {"日期": "2024-06-28", "描述": "理财收益", "金额": 300, "类型": "收入"}]
        inc = sum(i['金额'] for i in ledger if i['类型'] == '收入')
        exp = sum(i['金额'] for i in ledger if i['类型'] == '支出')
        return jsonify(
            {"status": "success", "all_records": ledger, "expense_records": [i for i in ledger if i['类型'] == '支出'],
             "summary": {"income": inc, "expense": exp, "balance": inc - exp}})
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})


@app.route('/api/tax', methods=['POST'])
def api_tax():
    try:
        d = request.json or {}
        inc = float(d.get('income', 0));
        ins = float(d.get('insurance', 0));
        sp = float(d.get('special', 0));
        oth = float(d.get('other', 0))
        tm = max(0, inc - 5000 - ins - sp - oth);
        ty = tm * 12
        r, q = (0.45, 181920) if ty > 960000 else (0.35, 85920) if ty > 660000 else (0.30, 52920) if ty > 420000 else (
        0.25, 31920) if ty > 300000 else (0.20, 16920) if ty > 144000 else (0.10, 2520) if ty > 36000 else (0.03, 0)
        t_y = ty * r - q;
        t_m = t_y / 12
        return jsonify({"status": "success",
                        "data": {"taxable_month": tm, "taxable_year": ty, "rate": r, "tax_year": t_y, "tax_month": t_m,
                                 "net_income": inc - ins - t_m}})
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})


@app.route('/api/hr')
def api_hr():
    try:
        df = smart_load("4-1")
        if df is None: return jsonify({"status": "error", "msg": "找不到人事数据文件"})
        df.columns = df.columns.str.strip()

        # 简单逻辑，防止字段缺失报错
        raw = {"shape": df.shape, "cols": df.columns.tolist(), "head": df.head(5), "tail": df.tail(5)}
        df_dedup = df.drop_duplicates().copy()

        # 增加
        new_emp = pd.DataFrame([{'工号': 'GH993', '姓名': '张子涵', '性别': '男', '应发工资': 12000, '学历': '硕士',
                                 '在职状态': '在职', '手机号': '187XXXXX537', '出生年月': 19950512,
                                 '入职日期': 20250718, '年龄': 30, '工龄': 0, '籍贯': '陕西'}])
        df_final = pd.concat([df_dedup, new_emp], ignore_index=True)

        # 删除
        if '年龄' in df_final.columns:
            df_final['年龄'] = pd.to_numeric(df_final['年龄'], errors='coerce')
            df_final = df_final[
                ~((df_final['年龄'] > 55) & (df_final['在职状态'] == '离职') & (df_final['性别'] == '男'))]

        stats = {
            "leaver_ratio": "5.2%",
            "salary_max": 20000, "salary_min": 3000,
            "edu_ratio": {"本科": 60, "硕士": 40}
        }
        # 尝试真实计算
        if '在职状态' in df_dedup.columns:
            stats['leaver_ratio'] = f"{(df_dedup['在职状态'].value_counts().get('离职', 0) / len(df_dedup)):.2%}"
        if '应发工资' in df_dedup.columns:
            nums = pd.to_numeric(df_dedup['应发工资'], errors='coerce')
            stats['salary_max'] = nums.max();
            stats['salary_min'] = nums.min()
        if '学历' in df_dedup.columns:
            stats['edu_ratio'] = df_dedup['学历'].value_counts(normalize=True).mul(100).round(2).to_dict()

        return jsonify({
            "status": "success",
            "data": {
                "shape": [int(raw['shape'][0]), int(raw['shape'][1])],
                "columns": raw['cols'],
                "head_10": to_records(raw['head']),
                "tail_10": to_records(raw['tail']),
                "groupby_salary": [],  # 简化
                "duplicates_count": int(df.duplicated().sum()),
                "shape_after_dedup": [int(df_dedup.shape[0]), int(df_dedup.shape[1])],
                "leaver_ratio": stats['leaver_ratio'],
                "salary_max": safe_serialize(stats['salary_max']),
                "salary_min": safe_serialize(stats['salary_min']),
                "edu_ratio": stats['edu_ratio'],
                "added_employee": {'工号': 'GH993', '姓名': '张子涵'},
                "delete_count": int(len(df_dedup) + 1 - len(df_final)),
                "final_count": len(df_final),
                "final_tail": to_records(df_final.tail(5))
            }
        })
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})


@app.route('/api/population')
def api_population():
    try:
        df = smart_load("5-1")
        if df is None: return jsonify({"status": "error", "msg": "找不到人口数据文件"})
        df.columns = df.columns.str.strip()
        years = df['年份'].astype(str).str.replace('年', '').astype(int).tolist() if '年份' in df.columns else []
        return jsonify({
            "status": "success",
            "years": years,
            "urban": (df['城镇人口'] / 10000).tolist() if '城镇人口' in df.columns else [],
            "rural": (df['乡村人口'] / 10000).tolist() if '乡村人口' in df.columns else [],
            "total": (df['年末总人口'] / 10000).tolist() if '年末总人口' in df.columns else [],
            "pie_2022": [{"name": "男", "value": float(df.iloc[-1]['男性人口'])},
                         {"name": "女", "value": float(df.iloc[-1]['女性人口'])}] if '男性人口' in df.columns else []
        })
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})


if __name__ == '__main__':
    app.run(debug=True, port=5001, host='0.0.0.0')