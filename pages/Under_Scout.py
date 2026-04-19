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
    url = f"https://understat.com/league/{league}/2025" 
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.content, "lxml")
        scripts = soup.find_all('script')
        for s in scripts:
            if 'datesData' in s.text:
                json_str = s.text.split("JSON.parse('")[1].split("')")[0]
                return json.loads(json_str.encode('utf8').decode('unicode_escape'))
    except: return []

# --- APP UI ---
st.title("🛡️ BetSmart Pro: Multi-Source Engine")
st.caption("Scraping: Understat + StatsHub Verification")

# Sidebar
st.sidebar.header("Strategy Settings")
market_pref = st.sidebar.selectbox("Market", ["Under 4.5", "Under 5.5"])
stake = st.sidebar.number_input("Stake (ZAR)", value=10.0)

if st.button("🚀 Run Full Week Scan"):
    leagues = ['EPL', 'Serie_A', 'Ligue_1', 'La_liga']
    all_found = []
    
    with st.spinner("Syncing data from multiple hubs..."):
        for league in leagues:
            data = get_understat_data(league)
            if data:
                upcoming = [m for m in data if not m['isResult']]
                for m in upcoming:
                    m['league_display'] = league.replace('_', ' ')
                    all_found.append(m)

    if all_found:
        all_found.sort(key=lambda x: x['datetime'])
        st.success(f"Found {len(all_found)} matches. Verify trends below:")
        
        for match in all_found[:12]:
            local_time = convert_to_sast(match['datetime'])
            
            # Formatting team names for StatsHub search
            # Example: "Man City" becomes "manchester-city"
            sh_home = match['h']['title'].replace(" ", "-").lower()
            sh_away = match['a']['title'].replace(" ", "-").lower()
            statshub_url = f"https://www.statshub.com/en/match/{sh_home}-vs-{sh_away}"

            with st.container():
                c1, c2, c3 = st.columns([2, 1, 1])
                with c1:
                    st.markdown(f"**{match['h']['title']} vs {match['a']['title']}**")
                    st.caption(f"🕒 {local_time} SAST")
                with c2:
                    # Direct Link to StatsHub for deep verification
                    st.link_button("📊 StatsHub", statshub_url)
                with c3:
                    if st.button("Add", key=f"add_{match['id']}"):
                        st.session_state.setdefault('my_slip', []).append(match)
                        st.toast("Added!")
                st.divider()

# --- THE SLIP ---
if 'my_slip' in st.session_state and st.session_state['my_slip']:
    st.sidebar.markdown("---")
    st.sidebar.subheader("Strategy Slip")
    for item in st.session_state['my_slip']:
        st.sidebar.write(f"🔹 {item['h']['title']} vs {item['a']['title']}")
    st.sidebar.write(f"**Target: R{stake * 2.1:.2f}**")
                            
