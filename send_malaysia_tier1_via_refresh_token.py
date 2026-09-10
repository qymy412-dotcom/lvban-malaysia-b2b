"""
Lvban Furniture — Gmail API via OAuth2 Refresh Token (无浏览器 OAuth flow)
=============================================================================
作者: 南瓜 (Scribe Expert / outreach-writer)
用途: 用 OAuth2 Refresh Token 直接调 Gmail API 发邮件
优势:
  - 无需本地 credentials.json / 无需浏览器 OAuth flow
  - 沙箱可直接调用（只走 HTTPS 443，不被 GFW/沙箱阻断）
  - 保留 qymy412@gmail.com 发件人身份（Gmail 高送达率）

⚙️ 必要环境变量（不落盘，只在 Bash 调用时临时设入）：
  - LVBAN_GMAIL_CLIENT_ID
  - LVBAN_GMAIL_CLIENT_SECRET
  - LVBAN_GMAIL_REFRESH_TOKEN

🚀 用法（与 v1 一致）：
  python send_malaysia_tier1_via_refresh_token.py --dry-run                       # 验证 OAuth + 队列
  python send_malaysia_tier1_via_refresh_token.py --start-now                     # 全部 EMAILS
  python send_malaysia_tier1_via_refresh_token.py --start-now --tag-filter "T2-"  # Tier 2 6 封
  python send_malaysia_tier1_via_refresh_token.py --start-now --single "..."      # 单封
"""

import os
import sys
import time
import json
import base64
import re
import random
import argparse
import urllib.request
import urllib.error
import urllib.parse
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta

# ============================================================
# 自动加载 .env（持久化环境变量 → 用户再也不用手动设）
# ============================================================

ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")


def load_dotenv():
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())


load_dotenv()
import json
import base64
import argparse
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ====== Gmail API OAuth2 配置 ======
TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
GMAIL_PROFILE_URL = "https://gmail.googleapis.com/gmail/v1/users/me/profile"

SENDER_EMAIL = "qymy412@gmail.com"
SENDER_NAME = "Sun Nan"
COMPANY = "Lvban Furniture Co., Ltd."
ADDRESS = "No.108 Jingwan Road, Yuhua District, Changsha, Hunan, China"
WEBSITE = "https://www.aerunelv.com/"

UNSUBSCRIBE_FOOTER = "\n\n---\nIf you'd prefer not to receive future emails from Lvban Furniture, simply reply with \"unsubscribe\" and we'll remove you from our list."

CATALOG_FOOTER = "\n\nYou can browse our full product range at https://www.aerunelv.com/ — pricing is per-customer after we understand your target SKU and rough quantity."

SIGNATURE_TEMPLATE = "\n\nBest regards,\n{sender}\n{company}\n{address}\n{website}"

