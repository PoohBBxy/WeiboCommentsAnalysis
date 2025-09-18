import concurrent
from threading import Lock
import time
import requests
import csv
import os
import random
from datetime import datetime
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- 配置区 ---
ARTICLES_CSV_INPUT = './articleData_sample.csv'
COMMENTS_CSV_OUTPUT = './commentsData.csv'
COMMENTS_CSV_HEADERS = [
    'articleId', 'commentId', 'created_at', 'like_counts', 'region', 'content',
    'authorName', 'authorGender', 'authorAddress', 'authorAvatar'
]

# 全局速率限制（跨线程）
RATE_CONFIG = {
    'rpm': 12,           # 每分钟最大请求数
    'min_delay': 3.0,    # 线程内部延时（秒）
    'max_delay': 6.0,
}
_RATE_LOCK = Lock()
_NEXT_TS = 0.0

def configure_rate_limit(rpm=None, min_delay=None, max_delay=None):
    global RATE_CONFIG
    if rpm is not None:
        try: RATE_CONFIG['rpm'] = max(1, int(rpm))
        except Exception: pass
    if min_delay is not None:
        try: RATE_CONFIG['min_delay'] = max(0.0, float(min_delay))
        except Exception: pass
    if max_delay is not None:
        try: RATE_CONFIG['max_delay'] = max(RATE_CONFIG['min_delay'], float(max_delay))
        except Exception: pass

def _global_throttle():
    global _NEXT_TS
    interval = 60.0 / float(RATE_CONFIG.get('rpm') or 12)
    with _RATE_LOCK:
        now = time.monotonic()
        wait = max(0.0, _NEXT_TS - now)
        _NEXT_TS = max(now, _NEXT_TS) + interval
    if wait > 0:
        time.sleep(wait)

def SHOULD_STOP():
    """可由外部注入的停止检查函数，默认不停止。"""
    return False

def SHOULD_PAUSE():
    """可由外部注入的暂停检查函数，默认不暂停。"""
    return False

_PAUSE_REPORTED = False

def WAIT_IF_PAUSED():
    global _PAUSE_REPORTED
    if SHOULD_PAUSE():
        if not _PAUSE_REPORTED:
            print("[任务] 已暂停，等待恢复...")
            _PAUSE_REPORTED = True
        while SHOULD_PAUSE():
            if SHOULD_STOP():
                return
            time.sleep(0.3)
        print("[任务] 已恢复，继续抓取。")
        _PAUSE_REPORTED = False

def init_csv(filename, headers):
    if not os.path.exists(filename):
        with open(filename, 'w', encoding='utf-8', newline='') as csvFile:
            writer = csv.writer(csvFile)
            writer.writerow(headers)


def write_rows_to_csv(filename, rows):
    with open(filename, 'a', encoding='utf-8', newline='') as csvFile:
        writer = csv.writer(csvFile)
        writer.writerows(rows)


def get_weibo_headers():

    headers = {
        'Cookie': 'XSRF-TOKEN=HokeuoS_PqynbGiNJjo0dCRp; SCF=AlhoumoW7UZVYRGLYis6L9X5cu6SS7FvfCW3uCHJB240ZwnbYV78AXqp4-9UBU7PJ-qFTjQCPVb1kjZIBGm4JSo.; SUB=_2A25FmZsoDeRhGe5O6loU9ivEyjWIHXVm1pLgrDV8PUNbmtAYLUj1kW9NdXp6cg2JezJdYA02J-RzId-19UmW_4vF; SUBP=0033WrSXqPxfM725Ws9jqgMF55529P9D9WWyA7RWckfpx4AJRxLfe.vL5NHD95QReh2RSKqf1h24Ws4DqcjMi--NiK.Xi-2Ri--ciKnRi-zN1h5p1h-cSKnp1Btt; ALF=02_1757771896; WBPSESS=6AYvRgHgchEaSWT0h6q9IPUifoMiwpqF-POAUJhmby8OZIJSttGfM9XmM636SK22IwAL9RwuXVGgYeym_DcL3cOGYp4W0PJv6GMk7p2HjTji0gYA__Yr2WI0cNgZlJwKlBG74CmeWi2cHKcQ8dVIow==',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
        'Referer': 'https://weibo.com/',
        'X-Requested-With': 'XMLHttpRequest',
        'X-XSRF-TOKEN': 'HokeuoS_PqynbGiNJjo0dCRp',
    }
    return headers


