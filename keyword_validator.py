#!/usr/bin/env python3
"""Mailbox Keyword Discovery & Validation. Usage: python keyword_validator.py"""
import asyncio, os, json, csv, re, sys
from datetime import datetime, timedelta
from collections import Counter
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

GROUP_A_KEYWORDS = {
    "receipt": 0.40, "invoice": 0.40, "payment": 0.35,
    "purchas": 0.40, "billing": 0.35, "charge": 0.30,
    "paid": 0.35, "transaction": 0.25, "debit": 0.25,
    "withdrawal": 0.25, "automatic payment": 0.40,
    "recurring": 0.35, "you paid": 0.40, "payment to": 0.40,
    "payment from": 0.30, "charged to": 0.35,
    "payment confirmation": 0.40, "payment receipt": 0.40,
    "receipt for": 0.40, "invoice from": 0.40,
    "order confirmation": 0.30, "account statement": 0.20,
    "tax invoice": 0.40, "subscription payment": 0.40,
    "payment processed": 0.35, "payment received": 0.35,
    "confirmed": 0.20,
    "danovy doklad": 0.40, "faktura": 0.40, "platba": 0.35,
    "uhrada": 0.35, "zuctovani": 0.30, "odchozi platba": 0.40,
    "platba kartou": 0.40, "potvrzeni platby": 0.40,
    "zauctovani": 0.30, "castka": 0.20,
}

GROUP_B_KEYWORDS = {
    "welcome": 0.35, "welcome to": 0.40, "welcome aboard": 0.40,
    "your account": 0.35, "account created": 0.40,
    "account confirmed": 0.40, "account verified": 0.35,
    "account activated": 0.40, "verification complete": 0.35,
    "verified": 0.25, "registration": 0.35, "registered": 0.35,
    "sign up": 0.35, "signup": 0.35, "subscription": 0.30,
    "subscription confirmed": 0.40, "your subscription": 0.35,
    "your plan": 0.35, "plan activated": 0.40, "activated": 0.30,
    "activation": 0.25, "confirmation": 0.25, "get started": 0.30,
    "you re in": 0.30, "you re all set": 0.35,
    "thank you for joining": 0.40, "thank you for subscribing": 0.45,
    "thank you for signing up": 0.40, "thanks for joining": 0.35,
    "thanks for subscribing": 0.40, "thanks for signing up": 0.35,
    "new account": 0.35, "your new": 0.20, "service activated": 0.35,
    "membership": 0.25, "trial started": 0.25, "trial activated": 0.25,
    "premium activated": 0.35, "pro activated": 0.35,
    "registered for": 0.30, "you joined": 0.30,
    "vitaj": 0.35, "vitejte": 0.35, "registrace": 0.35,
    "registrovan": 0.30, "ucet": 0.30, "predplatne": 0.35,
    "aktivace": 0.25, "potvrzeni registrace": 0.35,
    "profil": 0.15, "clenstvi": 0.25,
}

NEGATIVE_KEYWORDS = {
    "offer": -0.30, "discount": -0.30, "sale": -0.25,
    "promo": -0.25, "promotion": -0.25, "coupon": -0.25,
    "newsletter": -0.40, "unsubscribe": -0.30,
    "weekly digest": -0.40, "weekly update": -0.30,
    "job alert": -0.40, "marketing": -0.40,
    "advertisement": -0.40, "you might like": -0.35,
    "recommended for you": -0.35, "flash sale": -0.35,
    "limited time": -0.30, "percent off": -0.25,
    "referral": -0.30, "invite": -0.20, "gift": -0.20,
    "reward": -0.20, "check out": -0.20,
    "don t miss": -0.25, "last chance": -0.25,
    "board snapshot": -0.40, "comment on": -0.30,
    "push notification": -0.35, "mentioned you": -0.30,
    "new comment": -0.30, "new reply": -0.30, "spam": -0.50,
    "reklama": -0.40, "akce": -0.20, "sleva": -0.30, "darek": -0.20,
}

# ── CLASSIFICATION ENGINE ──────────────────────────────────

def compile_patterns():
    compiled = {}
    for label, kw_dict in [("A", GROUP_A_KEYWORDS), ("B", GROUP_B_KEYWORDS), ("NEG", NEGATIVE_KEYWORDS)]:
        pats = {}
        for kw, weight in kw_dict.items():
            esc = re.escape(kw).replace(r"\*", ".*").replace(r"\ ", r"\s+")
            pats[kw] = {"re": re.compile(esc, re.I), "weight": weight}
        compiled[label] = pats
    return compiled

def classify(subject, cp):
    if not subject:
        return {"a":0,"b":0,"neg":0,"a_hits":[],"b_hits":[],"neg_hits":[],"final":"skip"}
    s = subject.lower()
    a_score=0; b_score=0; neg_score=0
    a_hits=[]; b_hits=[]; neg_hits=[]
    for kw, info in cp["A"].items():
        if info["re"].search(s): a_score+=info["weight"]; a_hits.append(kw)
    for kw, info in cp["B"].items():
        if info["re"].search(s): b_score+=info["weight"]; b_hits.append(kw)
    for kw, info in cp["NEG"].items():
        if info["re"].search(s): neg_score+=info["weight"]; neg_hits.append(kw)
    a_score = max(0, a_score+neg_score)
    b_score = max(0, b_score+neg_score)
    is_a = a_score >= 0.35
    is_b = b_score >= 0.35
    if is_a and is_b: final="both"
    elif is_a: final="group_a_payment"
    elif is_b: final="group_b_account"
    else: final="skip"
    return {"a":round(a_score,3),"b":round(b_score,3),"neg":round(neg_score,3),
            "a_hits":a_hits[:5],"b_hits":b_hits[:5],"neg_hits":neg_hits[:5],
            "is_a":is_a,"is_b":is_b,"final":final}