# ====== 6 封 Tier 2 + D+1 跟进 + 原版 Tier 1 草稿（与 v1 一致）======
EMAILS = [
    # ===== Tier 1 原版（已发过，仅供参考）=====
    {
        "tag": "Mail 2",
        "company": "New Orient Marketing",
        "to": "info@neworient.com.my",
        "subject": "20 years importing chairs from China — fresh ergonomic lineup for 2026",
        "body": """Hi,

New Orient has spent 20 years building direct relationships with Chinese chair manufacturers — exactly the OEM pipeline we've been investing in from the factory side in Zhejiang.

I'm Sun Nan from Hunan Lvban Furniture. We manufacture ergonomic chairs, gaming chairs and office seating with our own R&D (HoverTech floating-seat system), BIFMA / ISO 9001 / SGS certifications, and 10 years' manufacturing expertise.

Our Export-Exclusive Smart series (foldable design, 70% less shipping volume) and P5 Pro ergonomic mesh chair are tailored for Asian climate and Asian body data — a fit for Sabah, Sarawak and Peninsular Malaysia alike, including the government and school accounts you already serve.

Send two details — target SKU and rough quantity — and I'll have a tailored quote back to you within 24 hours.""",
    },
    {
        "tag": "Mail 3",
        "company": "U-Heng Office Equipment",
        "to": "uhengjb@gmail.com",
        "subject": "Ergonomic chairs from China — for the U-Heng 35-year JB-Singapore franchise",
        "body": """Dear Mr. Tan,

U-Heng's 35-year journey from a JB office-equipment shop to a cross-strait franchise with 840 completed projects is a textbook case of how JB-Singapore furniture businesses mature.

I'm Sun Nan from Hunan Lvban Furniture. We make ergonomic office chairs, gaming chairs, and standing desks in our own factory in China, certified to BIFMA / ISO 9001 / SGS, with 10 years' manufacturing expertise.

What's new from our side is a tightly curated export lineup — the Smart (Export Exclusive) Folding series (70% container saving), the P5 Pro ergonomic mesh chair, and the L6 Flagship entry-tier — all engineered for the JB-Singapore distribution channel you've already mapped.

If Marcus is your quote contact, feel free to loop him in. Reply with target SKU + quantity, and a tailored quote lands back within 24 hours.""",
    },
    {
        "tag": "Mail 4",
        "company": "Zenith Projects (ZenPro)",
        "to": "info@zenpro.com.my",
        "subject": "Behind Steelcase — a complementary ergonomic lineup from China for ZenPro's corporate accounts",
        "body": """Hi Emily / Mark,

ZenPro's positioning — Steelcase Authorised Dealer alongside Kastel and Stua, plus the Flow workpod and biophilic Glow wall system — clearly targets the corporate specifier. That's exactly why a complementary mid-tier ergonomic lineup from China is the natural missing piece.

I'm Sun Nan from Hunan Lvban Furniture. Our factory makes ergonomic chairs and standing desks to ISO 9001 / BIFMA / SGS, with 10 years' manufacturing expertise and 8 years serving export distributors (HoverTech floating-seat system, 120,000-cycle durability). We're not here to compete with Steelcase — we're here to round out your proposal tier on mid-budget corporate fit-outs where your clients still need solid ergonomic seating but can't land Steelcase-spec pricing.

Reply with two details — target SKU and rough quantity — and a tailored quote reaches your inbox within 24 hours.""",
    },
    {
        "tag": "Mail 5",
        "company": "OfficePro / IN PRO GROUP",
        "to": "inquiry@officepro.my",
        "subject": "Direct-from-China ergonomic + gaming lineup — for OfficePro's 14K-company distribution",
        "body": """Hi Mr. Yow / Ms. Jia Ling,

IN PRO GROUP runs OfficePro, Office Chairs Malaysia and Office Furniture Shop — three storefronts serving 14,000+ companies with a mix of imported brands and your own Humon, Sino and RXGAMER lines. Your gaming lineup is well-positioned across Malaysia and Singapore.

I'm Sun Nan from Hunan Lvban Furniture. We run our own R&D and factory in China — HoverTech floating-seat system, BIFMA / ISO 9001 / SGS certified, 10 years' manufacturing expertise. Our S3 Gaming (racing bucket design, 4D armrests), P5 Pro ergonomic mesh (4D armrests, fiberglass base), and value-tier L6 Flagship are built for the JB-SG distribution depth you've already mapped.

If you're reviewing supplier depth for 2026, send two details — target SKU and rough quantity — and a tailored quote is back to you within 24 hours.""",
    },
    {
        "tag": "Mail 6",
        "company": "Merryfair Chair System",
        "to": "enquiry@merryfair.com",
        "subject": "A complementary OEM partner from China — for Merryfair's MIFF 2026 export programme",
        "body": """Dear Mr. Ong,

Merryfair's MIFF 2026 launch — the Greenguard Gold-certified Wau, the recycled-material Aire, and the full-mesh Zenit — marks another milestone in your 50-year export journey across 90+ countries. Behind scenes like this, supply-chain breadth matters as much as in-house depth.

I'm Sun Nan from Hunan Lvban Furniture. We manufacture ergonomic office chairs, gaming chairs and standing desks in our own factory in China, certified to BIFMA / EN 1335-equivalent / ISO 9001 / SGS — the same benchmark your premium-tier partners meet. We're not here to chase Merryfair's flagship tier; we're offering a complementary mid-range ergonomic lineup (Smart folding series, P5 Pro mesh, L6 Flagship) for clients who need your quality at a different price point.

A short reply with two details — target product category and rough MOQ — and I'll send a tailored proposal within 24 hours.""",
    },
    # ===== Tier 1 D+1 跟进（已发过 4 封，Mail 6b 失败待重发）=====
    {
        "tag": "Mail 2b (D+1 follow-up)",
        "company": "New Orient Marketing",
        "to": "info@neworient.com.my",
        "subject": "Following up — ergonomic chairs for New Orient's distributor portfolio",
        "body": """Hi,

A quick follow-up on my note from yesterday. Lvban's ergonomic chair line — P5 Pro mesh, Smart folding series (70% less shipping volume), L6 Flagship — is built for Asian climate and Asian body data, BIFMA / ISO 9001 / SGS certified.

Reply with target SKU + rough monthly volume, and I'll have a per-customer quote + PDF catalog back within 24h.""",
    },
    {
        "tag": "Mail 3b (D+1 follow-up)",
        "company": "U-Heng Office Equipment",
        "to": "uhengjb@gmail.com",
        "subject": "Following up — ergonomic chairs from China for U-Heng's JB-Singapore franchise",
        "body": """Dear Mr. Tan,

Following up on yesterday's note. Lvban's export lineup — Smart (foldable, 70% container saving), P5 Pro mesh, L6 Flagship — fits the JB-SG distribution depth you've mapped.

Reply with target SKU + quantity (loop in Marcus if needed), and I'll send a tailored quote within 24h.""",
    },
    {
        "tag": "Mail 4b (D+1 follow-up)",
        "company": "Zenith Projects (ZenPro)",
        "to": "info@zenpro.com.my",
        "subject": "Following up — complementary ergonomic lineup for ZenPro's corporate accounts",
        "body": """Hi Emily / Mark,

Following up on yesterday's note. Lvban's mid-tier ergonomic lineup complements your Steelcase-dealer tier — same BIFMA / ISO 9001 / SGS bar, 10 years' manufacturing expertise.

Reply with target SKU + rough qty, and a tailored quote lands in your inbox within 24h.""",
    },
    {
        "tag": "Mail 5b (D+1 follow-up)",
        "company": "OfficePro / IN PRO GROUP",
        "to": "inquiry@officepro.my",
        "subject": "Following up — direct ergonomic + gaming lineup for OfficePro's distribution",
        "body": """Hi Mr. Yow / Ms. Jia Ling,

Following up on yesterday's note. Lvban's export lineup — S3 Gaming, P5 Pro mesh, L6 Flagship — fits the JB-SG distribution depth your 14K-company roll-out covers.

Reply with target SKU + rough qty, and I'll send a tailored quote within 24h.""",
    },
    {
        "tag": "Mail 6b (D+1 follow-up)",
        "company": "Merryfair Chair System",
        "to": "enquiry@merryfair.com",
        "subject": "Following up — Merryfair's MIFF-grade distribution: cost-effective + customizable + after-sale backed",
        "body": """Dear Mr. Ong,

A quick follow-up on yesterday's note.

Lvban Furniture — direct from China factory, BIFMA / ISO 9001 / SGS certified.

Three reasons Merryfair's MIFF-grade distribution fits Lvban:

→ Cost-effective — competitive factory-direct pricing, transparent per-unit quotes
→ Customization-ready — fabric/leather color, finish, logo embossing, OEM packaging
→ After-sale backed — 5-year warranty + lifetime maintenance + 7×24 customer service

Reply with target product + rough MOQ, and a tailored proposal lands back within 24h.""",
    },
    # ===== Tier 2（W2 群发）=====
    {
        "tag": "Mail T2-1 Stable",
        "company": "Stable Office Automation",
        "to": "stable@stable.com.my",
        "subject": "Office chair & desking lineup for Stable's contract fit-out across Kedah/Penang",
        "body": """Dear Mr. Tan,

Stable's 39-year track record fitting out semiconductor, automotive and hospital floors across the Kedah/Penang corridor is exactly the kind of contract depth Lvban's mid-tier ergonomic lineup complements.

We manufacture ergonomic chairs, gaming chairs and workstations at our BIFMA / ISO 9001 / SGS-certified factory in China — designed for 8-hour-shift ergonomics and contract-volume pricing.

Reply with target category (task / executive / operator) + rough monthly volume, and I'll send a per-customer quote + PDF catalog within 24h.""",
    },
    {
        "tag": "Mail T2-2 Bristol",
        "company": "Bristol Technologies",
        "to": "export@bristol.com.my",
        "subject": "Bristol's Asia-Pacific network — cost-effective + customizable + after-sale backed",
        "body": """Hi Beatrice,

Lvban Furniture — direct from China factory, BIFMA / ISO 9001 / SGS certified.

Three reasons Bristol's 11-city Asia showroom network fits Lvban:

→ Cost-effective — competitive factory-direct pricing, typically 30-50% below market list
→ Customization-ready — fabric/leather color, finish, logo embossing, OEM packaging
→ After-sale backed — 5-year warranty + lifetime maintenance + 7×24 customer service

Reply with target category + rough MOQ, and a tailored quote lands back within 24h.""",
    },
    {
        "tag": "Mail T2-3 AM Office",
        "company": "AM Office",
        "to": "info@amoffice.com.my",
        "subject": "AM Office's 100K-business roll-out — cost-effective + customizable + after-sale backed",
        "body": """Dear Mr. Soo,

Lvban Furniture — direct from China factory, BIFMA / ISO 9001 / SGS certified.

Three reasons AM Office's 100,000-business roll-out across Selangor / KL / Johor fits Lvban:

→ Cost-effective — competitive factory-direct pricing, transparent per-unit quotes
→ Customization-ready — fabric/leather color, finish, logo, OEM packaging, retail-ready SKUs
→ After-sale backed — 5-year warranty + lifetime maintenance + 7×24 customer service

Reply with target category + rough monthly volume, and a tailored quote + PDF catalog lands back within 24h.""",
    },
    {
        "tag": "Mail T2-4 Duracon",
        "company": "Duracon Trading",
        "to": "duraconsale@yahoo.com",
        "subject": "Duracon's JB-SME fit-out — cost-effective + customizable + after-sale backed",
        "body": """Hi Mr. Chew / Tan / Louis / Oscar,

Lvban Furniture — direct from China factory, BIFMA / ISO 9001 / SGS certified.

Three reasons Duracon's JB-SME fit-out portfolio fits Lvban:

→ Cost-effective — competitive factory-direct pricing, transparent per-unit quotes
→ Customization-ready — fabric/leather color, finish, logo embossing, OEM packaging
→ After-sale backed — 5-year warranty + lifetime maintenance + 7×24 customer service

Reply with target category + rough monthly volume, and a tailored quote + PDF catalog lands back within 24h.""",
    },
    {
        "tag": "Mail T2-5 Sinaran",
        "company": "Sinaran Office Supply",
        "to": "sinaran.sos@gmail.com",
        "subject": "Ergonomic + workstation lineup for Sinaran's Negeri Sembilan/Melaka/Selangor coverage",
        "body": """Hi Edwin / Syafiqah,

Sinaran's decade-long office-supply coverage across Negeri Sembilan, Melaka, KL and Selangor lines up with Lvban's ergonomic chair + workstation lineup — built for 8-hour-shift comfort, BIFMA / ISO 9001 / SGS certified.

Reply with target category (chair / workstation / standing desk) + rough monthly volume, and a tailored quote + PDF catalog lands back within 24h.""",
    },
    {
        "tag": "Mail T2-6 SFI Niaga",
        "company": "S.F.I Niaga Industries",
        "to": "sfienterprise@yahoo.com",
        "subject": "SFI's MOF-registered portfolio — cost-effective + customizable + after-sale backed",
        "body": """Dear Mr. Shamsol,

Lvban Furniture — direct from China factory, BIFMA / ISO 9001 / SGS certified.

Three reasons SFI's MOF-registered government + school portfolio fits Lvban:

→ Cost-effective — competitive factory-direct pricing, MOQ-flexible for tenders
→ Customization-ready — fabric/leather color, finish, logo, OEM packaging, custom SKUs for institutional procurement
→ After-sale backed — 5-year warranty + lifetime maintenance + on-site service team for government / school installations

Reply with target category + rough MOQ, and a tailored proposal lands back within 24h.""",
    },
    {
        "tag": "Mail N1 In Concept",
        "company": "In Concept Furniture (i-con)",
        "to": "sales@i-confurniture.com",
        "subject": "In Concept's 15-country export depth — direct factory supply for your Shah Alam system",
        "body": """Hi,

Lvban Furniture — direct from China factory, BIFMA / ISO 9001 / SGS certified.

Three reasons In Concept's 15-country export depth fits Lvban:

→ Cost-effective — competitive factory-direct pricing, transparent per-unit quotes
→ Customization-ready — fabric/leather color, finish, logo embossing, OEM packaging
→ After-sale backed — 5-year warranty + lifetime maintenance + 7×24 customer service

Reply with target category + rough MOQ, and a tailored quote lands back within 24h.
""",
    },
    {
        "tag": "Mail N2 Kenwei",
        "company": "Kenwei Office System",
        "to": "sales@kenwei.com.my",
        "subject": "Direct factory pricing for Kenwei's 30-year Puchong distribution",
        "body": """Hi,

Lvban Furniture — direct from China factory, BIFMA / ISO 9001 / SGS certified.

Three reasons Kenwei's 30-year Puchong office system depth fits Lvban:

→ Cost-effective — competitive factory-direct pricing, transparent per-unit quotes
→ Customization-ready — fabric/leather color, finish, logo embossing, OEM packaging
→ After-sale backed — 5-year warranty + lifetime maintenance + 7×24 customer service

Reply with target category + rough MOQ, and a tailored quote lands back within 24h.
""",
    },
    {
        "tag": "Mail N3 Standard Office",
        "company": "Standard Office Construction",
        "to": "info@standardoffice.com.my",
        "subject": "Renovation + office chair bundle for Standard's Klang fit-out portfolio",
        "body": """Hi,

Lvban Furniture — direct from China factory, BIFMA / ISO 9001 / SGS certified.

Three reasons Standard Office's Klang renovation + fit-out portfolio fits Lvban:

→ Cost-effective — competitive factory-direct pricing, transparent per-unit quotes
→ Customization-ready — fabric/leather color, finish, logo embossing, OEM packaging
→ After-sale backed — 5-year warranty + lifetime maintenance + 7×24 customer service

Reply with target category + rough MOQ, and a tailored quote lands back within 24h.
""",
    },
    {
        "tag": "Mail N4 CBS",
        "company": "Human Art Office System (CBS)",
        "to": "inquiry.cbsfurniture@gmail.com",
        "subject": "Director chair + gaming chair for CBS's Sunway Damansara clientele",
        "body": """Hi,

Lvban Furniture — direct from China factory, BIFMA / ISO 9001 / SGS certified.

Three reasons CBS's Sunway Damansara office supply depth fits Lvban:

→ Cost-effective — competitive factory-direct pricing, transparent per-unit quotes
→ Customization-ready — fabric/leather color, finish, logo embossing, OEM packaging
→ After-sale backed — 5-year warranty + lifetime maintenance + 7×24 customer service

Reply with target category + rough MOQ, and a tailored quote lands back within 24h.
""",
    },
    {
        "tag": "Mail N5 AAA Supreme",
        "company": "AAA Office Furniture (Supreme)",
        "to": "nicholas@supremebusiness.com.my",
        "subject": "39-year distribution depth — direct factory pricing from China",
        "body": """Hi Nicholas,

Lvban Furniture — direct from China factory, BIFMA / ISO 9001 / SGS certified.

Three reasons AAA's 39-year Klang distribution depth fits Lvban:

→ Cost-effective — competitive factory-direct pricing, typically 30-50% below market list
→ Customization-ready — fabric/leather color, finish, logo embossing, OEM packaging
→ After-sale backed — 5-year warranty + lifetime maintenance + 7×24 customer service

Reply with target category + rough MOQ, and a tailored quote lands back within 24h.
""",
    },
    {
        "tag": "Mail N6 Aimsure",
        "company": "Aimsure Sdn Bhd",
        "to": "sales@aimsure.com.my",
        "subject": "20-year space-planning depth + direct ergonomic chair supply",
        "body": """Hi,

Lvban Furniture — direct from China factory, BIFMA / ISO 9001 / SGS certified.

Three reasons Aimsure's 20-year Seri Kembangan space-planning depth fits Lvban:

→ Cost-effective — competitive factory-direct pricing, transparent per-unit quotes
→ Customization-ready — fabric/leather color, finish, logo embossing, OEM packaging
→ After-sale backed — 5-year warranty + lifetime maintenance + 7×24 customer service

Reply with target category + rough MOQ, and a tailored quote lands back within 24h.
""",
    },
    {
        "tag": "Mail N7 My Perfect Team",
        "company": "My Perfect Team Marketing (MPT)",
        "to": "marketing@officefurnituresmalaysia.com",
        "subject": "B2B modular workstation + chair supply for MPT's Selangor footprint",
        "body": """Hi,

Lvban Furniture — direct from China factory, BIFMA / ISO 9001 / SGS certified.

Three reasons MPT's Selangor space-planning footprint fits Lvban:

→ Cost-effective — competitive factory-direct pricing, transparent per-unit quotes
→ Customization-ready — fabric/leather color, finish, logo embossing, OEM packaging
→ After-sale backed — 5-year warranty + lifetime maintenance + 7×24 customer service

Reply with target category + rough MOQ, and a tailored quote lands back within 24h.
""",
    },
    {
        "tag": "Mail N8 KT World Trading",
        "company": "KT World Trading",
        "to": "officegapsupply@gmail.com",
        "subject": "School + healthcare furniture for KT World — quality + cost-effective",
        "body": """Hi,

Lvban Furniture — direct from China factory, BIFMA / ISO 9001 / SGS certified.

Three reasons KT World's Shah Alam school + healthcare supply depth fits Lvban:

→ Cost-effective — competitive factory-direct pricing, transparent per-unit quotes
→ Customization-ready — fabric/leather color, finish, logo embossing, OEM packaging
→ After-sale backed — 5-year warranty + lifetime maintenance + 7×24 customer service

Reply with target category + rough MOQ, and a tailored quote lands back within 24h.
""",
    },
    {
        "tag": "Mail N9 Global E-Commerce",
        "company": "Global E-Commerce (Team Power)",
        "to": "sales@officefurnituremalaysian.com",
        "subject": "Direct ergonomic + gaming supply for Selangor 14K-customer reach",
        "body": """Hi,

Lvban Furniture — direct from China factory, BIFMA / ISO 9001 / SGS certified.

Three reasons Global E-Commerce's 14K-customer reach across Selangor fits Lvban:

→ Cost-effective — competitive factory-direct pricing, transparent per-unit quotes
→ Customization-ready — fabric/leather color, finish, logo embossing, OEM packaging
→ After-sale backed — 5-year warranty + lifetime maintenance + 7×24 customer service

Reply with target category + rough MOQ, and a tailored quote lands back within 24h.
""",
    },
    {
        "tag": "Mail N10 Apex",
        "company": "Apex Office Furniture Exporter",
        "to": "sales@apexfurniture.asia",
        "subject": "300-environment track record + complementary mid-tier ergonomic",
        "body": """Hi,

Lvban Furniture — direct from China factory, BIFMA / ISO 9001 / SGS certified.

Three reasons Apex's 300-environment track record across Malaysia fits Lvban:

→ Cost-effective — competitive factory-direct pricing, transparent per-unit quotes
→ Customization-ready — fabric/leather color, finish, logo embossing, OEM packaging
→ After-sale backed — 5-year warranty + lifetime maintenance + 7×24 customer service

Reply with target category + rough MOQ, and a tailored quote lands back within 24h.
""",
    },
    {
        "tag": "Mail N11 Wess Office",
        "company": "Wess Office System",
        "to": "sales@wessoffice.com.my",
        "subject": "Pahang + KL fit-out + direct chair supply — cost-effective",
        "body": """Hi,

Lvban Furniture — direct from China factory, BIFMA / ISO 9001 / SGS certified.

Three reasons Wess Office's Pahang + KL distribution depth fits Lvban:

→ Cost-effective — competitive factory-direct pricing, transparent per-unit quotes
→ Customization-ready — fabric/leather color, finish, logo embossing, OEM packaging
→ After-sale backed — 5-year warranty + lifetime maintenance + 7×24 customer service

Reply with target category + rough MOQ, and a tailored quote lands back within 24h.
""",
    },
    {
        "tag": "Mail N12 All Office Solution",
        "company": "All Office Solution (AOS)",
        "to": "info@aos.com.my",
        "subject": "100K-business cost-effective + customizable ergonomic supply",
        "body": """Hi,

Lvban Furniture — direct from China factory, BIFMA / ISO 9001 / SGS certified.

Three reasons AOS's 100K-business roll-out across Selangor / KL fits Lvban:

→ Cost-effective — competitive factory-direct pricing, transparent per-unit quotes
→ Customization-ready — fabric/leather color, finish, logo embossing, OEM packaging
→ After-sale backed — 5-year warranty + lifetime maintenance + 7×24 customer service

Reply with target category + rough MOQ, and a tailored quote lands back within 24h.
""",
    },
    {
        "tag": "Mail N13 Dream Office",
        "company": "Dream Office Concept",
        "to": "info@dreamoffice.com.my",
        "subject": "Local-manufactured mesh chair + direct import for Klang Valley",
        "body": """Hi,

Lvban Furniture — direct from China factory, BIFMA / ISO 9001 / SGS certified.

Three reasons Dream Office's Klang Valley mesh chair + import depth fits Lvban:

→ Cost-effective — competitive factory-direct pricing, transparent per-unit quotes
→ Customization-ready — fabric/leather color, finish, logo embossing, OEM packaging
→ After-sale backed — 5-year warranty + lifetime maintenance + 7×24 customer service

Reply with target category + rough MOQ, and a tailored quote lands back within 24h.
""",
    },
    {
        "tag": "Mail N14 Gozzo Direction",
        "company": "Gozzo Direction",
        "to": "sales@gozzodirection.com",
        "subject": "Manufacturer-direct ergonomic chair + after-sale backed",
        "body": """Hi,

Lvban Furniture — direct from China factory, BIFMA / ISO 9001 / SGS certified.

Three reasons Gozzo Direction's Klang ergonomic manufacturing depth fits Lvban:

→ Cost-effective — competitive factory-direct pricing, transparent per-unit quotes
→ Customization-ready — fabric/leather color, finish, logo embossing, OEM packaging
→ After-sale backed — 5-year warranty + lifetime maintenance + 7×24 customer service

Reply with target category + rough MOQ, and a tailored quote lands back within 24h.
""",
    },
    {
        "tag": "Mail N15 U-CASE",
        "company": "U-CASE Office Solutions",
        "to": "sales@u-case.com",
        "subject": "Penang fit-out + direct ergonomic supply for U-CASE distribution",
        "body": """Hi,

Lvban Furniture — direct from China factory, BIFMA / ISO 9001 / SGS certified.

Three reasons U-CASE's Penang office equipment + construction depth fits Lvban:

→ Cost-effective — competitive factory-direct pricing, transparent per-unit quotes
→ Customization-ready — fabric/leather color, finish, logo embossing, OEM packaging
→ After-sale backed — 5-year warranty + lifetime maintenance + 7×24 customer service

Reply with target category + rough MOQ, and a tailored quote lands back within 24h.
""",
    },
    {
        "tag": "Mail N16 LG Furnishing",
        "company": "LG Furnishing Sdn Bhd",
        "to": "sales@lgliving.com.my",
        "subject": "Penang design-led furniture + complementary office chair supply",
        "body": """Hi,

Lvban Furniture — direct from China factory, BIFMA / ISO 9001 / SGS certified.

Three reasons LG Furnishing's Penang design-led furniture depth fits Lvban:

→ Cost-effective — competitive factory-direct pricing, transparent per-unit quotes
→ Customization-ready — fabric/leather color, finish, logo embossing, OEM packaging
→ After-sale backed — 5-year warranty + lifetime maintenance + 7×24 customer service

Reply with target category + rough MOQ, and a tailored quote lands back within 24h.
""",
    },
    {
        "tag": "Mail N17 APEX Penang",
        "company": "APEX Office Furniture Penang (Perabut S&N)",
        "to": "sales@perabutsn.com.my",
        "subject": "30-year Penang distribution + direct China factory supply",
        "body": """Hi,

Lvban Furniture — direct from China factory, BIFMA / ISO 9001 / SGS certified.

Three reasons APEX Penang's 30-year Perlis / Kedah / Penang reach fits Lvban:

→ Cost-effective — competitive factory-direct pricing, transparent per-unit quotes
→ Customization-ready — fabric/leather color, finish, logo embossing, OEM packaging
→ After-sale backed — 5-year warranty + lifetime maintenance + 7×24 customer service

Reply with target category + rough MOQ, and a tailored quote lands back within 24h.
""",
    },
    {
        "tag": "Mail N18 Ebenezer",
        "company": "Ebenezer Furniture",
        "to": "sales@ebenezer.my",
        "subject": "Penang pioneer 50+ year + complementary office chair supply",
        "body": """Hi,

Lvban Furniture — direct from China factory, BIFMA / ISO 9001 / SGS certified.

Three reasons Ebenezer's 50+ year Penang furniture pioneer depth fits Lvban:

→ Cost-effective — competitive factory-direct pricing, transparent per-unit quotes
→ Customization-ready — fabric/leather color, finish, logo embossing, OEM packaging
→ After-sale backed — 5-year warranty + lifetime maintenance + 7×24 customer service

Reply with target category + rough MOQ, and a tailored quote lands back within 24h.
""",
    },
    {
        "tag": "Mail N19 Teyen",
        "company": "Teyen Office Furniture",
        "to": "info@teyenofficefurniture.com",
        "subject": "Custom-made office furniture for Banting SME + Selangor rollout",
        "body": """Hi,

Lvban Furniture — direct from China factory, BIFMA / ISO 9001 / SGS certified.

Three reasons Teyen's Banting custom-made office furniture depth fits Lvban:

→ Cost-effective — competitive factory-direct pricing, transparent per-unit quotes
→ Customization-ready — fabric/leather color, finish, logo embossing, OEM packaging
→ After-sale backed — 5-year warranty + lifetime maintenance + 7×24 customer service

Reply with target category + rough MOQ, and a tailored quote lands back within 24h.
""",
    },
    {
        "tag": "Mail N20 Ban Hoo",
        "company": "Ban Hoo Furniture Sdn Bhd",
        "to": "sales@banhoo.com.my",
        "subject": "Kedah retail + office furniture for Ban Hoo's North-Region clients",
        "body": """Hi,

Lvban Furniture — direct from China factory, BIFMA / ISO 9001 / SGS certified.

Three reasons Ban Hoo's Alor Setar home + office retail depth fits Lvban:

→ Cost-effective — competitive factory-direct pricing, transparent per-unit quotes
→ Customization-ready — fabric/leather color, finish, logo embossing, OEM packaging
→ After-sale backed — 5-year warranty + lifetime maintenance + 7×24 customer service

Reply with target category + rough MOQ, and a tailored quote lands back within 24h.
""",
    },
    {
        "tag": "Mail N21 ASPI",
        "company": "ASPI Typewriters & Stationery",
        "to": "sales@aspitypewriters.com",
        "subject": "1987 Kedah office equipment + direct chair supply for ASPI",
        "body": """Hi,

Lvban Furniture — direct from China factory, BIFMA / ISO 9001 / SGS certified.

Three reasons ASPI's 38-year Kedah office equipment depth fits Lvban:

→ Cost-effective — competitive factory-direct pricing, transparent per-unit quotes
→ Customization-ready — fabric/leather color, finish, logo embossing, OEM packaging
→ After-sale backed — 5-year warranty + lifetime maintenance + 7×24 customer service

Reply with target category + rough MOQ, and a tailored quote lands back within 24h.
""",
    },
    {
        "tag": "Mail N22 PK Furniture",
        "company": "PK Furniture System",
        "to": "sales@pkfurniture.com.my",
        "subject": "3000+ corporate clients + direct ergonomic chair supply",
        "body": """Hi,

Lvban Furniture — direct from China factory, BIFMA / ISO 9001 / SGS certified.

Three reasons PK Furniture's 3000+ corporate clients across JB fits Lvban:

→ Cost-effective — competitive factory-direct pricing, transparent per-unit quotes
→ Customization-ready — fabric/leather color, finish, logo embossing, OEM packaging
→ After-sale backed — 5-year warranty + lifetime maintenance + 7×24 customer service

Reply with target category + rough MOQ, and a tailored quote lands back within 24h.
""",
    },
    {
        "tag": "Mail N23 Homlux",
        "company": "Homlux Office System",
        "to": "sales@homluxoffice.com",
        "subject": "JB-SG cross-border + direct ergonomic supply for Homlux portfolio",
        "body": """Hi,

Lvban Furniture — direct from China factory, BIFMA / ISO 9001 / SGS certified.

Three reasons Homlux's JB-Singapore cross-border reach fits Lvban:

→ Cost-effective — competitive factory-direct pricing, transparent per-unit quotes
→ Customization-ready — fabric/leather color, finish, logo embossing, OEM packaging
→ After-sale backed — 5-year warranty + lifetime maintenance + 7×24 customer service

Reply with target category + rough MOQ, and a tailored quote lands back within 24h.
""",
    },
    {
        "tag": "Mail N24 Euroflex",
        "company": "Euroflex Design & Construction",
        "to": "sales@euroflexdesign.com",
        "subject": "JB design + construction + direct ergonomic supply bundle",
        "body": """Hi,

Lvban Furniture — direct from China factory, BIFMA / ISO 9001 / SGS certified.

Three reasons Euroflex's JB design + construction depth fits Lvban:

→ Cost-effective — competitive factory-direct pricing, transparent per-unit quotes
→ Customization-ready — fabric/leather color, finish, logo embossing, OEM packaging
→ After-sale backed — 5-year warranty + lifetime maintenance + 7×24 customer service

Reply with target category + rough MOQ, and a tailored quote lands back within 24h.
""",
    },
    {
        "tag": "Mail N25 Indah Office",
        "company": "Indah-Office Corporation",
        "to": "info@indahoffice.com.my",
        "subject": "10-year MOF + school + university + direct chair supply",
        "body": """Hi,

Lvban Furniture — direct from China factory, BIFMA / ISO 9001 / SGS certified.

Three reasons Indah-Office's 10-year MOF + university + school portfolio fits Lvban:

→ Cost-effective — competitive factory-direct pricing, transparent per-unit quotes
→ Customization-ready — fabric/leather color, finish, logo embossing, OEM packaging
→ After-sale backed — 5-year warranty + lifetime maintenance + 7×24 customer service

Reply with target category + rough MOQ, and a tailored quote lands back within 24h.
""",
    },
    {
        "tag": "Mail N26 SM Industries",
        "company": "S.M. Industries (M) Sdn Bhd",
        "to": "enquiries@smindustriessdnbhd.com",
        "subject": "1986 manufacturer + direct ergonomic + tender support for SM Industries",
        "body": """Hi,

Lvban Furniture — direct from China factory, BIFMA / ISO 9001 / SGS certified.

Three reasons SM Industries' 1986 manufacturer + government / private sector depth fits Lvban:

→ Cost-effective — competitive factory-direct pricing, transparent per-unit quotes
→ Customization-ready — fabric/leather color, finish, logo embossing, OEM packaging
→ After-sale backed — 5-year warranty + lifetime maintenance + 7×24 customer service

Reply with target category + rough MOQ, and a tailored quote lands back within 24h.
""",
    },
    {
        "tag": "Mail N27 WriteBest",
        "company": "WriteBest (JB) Sdn Bhd",
        "to": "sales@writebestjb.com.my",
        "subject": "Steel furniture + complementary office chair for WriteBest's 64-country reach",
        "body": """Hi,

Lvban Furniture — direct from China factory, BIFMA / ISO 9001 / SGS certified.

Three reasons WriteBest's JB steel furniture + 64-country export reach fits Lvban:

→ Cost-effective — competitive factory-direct pricing, transparent per-unit quotes
→ Customization-ready — fabric/leather color, finish, logo embossing, OEM packaging
→ After-sale backed — 5-year warranty + lifetime maintenance + 7×24 customer service

Reply with target category + rough MOQ, and a tailored quote lands back within 24h.
""",
    },
    {
        "tag": "Mail N28 Maxitech",
        "company": "Maxitech World Sdn Bhd",
        "to": "sales@maxitech.com.my",
        "subject": "Office automation + ergonomic + chair bundle for Maxitech's Klang B2B",
        "body": """Hi,

Lvban Furniture — direct from China factory, BIFMA / ISO 9001 / SGS certified.

Three reasons Maxitech's Klang office automation + system depth fits Lvban:

→ Cost-effective — competitive factory-direct pricing, transparent per-unit quotes
→ Customization-ready — fabric/leather color, finish, logo embossing, OEM packaging
→ After-sale backed — 5-year warranty + lifetime maintenance + 7×24 customer service

Reply with target category + rough MOQ, and a tailored quote lands back within 24h.
""",
    },
    {
        "tag": "Mail N29 ZAM",
        "company": "ZAM Automation",
        "to": "mail@zam.com.my",
        "subject": "100% Bumiputra + MOF + direct ergonomic supply for ZAM's tender portfolio",
        "body": """Hi,

Lvban Furniture — direct from China factory, BIFMA / ISO 9001 / SGS certified.

Three reasons ZAM's 100% Bumiputra + MOF-registered + Perlis / Penang / Kedah / Perak reach fits Lvban:

→ Cost-effective — competitive factory-direct pricing, transparent per-unit quotes
→ Customization-ready — fabric/leather color, finish, logo embossing, OEM packaging
→ After-sale backed — 5-year warranty + lifetime maintenance + 7×24 customer service

Reply with target category + rough MOQ, and a tailored quote lands back within 24h.
""",
    },
    {
        "tag": "Mail N30 HHT",
        "company": "HHT Office Furniture",
        "to": "hht@hhtoffice.com.my",
        "subject": "Office + gaming chair + direct ergonomic supply for HHT's Puchong reach",
        "body": """Hi,

Lvban Furniture — direct from China factory, BIFMA / ISO 9001 / SGS certified.

Three reasons HHT's Puchong office + gaming chair depth fits Lvban:

→ Cost-effective — competitive factory-direct pricing, transparent per-unit quotes
→ Customization-ready — fabric/leather color, finish, logo embossing, OEM packaging
→ After-sale backed — 5-year warranty + lifetime maintenance + 7×24 customer service

Reply with target category + rough MOQ, and a tailored quote lands back within 24h.
""",
    },
    {
        "tag": "Mail N31 Asiastar",
        "company": "Asiastar Furniture Trading Sdn Bhd",
        "to": "inquiry@asiastarfurniture.com",
        "subject": "Direct-from-China factory supply for Asiastar's 15K-company PJ + JB + nationwide reach",
        "body": """Hi,

Lvban Furniture — direct from China factory, BIFMA / ISO 9001 / TÜV SÜD / SGS certified.

Three reasons Asiastar's 15K-company + government + education + PJ + JB + nationwide footprint fits Lvban:

→ Cost-effective — factory-direct pricing that preserves margin on volume orders
→ Customization-ready — fabric/leather color, finish, logo embossing, OEM packaging, your own brand label
→ After-sale backed — 5-year warranty + lifetime maintenance + 7×24 customer service

Reply with target category + rough monthly volume, and a tailored quote lands back within 24h.
""",
    },
    {
        "tag": "Mail N32 Take A Seat",
        "company": "Take A Seat (Dreams Office Furniture Sdn Bhd)",
        "to": "enquiry@takeaseat.com.my",
        "subject": "JB Iskandar Puteri + direct ergonomic chair supply for Take A Seat's regional B2B",
        "body": """Hi,

Lvban Furniture — direct from China factory, BIFMA / ISO 9001 / SGS certified.

Three reasons Take A Seat's JB Iskandar Puteri + complete office furniture lineup fits Lvban:

→ Cost-effective — competitive factory-direct pricing, transparent per-unit quotes
→ Customization-ready — fabric/leather color, finish, logo embossing, OEM packaging
→ After-sale backed — 5-year warranty + lifetime maintenance + 7×24 customer service

Reply with target category + rough MOQ, and a tailored quote lands back within 24h.
""",
    },
    {
        "tag": "Mail N33 NSY Office System",
        "company": "NSY Office System",
        "to": "vincent.ng@nsyoffice.com",
        "subject": "22-year Puchong manufacturer + direct ergonomic + renovation supply bundle",
        "body": """Hi Vincent,

Lvban Furniture — direct from China factory, BIFMA / ISO 9001 / SGS certified.

Three reasons NSY's 22-year Puchong manufacturer + open-plan system + renovation expertise fits Lvban:

→ Cost-effective — competitive factory-direct pricing, transparent per-unit quotes
→ Customization-ready — fabric/leather color, finish, logo embossing, OEM packaging
→ After-sale backed — 5-year warranty + lifetime maintenance + 7×24 customer service

Reply with target category + rough MOQ, and a tailored quote lands back within 24h.
""",
    },
    {
        "tag": "Mail N34 KS Office Supplies",
        "company": "KS Office Supplies Sdn Bhd",
        "to": "enquiry@ksoffice.com.my",
        "subject": "Kota Damansara PJ one-stop + direct ergonomic supply for KS portfolio",
        "body": """Hi,

Lvban Furniture — direct from China factory, BIFMA / ISO 9001 / SGS certified.

Three reasons KS Office Supplies' Kota Damansara one-stop office furniture supply fits Lvban:

→ Cost-effective — competitive factory-direct pricing, transparent per-unit quotes
→ Customization-ready — fabric/leather color, finish, logo embossing, OEM packaging
→ After-sale backed — 5-year warranty + lifetime maintenance + 7×24 customer service

Reply with target category + rough MOQ, and a tailored quote lands back within 24h.
""",
    },
    {
        "tag": "Mail N35 JCOS Puchong",
        "company": "JC Team Office Solution (JCOS)",
        "to": "sales_jcteam@hotmail.com",
        "subject": "Puchong fit-out + renovation + direct ergonomic chair supply bundle",
        "body": """Hi,

Lvban Furniture — direct from China factory, BIFMA / ISO 9001 / SGS certified.

Three reasons JCOS's Puchong one-stop office furniture + renovation + carpet + partition depth fits Lvban:

→ Cost-effective — competitive factory-direct pricing, transparent per-unit quotes
→ Customization-ready — fabric/leather color, finish, logo embossing, OEM packaging
→ After-sale backed — 5-year warranty + lifetime maintenance + 7×24 customer service

Reply with target category + rough MOQ, and a tailored quote lands back within 24h.
""",
    },
    {
        "tag": "Mail N36 Cahaya Bintang",
        "company": "Cahaya Bintang Store",
        "to": "inquiry.cbsfurniture@gmail.com",
        "subject": "Sunway Damansara bulk ergonomic + direct China factory supply",
        "body": """Hi,

Lvban Furniture — direct from China factory, BIFMA / ISO 9001 / SGS certified.

Three reasons Cahaya Bintang's Sunway Damansara bulk ergonomic + office chair + partition supply fits Lvban:

→ Cost-effective — competitive factory-direct pricing, transparent per-unit quotes
→ Customization-ready — fabric/leather color, finish, logo embossing, OEM packaging
→ After-sale backed — 5-year warranty + lifetime maintenance + 7×24 customer service

Reply with target category + rough MOQ, and a tailored quote lands back within 24h.
""",
    },
    {
        "tag": "Mail N37 Comfort Office",
        "company": "Comfort Office Furniture",
        "to": "comfortofficefurniture@gmail.com",
        "subject": "Melaka southern region + direct ergonomic + bulk office furniture supply",
        "body": """Hi,

Lvban Furniture — direct from China factory, BIFMA / ISO 9001 / SGS certified.

Three reasons Comfort Office Furniture's Batu Berendam Melaka + southern region office supply fits Lvban:

→ Cost-effective — competitive factory-direct pricing, transparent per-unit quotes
→ Customization-ready — fabric/leather color, finish, logo embossing, OEM packaging
→ After-sale backed — 5-year warranty + lifetime maintenance + 7×24 customer service

Reply with target category + rough MOQ, and a tailored quote lands back within 24h.
""",
    },
    {
        "tag": "Mail N38 OFFICEPRO",
        "company": "OFFICEPRO (Office Pro Group)",
        "to": "info@officepro.my",
        "subject": "14k-company + KL/Penang/JB nationwide + direct China factory supply for OFFICEPRO",
        "body": """Hi,

Lvban Furniture — direct from China factory, BIFMA / ISO 9001 / SGS certified.

Three reasons OFFICEPRO's 14k-company KL/Selangor + Penang + JB + nationwide ergonomic office furniture line fits Lvban:

→ Cost-effective — factory-direct pricing that preserves margin on volume orders
→ Customization-ready — fabric/leather color, finish, logo embossing, OEM packaging, your own brand label
→ After-sale backed — 5-year warranty + lifetime maintenance + 7×24 customer service

Reply with target category + rough monthly volume, and a tailored quote lands back within 24h.
""",
    },
    {
        "tag": "Mail N39 MR.OFFICE",
        "company": "MR.OFFICE Malaysia (YANG SPACE SDN BHD)",
        "to": "mroffice2u@gmail.com",
        "subject": "Shah Alam Klang Valley + nationwide direct ergonomic + modular supply for MR.OFFICE",
        "body": """Hi,

Lvban Furniture — direct from China factory, BIFMA / ISO 9001 / SGS certified.

Three reasons MR.OFFICE's Shah Alam + Klang Valley + nationwide mesh chairs + workstations + partitions fits Lvban:

→ Cost-effective — factory-direct pricing with transparent per-unit quotes
→ Customization-ready — fabric/leather color, finish, logo embossing, OEM packaging
→ After-sale backed — 5-year warranty + lifetime maintenance + 7×24 customer service

Reply with target category + rough MOQ, and a tailored quote lands back within 24h.
""",
    },
    {
        "tag": "Mail N40 Furnic",
        "company": "Furnic Office Furniture",
        "to": "furnic.info@gmail.com",
        "subject": "Klang manufacturer + direct ergonomic + bulk office furniture supply for Furnic",
        "body": """Hi,

Lvban Furniture — direct from China factory, BIFMA / ISO 9001 / SGS certified.

Three reasons Furnic's Klang manufacturer + ergonomic chairs + workstations + storage fit Lvban:

→ Cost-effective — factory-direct pricing that preserves margin on volume orders
→ Customization-ready — fabric/leather color, finish, logo embossing, OEM packaging
→ After-sale backed — 5-year warranty + lifetime maintenance + 7×24 customer service

Reply with target category + rough monthly volume, and a tailored quote lands back within 24h.
""",
    },
    {
        "tag": "Mail N41 ZenPro",
        "company": "ZenPro / Zenith Projects Sdn Bhd",
        "to": "info@zenpro.com.my",
        "subject": "PJ Steelcase/Kastel/Stua authorized + direct China factory mid-tier bundle for ZenPro",
        "body": """Hi,

Lvban Furniture — direct from China factory, BIFMA / ISO 9001 / SGS certified.

Three reasons ZenPro's PJ modular workstations + acoustic pods + adjustable desks + Steelcase/Kastel/Stua authorized dealership fits Lvban:

→ Cost-effective — competitive factory-direct pricing, transparent per-unit quotes
→ Customization-ready — fabric/leather color, finish, logo embossing, OEM packaging
→ After-sale backed — 5-year warranty + lifetime maintenance + 7×24 customer service

Reply with target category + rough MOQ, and a tailored quote lands back within 24h.
""",
    },
    {
        "tag": "Mail N42 Ideal Safebox",
        "company": "IDEAL SAFEBOX MALAYSIA WORLD (Ideal Creations Empire)",
        "to": "sales.idealworlddestination@gmail.com",
        "subject": "Chubbsafes #1 + Klang/Setapak dual-branch + direct ergonomic supply for Ideal",
        "body": """Hi,

Lvban Furniture — direct from China factory, BIFMA / ISO 9001 / SGS certified.

Three reasons IDEAL SAFEBOX's Chubbsafes #1 Malaysia distributor + Klang + Setapak KL dual-branch + Shopee/Lazada + 100 Young CEO 2022 office supply fits Lvban:

→ Cost-effective — factory-direct pricing that preserves margin on volume orders
→ Customization-ready — fabric/leather color, finish, logo embossing, OEM packaging, your own brand label
→ After-sale backed — 5-year warranty + lifetime maintenance + 7×24 customer service

Reply with target category + rough monthly volume, and a tailored quote lands back within 24h.
""",
    },
    {
        "tag": "Mail N43 Kuching Sincere",
        "company": "Kuching Sincere Sdn Bhd",
        "to": "customerservice@kuchingsincere.com",
        "subject": "52-year Sarawak office-supply depth + direct China factory ergonomic chair supply",
        "body": """Hi,

Lvban Furniture — direct from China factory, BIFMA / ISO 9001 / SGS certified.

Three reasons Kuching Sincere's 52-year Sarawak 500+ corporate / government / school distribution depth + Paper One/GBC/Canon authorised stockist profile fits Lvban:

→ Cost-effective — factory-direct pricing that preserves margin on volume orders
→ Customization-ready — fabric/leather color, finish, logo embossing, OEM packaging, your own brand label
→ After-sale backed — 5-year warranty + lifetime maintenance + 7×24 customer service

Reply with target category + rough monthly volume, and a tailored quote lands back within 24h.
""",
    },
    {
        "tag": "Mail N44 Guess Office Solutions",
        "company": "Guess Office Solutions Sdn Bhd",
        "to": "sales@guessoffice.com.my",
        "subject": "Semenyih Selangor B2B + government/education/hotel supply depth + direct China ergonomic supply",
        "body": """Hi,

Lvban Furniture — direct from China factory, BIFMA / ISO 9001 / SGS certified.

Three reasons Guess Office Solutions' Semenyih Selangor 2008-established (SSM 809398-M) B2B + government / corporate / education / hotel / non-profit reach fits Lvban:

→ Cost-effective — factory-direct pricing that preserves margin on volume orders
→ Customization-ready — fabric/leather color, finish, logo embossing, OEM packaging, your own brand label
→ After-sale backed — 5-year warranty + lifetime maintenance + 7×24 customer service

Reply with target category + rough monthly volume, and a tailored quote lands back within 24h.
""",
    },
    {
        "tag": "Mail N45 POLO Furniture",
        "company": "POLO Furniture Sdn Bhd",
        "to": "polofurniture@gmail.com",
        "subject": "Kuantan Pahang 30-year office + Getha Mattress + gaming chair + direct ergonomic supply bundle",
        "body": """Hi,

Lvban Furniture — direct from China factory, BIFMA / ISO 9001 / SGS certified.

Three reasons POLO Furniture's Kuantan 1995-established (SSM 349774-H) 30-year Pahang office + Getha Mattress + gaming chair + sofa + work partition portfolio fits Lvban:

→ Cost-effective — factory-direct pricing that preserves margin on volume orders
→ Customization-ready — fabric/leather color, finish, logo embossing, OEM packaging, your own brand label
→ After-sale backed — 5-year warranty + lifetime maintenance + 7×24 customer service

Reply with target category + rough monthly volume, and a tailored quote lands back within 24h.
""",
    },
    {
        "tag": "Mail N46 KK Officepoint",
        "company": "KK Officepoint Sdn Bhd",
        "to": "support@kkofficepoint.com",
        "subject": "1992 JB-Ulu Tiram office furniture + Ironbox safety + direct ergonomic chair supply bundle",
        "body": """Hi,

Lvban Furniture — direct from China factory, BIFMA / ISO 9001 / SGS certified.

Three reasons KK Officepoint's 1992 JB Ulu Tiram 34-year office + Ironbox safety equipment subsidiary + school / education / safety equipment portfolio fits Lvban:

→ Cost-effective — factory-direct pricing that preserves margin on volume orders
→ Customization-ready — fabric/leather color, finish, logo embossing, OEM packaging, your own brand label
→ After-sale backed — 5-year warranty + lifetime maintenance + 7×24 customer service

Reply with target category + rough monthly volume, and a tailored quote lands back within 24h.
""",
    },
]


