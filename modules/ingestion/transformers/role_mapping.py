"""Keyword-based title-to-role mapping for bootstrapped job postings.

Maps raw job titles to canonical role names used by analytics_sdi for
SDI grouping. Applied in historical_bootstrap.py after all transformers run.

Rules:
- Matching is case-insensitive on the lowercased title.
- Rules are evaluated in order; the first match wins.
- Titles matching no rule are assigned "Other" and excluded from SDI computation.
- SBERT-based matching is deferred to Stage 2.
"""

from __future__ import annotations

# Each entry is (keywords_tuple, canonical_role_name).
# Order matters — more specific patterns must come before generic ones.
_ROLE_RULES: list[tuple[tuple[str, ...], str]] = [
    # Data & AI specializations — before generic "engineer"/"developer"
    (("data scientist", "machine learning engineer", "ml engineer", "ai engineer",
      "deep learning engineer", "research scientist", "research engineer",
      "computer vision engineer", "nlp engineer", "ai researcher"), "Data Scientist"),
    (("data engineer", "etl developer", "etl engineer", "data pipeline",
      "big data engineer", "data infrastructure", "analytics engineer",
      "data platform engineer"), "Data Engineer"),
    (("data analyst", "business analyst", "bi analyst", "business intelligence",
      "data analytics", "reporting analyst", "insights analyst",
      "data and analytics", "analytics analyst"), "Data Analyst"),

    # Infrastructure & Cloud
    (("devops engineer", "devops", "devsecops", "site reliability",
      "sre engineer", "sre", "platform engineer", "infrastructure engineer",
      "release engineer", "build engineer"), "DevOps Engineer"),
    (("cloud engineer", "cloud architect", "cloud infrastructure",
      "aws engineer", "azure engineer", "gcp engineer",
      "cloud solutions architect", "cloud developer"), "Cloud Engineer"),
    (("cybersecurity", "security engineer", "information security",
      "infosec", "security analyst", "penetration tester", "ethical hacker",
      "security operations", "soc analyst", "cyber analyst",
      "application security", "network security engineer"), "Cybersecurity Engineer"),
    (("network engineer", "network administrator", "network analyst",
      "network architect", "systems administrator", "sysadmin",
      "network technician", "network specialist",
      "telecommunications engineer"), "Network Engineer"),
    (("database administrator", "dba", "database engineer",
      "database analyst", "database developer",
      "sql developer", "sql engineer"), "Database Administrator"),
    (("systems engineer", "system engineer", "systems architect",
      "solutions architect", "enterprise architect",
      "solutions engineer", "technical architect"), "Systems Engineer"),

    # Software Development — backend/fullstack before frontend
    (("backend developer", "backend engineer", "back-end developer",
      "back end developer", "back end engineer",
      "api developer", "api engineer",
      "server-side developer"), "Software Engineer"),
    (("software engineer", "software developer", "swe",
      "application developer", "application engineer",
      "programmer", "programmer analyst",
      "software programmer", "software specialist",
      "junior developer", "senior developer",
      "associate developer", "associate engineer"), "Software Engineer"),
    (("fullstack developer", "full stack developer", "full-stack developer",
      "fullstack engineer", "full stack engineer", "full-stack engineer",
      "fullstack", "full stack"), "Web Developer"),
    (("frontend developer", "frontend engineer", "front-end developer",
      "front end developer", "front-end engineer", "front end engineer",
      "web developer", "web engineer",
      "ui developer", "ui engineer",
      "react developer", "angular developer", "vue developer",
      "javascript developer", "html developer"), "Web Developer"),

    # Mobile
    (("mobile developer", "mobile engineer", "android developer",
      "ios developer", "flutter developer", "react native developer",
      "mobile app developer", "mobile application developer",
      "swift developer", "kotlin developer"), "Mobile Developer"),

    # Embedded & Hardware
    (("embedded systems", "embedded engineer", "firmware engineer",
      "iot engineer", "hardware engineer", "fpga engineer"), "Embedded Engineer"),

    # QA & Testing
    (("qa engineer", "quality assurance engineer", "quality assurance analyst",
      "test engineer", "software tester", "automation engineer",
      "automation tester", "qa analyst", "qa tester",
      "sdet", "quality engineer", "testing engineer"), "QA Engineer"),

    # Project / Product Management
    (("product manager", "product owner", "technical product manager",
      "associate product manager", "it product manager"), "Product Manager"),
    (("project manager", "it project manager", "technical project manager",
      "scrum master", "agile coach", "delivery manager"), "Project Manager"),

    # Systems & Business Analysis
    (("systems analyst", "it analyst", "business systems analyst",
      "functional analyst", "requirements analyst",
      "technical analyst", "application analyst"), "Systems Analyst"),

    # IT Support & Operations
    (("it support", "helpdesk", "help desk", "desktop support",
      "technical support", "it technician", "it specialist",
      "service desk", "it operations", "field technician",
      "it administrator", "it coordinator", "end user support",
      "level 1 support", "l1 support", "l2 support"), "IT Support"),

    # Design
    (("ui ux", "ux designer", "ui designer", "user experience designer",
      "product designer", "interaction designer",
      "ux researcher", "ui/ux"), "UX Designer"),

    # Game Development
    (("game developer", "game programmer", "game engineer",
      "unity developer", "unreal developer",
      "game designer", "gameplay programmer"), "Game Developer"),

    # Blockchain / Web3
    (("blockchain developer", "blockchain engineer", "smart contract developer",
      "web3 developer", "solidity developer",
      "crypto developer"), "Blockchain Developer"),
]

OTHER_ROLE = "Other"


def map_role(title: str) -> str:
    """Map a raw job title to a canonical role name.

    Matching is case-insensitive and uses substring search against the
    lowercased title. The first matching rule wins.

    Args:
        title: Raw job title string from a source dataset.

    Returns:
        A canonical role name string, or 'Other' if no rule matches.
    """
    lower = title.strip().lower()
    for keywords, role in _ROLE_RULES:
        for kw in keywords:
            if kw in lower:
                return role
    return OTHER_ROLE


def get_all_canonical_roles() -> list[str]:
    """Return the list of all canonical role names defined in the mapping.

    Returns:
        Deduplicated list of canonical role name strings.
    """
    seen: set[str] = set()
    roles: list[str] = []
    for _, role in _ROLE_RULES:
        if role not in seen:
            seen.add(role)
            roles.append(role)
    return roles
