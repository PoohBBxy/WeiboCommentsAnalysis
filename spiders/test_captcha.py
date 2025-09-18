import pandas as pd
import requests
import urllib.parse
import time
import os

# --- 全局配置 ---
# EXCEL文件名，请确保此文件与脚本在同一目录下
INPUT_EXCEL_FILE = '/Users/wanghaotian/Downloads/220513-14班级学生信息(导入模版)(2024).xls'
# 输出结果的文件名
OUTPUT_EXCEL_FILE = '成绩查询结果.xlsx'
# 每次请求之间的延时（秒），避免请求过快被服务器屏蔽
REQUEST_DELAY = 10


def query_score(session, name, zkzh, km):
    """
    查询单个考生的四级或六级成绩。
    """
    if not isinstance(name, str) or not isinstance(zkzh, str) or not name.strip() or not zkzh.strip():
        return None

    try:
        # URL编码姓名
        encoded_name = urllib.parse.quote(name)
        query_url = f"https://cachecloud.neea.cn/latest/results/cet?km={km}&xm={encoded_name}&no={zkzh}"

        response = session.get(query_url, timeout=10)

        # 打印原始返回
        print(f"\n🔹 查询 URL: {query_url}")
        print(f"🔹 状态码: {response.status_code}")
        print(f"🔹 响应头: {response.headers}")
        print("🔹 原始响应内容:")
        print(response.text[:500])  # 只截取前500字符，避免太长

        # 确保返回的是JSON格式
        try:
            result = response.json()
            print("🔹 解析后的JSON:")
            print(result)
        except Exception:
            print("❌ 响应不是合法JSON")
            return None

        # 判断返回的数据结构
        data = result.get('data') if isinstance(result.get('data'), dict) else result

        if data and data.get('score') and data.get('score') != '--':
            return {
                '总分': data.get('score'),
                '听力': data.get('sco_lc'),
                '阅读': data.get('sco_rd'),
                '写作与翻译': data.get('sco_wt')
            }
        else:
            return None

    except requests.exceptions.RequestException as e:
        print(f"  -> 网络请求异常: {e}")
        return None
    except Exception as e:
        print(f"  -> 查询处理异常: {e}")
        return None


def main():
    """
    主函数，执行整个批量查询流程
    """
    # 检查输入文件是否存在
    if not os.path.exists(INPUT_EXCEL_FILE):
        print(f"错误: 未找到名单文件 '{INPUT_EXCEL_FILE}'。")
        print("请确保Excel名单文件与此脚本位于同一目录下。")
        return

    # 读取Excel文件，指定没有表头，并命名列
    print(f"正在读取 '{INPUT_EXCEL_FILE}'...")
    try:
        # 将所有列都作为字符串读取，以保证准考证号格式正确
        df = pd.read_excel(INPUT_EXCEL_FILE, header=None, names=['姓名', '准考证号'], dtype=str)
        df['准考证号'] = df['准考证号'].str.strip()
        df['姓名'] = df['姓名'].str.strip()
    except Exception as e:
        print(f"读取Excel文件时出错: {e}")
        return

    # 为结果新增列，并初始化
    df['总分'] = ''
    df['听力'] = ''
    df['阅读'] = ''
    df['写作与翻译'] = ''
    df['考试科目'] = ''

    # 创建一个Session以复用连接和headers
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
        'Referer': 'https://cjcx.neea.edu.cn/'
    })

    # --- 第一轮: 查询四级成绩 (km=1) ---
    print("\n--- 开始第一轮查询：大学英语四级(CET-4) ---")
    for index, row in df.iterrows():
        name, zkzh = row['姓名'], row['准考证号']

        # 跳过姓名或准考证号为空的行
        if pd.isna(name) or pd.isna(zkzh) or not name or not zkzh:
            print(f"第 {index + 2} 行信息不完整，跳过。")
            continue

        print(f"正在查询 (四级): {name} ({zkzh})")
        scores = query_score(session, name, zkzh, km=1)

        if scores:
            print(f"  -> 查询成功！总分: {scores['总分']}")
            df.loc[index, ['总分', '听力', '阅读', '写作与翻译', '考试科目']] = \
                [scores['总分'], scores['听力'], scores['阅读'], scores['写作与翻译'], '四级']
        else:
            print("  -> 未查到四级成绩。")

        time.sleep(REQUEST_DELAY)

    # --- 第二轮: 对第一轮未查到成绩的，查询六级成绩 (km=2) ---
    print("\n--- 开始第二轮查询：大学英语六级(CET-6) ---")
    # 筛选出'考试科目'列仍然为空的行进行查询
    for index, row in df[df['考试科目'] == ''].iterrows():
        name, zkzh = row['姓名'], row['准考证号']

        if pd.isna(name) or pd.isna(zkzh) or not name or not zkzh:
            continue  # 在第一轮已经提示过，这里不再重复提示

        print(f"正在查询 (六级): {name} ({zkzh})")
        scores = query_score(session, name, zkzh, km=2)

        if scores:
            print(f"  -> 查询成功！总分: {scores['总分']}")
            df.loc[index, ['总分', '听力', '阅读', '写作与翻译', '考试科目']] = \
                [scores['总分'], scores['听力'], scores['阅读'], scores['写作与翻译'], '六级']
        else:
            print("  -> 未查到六级成绩。")

        time.sleep(REQUEST_DELAY)

    # --- 保存结果 ---
    try:
        df.to_excel(OUTPUT_EXCEL_FILE, index=False)
        print(f"\n查询完成！结果已保存至 '{os.path.abspath(OUTPUT_EXCEL_FILE)}'")
    except Exception as e:
        print(f"\n保存结果到Excel文件时出错: {e}")


if __name__ == '__main__':
    main()