def get_data(url, params, headers):
    try:
        # 全局节流，跨线程串行化请求速率
        _global_throttle()
        response = requests.get(url, headers=headers, params=params, timeout=20)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"网络请求错误: {e}")
        return None


def parse_weibo_time(time_str):
    try:
        return datetime.strptime(time_str, '%a %b %d %H:%M:%S %z %Y').strftime('%Y-%m-%d %H:%M:%S')
    except (ValueError, TypeError):
        return time_str


def clean_html(raw_html):
    if not raw_html: return ""
    return BeautifulSoup(raw_html, 'lxml').get_text(separator=' ', strip=True)


def get_article_ids_from_csv(filename):
    if not os.path.exists(filename):
        print(f"错误: 输入文件 {filename} 不存在。")
        return []

    article_ids = []
    with open(filename, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        try:
            next(reader)
            for row in reader:
                if row: article_ids.append(row[0])
        except StopIteration:
            pass
    print(f"从 {filename} 中成功读取 {len(article_ids)} 个文章ID。")
    return article_ids


def parse_comments(response_data, article_id):
    """解析评论，同时过滤楼中楼回复和空评论。"""
    if not response_data or not isinstance(response_data, dict):
        return [], 0

    raw_comments = response_data.get('data', [])
    if not raw_comments:
        return [], 0

    cleaned_comments = []
    for comment in raw_comments:
        if comment.get('reply_comment'):
            continue

        # 过滤空评论
        content_cleaned = clean_html(comment.get('text', ''))
        if not content_cleaned:  # 如果清理后的文本是空字符串，则跳过
            continue

        user = comment.get('user', {})
        gender_map = {'m': '男', 'f': '女', 'n': '未知'}
        gender = gender_map.get(user.get('gender'), '未知')

        cleaned_comments.append([
            article_id,
            comment.get('idstr', ''),
            parse_weibo_time(comment.get('created_at', '')),
            comment.get('like_counts', 0),
            comment.get('source', '').replace('来自', ''),
            content_cleaned,  # 使用我们已经判断过的非空内容
            user.get('screen_name', ''),
            gender,
            user.get('location', ''),
            user.get('profile_image_url', '')
        ])

    next_max_id = response_data.get('max_id', 0)
    return cleaned_comments, next_max_id


def scrape_comments_for_article(article_id, max_comments_per_article=120, sleep_range=(3, 5)):
    """
    这个函数负责完成单个文章的所有评论爬取任务。
    它将被每个线程独立调用。
    """
    comments_url = 'https://weibo.com/ajax/statuses/buildComments'
    # 为降低风险，让每个线程都获取一次独立的headers，虽然内容一样
    headers = get_weibo_headers()

    print(f"[文章 {article_id}] 线程任务开始...")

    max_id = 0
    page_count = 1
    total_comments_for_article = 0
    all_comments_for_this_article = []

    while total_comments_for_article < max_comments_per_article:
        WAIT_IF_PAUSED()
        if SHOULD_STOP():
            print(f"[文章 {article_id}] 检测到终止信号，停止该文章评论抓取。")
            break
        params = {
            'id': article_id,
            'is_show_bulletin': 0,
            'max_id': max_id,
            'flow': 1
        }

        response_data = get_data(comments_url, params, headers)
        if response_data is None:
            print(f"[文章 {article_id}] 获取第 {page_count} 页评论数据失败。")
            break

        comments_to_write, next_max_id = parse_comments(response_data, article_id)
        if not comments_to_write:
            print(f"[文章 {article_id}] 在第 {page_count} 页已无更多评论。")
            break

        remaining_needed = max_comments_per_article - total_comments_for_article
        if len(comments_to_write) > remaining_needed:
            comments_to_write = comments_to_write[:remaining_needed]

        all_comments_for_this_article.extend(comments_to_write)
        total_comments_for_article += len(comments_to_write)

        print(
            f"[文章 {article_id}] 第 {page_count} 页成功获取 {len(comments_to_write)} 条评论 (累计: {total_comments_for_article}/{max_comments_per_article})")

        if next_max_id == 0:
            print(f"[文章 {article_id}] API表示已无更多评论。")
            break
        max_id = next_max_id
        page_count += 1

        # 【核心风控】增加每个线程内部的延时范围
        # 将长睡眠分割以便及时响应终止
        remain = random.uniform(sleep_range[0], sleep_range[1])
        step = 0.5
        while remain > 0:
            WAIT_IF_PAUSED()
            if SHOULD_STOP():
                print(f"[文章 {article_id}] 终止信号到达，提前结束等待。")
                break
            t = min(step, remain)
            time.sleep(t)
            remain -= t

    if not all_comments_for_this_article:
        print(f"[文章 {article_id}] 线程任务完成，但未收集到任何评论。")
    else:
        print(f"[文章 {article_id}] 线程任务完成，共找到 {total_comments_for_article} 条评论准备写入。")

    return all_comments_for_this_article


def start_scraping_with_threads(max_workers=3, max_comments_per_article=100):
    """使用线程池并发爬取评论的主函数。"""
    init_csv(COMMENTS_CSV_OUTPUT, COMMENTS_CSV_HEADERS)
    article_ids = get_article_ids_from_csv(ARTICLES_CSV_INPUT)

    if not article_ids:
        print("没有需要处理的文章ID，程序退出。")
        return

    # 使用全局配置的延时范围
    sleep_range = (RATE_CONFIG['min_delay'], RATE_CONFIG['max_delay'])

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        print(f"线程池已启动，最大并发数: {max_workers}, 延时范围: {sleep_range}秒")

        future_to_article = {}
        for article_id in article_ids:
            WAIT_IF_PAUSED()
            if SHOULD_STOP():
                print("[任务] 检测到终止信号，停止提交新的文章评论任务。")
                break
            # 为每个任务传递延时参数
            future = executor.submit(scrape_comments_for_article, article_id, max_comments_per_article, sleep_range)
            future_to_article[future] = article_id

        total_comments_written = 0
        # as_completed 可以在任何一个任务完成时立即处理它的结果
        for future in as_completed(future_to_article):
            WAIT_IF_PAUSED()
            article_id = future_to_article[future]
            try:
                if SHOULD_STOP():
                    print("[任务] 终止信号到达，停止等待剩余任务并取消后续。")
                    try:
                        executor.shutdown(wait=False, cancel_futures=True)
                    except Exception:
                        pass
                    break
                result_comments = future.result()
                if result_comments:
                    # 【核心风控】将写入操作加锁，防止多线程同时写文件导致冲突
                    # 虽然 'a' 模式下风险较小，但加锁是更规范的做法
                    with open(COMMENTS_CSV_OUTPUT, 'a', encoding='utf-8', newline='') as f:
                        writer = csv.writer(f)
                        writer.writerows(result_comments)

                    written_count = len(result_comments)
                    total_comments_written += written_count
                    print(f"文章 {article_id} 的 {written_count} 条评论已成功写入文件。")
            except Exception as exc:
                print(f"文章 {article_id} 在处理时产生了一个错误: {exc}")

    print(f"\n所有任务已完成！总共写入 {total_comments_written} 条评论。")


if __name__ == '__main__':
    # 在这里设置每篇文章最多爬取多少条评论,多少线程
    start_scraping_with_threads(max_workers=6, max_comments_per_article=120)
