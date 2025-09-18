import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# =====================================================================================
# 1. 配置区域
# =====================================================================================
SNOWNLP_RESULTS_FILE = 'sentiment_analysis_snownlp.csv'
MY_MODEL_RESULTS_FILE = 'sentiment_analysis_my_model.csv'


# =====================================================================================
# 2. 数据加载与合并 (与之前脚本相同)
# =====================================================================================
def load_and_merge_data(snownlp_file, my_model_file):
    try:
        df_snownlp = pd.read_csv(snownlp_file)
        df_my_model = pd.read_csv(my_model_file)
    except FileNotFoundError as e:
        print(f"❌ 错误: 找不到文件 {e.filename}。")
        return None

    df_merged = pd.merge(
        df_my_model.rename(columns={'score': 'score_my_model', 'label': 'label_my_model'}),
        df_snownlp.rename(columns={'score': 'score_snownlp', 'label': 'label_snownlp'}),
        on='text'
    )
    print(f"数据加载与合并完成！共找到 {len(df_merged)} 条共同评论。")
    return df_merged


# =====================================================================================
# 3. 最新的可视化函数
# =====================================================================================
def plot_sentiment_transition(df):
    """
    绘制情感转变分析图 (堆叠条形图)
    """
    print("生成图表: 情感转变分析图...")

    # 1. 使用crosstab计算两个模型判断的交叉统计表
    # 这会生成一个矩阵，行为SnowNLP的判断，列为你的模型的判断
    crosstab = pd.crosstab(df['label_snownlp'], df['label_my_model'])

    # 确保所有情感类别都存在，以防数据中缺少某一类
    all_labels = ['positive', 'neutral', 'negative']
    crosstab = crosstab.reindex(index=all_labels, columns=all_labels, fill_value=0)

    # 2. 计算每个SnowNLP类别的总数，并计算百分比
    # 我们按行进行归一化，使得每一行的总和为100%
    crosstab_percent = crosstab.div(crosstab.sum(axis=1), axis=0) * 100

    # 3. 绘图
    ax = crosstab_percent.plot(
        kind='bar',
        stacked=True,
        figsize=(14, 9),
        colormap='viridis',  # 使用一个视觉友好的色板
        width=0.7  # 条形宽度
    )

    # 4. 美化图表
    plt.title('Sentiment Transition Analysis', fontsize=18, pad=20)
    plt.xlabel('SnowNLP\'s Original Prediction', fontsize=14)
    plt.ylabel('Percentage of Comments (%)', fontsize=14)
    plt.xticks(rotation=0, fontsize=12)  # x轴标签水平显示
    plt.legend(title='My Model\'s New Prediction', bbox_to_anchor=(1.02, 1), loc='upper left')

    # 在每个色块上添加百分比标签
    for container in ax.containers:
        # 自定义标签格式
        def label_formatter(x):
            if x > 2:  # 只显示大于2%的标签，避免拥挤
                return f"{x:.1f}%"
            return ""

        ax.bar_label(container, labels=[label_formatter(x) for x in container.datavalues], label_type='center',
                     color='white', weight='bold')

    plt.tight_layout(rect=[0, 0, 0.85, 1])  # 调整布局为图例留出空间
    plt.savefig('sentiment_transition_analysis.png', dpi=300)
    plt.close()

    print("图表已保存为 'sentiment_transition_analysis.png'")


# =====================================================================================
# 4. 主函数
# =====================================================================================
def main():
    """主执行函数"""
    print("=== 最终模型对比分析脚本 ===")

    df_merged = load_and_merge_data(SNOWNLP_RESULTS_FILE, MY_MODEL_RESULTS_FILE)

    if df_merged is not None:
        plot_sentiment_transition(df_merged)
        print("\n✅ 分析完成！")


if __name__ == '__main__':
    main()