import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# --- 1. CONFIG & API SETTINGS ---
API_KEY = "8e1ac8e3fb43757f30f2aec94dbebb81" 
st.set_page_config(page_title="BetSmart Pro | Live", layout="wide")

# --- 2. LOGO MAPPING ---
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

# --- 3. LIVE SCORES & RESULTS ENGINE ---
def fetch_live_scores():
    # Fetching scores and start times
    url = f"https://api.the-odds-api.com/v4/sports/soccer_epl/scores/?apiKey={API_KEY}&daysFrom=1"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.json()
    except:
        return None

# --- 4. 4x4 MATRIX ENGINE ---
def fetch_matrix_data():
    url = f"https://api.the-odds-api.com/v4/sports/soccer_epl/odds/?apiKey={API_KEY}&regions=uk&markets=h2h&oddsFormat=decimal"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            all_teams = []
            for match in data:
                home_team = match['home_team']
                h_odds = max([o['price'] for b in match['bookmakers'] for m in b['markets'] for o in m['outcomes'] if o['name'] == home_team])
                all_teams.append({"Team": home_team, "Prob": round((1/h_odds)*100, 1), "Odds": h_odds})
            all_teams.sort(key=lambda x: x['Prob'], reverse=True)
            while len(all_teams) < 16: all_teams.append({"Team": "Pending...", "Prob": 0.0, "Odds": 1.0})
            return {"Option A (Bankers)": all_teams[0:4], "Option B (Home Edge)": all_teams[4:8], 
                    "Option C (Value Mix)": all_teams[8:12], "Option D (Underdogs)": all_teams[12:16]}
    except: return None

# --- 5. UI LAYOUT ---
st.title("🏆 Dual-Engine Auto-Picker")
st.subheader("📊 BetSmart 4x4 Strategic Matrix")

if st.button("🔄 Sync Live Odds & Scores"):
    st.cache_data.clear()

# Matrix Section
matrix_data = fetch_matrix_data()
if matrix_data:
    tabs = st.tabs(list(matrix_data.keys()))
    for i, (group_name, teams) in enumerate(matrix_data.items()):
        with tabs[i]:
            cols = st.columns(4)
            for j, team in enumerate(teams):
                with cols[j]:
                    st.image(get_team_logo_url(team['Team']), width=60)
                    st.metric(team['Team'], f"{team['Prob']}%", f"Odds: {team['Odds']}")
            if st.button(f"Analyze {group_name}", key=f"btn_{i}"):
                st.session_state.selected_odds = [t['Odds'] for t in teams]
                st.session_state.selected_group = group_name

st.divider()

# --- 6. FOLDABLE LIVE SCORES & DATES ---
with st.expander("🏟️ View Live Scores, Dates & Results", expanded=False):
    scores_data = fetch_live_scores()
    if scores_data:
        for match in scores_data:
            # Parse the game date
            commence_time = datetime.fromisoformat(match['commence_time'].replace('Z', ''))
            date_str = commence_time.strftime("%A, %d %B") # Example: Saturday, 12 April
            
            col1, col2, col3 = st.columns([2, 1, 2])
            home = match['home_team']
            away = match['away_team']
            
            if match['completed']:
                status = "🏁 Finished"
                score_text = f"{match['scores'][0]['score']} - {match['scores'][1]['score']}" if match['scores'] else "FT"
            else:
                status = "🔴 LIVE" if match.get('scores') else "📅 Upcoming"
                score_text = f"{match['scores'][0]['score']} - {match['scores'][1]['score']}" if match.get('scores') else "vs"
            
            col1.write(f"**{home}**")
            col2.info(f"**{score_text}**")
            col3.write(f"**{away}**")
            st.caption(f"📅 {date_str} | Status: {status}")
            st.write("---")
    else:
        st.write("No score data currently available.")

st.divider()

# --- 7. ZAR SYSTEM 3/4 CALCULATOR ---
st.header("💰 ZAR System 3/4 Calculator")
default_odds = st.session_state.get('selected_odds', [1.57, 1.59, 2.09, 3.30])
st.info(f"Analyzing: **{st.session_state.get('selected_group', 'Manual Entry')}**")

c1, c2 = st.columns(2)
with c1:
    total_stake = st.number_input("Total Budget (ZAR)", value=100.0)
    o1 = st.number_input("Team 1 Odds", value=float(default_odds[0]))
    o2 = st.number_input("Team 2 Odds", value=float(default_odds[1]))
with c2:
    o3 = st.number_input("Team 3 Odds", value=float(default_odds[2]))
    o4 = st.number_input("Team 4 Odds", value=float(default_odds[3]))

# Original 3/4 Math
spb = total_stake / 4
combos = [o1*o2*o3*spb, o1*o2*o4*spb, o1*o3*o4*spb, o2*o3*o4*spb]

res1, res2 = st.columns(2)
res1.success(f"### Max Payout\nR{sum(combos):.2f}")
res2.warning(f"### Safety Net\nR{min(combos):.2f}")
