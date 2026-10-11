"""Knowly Plus: persistent workspace and evidence-first study/comparison helpers."""
from __future__ import annotations
import json, os, re, sqlite3
from datetime import datetime
from html import escape
from pathlib import Path

DB_PATH = Path(os.environ.get("KNOWLY_DB_PATH", Path(__file__).with_name("knowly_workspace.sqlite3")))


def _connect():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("CREATE TABLE IF NOT EXISTS workspace (id INTEGER PRIMARY KEY CHECK(id=1), payload TEXT NOT NULL, updated_at TEXT NOT NULL)")
    return conn


def save_workspace(chunks, document_names, messages, bookmarks, summary=""):
    payload = {"chunks": chunks, "document_names": document_names, "messages": messages,
               "bookmarks": bookmarks, "summary": summary}
    with _connect() as conn:
        conn.execute("INSERT INTO workspace(id,payload,updated_at) VALUES(1,?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload, updated_at=excluded.updated_at",
                     (json.dumps(payload, ensure_ascii=False), datetime.now().isoformat(timespec="seconds")))


def load_workspace():
    try:
        with _connect() as conn:
            row = conn.execute("SELECT payload FROM workspace WHERE id=1").fetchone()
        return json.loads(row[0]) if row else {}
    except (sqlite3.Error, json.JSONDecodeError, OSError):
        return {}


def _sentences(text):
    return [re.sub(r"\s+", " ", s).strip(" \t\r\n•-") for s in re.split(r"(?<=[.!?])\s+|\n+", text or "") if len(s.strip()) >= 18]


def document_sentences(chunks):
    by_doc = {}
    for chunk in chunks or []:
        name = str(chunk.get("source", "Unknown document"))
        for sentence in _sentences(chunk.get("text", "")):
            key = re.sub(r"[^a-z0-9]+", " ", sentence.lower()).strip()
            if key:
                by_doc.setdefault(name, {})[key] = {"text": sentence, "page": chunk.get("page")}
    return {name: list(facts.values()) for name, facts in by_doc.items()}


def compare_documents(chunks, doc_a, doc_b):
    docs = document_sentences(chunks)
    a = docs.get(doc_a, [])
    b = docs.get(doc_b, [])
    def norm(s): return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()
    a_map, b_map = {norm(x['text']): x for x in a}, {norm(x['text']): x for x in b}
    shared = sorted(set(a_map) & set(b_map))
    only_a, only_b = sorted(set(a_map)-set(b_map)), sorted(set(b_map)-set(a_map))
    # Similar-looking but non-identical statements are surfaced as review candidates, never asserted contradictions.
    contradictions = []
    fields = [
        ("schedule", r"(?:training\s+)?schedule\s*[:\-]?\s*(.+)"),
        ("stipend", r"(?:monthly\s+)?(?:stipend|salary)\s*(?:is|of|:)?\s*(.+)"),
        ("duration", r"(?:internship\s+)?duration\s*(?:is|of|:)?\s*(.+)"),
        ("location", r"(?:training\s+)?location\s*(?:is|:)?\s*(.+)"),
        ("leave policy", r"leave\s+policy\s*[:\-]?\s*(.+)"),
    ]
    for label, pattern in fields:
        vals_a = [x['text'] for x in a if re.search(pattern, x['text'], re.I)]
        vals_b = [x['text'] for x in b if re.search(pattern, x['text'], re.I)]
        if vals_a and vals_b and {norm(x) for x in vals_a}.isdisjoint({norm(x) for x in vals_b}):
            contradictions.append({"field": label, "a": vals_a, "b": vals_b})
    return {"a": doc_a, "b": doc_b, "shared": [a_map[k]['text'] for k in shared],
            "only_a": [a_map[k]['text'] for k in only_a], "only_b": [b_map[k]['text'] for k in only_b],
            "review": contradictions,
            "note": "Exact sentence matches are shown as shared. Different wording is not automatically treated as a contradiction; review candidates require human confirmation."}


def extract_flashcards(chunks, limit=20):
    facts = []
    patterns = [
        (r"(?:training\s+)?schedule\s*:\s*(.+)", "What is the training schedule?"),
        (r"technical support email\s*:\s*([\w.+-]+@[\w.-]+\.[A-Za-z]{2,})", "What is the technical support email?"),
        (r"(?:training\s+)?location\s*:\s*(.+)", "Where is the training located?"),
        (r"(?:training coordinator|document contact|HR manager)\s*:\s*([A-Z][A-Za-z .'-]+)", "Who is the contact person?"),
        (r"(?:monthly\s+)?stipend\s+(?:is|of)\s*((?:Rs\.?|INR|₹)\s*[\d,]+(?:\s+per month)?)", "What is the monthly stipend?"),
        (r"(?:three|two|four|six|one|1|2|3|4|6)[- ]month internship", "What is the internship duration?"),
        (r"leave policy\s*:\s*(.+)", "What is the leave policy?"),
        (r"equipment policy\s*:\s*(.+)", "What is the equipment policy?"),
    ]
    seen=set()
    for chunk in chunks or []:
        text=chunk.get("text", "")
        for pattern, question in patterns:
            for m in re.finditer(pattern, text, re.I):
                answer=m.group(1).strip().rstrip(". ") if m.lastindex else m.group(0).strip().rstrip(". ")
                key=(question, answer.lower())
                if answer and key not in seen:
                    seen.add(key); facts.append({"question":question,"answer":answer,"source":chunk.get("source","Unknown"),"page":chunk.get("page")})
    # General factual sentences are useful flashcards, but never fabricate a question/answer pair.
    if len(facts)<limit:
        for chunk in chunks or []:
            for sentence in _sentences(chunk.get("text", "")):
                if re.search(r"\b(is|are|must|should|will|lasts|commencing|valid for)\b", sentence, re.I):
                    key=("What does the document state?", sentence.lower())
                    if key not in seen:
                        seen.add(key); facts.append({"question":"What does the document state?","answer":sentence,"source":chunk.get("source","Unknown"),"page":chunk.get("page")})
                if len(facts)>=limit: return facts
    return facts[:limit]


