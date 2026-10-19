"""Build the results page (site/index.html) from results/*/test.jsonl. No number is typed by hand.

    python scripts/report.py
"""
from __future__ import annotations

import html
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
SITE = ROOT / "site"
MAIN = "deepseek-flash"            # the model the assistant ships with

NAMES = {
    "deepseek-flash": {"en": "DeepSeek Flash", "ar": "DeepSeek Flash"},
    "deepseek-v4-pro": {"en": "DeepSeek V4 Pro", "ar": "DeepSeek V4 Pro"},
}
EXAMPLES = ["t001", "t023", "t146", "t081", "t177", "t184", "t214", "t234"]
LANG_LABEL = {"ar-sa": {"en": "Saudi dialect", "ar": "لهجة سعودية"},
              "ar-msa": {"en": "Formal Arabic", "ar": "فصحى"},
              "en": {"en": "English", "ar": "إنجليزي"}}
ACTION = {"answer": {"en": "Answered", "ar": "أجاب"},
          "handoff": {"en": "Handed to a person", "ar": "حوّل لموظف"},
          "redirect": {"en": "Polite redirect", "ar": "اعتذر ووجّه"}}

T = {
    "title": {"en": "A support assistant that answers in Saudi dialect — and knows when to hand over",
              "ar": "مساعد خدمة عملاء يرد باللهجة السعودية — ويعرف متى يحوّل لموظف"},
    "lead": {"en": "Customers of a travel agency ask about fees, refunds, baggage, visas and Umrah packages in Saudi dialect, formal Arabic or English. "
                   "The assistant answers only from the company's written policy, and code checks every answer before it is sent. "
                   "Anything it cannot prove — complaints, compensation, a specific booking, a question the policy doesn't cover — goes to a person.",
             "ar": "عملاء وكالة سفر يسألون عن الرسوم والاسترداد والأمتعة والتأشيرات وباقات العمرة باللهجة السعودية أو الفصحى أو الإنجليزية. "
                   "المساعد يجيب فقط من سياسة الشركة المكتوبة، والكود يراجع كل إجابة قبل إرسالها. "
                   "وكل ما لا يستطيع إثباته — الشكاوى والتعويضات وطلبات حجز محدد والأسئلة التي لا تغطيها السياسة — يذهب لموظف."},
    "fictional": {"en": "Saffar Travel is a fictional company invented for this project; its policies and prices are made up.",
                  "ar": "سفّار للسفر شركة وهمية صُممت لهذا المشروع؛ سياساتها وأسعارها غير حقيقية."},
    "headline": {"en": "Results on 245 test messages", "ar": "النتائج على 245 رسالة اختبار"},
    "s_wrong": {"en": "wrong answers sent to customers", "ar": "إجابات خاطئة وصلت للعملاء"},
    "s_wrong_note": {"en": "{sent} answers sent, every one checked by code", "ar": "من {sent} إجابة أُرسلت، كلها راجعها الكود"},
    "s_handoff": {"en": "messages that needed a person were handed over", "ar": "من الرسائل التي تحتاج موظفًا حُوّلت له"},
    "s_auto": {"en": "of policy questions answered correctly without a person", "ar": "من أسئلة السياسة أُجيبت صحيحًا دون موظف"},
    "s_cost": {"en": "per 1,000 conversations", "ar": "لكل 1,000 محادثة"},
    "s_cost_note": {"en": "median reply in {sec} s", "ar": "متوسط الرد {sec} ث"},
    "cmp_title": {"en": "Which model should run it?", "ar": "أي نموذج يشغّله؟"},
    "cmp_lead": {"en": "The same 245 messages, the same retrieval, the same checks — only the model changes.",
                 "ar": "نفس الـ 245 رسالة، ونفس البحث، ونفس الفحوصات — النموذج فقط يتغير."},
    "c_model": {"en": "Model", "ar": "النموذج"},
    "c_wrong": {"en": "Wrong answers sent", "ar": "إجابات خاطئة أُرسلت"},
    "c_handoff": {"en": "Handed over when needed", "ar": "حوّل عند الحاجة"},
    "c_auto": {"en": "Answered by itself", "ar": "أجاب وحده"},
    "c_cost": {"en": "Cost / 1,000", "ar": "التكلفة / 1,000"},
    "c_sec": {"en": "Median reply", "ar": "متوسط الرد"},
    "ex_title": {"en": "Real replies from the test", "ar": "ردود حقيقية من الاختبار"},
    "ex_lead": {"en": "Unedited output of the shipped model. The last column shows what the other model did with the same message.",
                "ar": "مخرجات النموذج المعتمد دون تعديل. العمود الأخير يوضح ماذا فعل النموذج الآخر بنفس الرسالة."},
    "miss_title": {"en": "Every miss, explained", "ar": "كل خطأ، مع شرحه"},
    "how_title": {"en": "How it works", "ar": "كيف يعمل"},
    "fair_title": {"en": "How the test was kept honest", "ar": "كيف حافظنا على نزاهة الاختبار"},
}
HOW = [
    {"en": "Find the policy. Each policy line is embedded in Arabic and English with a multilingual embedding model; the 5 closest sections are shown to the model, plus an index of all 14 so it can ask for one the search missed.",
     "ar": "إيجاد السياسة: كل سطر في السياسة مُمثَّل بالعربي والإنجليزي بنموذج تمثيل متعدد اللغات؛ تُعرض أقرب 5 أقسام على النموذج، مع فهرس الأقسام الـ 14 ليطلب قسمًا فاته البحث."},
    {"en": "Decide. One model call returns an action — answer, hand over, or redirect — with the reply and the sections it used.",
     "ar": "القرار: استدعاء واحد للنموذج يرجع إجراءً — يجيب أو يحوّل أو يعتذر — مع الرد والأقسام التي استخدمها."},
    {"en": "Check with code. An answer is sent only if it cites a section that was shown, and every number in it is in that section or follows from the customer's numbers (250 × 3 passengers). Otherwise it goes to a person.",
     "ar": "المراجعة بالكود: لا تُرسل الإجابة إلا إذا ذكرت قسمًا عُرض فعلًا، وكان كل رقم فيها موجودًا في القسم أو ناتجًا من أرقام العميل (250 × 3 ركاب). وإلا تذهب لموظف."},
    {"en": "Hand over cleanly. Complaints, compensation, actions on a booking, emergencies, legal threats, exceptions and anything the policy doesn't cover go to a person with a one-line summary.",
     "ar": "تحويل منظّم: الشكاوى والتعويضات وطلبات تنفيذ على حجز والطوارئ والتهديدات القانونية والاستثناءات وكل ما لا تغطيه السياسة تذهب لموظف مع ملخص بسطر واحد."},
]
FAIR = [
    {"en": "The 245 test messages were written and committed ({test_commit}) before any assistant code existed, and were not edited after the first run. Tuning used a separate 78-message dev set.",
     "ar": "كُتبت رسائل الاختبار الـ 245 وحُفظت ({test_commit}) قبل كتابة أي كود للمساعد، ولم تُعدَّل بعد أول تشغيل. التحسين تم على مجموعة منفصلة من 78 رسالة."},
    {"en": "Marking is done by code: the right action, a cited section from the expected list, and every expected figure present in the reply. No model grades another model.",
     "ar": "التصحيح بالكود: الإجراء الصحيح، وذكر قسم من الأقسام المتوقعة، ووجود كل رقم متوقع في الرد. لا يقيّم نموذجٌ نموذجًا آخر."},
    {"en": "The marking is strict: a correct reply that writes a number in words (\"two bags\") counts as wrong. The misses below show where that happened.",
     "ar": "التصحيح صارم: الرد الصحيح الذي يكتب الرقم بالحروف (\"حقيبتين\") يُحسب خطأ. الأخطاء أدناه توضح أين حدث ذلك."},
    {"en": "Mix of the test: {mix}.", "ar": "تركيبة الاختبار: {mix}."},
]


