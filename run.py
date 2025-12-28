import os
import sys
import pandas as pd
import numpy as np
from flask import Flask, jsonify, request, send_from_directory, send_file
import io

print("=" * 50)
print("正在启动 Python 数据分析服务 (高颜值试卷版)...")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
PUBLIC_DIR = os.path.join(BASE_DIR, 'public')

# 自检
required_files = ["4-1公司人事财务数据.xlsx", "5-1人口数据.xlsx"]
for f in required_files:
    if not os.path.exists(os.path.join(DATA_DIR, f)):
        print(f"❌ 严重错误: data 目录下缺失文件 {f}")
        sys.exit(1)
print("✅ 文件完整性检查通过")
print("=" * 50)

app = Flask(__name__, static_folder=PUBLIC_DIR)


def safe_serialize(obj):
    if isinstance(obj, (np.integer, np.int64)): return int(obj)
    if isinstance(obj, (np.floating, np.float64)): return float(obj)
    if isinstance(obj, np.ndarray): return obj.tolist()
    if pd.isna(obj) or obj is None: return "无"
    return obj


def process_df_to_records(df):
    df_filled = df.fillna("无")
    records = df_filled.to_dict(orient='records')
    return [{k: safe_serialize(v) for k, v in r.items()} for r in records]


@app.route('/')
def index():
    return send_from_directory(PUBLIC_DIR, 'index.html')


# --- 1-1 销售 ---
@app.route('/api/sales')
def api_sales():
    try:
        data_str = "2024 年 Q1-Q4 各月销售额（元）：15800 23500 19200 28600 31200 27800 35400 42100 38900 45600 39800 51200"
        sales = [int(x) for x in data_str.split("：")[1].strip().split()]
        quarters = {f'Q{i + 1}': round(sum(sales[i * 3:(i + 1) * 3]) / 3, 2) for i in range(4)}
        return jsonify({
            "status": "success",
            "raw_data": sales,
            "total": int(sum(sales)),
            "max": {"month": int(sales.index(max(sales)) + 1), "value": int(max(sales))},
            "min": {"month": int(sales.index(min(sales)) + 1), "value": int(min(sales))},
            "quarter_avg": quarters
        })
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)}), 500


# --- 2-1 财务 ---
@app.route('/api/finance')
def api_finance():
    try:
        ledger = [
            {"日期": "2024-06-01", "描述": "工资", "金额": 6000, "类型": "收入"},
            {"日期": "2024-06-02", "描述": "早餐", "金额": 15, "类型": "支出"},
            {"日期": "2024-06-05", "描述": "交通费", "金额": 80, "类型": "支出"},
            {"日期": "2024-06-10", "描述": "购物", "金额": 1200, "类型": "支出"},
            {"日期": "2024-06-15", "描述": "水电费", "金额": 200, "类型": "支出"},
            {"日期": "2024-06-20", "描述": "兼职收入", "金额": 1500, "类型": "收入"},
            {"日期": "2024-06-22", "描述": "午餐", "金额": 25, "类型": "支出"},
            {"日期": "2024-06-25", "描述": "话费", "金额": 50, "类型": "支出"},
            {"日期": "2024-06-28", "描述": "理财收益", "金额": 300, "类型": "收入"},
        ]
        total_in = sum(i['金额'] for i in ledger if i['类型'] == "收入")
        total_out = sum(i['金额'] for i in ledger if i['类型'] == "支出")
        return jsonify({
            "status": "success",
            "all_records": ledger,
            "expense_records": [i for i in ledger if i['类型'] == "支出"],
            "summary": {"income": total_in, "expense": total_out, "balance": total_in - total_out}
        })
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)}), 500


# --- 3-1 个税 ---
@app.route('/api/tax', methods=['POST'])
def api_tax():
    try:
        d = request.json
        income = float(d.get('income', 0))
        insurance = float(d.get('insurance', 0))
        special = float(d.get('special', 0))
        other = float(d.get('other', 0))

        taxable_month = max(0, income - 5000 - insurance - special - other)
        taxable_year = taxable_month * 12

        if taxable_year <= 36000:
            r, q = 0.03, 0
        elif taxable_year <= 144000:
            r, q = 0.10, 2520
        elif taxable_year <= 300000:
            r, q = 0.20, 16920
        elif taxable_year <= 420000:
            r, q = 0.25, 31920
        elif taxable_year <= 660000:
            r, q = 0.30, 52920
        elif taxable_year <= 960000:
            r, q = 0.35, 85920
        else:
            r, q = 0.45, 181920

        tax_year = taxable_year * r - q
        tax_month = tax_year / 12
        net = income - insurance - tax_month

        return jsonify({
            "status": "success",
            "data": {
                "taxable_month": taxable_month,
                "taxable_year": taxable_year,
                "rate": r,
                "quick_deduction": q,
                "tax_year": tax_year,
                "tax_month": tax_month,
                "net_income": net
            }
        })
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)}), 500


