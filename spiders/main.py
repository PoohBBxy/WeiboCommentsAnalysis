import sys
import os
import csv
import pymysql
import time
from datetime import datetime

# 导入爬虫模块（兼容包内/脚本两种运行方式）
try:
    from . import spiderContent
    from . import spiderComments
except ImportError:
    import spiderContent
    import spiderComments

# --- 数据库配置区 ---
DB_CONFIG = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': 'Password123!',  # 请修改为你的MySQL密码
    'database': 'weiboarticles',  # 请修改为你的数据库名
    'charset': 'utf8mb4'
}


class WeiboDataManager:
    def __init__(self):
        self.connection = None

    def connect_db(self):
        """连接数据库"""
        try:
            self.connection = pymysql.connect(**DB_CONFIG)
            print("数据库连接成功！")
            return True
        except Exception as e:
            print(f"数据库连接失败: {e}")
            return False

    def close_db(self):
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
            print("数据库连接已关闭。")

    def create_tables(self):
        """创建必要的数据表"""
        try:
            cursor = self.connection.cursor()

            # 创建文章表
            create_articles_table = """
            CREATE TABLE IF NOT EXISTS articles (
                id VARCHAR(50) PRIMARY KEY,
                typename VARCHAR(100),
                content TEXT,
                created_at DATETIME,
                likeNum INT DEFAULT 0,
                commentsLen INT DEFAULT 0,
                reposts_count INT DEFAULT 0,
                region VARCHAR(100),
                contentLen INT DEFAULT 0,
                detailUrl VARCHAR(500),
                authorName VARCHAR(100),
                authorDetail VARCHAR(500),
                authorAvatar VARCHAR(500),
                isVip VARCHAR(10),
                import_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """

            # 创建评论表
            create_comments_table = """
            CREATE TABLE IF NOT EXISTS comments (
                commentId VARCHAR(50) PRIMARY KEY,
                articleId VARCHAR(50),
                created_at DATETIME,
                like_counts INT DEFAULT 0,
                region VARCHAR(100),
                content TEXT,
                authorName VARCHAR(100),
                authorGender VARCHAR(10),
                authorAddress VARCHAR(100),
                authorAvatar VARCHAR(500),
                import_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (articleId) REFERENCES articles(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """

            cursor.execute(create_articles_table)
            cursor.execute(create_comments_table)
            self.connection.commit()
            print("数据表创建/检查完成。")

        except Exception as e:
            print(f"创建数据表失败: {e}")
            return False
        finally:
            cursor.close()
        return True

    def import_articles_from_csv(self, csv_file='./articleData_sample.csv'):
        """从CSV导入文章数据，检查重复"""
        if not os.path.exists(csv_file):
            print(f"文章CSV文件 {csv_file} 不存在。")
            return False

        try:
            cursor = self.connection.cursor()

            # 先获取数据库中已存在的文章ID
            cursor.execute("SELECT id FROM articles")
            existing_ids = set(row[0] for row in cursor.fetchall())
            print(f"数据库中已存在 {len(existing_ids)} 篇文章。")

            # 读取CSV文件
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                headers = next(reader)  # 跳过表头

                new_articles = []
                duplicate_count = 0

                for row in reader:
                    if not row:  # 跳过空行
                        continue

                    article_id = row[0]
                    if article_id in existing_ids:
                        duplicate_count += 1
                        continue

                    # 处理数据类型转换
                    try:
                        # 转换数字类型
                        like_num = int(row[4]) if row[4].isdigit() else 0
                        comments_len = int(row[5]) if row[5].isdigit() else 0
                        reposts_count = int(row[6]) if row[6].isdigit() else 0
                        content_len = int(row[8]) if row[8].isdigit() else 0

                        # 转换日期时间
                        created_at = row[3] if row[3] else None
                        if created_at and created_at != '':
                            try:
                                # 尝试解析日期时间
                                datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S')
                            except ValueError:
                                created_at = None

                        article_data = (
                            row[0],  # id
                            row[1],  # typename
                            row[2],  # content
                            created_at,  # created_at
                            like_num,  # likeNum
                            comments_len,  # commentsLen
                            reposts_count,  # reposts_count
                            row[7],  # region
                            content_len,  # contentLen
                            row[9],  # detailUrl
                            row[10],  # authorName
                            row[11],  # authorDetail
                            row[12],  # authorAvatar
                            row[13]  # isVip
                        )
                        new_articles.append(article_data)

                    except (ValueError, IndexError) as e:
                        print(f"处理文章数据时出错: {e}, 跳过行: {row}")
                        continue

                if new_articles:
                    # 批量插入新文章
                    insert_sql = """
                    INSERT INTO articles (id, typename, content, created_at, likeNum, 
                                        commentsLen, reposts_count, region, contentLen, 
                                        detailUrl, authorName, authorDetail, authorAvatar, isVip)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    cursor.executemany(insert_sql, new_articles)
                    self.connection.commit()

                    print(f"成功导入 {len(new_articles)} 篇新文章。")
                    if duplicate_count > 0:
                        print(f"跳过 {duplicate_count} 篇重复文章。")
                else:
                    print("没有新文章需要导入。")

        except Exception as e:
            print(f"导入文章数据失败: {e}")
            self.connection.rollback()
            return False
        finally:
            cursor.close()

        return True

    def import_comments_from_csv(self, csv_file='./commentsData.csv'):
        """从CSV导入评论数据，检查重复"""
        if not os.path.exists(csv_file):
            print(f"评论CSV文件 {csv_file} 不存在。")
            return False

        try:
            cursor = self.connection.cursor()

            # 先获取数据库中已存在的评论ID
            cursor.execute("SELECT commentId FROM comments")
            existing_comment_ids = set(row[0] for row in cursor.fetchall())
            print(f"数据库中已存在 {len(existing_comment_ids)} 条评论。")

            # 获取有效的文章ID
            cursor.execute("SELECT id FROM articles")
            valid_article_ids = set(row[0] for row in cursor.fetchall())

            # 读取CSV文件
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                headers = next(reader)  # 跳过表头

                new_comments = []
                duplicate_count = 0
                invalid_article_count = 0

                for row in reader:
                    if not row:  # 跳过空行
                        continue

                    comment_id = row[1]  # commentId
                    article_id = row[0]  # articleId

                    # 检查评论ID重复
                    if comment_id in existing_comment_ids:
                        duplicate_count += 1
                        continue

                    # 检查文章ID是否有效
                    if article_id not in valid_article_ids:
                        invalid_article_count += 1
                        continue

                    try:
                        # 处理数据类型转换
                        like_counts = int(row[3]) if row[3].isdigit() else 0

                        # 转换日期时间
                        created_at = row[2] if row[2] else None
                        if created_at and created_at != '':
                            try:
                                datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S')
                            except ValueError:
                                created_at = None

                        comment_data = (
                            comment_id,  # commentId
                            article_id,  # articleId
                            created_at,  # created_at
                            like_counts,  # like_counts
                            row[4],  # region
                            row[5],  # content
                            row[6],  # authorName
                            row[7],  # authorGender
                            row[8],  # authorAddress
                            row[9]  # authorAvatar
                        )
                        new_comments.append(comment_data)

                    except (ValueError, IndexError) as e:
                        print(f"处理评论数据时出错: {e}, 跳过行: {row}")
                        continue

                if new_comments:
                    # 批量插入新评论
                    insert_sql = """
                    INSERT INTO comments (commentId, articleId, created_at, like_counts, 
                                        region, content, authorName, authorGender, 
                                        authorAddress, authorAvatar)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    cursor.executemany(insert_sql, new_comments)
                    self.connection.commit()

                    print(f"成功导入 {len(new_comments)} 条新评论。")
                    if duplicate_count > 0:
                        print(f"跳过 {duplicate_count} 条重复评论。")
                    if invalid_article_count > 0:
                        print(f"跳过 {invalid_article_count} 条无效文章ID的评论。")
                else:
                    print("没有新评论需要导入。")

        except Exception as e:
            print(f"导入评论数据失败: {e}")
            self.connection.rollback()
            return False
        finally:
            cursor.close()

        return True

    def get_statistics(self):
        """获取数据库统计信息"""
        try:
            cursor = self.connection.cursor()

            # 文章统计
            cursor.execute("SELECT COUNT(*) FROM articles")
            articles_count = cursor.fetchone()[0]

            # 评论统计
            cursor.execute("SELECT COUNT(*) FROM comments")
            comments_count = cursor.fetchone()[0]

            # 各分类文章统计
            cursor.execute("SELECT typename, COUNT(*) FROM articles GROUP BY typename ORDER BY COUNT(*) DESC")
            type_stats = cursor.fetchall()

            print(f"\n=== 数据库统计信息 ===")
            print(f"文章总数: {articles_count}")
            print(f"评论总数: {comments_count}")
            print(f"\n各分类文章统计:")
            for typename, count in type_stats:
                print(f"  {typename}: {count} 篇")

        except Exception as e:
            print(f"获取统计信息失败: {e}")
        finally:
            cursor.close()