def load(model: str) -> tuple[list[dict], dict] | None:
    rows_file, summary_file = RESULTS / model / "test.jsonl", RESULTS / model / "test.summary.json"
    if not rows_file.exists():
        return None
    rows = [json.loads(l) for l in rows_file.read_text(encoding="utf-8").splitlines() if l.strip()]
    return rows, json.loads(summary_file.read_text(encoding="utf-8"))


def pct(x: float | None) -> str:
    return "—" if x is None else f"{100 * x:.1f}%".replace(".0%", "%")


def commit_of(path: str) -> str:
    out = subprocess.run(["git", "log", "--diff-filter=A", "--format=%h", "--", path], cwd=ROOT,
                         capture_output=True, text=True)
    return (out.stdout.strip().splitlines() or ["?"])[-1]


def explain(row: dict, lang: str) -> str:
    g, r = row["grade"]["why"], row["result"]
    if r["overruled"]:
        return {"en": f"The code withheld the answer ({r['overruled']}) and sent it to a person — a safe miss.",
                "ar": f"الكود أوقف الإجابة ({r['overruled']}) وحوّلها لموظف — خطأ آمن."}[lang]
    if g.startswith("expected answer, got handoff"):
        return {"en": "Handed to a person although the policy answers it — a safe miss.",
                "ar": "حوّل لموظف رغم أن السياسة تجيب — خطأ آمن."}[lang]
    if g.startswith("expected handoff, got answer"):
        return {"en": "Answered by itself where a person should decide — an unsafe miss.",
                "ar": "أجاب بنفسه حيث يجب أن يقرر موظف — خطأ غير آمن."}[lang]
    return {"en": f"Strict marking: {g}.", "ar": f"تصحيح صارم: {g}."}[lang]


