import streamlit as st
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass, field
import time
from urllib.parse import quote
import re

# ==================== CONFIGURATION ====================
@dataclass
class AppConfig:
    """Centralized configuration for the app"""
    available_leagues: List[str] = field(default_factory=lambda: ['EPL', 'Serie_A', 'Ligue_1', 'La_liga', 'Bundesliga'])
    default_leagues: List[str] = field(default_factory=lambda: ['EPL', 'Serie_A'])
    display_limit: int = 12
    odd_multiplier: float = 2.1
    sast_offset: int = 2
    request_timeout: int = 10
    rate_limit_delay: float = 2.0
    max_slip_size: int = 10

# ==================== DATA MODELS ====================
class Match:
    """Data model for a match"""
    def __init__(self, raw_data: dict, league: str):
        self.id = raw_data.get('id')
        self.home_team = raw_data.get('h', {}).get('title', 'Unknown')
        self.away_team = raw_data.get('a', {}).get('title', 'Unknown')
        self.datetime_utc = raw_data.get('datetime', '')
        self.is_result = raw_data.get('isResult', False)
        self.league = league
        self.raw_data = raw_data
    
    @property
    def display_name(self) -> str:
        return f"{self.home_team} vs {self.away_team}"
    
    @property
    def statshub_url(self) -> str:
        """Generate safe StatsHub URL"""
        home_slug = quote(self.home_team.replace(" ", "-").lower())
        away_slug = quote(self.away_team.replace(" ", "-").lower())
        return f"https://www.statshub.com/en/match/{home_slug}-vs-{away_slug}"
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'home_team': self.home_team,
            'away_team': self.away_team,
            'datetime_utc': self.datetime_utc,
            'league': self.league
        }

class BetSlip:
    """Manages the betting slip state"""
    def __init__(self):
        if 'my_slip' not in st.session_state:
            st.session_state.my_slip = []
    
    def add_match(self, match: Match) -> bool:
        """Add match to slip, returns success status"""
        if len(st.session_state.my_slip) >= AppConfig.max_slip_size:
            st.warning(f"Slip limited to {AppConfig.max_slip_size} matches")
            return False
        
        if not any(m['id'] == match.id for m in st.session_state.my_slip):
            st.session_state.my_slip.append(match.to_dict())
            return True
        return False
    
    def remove_match(self, index: int) -> None:
        """Remove match by index"""
        if 0 <= index < len(st.session_state.my_slip):
            st.session_state.my_slip.pop(index)
    
    def clear_all(self) -> None:
        """Clear all matches from slip"""
        st.session_state.my_slip = []
    
    def get_matches(self) -> List[dict]:
        return st.session_state.my_slip
    
    def calculate_payout(self, stake: float) -> float:
        return stake * AppConfig.odd_multiplier

# ==================== DATA SERVICE ====================
class UnderstatDataService:
    """Handles all data fetching from Understat"""
    
    @staticmethod
    @st.cache_data(ttl=300, show_spinner=False)
    def fetch_league_data(league: str) -> Optional[List[dict]]:
        """Fetch data for a single league with error handling"""
        url = f"https://understat.com/league/{league}/2025"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        
        try:
            response = requests.get(url, headers=headers, timeout=AppConfig.request_timeout)
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
            
        except requests.exceptions.Timeout:
            st.error(f"Timeout fetching {league}")
            return []
        except requests.exceptions.RequestException as e:
            st.error(f"Network error for {league}: {str(e)}")
            return []
        except (json.JSONDecodeError, AttributeError, re.error) as e:
            st.error(f"Data parsing error for {league}: {str(e)}")
            return []
    
    def fetch_multiple_leagues(self, leagues: List[str], progress_callback=None) -> List[Match]:
        """Fetch data for multiple leagues with rate limiting"""
        all_matches = []
        
        for i, league in enumerate(leagues):
            # Progress update
            if progress_callback:
                progress_callback(i + 1, len(leagues), league)
            
            # Rate limiting
            if i > 0:
                time.sleep(AppConfig.rate_limit_delay)
            
            data = self.fetch_league_data(league)
            
            if data:
                upcoming = [m for m in data if not m.get('isResult', True)]
                for match_data in upcoming:
                    # Validate required fields
                    if match_data.get('id') and match_data.get('h', {}).get('title') and match_data.get('a', {}).get('title'):
                        match = Match(match_data, league)
                        all_matches.append(match)
        
        return all_matches

