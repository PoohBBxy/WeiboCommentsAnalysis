# ensemble_debug.py
import os, sys, torch, numpy as np
from transformers import AutoTokenizer, AutoModelForSequenceClassification

os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
torch.set_printoptions(precision=4, sci_mode=False)

MAC_DIR = "./sentiment_model_clean_v2"   # 你的 MacBERT ckpt 目录
ROB_DIR = "./sentiment_roberta"         # 你的 RoBERTa ckpt 目录
MAX_LEN = 160
TEMP    = 1.0

def get_device():
    if torch.backends.mps.is_available():
        return torch.device("mps")
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")

def load_models(tokenizer_dir, mac_dir, rob_dir, device):
    print(f"[info] device: {device}")
    assert os.path.isdir(tokenizer_dir), f"tokenizer_dir not found: {tokenizer_dir}"
    assert os.path.isdir(mac_dir),       f"macbert dir not found: {mac_dir}"
    assert os.path.isdir(rob_dir),       f"roberta dir not found: {rob_dir}"

    print(f"[load] tokenizer from: {tokenizer_dir}")
    tok  = AutoTokenizer.from_pretrained(tokenizer_dir)

    print(f"[load] macbert from: {mac_dir}")
    m_mac = AutoModelForSequenceClassification.from_pretrained(mac_dir).to(device).eval()

    print(f"[load] roberta from: {rob_dir}")
    m_rob = AutoModelForSequenceClassification.from_pretrained(rob_dir).to(device).eval()

    # 打印标签映射，确认一致
    print("[info] id2label (mac):", getattr(m_mac.config, "id2label", None))
    print("[info] id2label (rob):", getattr(m_rob.config, "id2label", None))

    return tok, m_mac, m_rob

@torch.inference_mode()
def predict_ensemble(texts, tok, m_mac, m_rob, device, max_length=160, temp=1.0, bias=None):
    assert isinstance(texts, (list, tuple)), "texts must be a list of strings"
    assert len(texts) > 0, "texts is empty"
    print(f"[run] batch_size={len(texts)}  max_length={max_length}  temp={temp}")

    enc = tok(texts, truncation=True, padding=True, max_length=max_length, return_tensors="pt")
    enc = {k: v.to(device) for k, v in enc.items()}
    print("[shape] input_ids:", tuple(enc["input_ids"].shape))

    logit_mac = m_mac(**enc).logits
    logit_rob = m_rob(**enc).logits
    print("[shape] logits mac:", tuple(logit_mac.shape), "rob:", tuple(logit_rob.shape))

    logits = (logit_mac + logit_rob) / 2
    if bias is not None:
        # bias 例如：对 negative 轻扣 0.10 -> torch.tensor([-0.10, 0.0, 0.0], device=device)
        logits = logits + bias

    probs = torch.softmax(logits / float(temp), dim=-1)
    pred  = probs.argmax(dim=-1).cpu().tolist()
    return pred, probs.cpu().numpy()

def main():
    device = get_device()
    try:
        tok, m_mac, m_rob = load_models(MAC_DIR, MAC_DIR, ROB_DIR, device)
    except Exception as e:
        print("[error] load failed:", repr(e))
        sys.exit(1)

    # 自检样例（确保一定有输出）
    samples = [
        "这电影太差了，浪费时间！",
        "这更新就那样吧，影响不大。",
        "太喜欢了！绝绝子！😍"
    ]
    print("[data] samples:", samples)

    # 给 negative 轻扣偏置，减少 neutral→negative 误判
    bias = torch.tensor([-0.10, 0.0, 0.0], device=device)  # 或 None
    try:
        labels, probs = predict_ensemble(samples, tok, m_mac, m_rob, device,
                                         max_length=MAX_LEN, temp=TEMP, bias=bias)
        print("[ok] labels:", labels)
        print("[ok] probs:\n", np.round(probs, 4))
    except Exception as e:
        print("[error] predict failed:", repr(e))
        sys.exit(2)

if __name__ == "__main__":
    main()