def render(lang: str, runs: dict) -> str:
    e = html.escape
    t = lambda k, **kw: T[k][lang].format(**kw)  # noqa: E731
    rows, s = runs[MAIN]
    by_id = {m: {r["item"]["id"]: r for r in rr} for m, (rr, _) in runs.items()}
    other = next((m for m in runs if m != MAIN), None)

    stats = f"""
    <div class="stats">
      <div class="stat"><b>{s['wrong_answers_sent']}</b><span>{t('s_wrong')}</span><i>{t('s_wrong_note', sent=s['answers_sent'])}</i></div>
      <div class="stat"><b>{pct(s['handoff_recall'])}</b><span>{t('s_handoff')}</span><i>{round(s['handoff_recall'] * s['handoff_cases'])} / {s['handoff_cases']}</i></div>
      <div class="stat"><b>{pct(s['automation'])}</b><span>{t('s_auto')}</span><i>{round(s['automation'] * s['answerable'])} / {s['answerable']}</i></div>
      <div class="stat"><b>${s['cost_per_1000_usd']:.2f}</b><span>{t('s_cost')}</span><i>{t('s_cost_note', sec=f"{s['median_seconds']:.1f}")}</i></div>
    </div>"""

    cmp_rows = ""
    for m, (_, ms) in runs.items():
        cmp_rows += (f"<tr{' class=main' if m == MAIN else ''}><th>{e(NAMES.get(m, {}).get(lang, m))}</th>"
                     f"<td>{ms['wrong_answers_sent']} / {ms['answers_sent']}</td><td>{pct(ms['handoff_recall'])}</td>"
                     f"<td>{pct(ms['automation'])}</td><td>${ms['cost_per_1000_usd']:.2f}</td><td>{ms['median_seconds']:.1f} s</td></tr>")

    ex_rows = ""
    for qid in EXAMPLES:
        r = by_id[MAIN][qid]
        res = r["result"]
        tag = ", ".join(res["sections"]) if res["action"] == "answer" else res["reason"]
        oth = ""
        if other:
            o = by_id[other][qid]
            mark = "ok" if o["grade"]["ok"] else "bad"
            oth = f"<td class={mark}>{ACTION[o['result']['action']][lang]}</td>"
        ex_rows += (f"<tr><td><span class=lang>{LANG_LABEL[r['item']['lang']][lang]}</span><p dir=auto>{e(r['item']['q'])}</p></td>"
                    f"<td><span class='act {res['action']}'>{ACTION[res['action']][lang]}</span> <code>{e(tag)}</code><p dir=auto>{e(res['reply'])}</p></td>{oth}</tr>")

    misses = ""
    for m, (rr, _) in runs.items():
        for r in rr:
            if r["grade"]["ok"]:
                continue
            misses += (f"<li><b>{e(NAMES.get(m, {}).get(lang, m))}</b> · <span dir=auto>{e(r['item']['q'])}</span><br>"
                       f"<span class=muted>{e(explain(r, lang))}</span></li>")

    mix_counts = {}
    for r in rows:
        mix_counts[r["item"]["lang"]] = mix_counts.get(r["item"]["lang"], 0) + 1
    kinds = {k: sum(r["item"]["expect"] == k for r in rows) for k in ("answer", "handoff", "redirect")}
    mix = {"en": f"{kinds['answer']} policy questions, {kinds['handoff']} that need a person, {kinds['redirect']} off-topic; "
                 + ", ".join(f"{n} {LANG_LABEL[k]['en']}" for k, n in mix_counts.items()),
           "ar": f"{kinds['answer']} سؤالًا عن السياسة، و{kinds['handoff']} تحتاج موظفًا، و{kinds['redirect']} خارج الموضوع؛ "
                 + "، ".join(f"{n} {LANG_LABEL[k]['ar']}" for k, n in mix_counts.items())}[lang]
    fair = "".join(f"<li>{e(x[lang].format(test_commit=commit_of('eval/test.yaml'), mix=mix))}</li>" for x in FAIR)
    how = "".join(f"<li>{e(x[lang])}</li>" for x in HOW)
    other_head = f"<th>{e(NAMES.get(other, {}).get(lang, other))}</th>" if other else ""
    switch = '<a href="?lang=ar">العربية</a>' if lang == "en" else '<a href="?lang=en">English</a>'

    return f"""<section lang="{lang}" dir="{'rtl' if lang == 'ar' else 'ltr'}" data-lang="{lang}">
  <nav>{switch}</nav>
  <h1>{t('title')}</h1>
  <p class="lead">{t('lead')}</p>
  <p class="note">{t('fictional')}</p>
  <h2>{t('headline')} · {e(NAMES[MAIN][lang])}</h2>
  {stats}
  <h2>{t('cmp_title')}</h2>
  <p>{t('cmp_lead')}</p>
  <div class="scroll"><table class="cmp"><thead><tr><th>{t('c_model')}</th><th>{t('c_wrong')}</th><th>{t('c_handoff')}</th><th>{t('c_auto')}</th><th>{t('c_cost')}</th><th>{t('c_sec')}</th></tr></thead><tbody>{cmp_rows}</tbody></table></div>
  <h2>{t('ex_title')}</h2>
  <p>{t('ex_lead')}</p>
  <div class="scroll"><table class="ex"><tbody>{ex_rows}</tbody></table></div>
  <h2>{t('how_title')}</h2>
  <ol>{how}</ol>
  <h2>{t('miss_title')}</h2>
  <ul class="misses">{misses}</ul>
  <h2>{t('fair_title')}</h2>
  <ul>{fair}</ul>
</section>"""


