# The Unofficial Guide — Project 1

> Note to self: the reflective sections (Failure Case Analysis, Spec Reflection,
> AI Usage) are drafted from what I actually did — reword them in my own voice
> before submitting.

---

## Domain

**UC Berkeley Off-Campus Housing & Campus Survival Guide.**

This system covers the practical, survival-level knowledge of renting and living near
UC Berkeley: tenant and landlord rights under California law, how to recognize rental
and sublet scams, and student-cooperative (BSC) housing rules. This knowledge is
valuable because it is scattered across dense legal PDFs, campus-police warning pages,
and co-op policy wikis — no single official page pulls it together, and the parts that
matter most to a stressed student looking for housing (what's a scam red flag, how much
deposit is legal, what to do when a landlord won't fix something) are buried in long
documents most people never read end-to-end.

---

## Document Sources

The corpus that was **successfully ingested** for this build:

| # | Source | Type | URL or file path |
|---|--------|------|------------------|
| 1 | California Tenants Rights Guide (DRE) | PDF | documents/ca_tenants_guide.pdf — https://www.dre.ca.gov/files/pdf/2025_Landlord_Tenant_Guide.pdf |
| 2 | UCPD — Avoiding Scams | HTML | https://ucpd.berkeley.edu/safety/avoiding-scams |
| 3 | BSC Policy Wiki | HTML | https://policy.bsc.coop/index.php/BSC_Policy_Wiki |

**Sources planned but not ingested (honest accounting):**

| Source | Type | Why it isn't in the corpus |
|--------|------|----------------------------|
| r/berkeley threads (×3: landlords, northside/southside, safety) | Reddit | Reddit returns HTTP 403 to automated requests (blocks non-browser clients); would require manual `.txt` saves or the PRAW API |
| Off-Campus Housing — Avoid Scams | HTML | `och.berkeley.edu` sits behind a WAF that 403s non-browser IPs |
| Cal Housing FAQs | HTML | JavaScript-rendered — `requests`+BeautifulSoup only see an empty shell (14 chars after cleaning), so it is skipped |
| Crossroads / Durant dining reviews | CSV | Self-authored mock data, deliberately **disabled** (`enabled: False`) to keep the corpus to real, verifiable sources |
| Sublet scams guide | TXT | Self-authored, disabled for the same reason |

> The corpus is therefore **official / legal** in character (tenant law + scam warnings +
> co-op rules) rather than the community-opinion mix originally planned. See Spec Reflection.

---

## Chunking Strategy

**Chunk size:** 800 characters (sliding window, split on whitespace so words aren't cut).

**Overlap:** 150 characters (~10–20%, roughly one sentence).

**Preprocessing before chunking:**
- Stripped `script/style/nav/header/footer/form/aside/button` tags.
- Removed boilerplate nav lines ("Skip to main content", "Menu", etc.) and de-duplicated repeated lines.
- For MediaWiki (BSC), extracted only the `#mw-content-text` region and cut the "Retrieved from" footer.
- Fixed character-encoding mojibake by letting charset detection win (`resp.apparent_encoding`).
- Skipped JavaScript-rendered pages that cleaned down to < 200 chars (flagged, not chunked).
- PDF extracted page-by-page with pdfplumber (one record per page before chunking).

**Why these choices fit my documents:** the corpus is mixed-length. The tenant PDF and
the UCPD page are long-form, so an 800-char window holds about one complete idea (a single
scam red-flag, one security-deposit rule) without diluting the embedding with several
unrelated topics. The 150-char overlap keeps a fact that lands on a chunk boundary
recoverable in the adjacent chunk. (Short, atomic sources like CSV reviews would have been
kept whole, but those are disabled in this build.)

**Final chunk count:** **755 chunks** across the 3 ingested documents (732 from the PDF,
~19 UCPD, ~4 BSC). 0 empty chunks; chunk length min/avg/max = 304 / 761 / 799 chars.

---

## Sample Chunks (5 labeled)

1. **California Tenants Rights Guide (PDF)** — "…Before you move in, the landlord can only
   require you to pay up to one month's rent as a security deposit ($1,000). The landlord
   also can require you to pay the first month's rent…"
2. **California Tenants Rights Guide (PDF)** — "The tenant should notify the landlord in
   writing about the conditions that require repair… The rental unit must have serious
   habitability defects that were not caused by the tenant…"
3. **California Tenants Rights Guide (PDF)** — "The landlord or the landlord's agent must
   give the tenant reasonable advance notice in writing before entering the unit and can
   enter only during normal business hours (generally, 8 a.m. to 5 p.m. seven days per week)."
4. **UCPD: Avoiding Scams** — "The suspect frequently requires up-front payment of rent,
   deposit, and/or other significant fees, often before any showing of the property or
   signing any contract. They often claim to be unable to meet the victim in person, and
   might request payment via wire transfer…"
5. **BSC Policy Wiki** — "…Appendix A: Information for Members … Policy Creation and
   Formatting Guide … Policy Changes By Semester. The Board of Directors has chosen to
   elevate certain…" *(note: this page is largely a table of contents — see Failure Case)*

---

## Embedding Model

**Model used:** `all-MiniLM-L6-v2` (sentence-transformers, 384-dim), stored in **ChromaDB**
with **cosine** distance (`hnsw:space=cosine`). It runs locally with no API key or rate
limits, is fast, and gives solid general-purpose semantic quality — a good fit for a free,
local project. Each vector carries metadata: `source_name`, `source_type`, `kind`, `title`, `url`.

**Production tradeoff reflection:** my domain text is entity-heavy ("People's Park",
landlord names, statute references), and MiniLM can weight rare proper nouns weakly. With
cost no object I'd weigh a larger or domain-adapted model (e.g. OpenAI `text-embedding-3-large`)
for better rare-entity handling. I'd also weigh **context length** (MiniLM truncates around
256 tokens, so my 800-char chunks can get clipped — a longer-context model would embed full
chunks), **multilingual support** (Berkeley has many international students), and
**latency / hosting / privacy** (a bigger hosted model is slower and sends data off-machine,
versus MiniLM running locally). The core tradeoff is domain accuracy vs. latency, cost, and privacy.

---

## Retrieval Test Results

Top-k = 4, cosine distance (lower = closer). Three queries with their best-matching chunk:

| Query | Best distance | Source of top chunk |
|-------|---------------|---------------------|
| How much can a landlord charge for a security deposit in California? | **0.258** | California Tenants Rights Guide (PDF) |
| What can a tenant do if the landlord refuses to make repairs? | **0.218** | California Tenants Rights Guide (PDF) |
| What payment methods are red flags for a rental scam? | **0.370** | UCPD: Avoiding Scams |

**Why these are relevant (2 explained):**
- *Security deposit* (0.258): the top chunk is the exact passage stating the one-month-rent
  cap with a worked $1,000 example — directly answers "how much." The low distance reflects
  strong semantic overlap between "security deposit / charge / landlord" and the chunk.
- *Repairs* (0.218): the top chunk is the "repair and deduct / notify the landlord in writing"
  procedure — precisely the action a tenant takes when repairs are refused. The very low
  distance shows the embedding matched the *intent* ("what can a tenant do") not just keywords.

---

## Grounded Generation

**System prompt grounding instruction (verbatim):**

> You are an assistant for an Unofficial UC Berkeley Housing & Campus Survival Guide. Answer
> the user's question using ONLY the information in the provided context documents below.
> Follow these rules strictly:
> 1. Use only facts found in the context. Do NOT use outside or general knowledge.
> 2. If the context does not contain enough information to answer, reply exactly: "I don't
>    have enough information on that."
> 3. When the context comes from a community source (Reddit/student opinion), present it as
>    unverified student opinion, not established fact.
> 4. Be concise and specific. Do not speculate.

**Structural grounding choices (not just the prompt):**
- Each retrieved chunk is injected into the prompt with a labeled header
  `[Document N | source: … | type: official/community/mock]`, so the model sees provenance.
- An **out-of-scope guard** in code: if even the closest chunk is farther than a cosine
  distance of 0.85, the system returns "I don't have enough information on that." *without
  calling the LLM at all* — so off-topic questions can't trigger a hallucinated answer.
- `temperature=0` for deterministic, context-bound output.

**How source attribution is surfaced:** attribution is built **programmatically**, not left
to the LLM. After retrieval, `_format_sources()` collects the unique `source_name (url)` of
the chunks actually used and returns them as a separate `sources` list, which the UI shows
in a dedicated "Retrieved from" box. The citation is therefore guaranteed even if the model
forgets to mention it.

---

## Example Responses (source attribution visible)

**1. In-scope — security deposit**
> **Q:** How much can a landlord charge for a security deposit in California?
> **A:** According to the California Tenants Rights Guide, as of July 1, 2024, landlords in
> California can charge no more than one month's rent as a security deposit, regardless of
> whether the residence is furnished or unfurnished. This limit applies to all types of
> deposits, including pet deposits, key fees, and cleaning fees.
> **Retrieved from:** California Tenants Rights Guide (PDF) — documents/ca_tenants_guide.pdf

**2. In-scope — repairs**
> **Q:** What can a tenant do if the landlord refuses to make repairs?
> **A:** If the landlord refuses to make repairs, the tenant can either make the repairs (or
> hire someone) and deduct the cost from the rent, keeping all receipts; alternatively, the
> tenant can contact the local building, health, or housing department and request an inspection.
> **Retrieved from:** California Tenants Rights Guide (PDF) — documents/ca_tenants_guide.pdf

**3. Out-of-scope — correctly refuses**
> **Q:** What do students say about the best dining hall?
> **A:** I don't have enough information on that.
> **Retrieved from:** (declined — no source met the relevance threshold; dining data is disabled)

---

## Evaluation Report

The 5 test questions from planning.md, run end-to-end:

| # | Question | Expected answer | System response (summarized) | Retrieval quality | Response accuracy |
|---|----------|-----------------|------------------------------|-------------------|-------------------|
| 1 | What payment methods are red flags for a rental scam? | Untraceable methods: wire transfer, gift cards, crypto | "wire transfer, pre-paid debit cards, gift cards, cryptocurrency — hard to trace" (cited UCPD) | Relevant (0.37) | **Accurate** |
| 2 | Why is a landlord being out of the country a warning sign? | Scam excuse to avoid showing the unit / collect deposit first | "I don't have enough information on that." | Off-target | **Inaccurate** (see Failure Case) |
| 3 | What do students say about lunch-rush wait times at Crossroads? | Long lines ~noon, ~20 min | "I don't have enough information on that." | Off-target (0.72) | Correctly declined (data disabled) |
| 4 | Affordable late-night food on Durant? | La Burrita / Steve's Korean BBQ | "I don't have enough information on that." | Off-target (0.67) | Correctly declined (data disabled) |
| 5 | Beyond rent, what obligation do BSC members have? | Workshift/chore hours + conduct code | "I don't have enough information on that." | Partially relevant (0.53) | **Inaccurate** (data gap) |

Honest summary: 1/5 fully answered, 2/5 correctly declined (out-of-scope by design), 2/5
failed (one retrieval miss, one data gap). The system never hallucinated — every failure was
a refusal, not a wrong answer.

---

## Failure Case Analysis

**Question that failed:** "Why is a landlord being out of the country a warning sign?" (Q2)

**What the system returned:** "I don't have enough information on that." — even though the
UCPD source *does* describe this exact scam ("they often claim to be unable to meet the
victim in person…").

**Root cause (tied to the retrieval stage):** corpus imbalance. 732 of the 755 chunks come
from the California Tenants PDF, versus only ~19 from the UCPD scams page. For the indirect
phrasing "being out of the country," the four nearest chunks (top-k=4) were all tenant-PDF
passages (distances 0.41–0.49); the relevant UCPD chunk sat at roughly rank 5. With no
relevant chunk in the context window, the grounding prompt did its job and the model
correctly declined. (Diagnostic confirmation: re-querying with the word "scam" surfaces the
UCPD chunk at rank 1, distance 0.44 — so the content is retrievable, just out-ranked.)

**What I would change to fix it:** rebalance the corpus so one large document can't dominate
(ingest the blocked Reddit/OCH scam content so scam-topic chunks are better represented), or
add per-source retrieval / a small re-rank step, or increase k for recall. The cleanest fix
is corpus balance, since generation can't recover a chunk retrieval never returned.

---

## Spec Reflection

**One way the spec helped me during implementation:** deciding the `source_type`
(official / community / mock) tagging scheme in planning.md *before* writing code meant the
metadata was threaded through ingestion → chunking → embedding → generation from the start.
When I got to grounding, source attribution was almost free — the labels were already on
every chunk, so `_format_sources()` just had to collect them. Planning the metadata up front
saved a painful retrofit later.

**One way my implementation diverged from the spec, and why:** planning.md described a
community-heavy corpus (Reddit threads, mock dining reviews) balanced against official docs.
In practice Reddit and the OCH page block automated scraping, the Cal Housing FAQ is
JavaScript-rendered, and I chose to keep the AI-authored mock CSVs disabled to keep the
corpus to real, verifiable sources. The system therefore became an official tenant-law +
scam-warning guide rather than the planned opinion/official mix — which is also why eval
questions 3–5 (which assumed the community/dining data) fall out of scope.

---

## AI Usage

**Instance 1 — ingestion & chunking pipeline**
- *What I gave the AI:* my planning.md Documents and Chunking Strategy sections (file types:
  Reddit/HTML/PDF/CSV/TXT; chunk size 800 / overlap 150) and the `source_type` scheme.
- *What it produced:* `sources.py`, `ingest.py` (per-format extractors + a sliding-window
  `chunk_text()` in `chunk.py`).
- *What I changed or overrode:* after inspecting the first output I found mojibake
  (`person's` → `person�s`), leftover nav text, a MediaWiki menu leaking into chunks, and an
  empty JS-rendered FAQ page. I directed fixes: charset detection, boilerplate/dedup
  filtering, `#mw-content-text` extraction, and a < 200-char skip. I also disabled the mock
  data rather than trust AI-authored reviews.

**Instance 2 — retrieval & generation**
- *What I gave the AI:* my Retrieval Approach section (all-MiniLM-L6-v2, top-k=4, ChromaDB)
  and grounding requirements.
- *What it produced:* `embed.py` (cosine collection), `query.py` (`retrieve()` + grounded
  `ask()`), and the Gradio `app.py`.
- *What I changed or overrode:* I added the distance-cutoff out-of-scope guard and insisted
  attribution be built in code, not by the LLM. When Q2 failed, I ran a retrieval diagnostic
  and identified the 732-vs-19 corpus imbalance as the cause rather than blaming the prompt.
