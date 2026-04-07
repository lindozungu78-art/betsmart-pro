import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import math

# --- 1. CONFIG & API SETTINGS ---
API_KEY = "8e1ac8e3fb43757f30f2aec94dbebb81" 
st.set_page_config(page_title="BetSmart Pro | Master Engine", layout="wide")

# --- 2. LOGO MAPPING SYSTEM ---
def get_team_logo_url(team_name):
    team_ids = {
        "Arsenal": 57, "Aston Villa": 58, "Chelsea": 61, "Liverpool": 64, 
        "Manchester City": 65, "Manchester United": 66, "Newcastle United": 67,
        "Tottenham Hotspur": 73, "West Ham United": 563, "Brentford": 402,
        "Brighton & Hove Albion": 397, "Crystal Palace": 354, "Everton": 62,
        "Fulham": 63, "Leicester City": 338, "Wolverhampton Wanderers": 76,
        "Nottingham Forest": 351, "Bournemouth": 1044
    }
    for key, tid in team_ids.items():
        if key in team_name: return f"https://crests.football-data.org/{tid}.png"
    return "https://cdn-icons-png.flaticon.com/512/5323/5323884.png"

# --- 3. POISSON DRAW ENGINE ---
def calculate_draw_prob(h_prob, a_prob):
    # Higher draw probability when teams are closely matched
    balance_factor = 1 - abs(h_prob - a_prob) / 100
    return round(26.0 * balance_factor, 1)

# --- 4. DATA FETCHING (ODDS & SCORES) ---
def fetch_data(endpoint):
    url = f"https://api.the-odds-api.com/v4/sports/soccer_epl/{endpoint}/?apiKey={API_KEY}&regions=uk&markets=h2h&oddsFormat=decimal"
    try:
        response = requests.get(url, timeout=5)
        return response.json() if response.status_code == 200 else None
    except: return None

# --- 5. UI: HEADER & SYNC ---
st.title("🏆 Dual-Engine Auto-Picker")
st.subheader("📊 BetSmart 4x4 Strategic Matrix")

if st.button("🔄 Sync Master Data (Odds, Scores & Times)"):
    st.cache_data.clear()

# --- 6. 4x4 MATRIX LOGIC ---
odds_data = fetch_data("odds")
if odds_data:
    all_matches = []
    for match in odds_data:
        home = match['home_team']
        away = match['away_team']
        outcomes = match['bookmakers'][0]['markets'][0]['outcomes']
        h_odds = next(o['price'] for o in outcomes if o['name'] == home)
        a_odds = next(o['price'] for o in outcomes if o['name'] == away)
        d_odds = next(o['price'] for o in outcomes if o['name'] == "Draw")
        
        h_prob = (1/h_odds)*100
        a_prob = (1/a_odds)*100
        d_prob = calculate_draw_prob(h_prob, a_prob)
        
        all_matches.append({
            "Home": home, "Away": away, "H_Prob": round(h_prob, 1), 
            "D_Prob": d_prob, "H_Odds": h_odds, "D_Odds": d_odds
        })
    
    all_matches.sort(key=lambda x: x['H_Prob'], reverse=True)
    while len(all_matches) < 16: all_matches.append({"Home": "Pending", "Away": "...", "H_Prob": 0, "D_Prob": 0, "H_Odds": 1.0, "D_Odds": 1.0})

    matrix = {
        "Option A (Bankers)": all_matches[0:4],
        "Option B (Home Edge)": all_matches[4:8],
        "Option C (Draw/Value)": sorted(all_matches, key=lambda x: x['D_Prob'], reverse=True)[0:4],
        "Option D (Underdogs)": all_matches[12:16]
    }

    tabs = st.tabs(list(matrix.keys()))
    for i, (group, matches) in enumerate(matrix.items()):
        with tabs[i]:
            cols = st.columns(4)
            for j, m in enumerate(matches):
                with cols[j]:
                    st.image(get_team_logo_url(m['Home']), width=60)
                    st.metric(m['Home'], f"{m['H_Prob']}%", f"Draw: {m['D_Prob']}%")
                    st.caption(f"Odds: {m['H_Odds']}")
            
            if st.button(f"Load {group} into Calculator", key=f"load_{i}"):
                st.session_state.selected_odds = [x['H_Odds'] for x in matches]
                st.session_state.selected_group = group

# --- 7. FOLDABLE LIVE SCORES & SAST TIMES ---
st.divider()
with st.expander("🏟️ View Live Scores & Match Times (SAST)", expanded=False):
    scores_data = fetch_data("scores")
    if scores_data:
        for match in scores_data:
            utc_time = datetime.fromisoformat(match['commence_time'].replace('Z', ''))
            sast_time = utc_time + timedelta(hours=2) # Manual SAST Fix
            
            c1, c2, c3 = st.columns([2, 1, 2])
            score = f"{match['scores'][0]['score']} - {match['scores'][1]['score']}" if match.get('scores') else "vs"
            status = "🏁 FT" if match['completed'] else ("🔴 LIVE" if match.get('scores') else "📅 Upcoming")
            
            c1.write(f"**{match['home_team']}**")
            c2.info(f"**{score}**")
            c3.write(f"**{match['away_team']}**")
            st.caption(f"🕒 {sast_time.strftime('%d %b | %H:%M')} SAST | {status}")
            st.write("---")
    else: st.write("No live data available.")

# --- 8. ZAR SYSTEM 3/4 CALCULATOR (Wager vs Profit) ---
st.divider()
st.header("💰 ZAR System 3/4 Calculator")
def_odds = st.session_state.get('selected_odds', [1.57, 1.59, 2.09, 3.30])
st.info(f"Analyzing: **{st.session_state.get('selected_group', 'Manual Entry')}**")

col1, col2 = st.columns(2)
with col1:
    total_wager = st.number_input("Total Wager (ZAR)", value=100.0, step=10.0)
    o1, o2 = st.number_input("Odds 1", value=float(def_odds[0])), st.number_input("Odds 2", value=float(def_odds[1]))
with col2:
    o3, o4 = st.number_input("Odds 3", value=float(def_odds[2])), st.number_input("Odds 4", value=float(def_odds[3]))

spb = total_wager / 4
combos = [o1*o2*o3*spb, o1*o2*o4*spb, o1*o3*o4*spb, o2*o3*o4*spb]

r1, r2, r3 = st.columns(3)
r1.metric("Total Wager", f"R{total_wager:.2f}")
with r2:
    st.success(f"### Max Win (4/4)\n**Payout:** R{sum(combos):.2f}\n\n**Profit:** R{sum(combos)-total_wager:.2f}")
with r3:
    st.warning(f"### Safety Net (3/4)\n**Payout:** R{min(combos):.2f}\n\n**Profit/Loss:** R{min(combos)-total_wager:.2f}")
        
