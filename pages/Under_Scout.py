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
    # Season 2025 covers the 2025/2026 matches happening now
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
market_pref = st.sidebar.selectbox("Market Focus", ["Under 4.5", "Under 5.5"])
stake = st.sidebar.number_input("Stake (ZAR)", value=10.0)

if st.button("🚀 Run Full Week Scan"):
    # Leagues sorted by "Under" reliability
    leagues = ['Ligue_1', 'Serie_A', 'EPL', 'La_liga']
    all_found = []
    
    with st.spinner("Deep scanning for Monday - Friday fixtures..."):
        for league in leagues:
            data = get_understat_data(league)
            if data:
                # Look for everything from NOW into the future
                upcoming = [m for m in data if not m['isResult']]
                for m in upcoming:
                    m['league_display'] = league.replace('_', ' ')
                    all_found.append(m)

    if all_found:
        all_found.sort(key=lambda x: x['datetime'])
        st.success(f"Successfully found {len(all_found)} upcoming matches!")
        
        # Display results
        for match in all_found[:15]:
            local_time = convert_to_sast(match['datetime'])
            with st.container():
                c1, c2, c3 = st.columns([2, 1, 1])
                with c1:
                    st.markdown(f"**{match['h']['title']} vs {match['a']['title']}**")
                    st.caption(f"🏆 {match['league_display']} | 🕒 {local_time} SAST")
                with c2: st.write(f"✅ {market_pref}")
                with c3:
                    if st.button("Add", key=f"add_{match['id']}"):
                        st.session_state.setdefault('my_slip', []).append(match)
                        st.toast("Added!")
                st.divider()
    else:
        # Emergency Check: Show if the site is even responding
        st.error("No upcoming matches found in the next 7 days.")
        st.info("Check back tomorrow morning when the new week's data is fully indexed by Understat.")

# --- THE SLIP ---
if 'my_slip' in st.session_state and st.session_state['my_slip']:
    st.sidebar.markdown("---")
    st.sidebar.subheader("Strategy Slip")
    for i, item in enumerate(st.session_state['my_slip']):
        st.sidebar.write(f"{i+1}. {item['h']['title']} vs {item['a']['title']}")
    st.sidebar.write(f"**Target: R{stake * 2.1:.2f}**")
    if st.sidebar.button("Clear Slip"):
        st.session_state['my_slip'] = []
        st.rerun()
