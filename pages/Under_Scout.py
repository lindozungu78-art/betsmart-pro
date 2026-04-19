import streamlit as st
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime, timedelta

# --- HELPERS ---
def convert_to_sast(utc_time_str):
    utc_dt = datetime.strptime(utc_time_str, '%Y-%m-%d %H:%M:%S')
    sast_dt = utc_dt + timedelta(hours=2)
    return sast_dt.strftime('%d %b, %H:%M')

def get_understat_data(league):
    # CRITICAL: 2025 is the correct ID for April 2026 matches
    url = f"https://understat.com/league/{league}/2025" 
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.content, "lxml")
        scripts = soup.find_all('script')
        for s in scripts:
            if 'datesData' in s.text:
                json_str = s.text.split("JSON.parse('")[1].split("')")[0]
                decoded_data = json_str.encode('utf8').decode('unicode_escape')
                return json.loads(decoded_data)
    except Exception as e:
        st.error(f"Error connecting to {league}: {e}")
    return []

# --- APP UI ---
st.title("🛡️ BetSmart Pro: Weekly Under Engine")
st.caption("📍 Pietermaritzburg | 2.1 Odds Strategy")

# Sidebar
st.sidebar.header("Strategy Settings")
market_pref = st.sidebar.selectbox("Market", ["Under 4.5", "Under 5.5"])
stake = st.sidebar.number_input("Stake (ZAR)", value=10.0)

if st.button("🚀 Scan All Leagues"):
    leagues = ['EPL', 'Serie_A', 'Ligue_1', 'La_liga', 'Bundesliga']
    all_games = []
    
    with st.spinner("Scanning for Monday - Sunday fixtures..."):
        for league in leagues:
            data = get_understat_data(league)
            if data:
                for m in data:
                    m['league_name'] = league.replace('_', ' ')
                    all_games.append(m)

    if all_games:
        # 1. Filter for UPCOMING (Next 7 Days)
        upcoming = [m for m in all_games if not m['isResult']]
        
        if upcoming:
            upcoming.sort(key=lambda x: x['datetime'])
            st.success(f"Found {len(upcoming)} upcoming matches!")
            for match in upcoming[:15]:
                local_time = convert_to_sast(match['datetime'])
                with st.container():
                    c1, c2, c3 = st.columns([2, 1, 1])
                    with c1:
                        st.markdown(f"**{match['h']['title']} vs {match['a']['title']}**")
                        st.caption(f"🏆 {match['league_name']} | 🕒 {local_time} SAST")
                    with c2: st.write(f"✅ {market_pref}")
                    with c3:
                        if st.button("Add", key=f"add_{match['id']}"):
                            st.session_state.setdefault('my_slip', []).append(match)
                            st.toast("Added!")
                    st.divider()
        else:
            # 2. DEBUG: If no upcoming, show today's results to prove it's working
            st.warning("No matches starting in the next few hours. Showing today's completed results to verify connection:")
            results = [m for m in all_games if m['isResult']][-5:] # Last 5 finished
            for r in results:
                st.text(f"🏁 {r['h']['title']} {r['goals']['h']} - {r['goals']['a']} {r['a']['title']} (Finished)")
    else:
        st.error("Total connection failure. Check 'lxml' is in requirements.txt")

# --- SLIP ---
if 'my_slip' in st.session_state and st.session_state['my_slip']:
    st.sidebar.markdown("---")
    st.sidebar.subheader("Selected Slip")
    for i, item in enumerate(st.session_state['my_slip']):
        st.sidebar.write(f"{i+1}. {item['h']['title']} vs {item['a']['title']}")
    st.sidebar.write(f"**Target: R{stake * 2.1:.2f}**")
    if st.sidebar.button("Clear"):
        st.session_state['my_slip'] = []
        st.rerun()
