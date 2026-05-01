"""Build static HTML blog from _posts/*.md.

Outputs:
  - /blog/<slug>.html for each post
  - /blog/index.html (chronological listing)
  - /feed.xml (RSS 2.0)

No external deps beyond markdown-it-py (pre-installed).
Run: python3 _build_blog.py
"""
from __future__ import annotations
import os, re, html, datetime, sys
from pathlib import Path
from markdown_it import MarkdownIt

ROOT = Path(__file__).parent.resolve()
POSTS_DIR = ROOT / "_posts"
BLOG_DIR = ROOT / "blog"
SITE_URL = "https://spalsh-spec.github.io"
AUTHOR = "Sparsh Sharma"
EMAIL = "sparshsharma219@gmail.com"

md = MarkdownIt("commonmark", {"html": True, "linkify": True, "typographer": True}).enable("table")


def parse_post(path: Path) -> dict:
    """Read a markdown post, extract date + slug + title + body."""
    name = path.stem  # e.g. 2026-05-01-corpus-drift-trap
    m = re.match(r"^(\d{4}-\d{2}-\d{2})-(.+)$", name)
    if not m:
        raise ValueError(f"post filename must start with YYYY-MM-DD-: {name}")
    date_str, slug = m.group(1), m.group(2)
    body = path.read_text(encoding="utf-8")
    # First # heading is the title
    tm = re.search(r"^# +(.+)$", body, re.MULTILINE)
    title = tm.group(1).strip() if tm else slug
    # First italic line after the title is the dek/lede
    dm = re.search(r"^\* *([^\n*]+) *\*$", body, re.MULTILINE)
    lede = dm.group(1).strip() if dm else ""
    # Strip the title and the lede from the body before HTML conversion
    body_without_title = re.sub(r"^# +.+\n", "", body, count=1, flags=re.MULTILINE)
    body_without_lede = re.sub(r"^\* *[^\n*]+ *\*\n", "", body_without_title, count=1, flags=re.MULTILINE)
    html_body = md.render(body_without_lede)
    return {
        "slug": slug,
        "date": date_str,
        "date_obj": datetime.date.fromisoformat(date_str),
        "title": title,
        "lede": lede,
        "html_body": html_body,
        "url": f"/blog/{slug}.html",
        "abs_url": f"{SITE_URL}/blog/{slug}.html",
    }


# ----- HTML templates (inline; matches index.html palette) -----
COMMON_HEAD = """<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<link rel="alternate" type="application/rss+xml" title="Sparsh Sharma — blog" href="/feed.xml">
<style>
  :root{--ink:#1a1a1a;--ink-soft:#3d3d3d;--ink-faint:#7a7a7a;--paper:#fbf8f3;--rule:#d9d2c3;--accent:#8b3a1f;--code-bg:#f1ece1}
  *{box-sizing:border-box}
  html{font-size:17px}
  body{margin:0;background:var(--paper);color:var(--ink);font-family:Charter,"Iowan Old Style",Georgia,Cambria,"Times New Roman",serif;line-height:1.65;-webkit-font-smoothing:antialiased}
  main{max-width:38rem;margin:0 auto;padding:3rem 1.5rem 5rem}
  .breadcrumb{font-size:.85rem;color:var(--ink-faint);margin-bottom:2rem}
  .breadcrumb a{color:var(--ink-faint);text-decoration:underline;text-decoration-color:var(--rule);text-underline-offset:2px}
  .breadcrumb a:hover{color:var(--accent);text-decoration-color:var(--accent)}
  h1{font-size:1.75rem;font-weight:600;margin:0 0 .35rem;letter-spacing:-.005em;line-height:1.25}
  .post-meta{color:var(--ink-faint);font-size:.88rem;margin:0 0 .25rem}
  .lede{font-style:italic;color:var(--ink-soft);margin:.5rem 0 2rem;font-size:1.06rem;line-height:1.55}
  article h2{font-size:1.25rem;margin-top:2.4rem;margin-bottom:.7rem;font-weight:600;letter-spacing:-.003em}
  article h3{font-size:1.05rem;margin-top:1.8rem;margin-bottom:.5rem;font-weight:600}
  article p{margin:0 0 1.1rem}
  article a{color:var(--accent);text-decoration:underline;text-decoration-thickness:1px;text-underline-offset:2.5px}
  article a:hover{text-decoration-thickness:2px}
  article ul,article ol{padding-left:1.4rem;margin:0 0 1.1rem}
  article li{margin-bottom:.35rem}
  article hr{border:0;border-top:1px solid var(--rule);margin:2rem 0}
  article blockquote{border-left:3px solid var(--rule);margin:1rem 0;padding:.2rem 0 .2rem 1rem;color:var(--ink-soft);font-style:italic}
  article table{border-collapse:collapse;margin:1rem 0;font-size:.94rem;width:100%}
  article th,article td{border:1px solid var(--rule);padding:.4rem .6rem;text-align:left}
  article th{background:#f3eee2;font-weight:600}
  code{font-family:"SF Mono",Menlo,Consolas,monospace;font-size:.86rem;background:var(--code-bg);padding:.08rem .32rem;border-radius:2px;color:var(--ink)}
  pre{font-family:"SF Mono",Menlo,Consolas,monospace;font-size:.84rem;background:var(--code-bg);padding:.85rem 1rem;border-radius:3px;overflow-x:auto;margin:.6rem 0 1.4rem;line-height:1.5}
  pre code{background:none;padding:0}
  .post-list{list-style:none;padding:0;margin:0}
  .post-list li{margin-bottom:1.5rem;padding-bottom:1.4rem;border-bottom:1px solid var(--rule)}
  .post-list li:last-child{border-bottom:none}
  .post-list .title{font-size:1.1rem;font-weight:600;display:block;margin-bottom:.2rem}
  .post-list .title a{color:var(--ink);text-decoration:none}
  .post-list .title a:hover{color:var(--accent);text-decoration:underline}
  .post-list .date{color:var(--ink-faint);font-size:.85rem;margin-bottom:.4rem}
  .post-list .lede-mini{color:var(--ink-soft);font-size:.96rem;font-style:italic;line-height:1.5}
  footer{margin-top:4rem;padding-top:1.5rem;border-top:1px solid var(--rule);font-size:.82rem;color:var(--ink-faint);text-align:center}
  footer a{color:var(--ink-faint)}
  @media (max-width:480px){html{font-size:16px}main{padding:2rem 1.2rem 3rem}}
</style>"""

