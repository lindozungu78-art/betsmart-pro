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
    # CRITICAL: Understat uses the START year of the season (2025 = 2025/26 season)
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
    except:
        return []
    return []

# --- APP UI ---
st.title("🛡️ BetSmart Pro: 7-Day Scout")
st.caption("📍 Pietermaritzburg | Under 4.5/5.5 Strategy")

# Sidebar
st.sidebar.header("Strategy Settings")
market_pref = st.sidebar.selectbox("Market", ["Under 4.5", "Under 5.5"])
stake = st.sidebar.number_input("Stake (ZAR)", value=10.0)

if st.button("🚀 Run Full Week Scan"):
    # Leagues you requested + extras for volume
    leagues = ['EPL', 'Serie_A', 'Ligue_1', 'La_liga']
    all_upcoming = []
    
    with st.spinner("Scanning European fixtures..."):
        for league in leagues:
            data = get_understat_data(league)
            # Find games that haven't started yet
            upcoming = [m for m in data if not m['isResult']]
            for m in upcoming:
                m['league_name'] = league.replace('_', ' ')
                all_upcoming.append(m)

    if all_upcoming:
        # Sort by date so Monday/Tuesday games are at the top
        all_upcoming.sort(key=lambda x: x['datetime'])
        
        st.success(f"Found {len(all_upcoming)} upcoming matches!")
        
        # Show top picks for the week
        for match in all_upcoming[:15]:
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
                        st.toast("Added to Strategy Slip")
                st.divider()
    else:
        st.warning("No matches found. This usually happens during International breaks or between seasons.")

# --- THE SLIP ---
if 'my_slip' in st.session_state and st.session_state['my_slip']:
    st.sidebar.markdown("---")
    st.sidebar.subheader("Strategy Slip (2.1 Odds)")
    for i, item in enumerate(st.session_state['my_slip']):
        st.sidebar.write(f"{i+1}. {item['h']['title']} vs {item['a']['title']}")
    
    st.sidebar.write(f"**Target Return: R{stake * 2.1:.2f}**")
    if st.sidebar.button("Clear Slip"):
        st.session_state['my_slip'] = []
        st.rerun()
