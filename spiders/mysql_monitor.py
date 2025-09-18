import pymysql
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional


class MySQLMonitor:
    """MySQL数据库监测类"""

    def __init__(self, host: str, user: str, password: str, database: str, port: int = 3306):
        """
        初始化MySQL连接参数
        """
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.port = port
        self.connection = None

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('mysql_monitor.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def connect(self) -> bool:
        """建立数据库连接"""
        try:
            self.connection = pymysql.connect(
                host=self.host, user=self.user, password=self.password,
                database=self.database, port=self.port, charset='utf8mb4', autocommit=True
            )
            self.logger.info(f"成功连接到数据库 {self.database}")
            return True
        except Exception as e:
            self.logger.error(f"数据库连接失败: {e}")
            return False

    def disconnect(self):
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
            self.logger.info("数据库连接已关闭")

    def get_table_count(self, table_name: str) -> Optional[int]:
        """获取指定表的数据条数"""
        try:
            with self.connection.cursor() as cursor:
                sql = f"SELECT COUNT(*) FROM `{table_name}`"
                cursor.execute(sql)
                result = cursor.fetchone()
                return result[0] if result else 0
        except Exception as e:
            self.logger.error(f"查询表 {table_name} 失败: {e}")
            return None

    def get_articles_without_comments_count(self) -> Optional[int]:
        """获取尚未爬取评论的文章数量（且评论数>0）"""
        try:
            with self.connection.cursor() as cursor:
                # --- 同步更新查询逻辑 ---
                query = """
                    SELECT COUNT(a.id)
                    FROM `article` a
                    LEFT JOIN `comments` c ON a.id = c.articleId
                    WHERE c.articleId IS NULL AND a.commentsLen > 0
                """
                cursor.execute(query)
                result = cursor.fetchone()
                return result[0] if result else 0
        except Exception as e:
            self.logger.error(f"查询无评论文章数失败: {e}")
            return None

    def get_all_tables(self) -> List[str]:
        """获取数据库中所有表名"""
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("SHOW TABLES")
                tables = [table[0] for table in cursor.fetchall()]
                return tables
        except Exception as e:
            self.logger.error(f"获取表列表失败: {e}")
            return []

    def _display_report(self, table_counts: Dict[str, int], title: str):
        """统一显示报告格式"""
        total_records = sum(table_counts.values())
        print(f"\n{'=' * 60}")
        print(f"{title} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"数据库: {self.database}")
        print(f"{'=' * 60}")

        for table, count in table_counts.items():
            print(f"表 {table:30s}: {count:>10,} 条记录")

        # 显示待处理文章数
        uncommented_count = self.get_articles_without_comments_count()
        print(f"{'-' * 60}")
        if uncommented_count is not None:
            print(f"待爬取评论的文章数 (commentsLen > 0): {uncommented_count:,}")
        else:
            print("待爬取评论的文章数: 查询失败")

        print(f"{'=' * 60}")
        print(f"总计: {len(table_counts)} 个表，{total_records:,} 条记录")
        print(f"{'=' * 60}\n")

    def monitor_all_tables(self) -> Dict[str, int]:
        """监测所有表的数据条数"""
        if not self.connection and not self.connect():
            return {}

        tables = self.get_all_tables()
        if not tables:
            self.logger.warning("未找到任何表")
            return {}

        table_counts = {}
        self.logger.info(f"开始监测 {len(tables)} 个表的数据...")
        for table in tables:
            count = self.get_table_count(table)
            if count is not None:
                table_counts[table] = count

        self._display_report(table_counts, "数据库全表监测报告")
        return table_counts

    def monitor_specific_tables(self, table_names: List[str]) -> Dict[str, int]:
        """监测指定表的数据条数"""
        if not self.connection and not self.connect():
            return {}

        table_counts = {}
        self.logger.info(f"开始监测指定的 {len(table_names)} 个表...")
        for table in table_names:
            count = self.get_table_count(table)
            if count is not None:
                table_counts[table] = count

        self._display_report(table_counts, "指定表监测报告")
        return table_counts

    def continuous_monitor(self, interval: int = 60, tables: Optional[List[str]] = None):
        """持续监测数据库"""
        self.logger.info(f"开始持续监测，间隔 {interval} 秒...")
        try:
            while True:
                if tables:
                    self.monitor_specific_tables(tables)
                else:
                    self.monitor_all_tables()
                print(f"等待 {interval} 秒后进行下次监测...")
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n监测已停止")
            self.logger.info("用户中断了持续监测")
        finally:
            self.disconnect()


def main():
    """主函数 - 使用示例"""
    DB_CONFIG = {
        'host': 'localhost', 'user': 'root', 'password': 'Password123!',
        'database': 'weiboarticles', 'port': 3306
    }
    monitor = MySQLMonitor(**DB_CONFIG)

    if not monitor.connect():
        print("数据库连接失败，程序退出")
        return

    try:
        print("MySQL数据库监测工具")
        print("1. 监测所有表（一次性）")
        print("2. 监测指定表（一次性）")
        print("3. 持续监测所有表")
        print("4. 持续监测指定表")
        choice = input("请选择监测模式 (1-4): ").strip()

        if choice == '1':
            monitor.monitor_all_tables()
        elif choice == '2':
            table_input = input("请输入要监测的表名（多个表用逗号分隔）: ").strip()
            tables = [t.strip() for t in table_input.split(',') if t.strip()]
            if tables:
                monitor.monitor_specific_tables(tables)
            else:
                print("未输入有效的表名")
        elif choice == '3':
            interval = input("请输入监测间隔（秒，默认60）: ").strip()
            interval = int(interval) if interval.isdigit() else 60
            monitor.continuous_monitor(interval)
        elif choice == '4':
            table_input = input("请输入要监测的表名（多个表用逗号分隔）: ").strip()
            tables = [t.strip() for t in table_input.split(',') if t.strip()]
            if tables:
                interval = input("请输入监测间隔（秒，默认60）: ").strip()
                interval = int(interval) if interval.isdigit() else 60
                monitor.continuous_monitor(interval, tables)
            else:
                print("未输入有效的表名")
    except Exception as e:
        print(f"程序执行出错: {e}")
    finally:
        monitor.disconnect()


if __name__ == "__main__":
    main()