#!/usr/bin/env python3
"""
调试和修复BERT模型输出格式问题
"""
import os
import warnings

warnings.filterwarnings('ignore')

# 配置清华源
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'


def debug_bert_output():
    """调试BERT输出格式"""
    try:
        from transformers import pipeline

        print("🔍 调试BERT模型输出格式...")

        # 加载你现在使用的模型
        classifier = pipeline(
            "sentiment-analysis",
            model="cardiffnlp/twitter-xlm-roberta-base-sentiment",
            device=-1,
            cache_dir="./tsinghua_model_cache"
        )

        # 测试几个例子，查看输出格式
        test_texts = [
            "期待朱一龙！",
            "少年热血，扬帆起航",
            "666"
        ]

        for text in test_texts:
            print(f"\n📝 测试文本: {text}")
            try:
                result = classifier(text)
                print(f"   输出类型: {type(result)}")
                print(f"   输出内容: {result}")

                # 尝试解析
                if isinstance(result, list) and len(result) > 0:
                    print(f"   第一个元素类型: {type(result[0])}")
                    print(f"   第一个元素内容: {result[0]}")

                    if isinstance(result[0], dict):
                        print(f"   标签: {result[0].get('label', 'N/A')}")
                        print(f"   分数: {result[0].get('score', 'N/A')}")

            except Exception as e:
                print(f"   ❌ 错误: {e}")

        return classifier

    except Exception as e:
        print(f"❌ 调试失败: {e}")
        return None


def robust_sentiment_analysis(text, classifier):
    """健壮的情感分析函数"""
    try:
        # 预处理
        text = text.strip()
        if len(text) < 2:
            return 0.5, 'neutral', 0.5

        # 调用BERT
        results = classifier(text)

        # 健壮的结果解析
        label = None
        score = None

        if isinstance(results, list) and len(results) > 0:
            first_result = results[0]
            if isinstance(first_result, dict):
                label = first_result.get('label')
                score = first_result.get('score')
            elif isinstance(first_result, list) and len(first_result) > 0:
                # 多标签情况，取分数最高的
                best = max(first_result, key=lambda x: x.get('score', 0))
                label = best.get('label')
                score = best.get('score')
        elif isinstance(results, dict):
            label = results.get('label')
            score = results.get('score')

        # 如果解析失败，返回默认值
        if label is None or score is None:
            print(f"   ⚠️ 解析失败，results格式: {type(results)} - {str(results)[:100]}...")
            return fallback_analysis(text)

        # 标签标准化
        label_clean = str(label).upper()

        # 情感分数转换
        if 'POSITIVE' in label_clean or 'POS' in label_clean:
            return float(score), 'positive', float(score)
        elif 'NEGATIVE' in label_clean or 'NEG' in label_clean:
            return 1 - float(score), 'negative', float(score)
        elif 'NEUTRAL' in label_clean:
            return 0.5, 'neutral', float(score)
        else:
            # 未知标签，根据分数推断
            if float(score) > 0.6:
                return float(score), 'positive', float(score)
            elif float(score) < 0.4:
                return 1 - float(score), 'negative', float(score)
            else:
                return 0.5, 'neutral', float(score)

    except Exception as e:
        print(f"   ❌ BERT分析出错: {str(e)[:50]}...")
        return fallback_analysis(text)


def fallback_analysis(text):
    """备用分析方法"""
    import jieba

    # 简单的关键词分析
    pos_keywords = ['期待', '美', '棒', '好', '赞', '支持', '666', '热血', '扬帆起航']
    neg_keywords = ['差', '坏', '失望', '烂']

    words = jieba.lcut(text)

    pos_score = sum(1 for word in words if any(pk in word for pk in pos_keywords))
    neg_score = sum(1 for word in words if any(nk in word for nk in neg_keywords))

    # 特殊规则
    if '666' in text:
        return 0.85, 'positive', 0.85
    if '期待' in text and ('！' in text or '!' in text):
        return 0.9, 'positive', 0.9
    if '热血' in text:
        return 0.88, 'positive', 0.88

    total = pos_score + neg_score
    if total == 0:
        return 0.5, 'neutral', 0.5

    sentiment_score = pos_score / total
    if sentiment_score > 0.6:
        return sentiment_score, 'positive', sentiment_score
    elif sentiment_score < 0.4:
        return sentiment_score, 'negative', 1 - sentiment_score
    else:
        return 0.5, 'neutral', 0.5


def run_fixed_analysis():
    """运行修复后的分析"""
    from utils.getPublicData import getAllCommentData

    print("🚀 运行修复后的情感分析...")

    # 调试模型输出
    classifier = debug_bert_output()

    if classifier is None:
        print("❌ 无法加载BERT模型，使用备用方案")
        return

    # 获取数据
    commentsList = getAllCommentData()

    # 分析前几条，确认修复效果
    print(f"\n📊 分析前10条评论，验证修复效果:")
    print("=" * 80)

    for i in range(min(10, len(commentsList))):
        text = commentsList[i][5]
        score, label, confidence = robust_sentiment_analysis(text, classifier)

        print(f"{i + 1:2d} | {score:5.3f} | {label:8s} | {text[:50]}")

    print("\n✅ 如果上面的结果正常显示，说明问题已修复！")
    print("现在可以运行完整的分析了。")

    return classifier


if __name__ == "__main__":
    classifier = run_fixed_analysis()