POST_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
{common_head}
<title>{title} — Sparsh Sharma</title>
<meta name="description" content="{description}">
<meta name="author" content="{author}">
<link rel="canonical" href="{abs_url}">
<meta property="og:type" content="article">
<meta property="og:url" content="{abs_url}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{description}">
<meta property="og:image" content="{site_url}/og-image.png">
<meta property="article:published_time" content="{date}">
<meta property="article:author" content="{author}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{description}">
<meta name="twitter:image" content="{site_url}/og-image.png">
</head>
<body>
<main>
<nav class="breadcrumb"><a href="/">home</a> &nbsp;/&nbsp; <a href="/blog/">blog</a> &nbsp;/&nbsp; <span>{slug}</span></nav>
<header>
  <h1>{title}</h1>
  <p class="post-meta">{date_pretty} &nbsp;&middot;&nbsp; {author}</p>
  {lede_html}
</header>
<article>
{html_body}
</article>
<footer>
  <a href="/blog/">&larr; all posts</a> &nbsp;&middot;&nbsp; <a href="/">home</a> &nbsp;&middot;&nbsp; <a href="https://github.com/spalsh-spec/falsify-eval">repo</a>
</footer>
</main>
</body>
</html>
"""

INDEX_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
{common_head}
<title>Blog — Sparsh Sharma</title>
<meta name="description" content="Notes on falsification methodology, retrieval evaluation, and computational philology.">
<link rel="canonical" href="{site_url}/blog/">
<meta property="og:title" content="Blog — Sparsh Sharma">
<meta property="og:description" content="Notes on falsification methodology, retrieval evaluation, and computational philology.">
<meta property="og:image" content="{site_url}/og-image.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="{site_url}/og-image.png">
</head>
<body>
<main>
<nav class="breadcrumb"><a href="/">home</a> &nbsp;/&nbsp; <span>blog</span></nav>
<header>
  <h1>Blog</h1>
  <p class="post-meta">Notes on falsification methodology, retrieval evaluation, and computational philology. <a href="/feed.xml">RSS</a>.</p>
</header>
<ul class="post-list">
{post_items}
</ul>
<footer>
  <a href="/">&larr; home</a> &nbsp;&middot;&nbsp; <a href="https://github.com/spalsh-spec/falsify-eval">repo</a>
</footer>
</main>
</body>
</html>
"""

POST_LIST_ITEM = """<li>
  <span class="title"><a href="{url}">{title}</a></span>
  <span class="date">{date_pretty}</span>
  <p class="lede-mini">{lede}</p>
</li>"""