# --- 4-1 HR 数据 ---
def process_hr_logic():
    path = os.path.join(DATA_DIR, "4-1公司人事财务数据.xlsx")
    df = pd.read_excel(path, header=1, engine='openpyxl')
    df.columns = df.columns.str.strip()

    raw_info = {"shape": df.shape, "head": df.head(10), "tail": df.tail(10), "cols": df.columns.tolist()}

    df_calc = df.copy()
    df_calc['应发工资'] = pd.to_numeric(df_calc['应发工资'], errors='coerce')
    gb = df_calc.dropna(subset=['应发工资']).groupby(['学历', '性别'])['应发工资'].mean().reset_index().round(2)

    dup_count = int(df.duplicated().sum())
    df_dedup = df.drop_duplicates().copy()
    dedup_shape = df_dedup.shape

    counts = df_dedup['在职状态'].value_counts()
    leaver_ratio = counts.get('离职', 0) / len(df_dedup)

    df_dedup['应发工资'] = pd.to_numeric(df_dedup['应发工资'], errors='coerce')
    max_salary = df_dedup['应发工资'].max()
    min_salary = df_dedup['应发工资'].min()
    edu_ratio = df_dedup['学历'].value_counts(normalize=True).mul(100).round(2).to_dict()

    new_emp = pd.DataFrame([{
        '工号': 'GH993', '姓名': '张子涵', '性别': '男',
        '应发工资': 12000, '学历': '硕士', '在职状态': '在职',
        '手机号': '187XXXXX537', '出生年月': 19950512, '入职日期': 20250718,
        '年龄': 30, '工龄': 0, '籍贯': '陕西'
    }])
    df_added = pd.concat([df_dedup, new_emp], ignore_index=True)

    df_added['年龄'] = pd.to_numeric(df_added['年龄'], errors='coerce')
    cond = (df_added['年龄'] > 55) & (df_added['在职状态'] == '离职') & (df_added['性别'] == '男')
    del_count = int(cond.sum())
    df_final = df_added[~cond].copy()

    # 最终预览数据 (重点：展示最后几行看新增员工)
    final_head = df_final.head(5)
    final_tail = df_final.tail(5)

    return {
        "raw_info": raw_info,
        "gb_data": gb,
        "clean_info": {"dup_count": dup_count, "dedup_shape": dedup_shape},
        "stats": {"leaver_ratio": leaver_ratio, "max": max_salary, "min": min_salary, "edu_ratio": edu_ratio},
        "crud_info": {"del_count": del_count, "final_count": len(df_final)},
        "final_df": df_final.fillna("无"),
        "final_preview": {"head": final_head, "tail": final_tail}
    }


@app.route('/api/hr')
def api_hr():
    try:
        res = process_hr_logic()
        raw = res['raw_info']
        return jsonify({
            "status": "success",
            "data": {
                "shape": [int(raw['shape'][0]), int(raw['shape'][1])],
                "columns": raw['cols'],
                "head_10": process_df_to_records(raw['head']),
                "tail_10": process_df_to_records(raw['tail']),
                "groupby_salary": process_df_to_records(res['gb_data']),
                "duplicates_count": res['clean_info']['dup_count'],
                "shape_after_dedup": [int(res['clean_info']['dedup_shape'][0]),
                                      int(res['clean_info']['dedup_shape'][1])],
                "leaver_ratio": f"{res['stats']['leaver_ratio']:.2%}",
                "salary_max": safe_serialize(res['stats']['max']),
                "salary_min": safe_serialize(res['stats']['min']),
                "edu_ratio": res['stats']['edu_ratio'],
                "added_employee": {'工号': 'GH993', '姓名': '张子涵', '性别': '男', '工资': 12000},
                "delete_count": res['crud_info']['del_count'],
                "final_count": res['crud_info']['final_count'],
                # 最终列表预览
                "final_head": process_df_to_records(res['final_preview']['head']),
                "final_tail": process_df_to_records(res['final_preview']['tail'])
            }
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "msg": str(e)}), 500


@app.route('/api/hr/export')
def api_hr_export():
    try:
        res = process_hr_logic()
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            res['final_df'].to_excel(writer, index=False, sheet_name='Result')
        output.seek(0)
        return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                         as_attachment=True, download_name='4-1_Result.xlsx')
    except Exception as e:
        return str(e), 500


# --- 5-1 人口 ---
@app.route('/api/population')
def api_population():
    try:
        path = os.path.join(DATA_DIR, "5-1人口数据.xlsx")
        df = pd.read_excel(path, engine='openpyxl')
        df.columns = df.columns.str.strip()
        if df['年份'].dtype == 'object':
            df['year_num'] = df['年份'].astype(str).str.replace('年', '').astype(int)
        else:
            df['year_num'] = df['年份']
        return jsonify({
            "status": "success",
            "years": [int(x) for x in df['year_num']],
            "urban": [float(x / 10000) for x in df['城镇人口']],
            "rural": [float(x / 10000) for x in df['乡村人口']],
            "total": [float(x / 10000) for x in df['年末总人口']],
            "pie_2022": [
                {"name": "男性", "value": float(df.iloc[-1]['男性人口'])},
                {"name": "女性", "value": float(df.iloc[-1]['女性人口'])}
            ]
        })
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)}), 500


if __name__ == '__main__':
    print(">>> 服务启动成功！请打开浏览器访问: http://127.0.0.1:5001")
    app.run(debug=True, port=5001, host='0.0.0.0')