import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
from datetime import datetime
import re
import time

st.set_page_config(page_title="Lottery Data Extractor", page_icon="🎰", layout="wide")

# Inițializare session state
if 'saved_sources' not in st.session_state:
    st.session_state.saved_sources = []

if 'extracted_data' not in st.session_state:
    st.session_state.extracted_data = None

st.title("🎰 Lottery Data Extractor")
st.markdown("Extrage date istorice de la diverse loterii")

# ----------------------------------------------------------------------
# SECȚIUNEA 1: SIDEBAR ȘI SURSE SALVATE
# ----------------------------------------------------------------------
with st.sidebar:
    st.header("📋 Surse Salvate")
    
    if st.session_state.saved_sources:
        for idx, source in enumerate(st.session_state.saved_sources):
            with st.expander(f"{source['name']}"):
                st.write(f"**URL:** {source['url']}")
                st.write(f"**Tip:** {source['type']}")
                if st.button(f"Șterge", key=f"del_{idx}"):
                    st.session_state.saved_sources.pop(idx)
                    st.rerun()
    else:
        st.info("Nicio sursă salvată încă")

# Tab-uri principale
tab1, tab2, tab3 = st.tabs(["➕ Adaugă Sursă", "📊 Extrage Date", "ℹ️ Info"])

# ----------------------------------------------------------------------
# SECȚIUNEA 2: ADAUGĂ SURSĂ
# ----------------------------------------------------------------------
with tab1:
    st.header("Adaugă o nouă sursă de loterie")
    
    col1, col2 = st.columns(2)
    
    with col1:
        source_name = st.text_input("Nume sursă", placeholder="ex: Cehia Keno Rapido")
        source_url = st.text_input("URL complet", placeholder="https://...")
        
    with col2:
        source_type = st.selectbox(
            "Tip loterie",
            ["Keno", "Loto", "Powerball", "EuroJackpot", "Rapido", "Altul"]
        )
        
        numbers_count = st.number_input("Câte numere se extrag", min_value=1, max_value=100, value=20)
    
    numbers_range = st.text_input("Interval numere", placeholder="ex: 1-80 sau 1-66", value="1-80")
    
    if st.button("💾 Salvează Sursa", type="primary"):
        if source_name and source_url:
            new_source = {
                'name': source_name,
                'url': source_url,
                'type': source_type,
                'numbers_count': numbers_count,
                'numbers_range': numbers_range
            }
            st.session_state.saved_sources.append(new_source)
            st.success(f"✅ Sursa '{source_name}' a fost salvată!")
        else:
            st.error("Te rog completează cel puțin numele și URL-ul!")

