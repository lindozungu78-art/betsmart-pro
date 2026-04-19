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
    # Season 2025 covers the current 2025/2026 matches
    url = f"https://understat.com/league/{league}/2025" 
    res = requests.get(url)
    soup = BeautifulSoup(res.content, "lxml")
    scripts = soup.find_all('script')
    for s in scripts:
        if 'datesData' in s.text:
            data = s.text.split("JSON.parse('")[1].split("')")[0]
            return json.loads(data.encode('utf8').decode('unicode_escape'))
    return []

# --- APP UI ---
st.title("🛡️ BetSmart Pro: Weekly Under Engine")
st.info(f"Scanning for matches between now and { (datetime.now() + timedelta(days=7)).strftime('%d %b') }")

# Sidebar for strategy
st.sidebar.header("Strategy Settings")
market_pref = st.sidebar.radio("Target Market", ["Under 4.5", "Under 5.5"])
stake = st.sidebar.number_input("Stake (ZAR)", value=10.0)

if st.button("🚀 Scan All Leagues"):
    # Expanded list to ensure you find games even on quiet nights
    leagues = ['EPL', 'La_liga', 'Serie_A', 'Ligue_1', 'Bundesliga']
    all_upcoming = []
    
    with st.spinner("Analyzing schedules for upcoming week..."):
        for league in leagues:
            data = get_understat_data(league)
            # Filter for games that haven't started (isResult: False)
            upcoming = [m for m in data if not m['isResult']]
            for m in upcoming:
                m['league_name'] = league.replace('_', ' ')
                all_upcoming.append(m)

    if all_upcoming:
        # Sort by date so the soonest games are at the top
        all_upcoming.sort(key=lambda x: x['datetime'])
        
        st.success(f"Found {len(all_upcoming)} upcoming matches across 5 leagues!")
        
        for match in all_upcoming[:15]: # Show top 15 games
            local_time = convert_to_sast(match['datetime'])
            
            with st.container():
                c1, c2, c3 = st.columns([2, 1, 1])
                with c1:
                    st.markdown(f"**{match['h']['title']} vs {match['a']['title']}**")
                    st.caption(f"🏆 {match['league_name']} | 🕒 {local_time} SAST")
                with c2:
                    st.write(f"✅ {market_pref}")
                with c3:
                    if st.button("Add", key=f"btn_{match['id']}"):
                        st.session_state.setdefault('my_slip', []).append(match)
                        st.toast("Added to slip!")
                st.divider()
    else:
        st.error("No matches found. Check your internet connection or URL season year.")

# --- THE SLIP TRACKER ---
if 'my_slip' in st.session_state and st.session_state['my_slip']:
    st.sidebar.markdown("---")
    st.sidebar.subheader("Selected Slip (2.1 Strategy)")
    for i, item in enumerate(st.session_state['my_slip']):
        st.sidebar.write(f"{i+1}. {item['h']['title']} vs {item['a']['title']}")
    
    st.sidebar.write(f"**Target Return: R{stake * 2.1:.2f}**")
    if st.sidebar.button("Clear All"):
        st.session_state['my_slip'] = []
        st.rerun()
