# update_cache.py
import json
import time
from getHomePageData import _precompute_all_data, CACHE_FILE_PATH


def update_cache_file():
    """
    手动执行此脚本以更新所有首页数据缓存。
    """
    start_time = time.time()
    print("开始更新首页数据缓存...")

    # 调用正确的函数名
    all_data = _precompute_all_data()

    with open(CACHE_FILE_PATH, 'w', encoding='utf-8') as f:
        # 使用 ensure_ascii=False 以便正确保存中文字符
        json.dump(all_data, f, ensure_ascii=False, indent=4)

    end_time = time.time()
    print(f"数据缓存更新完成，耗时: {end_time - start_time:.2f} 秒。")


if __name__ == '__main__':
    update_cache_file()