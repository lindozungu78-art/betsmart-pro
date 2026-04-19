import streamlit as st
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime, timedelta

# --- HELPERS ---
def convert_to_sast(utc_time_str):
    """Converts Understat UTC string to SAST (UTC+2)"""
    utc_dt = datetime.strptime(utc_time_str, '%Y-%m-%d %H:%M:%S')
    sast_dt = utc_dt + timedelta(hours=2)
    return sast_dt.strftime('%d %b, %H:%M')

def get_understat_data(league):
    # CRITICAL: 2025 is the code for the 2025/2026 season
    url = f"https://understat.com/league/{league}/2025" 
    try:
        res = requests.get(url, timeout=10)
        soup = BeautifulSoup(res.content, "lxml")
        scripts = soup.find_all('script')
        for s in scripts:
            if 'datesData' in s.text:
                # Extracting the JSON string from the script tag
                json_data = s.text.split("JSON.parse('")[1].split("')")[0]
                decoded_data = json_data.encode('utf8').decode('unicode_escape')
                return json.loads(decoded_data)
    except Exception as e:
        st.error(f"Error fetching {league}: {e}")
    return []

# --- APP UI ---
st.title("🛡️ BetSmart Pro: Weekly Under Engine")
st.info(f"📍 Location: Pietermaritzburg | Scanning next 7 days")

# Sidebar
st.sidebar.header("Strategy Settings")
market_pref = st.sidebar.selectbox("Market Focus", ["Under 4.5", "Under 5.5"])
stake = st.sidebar.number_input("Stake (ZAR)", value=10.0)

if st.button("🚀 Scan All Leagues"):
    # Scrutinizing the leagues you requested + others for volume
    leagues = ['EPL', 'Serie_A', 'Ligue_1', 'La_liga', 'Bundesliga']
    all_upcoming = []
    
    with st.spinner("Deep scanning European leagues..."):
        for league in leagues:
            data = get_understat_data(league)
            # Only games that haven't happened yet (isResult: False)
            upcoming = [m for m in data if not m['isResult']]
            for m in upcoming:
                m['league_display'] = league.replace('_', ' ')
                all_upcoming.append(m)

    if all_upcoming:
        # Sort by date so Monday/Tuesday games appear first
        all_upcoming.sort(key=lambda x: x['datetime'])
        
        st.success(f"Found {len(all_upcoming)} upcoming matches!")
        
        for match in all_upcoming[:12]: # Show the next 12 games
            local_time = convert_to_sast(match['datetime'])
            
            with st.container():
                c1, c2, c3 = st.columns([2, 1, 1])
                with c1:
                    st.markdown(f"**{match['h']['title']} vs {match['a']['title']}**")
                    st.caption(f"🏆 {match['league_display']} | 🕒 {local_time} SAST")
                with c2:
                    st.write(f"✅ {market_pref}")
                with c3:
                    if st.button("Add", key=f"add_{match['id']}"):
                        st.session_state.setdefault('my_slip', []).append(match)
                        st.toast("Added to slip!")
                st.divider()
    else:
        st.warning("No matches found. This usually means the season is in a break or the year in the URL is wrong.")

# --- THE SLIP ---
if 'my_slip' in st.session_state and st.session_state['my_slip']:
    st.sidebar.markdown("---")
    st.sidebar.subheader("Selected Slip (2.1 Odds)")
    for i, item in enumerate(st.session_state['my_slip']):
        st.sidebar.write(f"{i+1}. {item['h']['title']} vs {item['a']['title']}")
    
    st.sidebar.write(f"**Potential Payout: R{stake * 2.1:.2f}**")
    if st.sidebar.button("Clear Slip"):
        st.session_state['my_slip'] = []
        st.rerun()