# ====== OAuth2 Refresh Token 认证 ======
def get_access_token():
    """用 refresh_token 换 access_token（无需浏览器 OAuth flow）"""
    client_id = os.environ.get("LVBAN_GMAIL_CLIENT_ID")
    client_secret = os.environ.get("LVBAN_GMAIL_CLIENT_SECRET")
    refresh_token = os.environ.get("LVBAN_GMAIL_REFRESH_TOKEN")

    missing = []
    if not client_id: missing.append("LVBAN_GMAIL_CLIENT_ID")
    if not client_secret: missing.append("LVBAN_GMAIL_CLIENT_SECRET")
    if not refresh_token: missing.append("LVBAN_GMAIL_REFRESH_TOKEN")
    if missing:
        print(f"❌ 缺少环境变量: {', '.join(missing)}")
        print(f"   设置方法：")
        print(f'   [Environment]::SetEnvironmentVariable("LVBAN_GMAIL_CLIENT_ID", "...", "User")')
        print(f'   [Environment]::SetEnvironmentVariable("LVBAN_GMAIL_CLIENT_SECRET", "...", "User")')
        print(f'   [Environment]::SetEnvironmentVariable("LVBAN_GMAIL_REFRESH_TOKEN", "...", "User")')
        sys.exit(1)

    data = urllib.parse.urlencode({
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }).encode()

    req = urllib.request.Request(TOKEN_URL, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
        return result["access_token"], result.get("expires_in", 3600)
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        print(f"❌ Token 端点错误 {e.code}: {body}")
        sys.exit(1)


def verify_sender(access_token):
    """验证发件人邮箱"""
    req = urllib.request.Request(GMAIL_PROFILE_URL, headers={"Authorization": f"Bearer {access_token}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        return data.get("emailAddress", "未知")
    except urllib.error.HTTPError as e:
        return f"(HTTP {e.code})"


# ====== Gmail API 发件 ======
def send_email(access_token, to_email, subject, body):
    msg = MIMEMultipart()
    msg['From'] = f"{SENDER_NAME} <{SENDER_EMAIL}>"
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    payload = json.dumps({"raw": raw}).encode()

    req = urllib.request.Request(
        GMAIL_SEND_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def build_full_body(email):
    signature = SIGNATURE_TEMPLATE.format(
        sender=SENDER_NAME, company=COMPANY, address=ADDRESS, website=WEBSITE
    )
    return email["body"] + CATALOG_FOOTER + signature + UNSUBSCRIBE_FOOTER


# ====== 送达日志 ======
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "send_log_v2.txt")

def log_event(event):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {event}\n"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line)
    print(line, end="")


# ====== 主流程 ======
def main():
    parser = argparse.ArgumentParser(description="Lvban Furniture — Gmail API via Refresh Token")
    parser.add_argument("--dry-run", action="store_true", help="仅校验 OAuth + 队列")
    parser.add_argument("--start-now", action="store_true", help="立即启动（默认等 MYT 09:00）")
    parser.add_argument("--start-at", metavar="ISO", help="指定启动时间（ISO 格式，如 2026-08-28T09:00:00+08:00）")
    parser.add_argument("--start-at-time", metavar="HH:MM", help="从现在等到指定时分（24h 制，如 09:00）")
    parser.add_argument("--auto-progress", action="store_true", help="按 Campaign Day 自动 daily-cap（Day 1-3=5, Day 4-7=8, Day 8-14=12, Day 15+=15）")
    parser.add_argument("--single", metavar="EMAIL", help="只发指定收件人")
    parser.add_argument("--interval", type=int, default=300, help="邮件间隔秒数（默认 300 = 5 分钟 + ±30% jitter）")
    parser.add_argument("--tag-filter", metavar="SUBSTR", help="只发 tag 含指定子串的邮件")
    parser.add_argument("--daily-cap", type=int, default=15, help="单日上限（默认 15）")
    args = parser.parse_args()

    print("=" * 70)
    print(f"🍂 Lvban Furniture — Gmail API via Refresh Token")
    print(f"   模式: {'DRY-RUN' if args.dry_run else 'LIVE SEND'}")
    print(f"   收件人: {len(EMAILS)} 封")
    print(f"   间隔: {args.interval}s ±30% jitter")
    print(f"   单日上限: {args.daily_cap} 封")
    print("=" * 70)

    # 拿 access_token
    try:
        access_token, expires_in = get_access_token()
        log_event(f"✓ Refresh Token → Access Token 成功 (有效期 {expires_in}s)")
    except SystemExit:
        sys.exit(1)

    # 验证发件人
    sender_email = verify_sender(access_token)
    if sender_email == SENDER_EMAIL:
        log_event(f"✓ 发件人验证: {sender_email}")
    else:
        log_event(f"⚠️ 发件人不匹配: 期望 {SENDER_EMAIL}, 实际 {sender_email}")

    # --auto-progress 模式：按 Campaign Day 自动算 daily-cap
    if args.auto_progress and not args.dry_run:
        # Day 1 = 2026-08-26（首次 LIVE 发送日）
        from datetime import date
        day1 = date(2026, 8, 26)
        today = date.today()
        delta_days = (today - day1).days
        day_n = max(1, delta_days + 1)
        if day_n <= 3:
            auto_cap = 5
        elif day_n <= 7:
            auto_cap = 8
        elif day_n <= 14:
            auto_cap = 12
        else:
            auto_cap = 15
        args.daily_cap = auto_cap
        log_event(f"📅 Campaign Day {day_n}（{today.isoformat()}）→ 自动 daily-cap = {auto_cap}")

    # 选择队列
    queue = list(EMAILS)
    if args.single:
        queue = [e for e in queue if e["to"] == args.single]
    if args.tag_filter:
        queue = [e for e in queue if args.tag_filter in e.get("tag", "")]
    if args.single and not queue:
        log_event(f"❌ --single 收件人 {args.single} 不在草稿列表")
        sys.exit(1)
    if args.tag_filter and not queue:
        log_event(f"❌ --tag-filter '{args.tag_filter}' 没匹配")
        sys.exit(1)

    # 时间调度
    target_dt = None
    if args.start_at:
        try:
            from datetime import timezone
            target_dt = datetime.fromisoformat(args.start_at)
            log_event(f"⏰ 自定义启动时间: {target_dt.isoformat()}")
        except ValueError:
            log_event(f"❌ --start-at 格式错误，应为 ISO 格式如 2026-08-28T09:00:00+08:00")
            sys.exit(1)
    elif args.start_at_time:
        try:
            hh, mm = args.start_at_time.split(":")
            target_dt = datetime.now().replace(hour=int(hh), minute=int(mm), second=0, microsecond=0)
            if datetime.now() >= target_dt:
                target_dt += timedelta(days=1)
            log_event(f"⏰ 目标时分: {args.start_at_time} → 自动等到 {target_dt.isoformat()}")
        except Exception as e:
            log_event(f"❌ --start-at-time 格式错误: {e}")
            sys.exit(1)
    elif not args.start_now and not args.dry_run:
        target_dt = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
        if datetime.now() >= target_dt:
            target_dt += timedelta(days=1)
        log_event(f"待 MYT 09:00 启动（{(target_dt - datetime.now()).total_seconds()/3600:.1f}h 后），用 --start-now 跳过")

    if target_dt and not args.dry_run:
        now = datetime.now()
        wait_sec = (target_dt - now).total_seconds()
        if wait_sec > 0:
            log_event(f"💤 等待 {wait_sec/3600:.1f}h 后启动 — 您可以关闭电脑，沙箱会独立运行")
            # 同步在脚本里 sleep（沙箱后台跑，无需交互）
            import time
            time.sleep(wait_sec)
            log_event(f"⏰ 启动时间到！开始执行...")

    # ============================================================
    # 防封号保护（核心新增）
    # ============================================================
    daily_limit = getattr(args, 'daily_cap', 20)        # 单日上限
    warmup_sec = 60                                     # 第一封预热
    jitter_pct = 0.30                                   # 间隔随机化 ±30%

    # 从两份文件读已发清单（续跑机制）
    # 1) 新版 sent_addresses.txt（每行一个邮箱，最可靠）
    # 2) 老版 send_log_v2.txt（兼容历史 data，回退使用正则）
    already_sent = set()
    sent_addr_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sent_addresses.txt")
    if os.path.exists(sent_addr_file):
        with open(sent_addr_file, "r", encoding="utf-8") as f:
            for line in f:
                addr = line.strip()
                if addr and "@" in addr:
                    already_sent.add(addr)
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if "已发送" in line and "DRY-RUN" not in line and "已发送 →" in line:
                    m = re.search(r"已发送 → (\S+@\S+)", line)
                    if m:
                        already_sent.add(m.group(1))

    if already_sent:
        log_event(f"⏭️  检测到已发记录，跳过 {len(already_sent)} 封（续跑模式）")

    # 检查单日 quota（基于日志最近 24h）
    recent_24h = 0
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if "已发送" in line and "DRY-RUN" not in line:
                    ts_match = re.search(r"\[([\d\-: ]+)\]", line)
                    if ts_match:
                        try:
                            ts = datetime.strptime(ts_match.group(1).strip(), "%Y-%m-%d %H:%M:%S")
                            if (datetime.now() - ts).total_seconds() < 86400:
                                recent_24h += 1
                        except Exception:
                            pass

    if recent_24h >= daily_limit and not args.dry_run:
        log_event(f"❌ 24h 内已发 {recent_24h} 封 ≥ 上限 {daily_limit}，停止保护账号")
        sys.exit(1)

    if not args.dry_run:
        log_event(f"🛡️  防封策略: 单日上限 {daily_limit} | 间隔 {args.interval}s ±{int(jitter_pct*100)}% | 预热 {warmup_sec}s")

    # 发送
    sent_this_run = 0
    for i, email_item in enumerate(queue, 1):
        to_addr = email_item["to"]

        # 跳过已发（续跑）
        if to_addr in already_sent and not args.dry_run:
            log_event(f"[{i}/{len(queue)}] ⏭️  跳过 {email_item['tag']}（已发过）")
            continue

        full_body = build_full_body(email_item)
        log_event(f"[{i}/{len(queue)}] 准备发送 {email_item['tag']} → {email_item['company']} ({to_addr})")
        log_event(f"   主题: {email_item['subject'][:60]}...")

        if args.dry_run:
            log_event("   ✓ DRY-RUN: 跳过实际发送")
        else:
            try:
                result = send_email(access_token, to_addr, email_item["subject"], full_body)
                # ✅ 修复：日志行加上邮箱，确保续跑去重正则能匹配
                log_event(f"   ✓ 已发送 → {to_addr} (Message-ID: {result.get('id', 'n/a')})")
                sent_this_run += 1
                # ✅ 维护发送邮箱的记忆（防御性，避免日志格式变更导致去重失效）
                sent_emails_log = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sent_addresses.txt")
                with open(sent_emails_log, "a", encoding="utf-8") as f:
                    f.write(to_addr + "\n")
            except urllib.error.HTTPError as e:
                body = e.read().decode() if e.fp else ""
                log_event(f"   ✗ HTTP {e.code}: {body[:200]}")
                # HTTP 429 = rate limit：长等一下 + 继续
                if e.code == 429:
                    log_event("   ⚠️ 触发 Gmail 429 rate limit，暂停 1 小时 + 立即停止当日发送")
                    sys.exit(1)
            except Exception as e:
                log_event(f"   ✗ 错误: {e}")

        if i < len(queue) and not args.dry_run:
            # 间隔 ± 30% jitter（避免时序指纹）
            base = args.interval
            jitter = int(base * jitter_pct)
            actual = base + random.randint(-jitter, jitter)
            log_event(f"   等待 {actual}s（基础 {base}s ±{int(jitter_pct*100)}%）...")
            time.sleep(actual)

    log_event("=" * 50)
    log_event(f"全部完成 — {sent_this_run}/{len(queue)} 封 LIVE（已计入 daily-cap {daily_limit}）")
    log_event("=" * 50)


if __name__ == "__main__":
    main()