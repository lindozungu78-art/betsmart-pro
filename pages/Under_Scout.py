import streamlit as st
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime, timedelta

# --- HELPERS ---
def convert_to_sast(utc_time_str):
    utc_dt = datetime.strptime(utc_time_str, '%Y-%m-%d %H:%M:%S')
    sast_dt = utc_dt + timedelta(hours=2)
    return sast_dt.strftime('%H:%M')

def get_understat_data(league):
    url = f"https://understat.com/league/{league}/2025" 
    res = requests.get(url)
    soup = BeautifulSoup(res.content, "lxml")
    scripts = soup.find_all('script')
    for s in scripts:
        if 'datesData' in s.text:
            data = s.text.split("JSON.parse('")[1].split("')")[0]
            return json.loads(data.encode('utf8').decode('unicode_escape'))
    return []

# --- APP PAGE ---
st.title("🛡️ BetSmart Pro: Under 4.5/5.5 Engine")

# Sidebar settings for your 2.1 odds strategy
st.sidebar.header("Strategy Settings")
stake = st.sidebar.number_input("Starting Stake (ZAR)", value=10.0)
target_market = st.sidebar.selectbox("Preferred Market", ["Under 4.5", "Under 5.5"])

if st.button("🚀 Run Deep Scan"):
    leagues = ['EPL', 'La_liga', 'Serie_A', 'Ligue_1']
    all_picks = []
    
    with st.spinner("Scanning major leagues for low-scoring trends..."):
        for league in leagues:
            data = get_understat_data(league)
            # Filter only upcoming games
            upcoming = [m for m in data if not m['isResult']]
            for m in upcoming[:5]:
                # Add league info for the card
                m['league'] = league
                all_picks.append(m)

    if all_picks:
        st.success(f"Scan Complete. Found {len(all_picks)} matches for {target_market}.")
        
        # Display as actionable cards
        for match in all_picks:
            sast_time = convert_to_sast(match['datetime'])
            
            with st.container():
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    st.markdown(f"**{match['h']['title']} vs {match['a']['title']}**")
                    st.caption(f"🏆 {match['league']} | 🕒 {sast_time} SAST")
                with col2:
                    st.write(f"✅ {target_market}")
                with col3:
                    if st.button("Add Game", key=f"add_{match['id']}"):
                        st.session_state.setdefault('slip', []).append(match)
                        st.toast(f"Added to R{stake * 2.1:.2f} Strategy Slip")
                st.divider()
    else:
        st.error("No upcoming matches found in the scan.")

# --- THE SLIP CALCULATOR ---
if 'slip' in st.session_state and st.session_state['slip']:
    st.sidebar.subheader("Your 2.1 Slip")
    for item in st.session_state['slip']:
        st.sidebar.write(f"🔹 {item['h']['title']} vs {item['a']['title']}")
    
    if st.sidebar.button("Clear Slip"):
        st.session_state['slip'] = []
        st.rerun()
  
