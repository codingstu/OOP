from flask import Flask, jsonify, request, send_from_directory
import pandas as pd
import numpy as np
import os

# ================= 配置路径 =================
base_dir = os.path.dirname(os.path.abspath(__file__))
public_dir = os.path.join(base_dir, '..', 'public')
data_dir = os.path.join(base_dir, '..', 'data')

app = Flask(__name__, static_folder=public_dir)


def get_data_path(filename):
    return os.path.join(data_dir, filename)


@app.route('/')
def serve_index():
    return send_from_directory(public_dir, 'index.html')


# --- 1-1 销售数据 ---
@app.route('/api/sales')
def get_sales():
    data_str = "2024 年 Q1-Q4 各月销售额（元）：15800 23500 19200 28600 31200 27800 35400 42100 38900 45600 39800 51200"
    try:
        sales = [int(x) for x in data_str.split("：")[1].strip().split()]
        quarters = {}
        for i in range(4):
            q_sales = sales[i * 3: (i + 1) * 3]
            # 确保结果是原生 float
            quarters[f'Q{i + 1}'] = float(round(sum(q_sales) / len(q_sales), 2))

        return jsonify({
            "raw_data": sales,
            "total": int(sum(sales)),
            "max": {"month": int(sales.index(max(sales)) + 1), "value": int(max(sales))},
            "min": {"month": int(sales.index(min(sales)) + 1), "value": int(min(sales))},
            "quarter_avg": quarters
        })
    except Exception as e:
        print(f"Error in sales: {e}")
        return jsonify({"error": str(e)})


# --- 2-1 财务数据 ---
@app.route('/api/finance')
def get_finance():
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
    total_in = int(sum(i['金额'] for i in ledger if i['类型'] == "收入"))
    total_out = int(sum(i['金额'] for i in ledger if i['类型'] == "支出"))
    return jsonify({
        "all_records": ledger,
        "expense_records": [i for i in ledger if i['类型'] == "支出"],
        "summary": {"income": total_in, "expense": total_out, "balance": total_in - total_out}
    })


# --- 3-1 个税计算 ---
@app.route('/api/tax', methods=['POST'])
def calculate_tax():
    try:
        d = request.json
        income = float(d.get('income', 0))
        insurance = float(d.get('insurance', 0))
        special = float(d.get('special', 0))
        other = float(d.get('other', 0))

        base = 5000
        taxable_month = max(0, income - base - insurance - special - other)
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
        net_income = income - insurance - tax_month

        return jsonify({
            "status": "success",
            "data": {
                "taxable_month": float(taxable_month),
                "taxable_year": float(taxable_year),
                "rate": float(r),
                "quick_deduction": float(q),
                "tax_year": float(tax_year),
                "tax_month": float(tax_month),
                "net_income": float(net_income)
            }
        })
    except ValueError:
        return jsonify({"status": "error", "msg": "请输入有效的数字"})


# --- 4-1 HR 数据分析 ---
@app.route('/api/hr')
def get_hr_logic():
    path = get_data_path("4-1公司人事财务数据.xlsx")
    if not os.path.exists(path):
        return jsonify({"error": f"文件不存在: {path}"})

    try:
        # 读取数据
        df = pd.read_excel(path, header=1, engine='openpyxl')

        result = {}
        # 手动将 numpy.int64 转为 python int
        result['shape'] = [int(df.shape[0]), int(df.shape[1])]

        # 处理 NaN
        result['head_10'] = df.head(10).where(pd.notnull(df), None).to_dict(orient='records')
        result['tail_10'] = df.tail(10).where(pd.notnull(df), None).to_dict(orient='records')
        result['columns'] = df.columns.tolist()

        # Groupby
        df['应发工资'] = pd.to_numeric(df['应发工资'], errors='coerce')
        gb = df.dropna(subset=['应发工资']).groupby(['学历', '性别'])['应发工资'].mean().reset_index()
        gb['应发工资'] = gb['应发工资'].round(2)
        # 确保 groupby 结果里的数字也是原生 float
        gb_records = gb.to_dict(orient='records')
        for item in gb_records:
            item['应发工资'] = float(item['应发工资'])
        result['groupby_salary'] = gb_records

        # 缺失值与重复值
        duplicates_count = int(df.duplicated().sum())
        result['duplicates_count'] = duplicates_count

        # 使用 copy() 修复 Warning
        df_clean = df.drop_duplicates().copy()
        result['shape_after_dedup'] = [int(df_clean.shape[0]), int(df_clean.shape[1])]

        # 增删改查
        status_counts = df_clean['在职状态'].value_counts()
        leaver_ratio = status_counts.get('离职', 0) / len(df_clean)
        result['leaver_ratio'] = f"{leaver_ratio:.2%}"
        # 转换字典里的值为 int
        result['status_counts'] = {k: int(v) for k, v in status_counts.items()}

        result['salary_max'] = float(df_clean['应发工资'].max())
        result['salary_min'] = float(df_clean['应发工资'].min())

        # 学历结构
        edu_ratio = df_clean['学历'].value_counts(normalize=True).mul(100).round(2)
        result['edu_ratio'] = {k: float(v) for k, v in edu_ratio.items()}

        # 增加员工
        new_emp = {
            '工号': 'GH993', '姓名': '张子涵', '性别': '男',
            '应发工资': 12000, '学历': '硕士', '在职状态': '在职'
        }
        result['added_employee'] = new_emp

        # 删除逻辑
        df_clean['年龄'] = pd.to_numeric(df_clean['年龄'], errors='coerce')
        condition = (df_clean['年龄'] > 55) & (df_clean['在职状态'] == '离职') & (df_clean['性别'] == '男')
        delete_count = int(condition.sum())

        result['delete_condition'] = "年龄>55 且 离职 且 男性"
        result['delete_count'] = delete_count
        result['final_count'] = int(len(df_clean) - delete_count)

        return jsonify(result)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)})


# --- 5-1 人口数据 ---
@app.route('/api/population')
def get_population():
    path = get_data_path("5-1人口数据.xlsx")
    if not os.path.exists(path):
        return jsonify({"error": "文件不存在"})

    try:
        df = pd.read_excel(path, engine='openpyxl')
        if df['年份'].dtype == 'object':
            df['year_num'] = df['年份'].astype(str).str.replace('年', '').astype(int)
        else:
            df['year_num'] = df['年份']

        # 列表推导式 + float() 强转，确保万无一失
        return jsonify({
            "years": [int(x) for x in df['year_num'].tolist()],
            "urban": [float(x / 10000) for x in df['城镇人口'].tolist()],
            "rural": [float(x / 10000) for x in df['乡村人口'].tolist()],
            "total": [float(x / 10000) for x in df['年末总人口'].tolist()],
            "pie_2022": [
                {"name": "男性", "value": float(df.iloc[-1]['男性人口'])},
                {"name": "女性", "value": float(df.iloc[-1]['女性人口'])}
            ]
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)})


if __name__ == '__main__':
    print("服务器正在启动...")
    print("请访问: http://127.0.0.1:5001")
    app.run(debug=True, port=5001)