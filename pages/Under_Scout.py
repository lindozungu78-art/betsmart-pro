import streamlit as st
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime, timedelta
import time
from urllib.parse import quote
import re

# ==================== CONFIGURATION ====================
AVAILABLE_LEAGUES = ['EPL', 'Serie_A', 'Ligue_1', 'La_liga', 'Bundesliga']
DEFAULT_LEAGUES = ['EPL', 'Serie_A']
DISPLAY_LIMIT = 12
ODD_MULTIPLIER = 2.1
SAST_OFFSET = 2
REQUEST_TIMEOUT = 10
RATE_LIMIT_DELAY = 2.0
MAX_SLIP_SIZE = 10

# ==================== HELPER FUNCTIONS ====================
def convert_to_sast(utc_time_str: str) -> str:
    """Convert UTC time to SAST"""
    try:
        utc_dt = datetime.strptime(utc_time_str, '%Y-%m-%d %H:%M:%S')
        sast_dt = utc_dt + timedelta(hours=SAST_OFFSET)
        return sast_dt.strftime('%d %b, %H:%M')
    except (ValueError, TypeError):
        return "Date TBA"

@st.cache_data(ttl=300, show_spinner=False)
def fetch_league_data(league: str):
    """Fetch data for a single league with error handling"""
    url = f"https://understat.com/league/{league}/2025"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    try:
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, "lxml")
        scripts = soup.find_all('script')
        
        for script in scripts:
            if 'datesData' in script.text:
                # Added re.DOTALL to handle multiline scripts
                json_match = re.search(r"datesData\s*=\s*JSON\.parse\('(.*?)'\)", script.text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                    # Handle escape sequences properly
                    json_str = json_str.encode('utf-8').decode('unicode_escape')
                    data = json.loads(json_str)
                    return data if isinstance(data, list) else []
        return []
        
    except Exception as e:
        st.error(f"Error fetching {league}: {str(e)}")
        return []

def fetch_all_leagues(leagues, progress_callback=None):
    """Fetch data for multiple leagues with rate limiting"""
    all_matches = []
    
    for i, league in enumerate(leagues):
        if progress_callback:
            progress_callback(i + 1, len(leagues), league)
        
        if i > 0:
            time.sleep(RATE_LIMIT_DELAY)
        
        data = fetch_league_data(league)
        
        if data:
            for match in data:
                if not match.get('isResult', True):
                    # Validate required fields
                    if match.get('id') and match.get('h', {}).get('title') and match.get('a', {}).get('title'):
                        all_matches.append({
                            'id': match['id'],
                            'home_team': match['h']['title'],
                            'away_team': match['a']['title'],
                            'datetime_utc': match.get('datetime', ''),
                            'league': league,
                            'raw_data': match
                        })
    
    return all_matches

def get_statshub_url(home_team, away_team):
    """Generate safe StatsHub URL"""
    home_slug = quote(home_team.replace(" ", "-").lower())
    away_slug = quote(away_team.replace(" ", "-").lower())
    return f"https://www.statshub.com/en/match/{home_slug}-vs-{away_slug}"

# ==================== SESSION STATE MANAGEMENT ====================
def init_session_state():
    """Initialize session state variables"""
    if 'my_slip' not in st.session_state:
        st.session_state.my_slip = []
    if 'selected_market' not in st.session_state:
        st.session_state.selected_market = "Under 4.5"

def add_to_slip(match):
    """Add match to slip"""
    if len(st.session_state.my_slip) >= MAX_SLIP_SIZE:
        st.warning(f"Slip limited to {MAX_SLIP_SIZE} matches")
        return False
    
    if not any(m['id'] == match['id'] for m in st.session_state.my_slip):
        st.session_state.my_slip.append(match)
        return True
    return False

def remove_from_slip(index):
    """Remove match from slip by index"""
    if 0 <= index < len(st.session_state.my_slip):
        st.session_state.my_slip.pop(index)

def clear_slip():
    """Clear all matches from slip"""
    st.session_state.my_slip = []

# ==================== UI COMPONENTS ====================
def render_sidebar():
    """Render sidebar and return user inputs"""
    st.sidebar.header("⚙️ Strategy Settings")
    
    # League selection
    st.sidebar.subheader("Leagues to Scan")
    selected_leagues = st.sidebar.multiselect(
        "Select leagues",
        options=AVAILABLE_LEAGUES,
        default=DEFAULT_LEAGUES
    )
    
    # Market selection
    market_pref = st.sidebar.selectbox(
        "Market",
        ["Under 4.5", "Under 5.5", "Over 2.5", "Both Teams to Score"]
    )
    
    # Stake input with validation
    stake = st.sidebar.number_input(
        "Stake (ZAR)",
        min_value=0.0,
        max_value=10000.0,
        value=10.0,
        step=5.0,
        help="Minimum R0, Maximum R10,000"
    )
    
    # Scan button
    scan_button = st.sidebar.button("🚀 Run Full Week Scan", type="primary", use_container_width=True)
    
    return selected_leagues, stake, market_pref, scan_button

def render_bet_slip(stake):
    """Render the betting slip in sidebar"""
    if not st.session_state.my_slip:
        return
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("📋 Strategy Slip")
    
    for idx, match in enumerate(st.session_state.my_slip):
        col1, col2 = st.sidebar.columns([4, 1])
        with col1:
            st.write(f"🔹 {match['home_team']} vs {match['away_team']}")
            st.caption(f"🏆 {match['league'].replace('_', ' ')}")
        with col2:
            if st.button("❌", key=f"remove_{idx}"):
                remove_from_slip(idx)
                st.rerun()
    
    st.sidebar.markdown("---")
    
    # Payout calculation
    payout = stake * ODD_MULTIPLIER
    st.sidebar.metric(
        "💰 Potential Payout",
        f"R{payout:.2f}",
        delta=f"Based on R{stake:.2f} stake",
        delta_color="off"
    )
    
    # Clear all button
    if st.sidebar.button("🗑️ Clear All", use_container_width=True):
        clear_slip()
        st.rerun()

def render_match_card(match):
    """Render a single match card"""
    local_time = convert_to_sast(match['datetime_utc'])
    statshub_url = get_statshub_url(match['home_team'], match['away_team'])
    
    with st.container():
        col1, col2, col3 = st.columns([2.5, 1, 0.8])
        
        with col1:
            st.markdown(f"**{match['home_team']} vs {match['away_team']}**")
            st.caption(f"🏆 {match['league'].replace('_', ' ')} | 🕒 {local_time} SAST")
        
        with col2:
            st.link_button("📊 StatsHub", statshub_url, use_container_width=True)
        
        with col3:
            if st.button("➕ Add", key=f"add_{match['id']}", use_container_width=True):
                if add_to_slip(match):
                    st.toast(f"✅ Added: {match['home_team']} vs {match['away_team']}", icon="✅")
                else:
                    st.toast("❌ Slip full or duplicate", icon="⚠️")
        
        st.divider()

# ==================== MAIN APP ====================
def main():
    """Main application entry point"""
    st.set_page_config(
        page_title="BetSmart Pro",
        page_icon="🛡️",
        layout="wide"
    )
    
    st.title("🛡️ BetSmart Pro: Multi-Source Engine")
    st.caption("Scraping: Understat + StatsHub Verification | Data refreshes every 5 minutes")
    
    # Initialize session state
    init_session_state()
    
    # Render sidebar and get inputs
    selected_leagues, stake, market_pref, scan_button = render_sidebar()
    
    # Store market preference
    if market_pref:
        st.session_state.selected_market = market_pref
    
    # Run scan when button clicked
    if scan_button:
        if not selected_leagues:
            st.warning("Please select at least one league to scan")
        else:
            # Progress bar for scanning
            progress_text = st.empty()
            progress_bar = st.progress(0)
            
            def update_progress(current, total, league):
                progress_text.info(f"📡 Scanning {league}... ({current}/{total})")
                progress_bar.progress(current / total)
            
            # Fetch matches
            with st.spinner("Fetching match data..."):
                matches = fetch_all_leagues(selected_leagues, update_progress)
            
            # Clear progress indicators
            progress_text.empty()
            progress_bar.empty()
            
            if not matches:
                st.error("❌ No upcoming matches found. Please try again later.")
            else:
                # Sort by datetime
                matches.sort(key=lambda x: x['datetime_utc'])
                
                # Limit display
                display_matches = matches[:DISPLAY_LIMIT]
                
                st.success(f"✅ Found {len(matches)} upcoming matches (showing {len(display_matches)})")
                
                # Display matches
                for match in display_matches:
                    render_match_card(match)
    
    # Always show betting slip
    render_bet_slip(stake)

# ==================== ENTRY POINT ====================
if __name__ == "__main__":
    main()