# ----------------------------------------------------------------------
# SECȚIUNEA 3: EXTRAGE DATE
# ----------------------------------------------------------------------
with tab2:
    st.header("Extrage date de la sursele salvate")
    
    if not st.session_state.saved_sources:
        st.warning("Nu ai surse salvate! Adaugă o sursă în tab-ul 'Adaugă Sursă'")
    else:
        selected_source = st.selectbox(
            "Alege sursa",
            range(len(st.session_state.saved_sources)),
            format_func=lambda x: st.session_state.saved_sources[x]['name']
        )
        
        source = st.session_state.saved_sources[selected_source]
        
        col1, col2 = st.columns(2)
        with col1:
            num_rounds = st.number_input("Câte runde să extrag", min_value=1, max_value=5000, value=100)
        
        with col2:
            st.write(f"**URL:** {source['url']}")
            st.write(f"**Tip:** {source['type']}")
        
        if st.button("🔍 Extrage Date", type="primary"):
            with st.spinner(f"Extrag {num_rounds} runde de la {source['name']}..."):
                try:
                    results = []
                    api_worked = False

                    # Logica specială pentru Sazka.cz Rychlé kačky - Încercăm doar endpoint-ul principal
                    if 'sazka.cz' in source['url'] and 'rychle-kacky' in source['url']:
                        st.info("🎯 Detectat Sazka Rychlé kačky - folosesc API Gateway...")
                        
                        # API-ul confirmat: v2
                        api_base = "https://apigw.sazka.cz/lottery/v2/cs/online-lotteries/rychle-kacky/draws"
                        
                        headers = {
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                            'Accept': 'application/json',
                            'Ocp-Apim-Subscription-Key': '6fdc6e24bfcb438bac06efb0f1488534',
                            
                            # 🌟 HEADER ESENȚIAL PENTRU A EVITA BLOCAREA API GATEWAY 🌟
                            'X-Origin-Host': 'www.sazka.cz', 
                            
                            'Referer': source['url'],
                            'Origin': 'https://www.sazka.cz'
                        }
                        
                        try:
                            st.info(f"Încerc: {api_base}")
                            # Test rapid de conectivitate
                            response = requests.get(api_base, headers=headers, params={'limit': 1}, timeout=10)
                            
                            if response.status_code == 200:
                                st.success(f"✅ API funcționează! Status Code: 200")
                                api_worked = True
                                
                                # Setări pentru extragerea completă
                                rounds_per_request = 50
                                num_requests = (num_rounds // rounds_per_request) + 1
                                
                                progress_bar = st.progress(0)
                                status_text = st.empty()
                                
                                for page in range(num_requests):
                                    if len(results) >= num_rounds:
                                        break
                                        
                                    status_text.text(f"📥 Extrag pagina {page + 1}/{num_requests}...")
                                    
                                    params = {
                                        'limit': rounds_per_request,
                                        'offset': page * rounds_per_request
                                    }
                                    
                                    response = requests.get(api_base, headers=headers, params=params, timeout=10)
                                    
                                    if response.status_code == 200:
                                        data = response.json()
                                        draws = data if isinstance(data, list) else data.get('draws', data.get('data', []))
                                        
                                        for draw in draws:
                                            if len(results) >= num_rounds:
                                                break
                                            
                                            row = []
                                            
                                            # Extrage ID-ul
                                            draw_id = draw.get('id') or draw.get('drawId') or draw.get('draw_id')
                                            if draw_id:
                                                row.append(str(draw_id))
                                            
                                            # Extrage data/ora
                                            draw_time = draw.get('drawTime') or draw.get('time') or draw.get('date')
                                            if draw_time:
                                                try:
                                                    if 'T' in str(draw_time):
                                                        dt = datetime.fromisoformat(str(draw_time).replace('Z', '+00:00'))
                                                        row.append(dt.strftime('%d.%m.%Y'))
                                                        row.append(dt.strftime('%H:%M:%S'))
                                                    else:
                                                        row.append(str(draw_time))
                                                except:
                                                    row.append(str(draw_time))
                                            
                                            # Extrage numerele
                                            numbers = draw.get('numbers') or draw.get('winningNumbers') or []
                                            if numbers:
                                                row.append(', '.join(map(str, sorted(numbers))))
                                            
                                            if len(row) >= 2:
                                                results.append(row)
                                    else:
                                        st.error(f"❌ Eroare pagină API: Status {response.status_code}")
                                        break # Oprim la prima eroare de pagină
                                    
                                    progress_bar.progress(min((page + 1) / num_requests, 1.0))
                                    time.sleep(0.1)
                                
                                progress_bar.empty()
                                status_text.empty()
                            
                            else:
                                # Afișăm eroarea exactă returnată de server
                                error_details = response.text
                                if len(error_details) > 200:
                                    error_details = error_details[:200] + "..."
                                st.error(f"❌ API a returnat: Status {response.status_code}. Detalii: {error_details}")

                        except requests.exceptions.RequestException as e:
                            st.error(f"❌ Eroare de rețea la {api_base}: {str(e)}")
                        except Exception as e:
                            st.error(f"❌ Eroare la procesarea răspunsului: {str(e)}")

                        if results:
                            st.success(f"✅ Am extras {len(results)} runde din API!")
                        elif not api_worked:
                            st.warning("⚠️ API-ul Sazka a eșuat. Încerc scraping HTML...")
                    
                    # Scraping HTML generic
                    if not results:
                        st.info("📄 Încerc scraping HTML...")
                        
                        headers_scrape = {
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                        }
                        
                        # Folosim source['url'] pentru scraping
                        response = requests.get(source['url'], headers=headers_scrape, timeout=15)
                        response.raise_for_status()
                        soup = BeautifulSoup(response.content, 'html.parser')
                        
                        # Caută tabele
                        tables = soup.find_all('table')
                        if tables:
                            st.info(f"✓ Am găsit {len(tables)} tabel(e)")
                            for table in tables:
                                rows = table.find_all('tr')
                                for row in rows[1:num_rounds+1]:
                                    cells = row.find_all(['td', 'th'])
                                    if len(cells) >= 2:
                                        row_data = [cell.get_text(strip=True) for cell in cells]
                                        if any(row_data):
                                            results.append(row_data)
                                if results:
                                    break
                    
                    # Afișează rezultatele
                    if results:
                        max_cols = max(len(r) for r in results) if results else 0
                        results_padded = [r + [''] * (max_cols - len(r)) for r in results]
                        
                        if 'sazka.cz' in source['url'] and api_worked:
                            columns = ['ID Runda', 'Data', 'Ora', 'Numere Extrase'] + [f'Col_{i}' for i in range(max_cols - 4)]
                            df = pd.DataFrame(results_padded, columns=columns[:max_cols])
                        else:
                            df = pd.DataFrame(results_padded)

                        st.session_state.extracted_data = df
                        st.success(f"✅ Am extras {len(results)} runde!")
                        st.dataframe(df, use_container_width=True)
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            csv = df.to_csv(index=False).encode('utf-8')
                            st.download_button(
                                "📥 Download CSV",
                                csv,
                                f"{source['name']}_data.csv",
                                "text/csv"
                            )
                        
                        with col2:
                            json_str = df.to_json(orient='records', indent=2)
                            st.download_button(
                                "📥 Download JSON",
                                json_str,
                                f"{source['name']}_data.json",
                                "application/json"
                            )
                    else:
                        st.error("❌ Nu am putut extrage date.")
                        st.info("💡 Verifică URL-ul sau structura paginii")
                
                except Exception as e:
                    st.error(f"Eroare generală la extragere: {str(e)}")

# ----------------------------------------------------------------------
# SECȚIUNEA 4: INFO
# ----------------------------------------------------------------------
with tab3:
    st.header("ℹ️ Cum să folosești aplicația")
    
    st.markdown("""
    ### 📝 Pași:
    
    1. **Adaugă o sursă**
       - Mergi la tab-ul "Adaugă Sursă"
       - Completează numele loteriei și URL-ul complet
       - Salvează sursa
    
    2. **Extrage date**
       - Mergi la tab-ul "Extrage Date"
       - Alege sursa din listă
       - Specifică câte runde vrei
       - Apasă "Extrage Date"
    
    3. **Download**
       - Descarcă datele în format CSV sau JSON
    
    ### 🎯 Notă importantă pentru Sazka Rychlé kačky:
    
    API-ul Sazka (apigw.sazka.cz) este protejat de un **API Gateway foarte strict**. Dacă extracția eșuează cu un cod de eroare (ex. 403 Forbidden), cel mai probabil mediul de rulare (Streamlit Cloud) este blocat pe baza adresei IP. În acest caz, singura soluție este rularea scriptului de pe o altă mașină sau depanarea rutinei de scraping HTML.
    
    ### 📦 Requirements:
    ```
    streamlit
    requests
    beautifulsoup4
    pandas
    ```
    """)

st.divider()
st.markdown("""
<div style='text-align: center; color: #666; padding: 20px;'>
    🎰 Lottery Data Extractor v2.1 | Made with Streamlit
</div>
""", unsafe_allow_html=True)