# ── FETCHING ───────────────────────────────────────────────

async def fetch_source(source, limit, days):
    print(f"  Fetching up to {limit} from {source} (last {days}d)...")
    from email_fetcher import EmailFetcher
    f = EmailFetcher()
    try:
        if source == "gmail":
            em = await f.fetch_gmail(max_results=limit, since_days=days)
        elif source == "outlook":
            em = await f.fetch_outlook(max_results=limit, since_days=days)
        elif source == "imap":
            em = await f.fetch_imap(max_results=limit, since_days=days)
        else:
            em = []
        print(f"  Got {len(em)} from {source}")
        return em
    except Exception as e:
        print(f"  Error {source}: {e}")
        return []

async def run_discovery(sources=None, limit=200, days=90):
    if sources is None: sources = ["gmail", "outlook", "imap"]
    out = Path("discovery_output"); out.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    cp = compile_patterns()
    all_r = []
    stats = {"total":0,"a":0,"b":0,"both":0,"skip":0,"by_src":{},
             "top_a":Counter(),"top_b":Counter(),"top_neg":Counter()}
    for src in sources:
        print(f"\n[{src.upper()}]")
        emails = await fetch_source(src, limit, days)
        stats["by_src"][src] = len(emails)
        for em in emails:
            subj = em.get("subject","") or ""
            res = classify(subj, cp)
            entry = {"source":src,"message_id":(em.get("message_id","") or "")[:40],
                     "subject":subj[:120],"sender":(em.get("sender","") or "")[:80],
                     "body_preview":((em.get("body","") or "")[:100]),
                     "a_score":res["a"],"b_score":res["b"],"neg_score":res["neg"],
                     "a_hits":"|".join(res["a_hits"]),"b_hits":"|".join(res["b_hits"]),
                     "neg_hits":"|".join(res["neg_hits"]),"final":res["final"],
                     "date":em.get("date","")}
            all_r.append(entry)
            stats["total"]+=1
            if res["final"]=="skip": stats["skip"]+=1
            elif res["final"]=="both": stats["both"]+=1
            elif res["final"]=="group_a_payment": stats["a"]+=1
            elif res["final"]=="group_b_account": stats["b"]+=1
            for k in res["a_hits"]: stats["top_a"][k]+=1
            for k in res["b_hits"]: stats["top_b"][k]+=1
            for k in res["neg_hits"]: stats["top_neg"][k]+=1
    jpath = out/f"discovery_{ts}.json"
    with open(jpath,"w",encoding="utf-8") as f:
        json.dump({"summary":{k:v for k,v in stats.items() if k!="top_a" and k!="top_b" and k!="top_neg"},"results":all_r}, f, indent=2, ensure_ascii=False)
    cpath = out/f"discovery_{ts}.csv"
    fn = ["source","subject","sender","final","a_score","b_score","neg_score","a_hits","b_hits","neg_hits","date"]
    with open(cpath,"w",newline="",encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fn)
        w.writeheader()
        for r in all_r: w.writerow({k:r.get(k,"") for k in fn})
    t = stats["total"]
    print(f"\n{'='*60}")
    print(f"DISCOVERY SUMMARY")
    print(f"{'='*60}")
    print(f"Total:     {t}")
    print(f"Group A:   {stats['a']:>5} ({stats['a']/max(t,1)*100:.1f}%)")
    print(f"Group B:   {stats['b']:>5} ({stats['b']/max(t,1)*100:.1f}%)")
    print(f"Both:      {stats['both']:>5} ({stats['both']/max(t,1)*100:.1f}%)")
    print(f"Skip:      {stats['skip']:>5} ({stats['skip']/max(t,1)*100:.1f}%)")
    print(f"\nTop A keywords:")
    for kw,c in stats["top_a"].most_common(15): print(f"  {kw:25s} {c:>4}")
    print(f"\nTop B keywords:")
    for kw,c in stats["top_b"].most_common(15): print(f"  {kw:25s} {c:>4}")
    print(f"\nTop Negative:")
    for kw,c in stats["top_neg"].most_common(10): print(f"  {kw:25s} {c:>4}")
    print(f"\nJSON: {jpath}")
    print(f"CSV:  {cpath}")
    return stats, all_r

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--source", choices=["gmail","outlook","imap","all"], default="all")
    p.add_argument("--limit", type=int, default=200)
    p.add_argument("--days", type=int, default=90)
    a = p.parse_args()
    srcs = ["gmail","outlook","imap"] if a.source == "all" else [a.source]
    asyncio.run(run_discovery(srcs, a.limit, a.days))