def extract_entities(chunks, max_nodes=45):
    """Extract conservative entities from document text for a lightweight graph."""
    entity_patterns = [
        ("Email", r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b"),
        ("Date", r"\b\d{1,2}(?:st|nd|rd|th)?\s+[A-Z][a-z]+\s+\d{4}\b|\b\d{4}-\d{2}-\d{2}\b"),
        ("Money", r"\b(?:Rs\.?|INR|₹)\s?[\d,]+(?:\s+per month)?\b"),
        ("Organization", r"\b[A-Z][A-Za-z&.-]+(?:\s+[A-Z][A-Za-z&.-]+){1,5}\s+(?:Pvt\.? Ltd\.?|Limited|Ltd\.?|Inc\.?|Corporation)\b"),
        ("Person", r"\b(?:[A-Z][a-z]+\s+){1,2}[A-Z][a-z]+\b"),
    ]
    nodes, edges, seen = [], [], set()
    for chunk in chunks or []:
        text=chunk.get("text", "")
        found=[]
        for kind, pattern in entity_patterns:
            for match in re.finditer(pattern, text):
                value=match.group(0).strip().rstrip(".,")
                key=(kind,value.lower())
                if key not in seen and len(nodes)<max_nodes:
                    seen.add(key); nodes.append({"id":value,"label":value,"kind":kind,"source":chunk.get("source","Unknown")})
                if value not in found: found.append(value)
        for i, left in enumerate(found):
            for right in found[i+1:]:
                pair=tuple(sorted((left,right)))
                if pair not in {(e["from"],e["to"]) for e in edges}:
                    edges.append({"from":pair[0],"to":pair[1]})
    return nodes, edges


def graph_html(chunks):
    """Create a standalone interactive graph with vis-network; no Python graph package required."""
    nodes, edges = extract_entities(chunks)
    node_json=json.dumps(nodes, ensure_ascii=False).replace("</", "<\\/")
    edge_json=json.dumps(edges, ensure_ascii=False).replace("</", "<\\/")
    html_doc=f'''<!doctype html><html><head><meta charset="utf-8"><script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script><style>body{{margin:0;background:#0b0d18;color:#f7f7ff;font:14px Arial}}#graph{{height:510px;border:1px solid #34334d;border-radius:16px;background:radial-gradient(circle at 50% 40%,#1c1b38,#0b0d18)}}#hint{{padding:10px;color:#a9acc8}}</style></head><body><div id="hint">Drag nodes · scroll to zoom · click a node to inspect its type and source</div><div id="graph"></div><script>const rawNodes={node_json};const rawEdges={edge_json};const palette={{Person:'#a88aff',Organization:'#47d8df',Date:'#ffbd69',Money:'#6fe0a5',Email:'#ff7caa'}};const ns=new vis.DataSet(rawNodes.map((n,i)=>({{id:n.id,label:n.label,title:n.kind+' · '+n.source,color:palette[n.kind]||'#a88aff',shape:'dot',size:18,font:{{color:'#f7f7ff',size:14}}}})));const es=new vis.DataSet(rawEdges.map((e,i)=>({{id:i,from:e.from,to:e.to,color:{{color:'#565879',highlight:'#b09aff'}},smooth:{{type:'continuous'}}}})));const container=document.getElementById('graph');const network=new vis.Network(container,{{nodes:ns,edges:es}},{{physics:{{stabilization:{{iterations:90}},barnesHut:{{gravitationalConstant:-4500,springLength:140}}}},interaction:{{hover:true,navigationButtons:true,keyboard:true}},edges:{{width:1.3}},nodes:{{borderWidth:1,shadow:true}}}});network.on('click',p=>{{if(p.nodes.length){{const n=rawNodes.find(x=>x.id===p.nodes[0]);document.getElementById('hint').textContent=n.label+' · '+n.kind+' · Source: '+n.source}}}});if(rawNodes.length===0)document.getElementById('hint').textContent='No clear names, dates, emails, amounts, or organizations found yet. Upload and process documents first.';</script></body></html>'''
    return html_doc, len(nodes), len(edges)
