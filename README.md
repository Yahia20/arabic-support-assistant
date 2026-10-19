# arabic-support-assistant

A customer-support assistant for a travel agency in Saudi Arabia. Customers ask about fees,
refunds, baggage, visas and Umrah packages in **Saudi dialect, formal Arabic or English**. The
assistant answers only from the company's written policy, **code checks every answer before it
is sent**, and anything it cannot prove goes to a person.

**Results page:** https://yahia20.github.io/arabic-support-assistant/ ([العربية](https://yahia20.github.io/arabic-support-assistant/?lang=ar))
· [README بالعربي](README.ar.md)

> Saffar Travel is a fictional company invented for this project. Its policies and prices are made up.

## Results

245 test messages, written and committed before any assistant code existed, marked by code.

| Model | Wrong answers sent | Handed over when needed | Answered by itself | Cost / 1,000 conversations | Median reply |
|---|---|---|---|---|---|
| **DeepSeek Flash** (shipped) | **0 / 163** | **68 / 68** | 163 / 165 (98.8%) | **$0.17** | 1.4 s |
| DeepSeek V4 Pro | 4 / 167 | 65 / 68 | 163 / 165 (98.8%) | $0.92 | 3.4 s |

The model that costs 5 times more did worse. It answered three compensation and exception
requests itself — "there is no additional financial compensation" — a decision the policy never
makes and a person should. The cheaper model handed every one of them over.

By language (DeepSeek Flash): Saudi dialect 124 / 126, formal Arabic 40 / 40, English 79 / 79.
The right policy section reached the model for all 165 policy questions.

## How it works

```
message ─> find sections ─> one model call ─> code checks ─┬─ answer (cited, numbers verified)
           (embeddings,      answer / handoff /             ├─ hand over to a person + summary
            top 5 + index)   redirect / need_section        └─ polite redirect
```

1. **Find the policy.** Every policy line is embedded in Arabic and English with
   `paraphrase-multilingual-MiniLM-L12-v2`. A section scores as well as its best line, plus a
   small word-overlap bonus. The 5 best sections are shown to the model, with an index of all 14
   so it can ask for a section the search missed (`need_section`, used once at most).
2. **Decide.** One model call returns JSON: the action, the reply in the customer's language, the
   sections used, and for a hand-over a reason and a one-line summary for the agent.
3. **Check with code.** An answer is sent only if it cites a section that was shown and every
   number in it is in that section or follows from the customer's numbers by one step of
   arithmetic (250 × 3 passengers). Otherwise it becomes a hand-over. Hand-over and redirect
   replies get the same number check; one that adds an outside number (a phone number, a fee) is
   replaced with the standard hand-over text.
4. **Hand over cleanly.** Complaints, compensation, actions on a specific booking or account,
   billing problems, emergencies, legal threats, requests for exceptions, and anything the policy
   does not cover go to a person.

## Run it

```bash
pip install -r requirements.txt
cp .env.example .env                     # add DEEPSEEK_API_KEY
python -m pytest                         # checks, grader, question sets — no API calls
PYTHONPATH=src python -m support_assistant "ابي اغير موعد رحلتي وتذكرتي توفير، كم الرسوم؟"
python eval/run_eval.py --set dev        # tuning set
python eval/run_eval.py --set test --model deepseek-v4-pro
python scripts/report.py                 # rebuild site/index.html from results/
```

Every model reply is cached in `.cache/`, so a re-run only pays for new messages, and spend is
capped by `MAX_SPEND_USD`. Re-running the whole test from cache costs nothing.

## How the test was kept honest

- `eval/test.yaml` (245 messages) was committed in `7ebd4eb`, before the assistant code, and has
  not been edited since. All tuning used `eval/dev.yaml` (78 different messages).
- Marking is code only: the right action, a cited section from the expected list, and every
  expected figure in the reply. No model grades another model.
- The marking is strict. A correct reply that writes a number in words ("حقيبتين", two bags)
  counts as wrong — that is one of DeepSeek V4 Pro's four.
- Results files (`results/*/test.jsonl`) hold every message, reply and mark.

## Good to know

- Both of DeepSeek Flash's misses are safe: they went to a person. One is a check limitation:
  "12 الف ريال" (12 thousand) is not read as 12,000, so a correct answer containing 12,000 was
  held back. The test was not changed to hide it.
- Reading the test replies showed hand-over messages could add numbers of their own (an
  emergency phone number). That is why hand-over replies now pass the number check too. If you
  want the assistant to give emergency numbers, write them into the policy.
- The policy book has 14 sections. A much larger one would need a reranker and its own retrieval test.
- The test is single messages, not long conversations.

## Layout

```
policies/policies.yaml      the fictional company's policy, Arabic and English, same numbers
eval/test.yaml, dev.yaml    question sets
eval/run_eval.py            run + mark a set for one model
src/support_assistant/      retrieval, model call, checks, grader
scripts/report.py           results page
results/<model>/            every reply and mark
```