# ==================== UI COMPONENTS ====================
class MatchCard:
    """Renders a single match card"""
    
    @staticmethod
    def convert_to_sast(utc_time_str: str, offset: int = 2) -> str:
        """Convert UTC time to SAST"""
        try:
            utc_dt = datetime.strptime(utc_time_str, '%Y-%m-%d %H:%M:%S')
            sast_dt = utc_dt + timedelta(hours=offset)
            return sast_dt.strftime('%d %b, %H:%M')
        except (ValueError, TypeError):
            return "Date TBA"
    
    def render(self, match: Match, slip: BetSlip) -> None:
        """Render a single match card"""
        local_time = self.convert_to_sast(match.datetime_utc, AppConfig.sast_offset)
        
        with st.container():
            col1, col2, col3, col4 = st.columns([2, 1, 0.8, 0.8])
            
            with col1:
                st.markdown(f"**{match.display_name}**")
                st.caption(f"🏆 {match.league.replace('_', ' ')} | 🕒 {local_time} SAST")
            
            with col2:
                st.link_button("📊 StatsHub", match.statshub_url, use_container_width=True)
            
            with col3:
                if st.button("➕ Add", key=f"add_{match.id}", use_container_width=True):
                    if slip.add_match(match):
                        st.toast(f"✅ Added: {match.display_name}", icon="✅")
                    else:
                        st.toast("❌ Slip full or duplicate", icon="⚠️")
            
            with col4:
                st.button("ℹ️ Info", key=f"info_{match.id}", disabled=True, use_container_width=True)
            
            st.divider()

class SidebarUI:
    """Handles sidebar rendering and user input"""
    
    @staticmethod
    def render() -> tuple:
        """Returns (selected_leagues, stake, market_pref, scan_button)"""
        st.sidebar.header("⚙️ Strategy Settings")
        
        # League selection
        st.sidebar.subheader("Leagues to Scan")
        selected_leagues = st.sidebar.multiselect(
            "Select leagues",
            options=AppConfig.available_leagues,
            default=AppConfig.default_leagues
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

class BetSlipUI:
    """Renders the betting slip in sidebar"""
    
    @staticmethod
    def render(slip: BetSlip, stake: float) -> None:
        """Display current betting slip"""
        matches = slip.get_matches()
        
        if not matches:
            return
        
        st.sidebar.markdown("---")
        st.sidebar.subheader("📋 Strategy Slip")
        
        for idx, match in enumerate(matches):
            col1, col2 = st.sidebar.columns([4, 1])
            with col1:
                st.write(f"🔹 {match['home_team']} vs {match['away_team']}")
                st.caption(f"🏆 {match['league'].replace('_', ' ')}")
            with col2:
                if st.button("❌", key=f"remove_{idx}"):
                    slip.remove_match(idx)
                    st.rerun()
        
        st.sidebar.markdown("---")
        
        # Payout calculation
        payout = slip.calculate_payout(stake)
        st.sidebar.metric(
            "💰 Potential Payout",
            f"R{payout:.2f}",
            delta=f"Based on R{stake:.2f} stake",
            delta_color="off"
        )
        
        # Clear all button
        if st.sidebar.button("🗑️ Clear All", use_container_width=True):
            slip.clear_all()
            st.rerun()

# ==================== MAIN APP ====================
class BetSmartApp:
    """Main application class"""
    
    def __init__(self):
        self.config = AppConfig()
        self.data_service = UnderstatDataService()
        self.slip = BetSlip()
        self.match_card = MatchCard()
        self.sidebar_ui = SidebarUI()
        self.slip_ui = BetSlipUI()
    
    def run_scan(self, selected_leagues: List[str]) -> None:
        """Execute the match scanning process"""
        if not selected_leagues:
            st.warning("Please select at least one league to scan")
            return
        
        # Progress bar for scanning
        progress_text = st.empty()
        progress_bar = st.progress(0)
        
        def update_progress(current, total, league):
            progress_text.info(f"📡 Scanning {league}... ({current}/{total})")
            progress_bar.progress(current / total)
        
        # Fetch matches
        matches = self.data_service.fetch_multiple_leagues(
            selected_leagues,
            progress_callback=update_progress
        )
        
        # Clear progress indicators
        progress_text.empty()
        progress_bar.empty()
        
        if not matches:
            st.error("❌ No upcoming matches found. Please try again later.")
            return
        
        # Sort by datetime
        matches.sort(key=lambda x: x.datetime_utc)
        
        # Limit display
        display_matches = matches[:AppConfig.display_limit]
        
        st.success(f"✅ Found {len(matches)} upcoming matches (showing {len(display_matches)})")
        
        # Display matches
        for match in display_matches:
            self.match_card.render(match, self.slip)
    
    def run(self):
        """Main application entry point"""
        st.set_page_config(
            page_title="BetSmart Pro",
            page_icon="🛡️",
            layout="wide"
        )
        
        st.title("🛡️ BetSmart Pro: Multi-Source Engine")
        st.caption("Scraping: Understat + StatsHub Verification | Data refreshes every 5 minutes")
        
        # CRITICAL FIX: Added parentheses to call the render method
        selected_leagues, stake, market_pref, scan_button = self.sidebar_ui.render()
        
        # Display unused variable warning (or use it for future features)
        if market_pref:
            st.session_state['selected_market'] = market_pref
        
        # Run scan when button clicked
        if scan_button:
            self.run_scan(selected_leagues)
        
        # Always show betting slip
        self.slip_ui.render(self.slip, stake)

# ==================== ENTRY POINT ====================
if __name__ == "__main__":
    app = BetSmartApp()
    app.run()