CSS = """
:root{--bg:#f6f5f1;--surface:#fff;--ink:#15171a;--ink2:#3c4148;--muted:#5d636b;--line:#e0dfd8;--accent:#0b6b62;--soft:#ddf0ec;--bad:#b42318;--badsoft:#fde7e4}
@media (prefers-color-scheme:dark){:root{--bg:#0f1113;--surface:#171a1e;--ink:#eceef0;--ink2:#c5cad0;--muted:#9ba2ab;--line:#2a2f35;--accent:#3cc4b1;--soft:#11302c;--bad:#ff8073;--badsoft:#321614}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 "IBM Plex Sans","IBM Plex Sans Arabic",system-ui,sans-serif}
section{max-width:1040px;margin:0 auto;padding:32px 16px 64px}section[hidden]{display:none}
nav{display:flex;justify-content:flex-end}nav a{color:var(--accent);font-weight:600;text-decoration:none;border:1px solid var(--line);padding:6px 14px;border-radius:999px}
h1{font-size:clamp(1.7rem,4vw,2.6rem);line-height:1.2;margin:16px 0}h2{margin-top:44px;font-size:1.35rem}
.lead{font-size:1.1rem;color:var(--ink2);max-width:75ch}.note{color:var(--muted);font-size:.9rem}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px}
.stat{background:var(--surface);border:1px solid var(--line);border-radius:16px;padding:16px 18px;display:flex;flex-direction:column;gap:4px}
.stat b{font-size:2.1rem;color:var(--accent);line-height:1.1}.stat i{font-style:normal;color:var(--muted);font-size:.85rem}
.scroll{overflow-x:auto}table{border-collapse:collapse;width:100%;background:var(--surface);border:1px solid var(--line);border-radius:14px;overflow:hidden}
th,td{padding:10px 12px;border-bottom:1px solid var(--line);text-align:start;vertical-align:top}thead th{font-size:.85rem;color:var(--muted)}
tr.main th{color:var(--accent)}td p{margin:4px 0 0}.ex td:first-child{width:32%}
.lang{font-size:.75rem;color:var(--muted);font-weight:600}.act{font-size:.78rem;font-weight:700;padding:2px 8px;border-radius:999px;background:var(--soft);color:var(--accent)}
.act.handoff{background:#fbeedb;color:#9a5700}code{font-size:.78rem;color:var(--muted)}
td.ok{color:var(--accent);font-weight:600}td.bad{color:var(--bad);font-weight:600;background:var(--badsoft)}
.misses li{margin-bottom:10px}.muted{color:var(--muted)}
"""


def main() -> int:
    models = [MAIN] + sorted(p.name for p in RESULTS.iterdir() if p.is_dir() and p.name != MAIN)
    runs = {m: r for m in models if (r := load(m))}
    body = "\n".join(render(lang, runs) for lang in ("en", "ar"))
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Arabic support assistant · results</title>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Arabic:wght@400;600;700&family=IBM+Plex+Sans:wght@400;600;700&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body>
{body}
<script>
  var lang = new URLSearchParams(location.search).get("lang") === "ar" ? "ar" : "en";
  document.querySelectorAll("section[data-lang]").forEach(function (s) {{ s.hidden = s.dataset.lang !== lang; }});
  document.documentElement.lang = lang; document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
</script>
</body></html>"""
    SITE.mkdir(exist_ok=True)
    (SITE / "index.html").write_text(page, encoding="utf-8")
    summary = {m: s for m, (_, s) in runs.items()}
    (SITE / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote site/index.html · models: {', '.join(runs)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
