"""
Central registry of all 10 document sources for the Unofficial Berkeley Housing Guide.

Each source has:
  - name:        human-readable label
  - kind:        how to ingest it -> "reddit" | "html" | "pdf" | "csv" | "txt"
  - source_type: trust tag used later for retrieval/grounding
                 "official" (.edu/.gov/co-op rules) | "community" (Reddit) | "mock" (self-authored)
  - location:    a URL (remote) OR a path under documents/ (local file)
  - extra:       per-kind options (e.g. Reddit search params)

NOTE on Reddit: we don't hardcode fragile thread IDs. We hit the subreddit
search .json endpoint, take the top N posts, and pull each post + its comments.
"""

# Subreddit we scrape
SUBREDDIT = "berkeley"

SOURCES = [
    # ---------------- Reddit (community / lived experience) ----------------
    {
        "name": "Reddit: Northside vs Southside",
        "kind": "reddit",
        "source_type": "community",
        "location": "northside vs southside housing",
        "extra": {"limit": 8},
    },
    {
        "name": "Reddit: Worst Landlords & Property Management",
        "kind": "reddit",
        "source_type": "community",
        "location": "bad landlord property management",
        "extra": {"limit": 8},
    },
    {
        "name": "Reddit: Night Safety & People's Park",
        "kind": "reddit",
        "source_type": "community",
        "location": "safety peoples park night",
        "extra": {"limit": 8},
    },

    # ---------------- Official HTML ----------------
    {
        "name": "Cal Housing FAQs",
        "kind": "html",
        "source_type": "official",
        "location": "https://housing.berkeley.edu/resources/faqs/",
    },
    {
        "name": "Off-Campus Housing: Avoid Scams & Fraud",
        "kind": "html",
        "source_type": "official",
        "location": "https://och.berkeley.edu/avoid-scams-and-fraud",
    },
    {
        "name": "UCPD: Avoiding Scams",
        "kind": "html",
        "source_type": "official",
        "location": "https://ucpd.berkeley.edu/safety/avoiding-scams",
    },
    {
        "name": "BSC Policy Wiki",
        "kind": "html",
        "source_type": "official",
        "location": "https://policy.bsc.coop/index.php/BSC_Policy_Wiki",
    },

    # ---------------- PDF (download once into documents/) ----------------
    # Download the "California Tenants: A Guide to Residential Tenants' and
    # Landlords' Rights and Responsibilities" PDF and save it as the path below.
    # (Search: "California Tenants guide pdf landlordtenant.dre.ca.gov")
    {
        "name": "California Tenants Rights Guide (PDF)",
        "kind": "pdf",
        "source_type": "official",
        "location": "documents/ca_tenants_guide.pdf",
    },

    # ---------------- CSV (self-authored mock review data) ----------------
    {
        "name": "Crossroads Dining Reviews",
        "kind": "csv",
        "source_type": "mock",
        "location": "documents/crossroads_reviews.csv",
    },
    {
        "name": "Durant Ave Cheap Eats Reviews",
        "kind": "csv",
        "source_type": "mock",
        "location": "documents/durant_eats_reviews.csv",
    },

    # ---------------- TXT (self-authored guide) ----------------
    {
        "name": "Sublet Scams Guide",
        "kind": "txt",
        "source_type": "mock",
        "location": "documents/sublet_scams_guide.txt",
    },
]