def render_lede_html(lede: str) -> str:
    return f'<p class="lede">{html.escape(lede)}</p>' if lede else ""


def make_description(post: dict) -> str:
    if post["lede"]:
        return post["lede"][:280]
    # Fallback: first paragraph of body, stripped of HTML
    text = re.sub(r"<[^>]+>", "", post["html_body"])
    text = re.sub(r"\s+", " ", text).strip()
    return text[:280]


def write_post(post: dict):
    out = BLOG_DIR / f"{post['slug']}.html"
    html_doc = POST_TEMPLATE.format(
        common_head=COMMON_HEAD,
        title=html.escape(post["title"]),
        description=html.escape(make_description(post)),
        author=html.escape(AUTHOR),
        abs_url=post["abs_url"],
        site_url=SITE_URL,
        date=post["date"],
        date_pretty=post["date_obj"].strftime("%-d %B %Y"),
        slug=post["slug"],
        lede_html=render_lede_html(post["lede"]),
        html_body=post["html_body"],
    )
    out.write_text(html_doc, encoding="utf-8")
    print(f"  wrote {out.relative_to(ROOT)}")


def write_index(posts: list[dict]):
    items = "\n".join(
        POST_LIST_ITEM.format(
            url=p["url"],
            title=html.escape(p["title"]),
            date_pretty=p["date_obj"].strftime("%-d %B %Y"),
            lede=html.escape(p["lede"]),
        )
        for p in posts
    )
    out = BLOG_DIR / "index.html"
    out.write_text(
        INDEX_TEMPLATE.format(common_head=COMMON_HEAD, site_url=SITE_URL, post_items=items),
        encoding="utf-8",
    )
    print(f"  wrote {out.relative_to(ROOT)}")


def write_rss(posts: list[dict]):
    """RSS 2.0 with full post content."""
    now_rfc822 = datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000")
    items = []
    for p in posts:
        pub = datetime.datetime.combine(p["date_obj"], datetime.time(12, 0, 0))
        pub_rfc822 = pub.strftime("%a, %d %b %Y %H:%M:%S +0000")
        items.append(f"""    <item>
      <title>{html.escape(p["title"])}</title>
      <link>{p["abs_url"]}</link>
      <guid isPermaLink="true">{p["abs_url"]}</guid>
      <pubDate>{pub_rfc822}</pubDate>
      <author>{EMAIL} ({AUTHOR})</author>
      <description>{html.escape(make_description(p))}</description>
      <content:encoded><![CDATA[{p["html_body"]}]]></content:encoded>
    </item>""")
    body = "\n".join(items)
    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>Sparsh Sharma — blog</title>
    <link>{SITE_URL}/blog/</link>
    <atom:link href="{SITE_URL}/feed.xml" rel="self" type="application/rss+xml"/>
    <description>Notes on falsification methodology, retrieval evaluation, and computational philology.</description>
    <language>en-au</language>
    <lastBuildDate>{now_rfc822}</lastBuildDate>
{body}
  </channel>
</rss>
"""
    (ROOT / "feed.xml").write_text(rss, encoding="utf-8")
    print(f"  wrote feed.xml ({len(items)} items)")


def update_sitemap(posts: list[dict]):
    """Regenerate sitemap.xml to include /blog/ and each post."""
    urls = [
        (f"{SITE_URL}/", "2026-05-01", "monthly", "1.0"),
        (f"{SITE_URL}/blog/", "2026-05-01", "weekly", "0.9"),
    ]
    for p in posts:
        urls.append((p["abs_url"], p["date"], "yearly", "0.7"))
    items = "\n".join(
        f"  <url>\n    <loc>{loc}</loc>\n    <lastmod>{lm}</lastmod>\n    <changefreq>{cf}</changefreq>\n    <priority>{pr}</priority>\n  </url>"
        for loc, lm, cf, pr in urls
    )
    body = f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{items}\n</urlset>\n'
    (ROOT / "sitemap.xml").write_text(body, encoding="utf-8")
    print(f"  wrote sitemap.xml ({len(urls)} urls)")


def main():
    BLOG_DIR.mkdir(exist_ok=True)
    posts = sorted(
        (parse_post(p) for p in POSTS_DIR.glob("*.md")),
        key=lambda x: x["date_obj"],
        reverse=True,
    )
    print(f"found {len(posts)} posts")
    for p in posts:
        write_post(p)
    write_index(posts)
    write_rss(posts)
    update_sitemap(posts)
    print("done.")


if __name__ == "__main__":
    main()