def main():
    """主函数：协调整个爬虫和数据导入流程"""
    print("=== 微博数据爬取和导入系统 ===")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # 初始化数据管理器
    data_manager = WeiboDataManager()

    # 连接数据库
    if not data_manager.connect_db():
        print("数据库连接失败，程序退出。")
        return

    # 创建数据表
    if not data_manager.create_tables():
        print("数据表创建失败，程序退出。")
        data_manager.close_db()
        return

    try:
        # 第一步：爬取文章内容
        print("=== 第一步：开始爬取文章内容 ===")
        spiderContent.start(pageNum_per_type=3)  # 每个分类爬取3页
        print("文章内容爬取完成。\n")

        # 第二步：导入文章到数据库
        print("=== 第二步：导入文章数据到数据库 ===")
        if data_manager.import_articles_from_csv():
            print("文章数据导入成功。\n")
        else:
            print("文章数据导入失败，终止程序。")
            return

        # 第三步：爬取评论
        print("=== 第三步：开始爬取评论数据 ===")
        spiderComments.start_scraping_with_threads(max_workers=3, max_comments_per_article=50)
        print("评论数据爬取完成。\n")

        # 第四步：导入评论到数据库
        print("=== 第四步：导入评论数据到数据库 ===")
        if data_manager.import_comments_from_csv():
            print("评论数据导入成功。\n")
        else:
            print("评论数据导入失败。")

        # 第五步：显示统计信息
        print("=== 第五步：数据统计信息 ===")
        data_manager.get_statistics()

    except KeyboardInterrupt:
        print("\n\n程序被用户中断。")
    except Exception as e:
        print(f"\n程序执行过程中发生错误: {e}")
    finally:
        # 清理资源
        data_manager.close_db()
        print(f"\n程序结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=== 程序执行完毕 ===")


if __name__ == '__main__':
    main()
