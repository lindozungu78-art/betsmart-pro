import streamlit as st
import requests
import pandas as pd
from scipy.stats import poisson
import datetime
import time
from streamlit_lottie import st_lottie

# --- 1. CONFIG & STYLING ---
st.set_page_config(page_title="BetSmart Pro Dual-Engine", layout="wide")

st.markdown("""
    <style>
    .stMetric { background-color: #1f2937; padding: 15px; border-radius: 10px; border: 1px solid #374151; }
    .main { background-color: #0e1117; }
    div[data-testid="stExpander"] { background-color: #111827; border: 1px solid #374151; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. API KEYS ---
AF_KEY = "76471fa1bb4374780c59eb417d7177f2" 
FD_KEY = "7105d84fa3474f46ba3a38497426a863"

# --- 3. HELPER FUNCTIONS ---
def load_lottieurl(url: str):
    r = requests.get(url)
    return r.json() if r.status_code == 200 else None

@st.cache_data(ttl=3600)
def get_dual_data():
    headers = {"X-Auth-Token": FD_KEY}
    # Standings
    table = requests.get("https://api.football-data.org/v4/competitions/PL/standings", headers=headers).json()['standings'][0]['table']
    # Weekly Fixtures
    today = datetime.date.today()
    next_week = today + datetime.timedelta(days=7)
    matches = requests.get(f"https://api.football-data.org/v4/competitions/PL/matches?dateFrom={today}&dateTo={next_week}", headers=headers).json().get('matches', [])
    return table, matches

import requests
import streamlit as st

def display_team_logo(logo_url, team_name):
    # This is a generic "No Image" placeholder
    fallback_url = "https://raw.githubusercontent.com/lucasbento/google-maps-logos/master/google-maps-logos.png" # Or any football icon URL
    
    try:
        # Check if the URL actually works (timeout after 1 second so it doesn't lag)
        response = requests.head(logo_url, timeout=1)
        if response.status_code == 200:
            st.image(logo_url, width=50)
        else:
            st.image(fallback_url, width=50)
    except:
        # If the API fails or link is dead, show the fallback
        st.image(fallback_url, width=50)

# --- 4. LOADING SCREEN (Fixed with Safety Check) ---
lottie_anim = load_lottieurl("https://lottie.host/80f76921-950c-4573-9029-79883500d418/Aas8Zk5XmS.json")

if 'data_loaded' not in st.session_state:
    with st.empty():
        # ONLY run st_lottie if lottie_anim is NOT None
        if lottie_anim:
            st_lottie(lottie_anim, height=250)
        else:
            st.info("⚽ Loading Match Data...") # Fallback if animation fails
            
        st.write("### 🤖 Dual-Engine Analysis in Progress...")
        table, matches = get_dual_data()
        st.session_state['table'] = table
        st.session_state['matches'] = matches
        st.session_state['data_loaded'] = True
        time.sleep(1)
        st.empty()
table = st.session_state['table']
matches = st.session_state['matches']

# --- 5. DASHBOARD ---
st.title("🏆 Dual-Engine Auto-Picker")
if st.button("🔄 Refresh Weekly Search"):
    st.cache_data.clear()
    st.rerun()

# Math Engine
all_preds = []
avg_goals = (sum(t['goalsFor'] for t in table) / sum(t['playedGames'] for t in table)) / 2

for m in matches:
    try:
        h, a = m['homeTeam']['name'], m['awayTeam']['name']
        h_s = next(t for t in table if t['team']['name'] == h)
        a_s = next(t for t in table if t['team']['name'] == a)
        h_exp = ((h_s['goalsFor']/h_s['playedGames'])/avg_goals) * ((a_s['goalsAgainst']/a_s['playedGames'])/avg_goals) * avg_goals
        win_p = sum(poisson.pmf(i, h_exp) * poisson.pmf(j, 1.2) for i in range(1, 6) for j in range(0, i))
        all_preds.append({"Match": f"{h} vs {a}", "Win": win_p*100, "Team": h, "Date": m['utcDate'][:10]})
    except: continue

# Top 4 Display
top_4 = sorted(all_preds, key=lambda x: x['Win'], reverse=True)[:4]
st.write("### 🔥 Top 4 'Value' Picks")
cols = st.columns(4)
for i, pick in enumerate(top_4):
    with cols[i]:
display_team_logo(pick['Logo_URL'], pick['Team'])
        st.metric(label=pick['Team'], value=f"{pick['Win']:.1f}%", delta="VALUE FOUND")
        st.caption(f"📅 {pick['Date']}")

# --- 6. ZAR CALCULATOR (The Missing Piece!) ---
st.markdown("---")
st.header("🇿🇦 System 3/4 Accumulator Builder (ZAR)")
col_in, col_res = st.columns([1, 1])

with col_in:
    st.write("Enter Odds from Betway:")
    o1 = st.number_input("Game 1 Odds", value=1.80)
    o2 = st.number_input("Game 2 Odds", value=2.00)
    o3 = st.number_input("Game 3 Odds", value=1.90)
    o4 = st.number_input("Game 4 Odds", value=2.10)
    total_stake = st.number_input("Total Stake (R)", value=100.0)

with col_res:
    if st.button("💰 Calculate Payout"):
        combinations = [(o1*o2*o3), (o1*o2*o4), (o1*o3*o4), (o2*o3*o4)]
        max_p = sum(combinations) * (total_stake / 4)
        min_p = min(combinations) * (total_stake / 4)
        
        st.success(f"**Max Payout: R{max_p:.2f}**")
        st.warning(f"**Safety Net Payout: R{min_p:.2f}**")
        st.info("The Safety Net payout is what you win if ONE team loses.")

# --- 7. FULL LIST ---
st.markdown("---")
with st.expander("📂 View All Weekly Fixtures"):
    for p in all_preds:
        st.write(f"{p['Date']} | **{p['Match']}** | Confidence: {p['Win']:.1f}%")
