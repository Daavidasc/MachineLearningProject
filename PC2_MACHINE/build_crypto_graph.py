
import requests, time, os, math
import pandas as pd
import networkx as nx
from pyvis.network import Network
import matplotlib.pyplot as plt
import numpy as np

OUT = "fast_output"
os.makedirs(OUT, exist_ok=True)

BASE = "https://api.coingecko.com/api/v3"
VS = "usd"
PER_PAGE = 250
MAX_PAGES = 4      
SLEEP_SIMPLE = 1.0 


KW_AI = ["ai", "artificial", "machine", "bittensor", "tensor", "cerebral", "deep"]
KW_GAMING = ["game", "gaming", "play", "metaverse", "axie", "sandbox", "immutable", "gala"]
KW_RWA = ["real", "rwa", "tokenized", "asset", "real world", "toke", "tokenize"]
KW_MEME = ["meme", "doge", "dogecoin", "shiba", "pepe", "meme"]

def fetch_markets():
    coins = []
    for page in range(1, MAX_PAGES+1):
        print(f"Fetching markets page {page}...")
        url = f"{BASE}/coins/markets"
        params = {"vs_currency": VS, "order":"market_cap_desc", "per_page": PER_PAGE, "page": page, "sparkline": "false"}
        r = requests.get(url, params=params)
        r.raise_for_status()
        data = r.json()
        coins.extend(data)
        time.sleep(SLEEP_SIMPLE)
    print("Fetched:", len(coins))
    return coins

def classify_name(name):
    ln = (name or "").lower()
    for k in KW_AI:
        if k in ln:
            return "AI"
    for k in KW_GAMING:
        if k in ln:
            return "Gaming"
    for k in KW_RWA:
        if k in ln:
            return "RWA"
    for k in KW_MEME:
        if k in ln:
            return "Meme"
    return "Other"

def normalize_series(s):
    s = np.array(s, dtype=float)
    s = s.copy()

    if np.nanmax(s) == np.nanmin(s):
        return np.ones_like(s)

    s = (s - np.nanmin(s)) / (np.nanmax(s) - np.nanmin(s) + 1e-12)
    return s

def build_graph(coins):
    G = nx.Graph()

    exchanges = ["Binance", "Coinbase", "Kraken", "KuCoin", "Gate", "Bitfinex", "OKX"]
    wallets = ["MetaMask", "TrustWallet", "Ledger", "Trezor"]
    communities = ["Twitter", "Discord", "Reddit", "Telegram"]


    for ex in exchanges:
        G.add_node(f"ex::{ex}", type="exchange", name=ex)
    for w in wallets:
        G.add_node(f"w::{w}", type="wallet", name=w)
    for c in communities:
        G.add_node(f"comm::{c}", type="community", name=c)


    market_caps = [c.get("market_cap") or 0 for c in coins]
    vol24 = [c.get("total_volume") or 0 for c in coins]
    mk_norm = normalize_series(market_caps)
    vol_norm = normalize_series(vol24)

    for i, c in enumerate(coins):
        cid = c.get("id")
        node = f"proj::{cid}"
        name = c.get("name")
        symbol = c.get("symbol")
        price = c.get("current_price")
        mc = c.get("market_cap") or 0
        vol = c.get("total_volume") or 0
        cat = classify_name(name + " " + (c.get("symbol") or ""))

        G.add_node(node, type="project", name=name, symbol=symbol, price=price, market_cap=mc, volume=vol, category=cat)

        p = min(0.95, 0.05 + mk_norm[i]) 
        for ex in exchanges:
            if np.random.rand() < p:  
                G.add_edge(node, f"ex::{ex}", weight=1.0 * (0.5 + mk_norm[i]))

        wcount = 1 + int(3 * mk_norm[i])
        wallet_choices = np.random.choice(wallets, size=wcount, replace=False)
        for w in wallet_choices:
            G.add_edge(node, f"w::{w}", weight=0.8 * (0.5 + vol_norm[i]))

        G.add_edge(node, "comm::Twitter", weight=0.9)
        if np.random.rand() < 0.5:
            G.add_edge(node, "comm::Discord", weight=0.6)
        if np.random.rand() < 0.3:
            G.add_edge(node, "comm::Reddit", weight=0.4)
        if np.random.rand() < 0.2:
            G.add_edge(node, "comm::Telegram", weight=0.3)

    return G

def export_graph(G):

    nodes = []
    for n, a in G.nodes(data=True):
        row = {"node_id": n}
        row.update(a)
        nodes.append(row)
    df_nodes = pd.DataFrame(nodes)
    df_nodes.to_csv(os.path.join(OUT, "nodes.csv"), index=False)

    edges = []
    for u, v, a in G.edges(data=True):
        edges.append({"source": u, "target": v, "weight": a.get("weight", 1)})
    df_edges = pd.DataFrame(edges)
    df_edges.to_csv(os.path.join(OUT, "edges.csv"), index=False)
    print("Exported nodes.csv and edges.csv")

def visualize(G):

    net = Network(height="900px", width="100%", notebook=False)
    net.barnes_hut()
    for n, a in G.nodes(data=True):
        label = a.get("name") or n
        color = "grey"
        if a.get("type") == "project": color = "blue"
        if a.get("type") == "exchange": color = "red"
        if a.get("type") == "wallet": color = "green"
        if a.get("type") == "community": color = "orange"
        net.add_node(n, label=(label if len(label)<18 else label[:16]+"..."), title=str(a), color=color)
    for u, v, a in G.edges(data=True):
        net.add_edge(u, v, value=a.get("weight",1))
    htmlp = os.path.join(OUT, "graph.html")
    net.write_html(htmlp, open_browser=False)
    print("Saved interactive graph:", htmlp)


    plt.figure(figsize=(14,10))
    pos = nx.spring_layout(G, k=0.12, iterations=40)
    types = nx.get_node_attributes(G, "type")
    color_map = []
    sizes = []
    for n in G.nodes():
        t = types.get(n,"")
        if t=="project":
            color_map.append("tab:blue"); sizes.append(40)
        elif t=="exchange":
            color_map.append("tab:red"); sizes.append(120)
        elif t=="wallet":
            color_map.append("tab:green"); sizes.append(100)
        elif t=="community":
            color_map.append("tab:orange"); sizes.append(80)
        else:
            color_map.append("grey"); sizes.append(50)
    nx.draw_networkx_nodes(G, pos, node_color=color_map, node_size=sizes, alpha=0.85)
    nx.draw_networkx_edges(G, pos, alpha=0.25)
    plt.title("Crypto graph (fast build) — projects / exchanges / wallets / communities")
    pngp = os.path.join(OUT, "graph.png")
    plt.savefig(pngp, dpi=200, bbox_inches="tight")
    plt.close()
    print("Saved static snapshot:", pngp)

def main():
    coins = fetch_markets()

    print("Total coins fetched:", len(coins))
    G = build_graph(coins)
    export_graph(G)
    visualize(G)
    print("Done. Output folder:", OUT)

if __name__ == "__main__":
    main()
