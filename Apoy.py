import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
from datetime import datetime
import re

st.set_page_config(page_title="Lottery Data Extractor", page_icon="🎰", layout="wide")

# Inițializare session state
if 'saved_sources' not in st.session_state:
    st.session_state.saved_sources = []

if 'extracted_data' not in st.session_state:
    st.session_state.extracted_data = None

st.title("🎰 Lottery Data Extractor")
st.markdown("Extrage date istorice de la diverse loterii")

# Sidebar pentru surse salvate
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
    
    # Informații despre selectori CSS/HTML
    with st.expander("⚙️ Setări Avansate (Opțional)"):
        st.markdown("Ajută aplicația să găsească datele pe pagină:")
        css_selector = st.text_input("Selector CSS pentru tabel/rezultate", placeholder="ex: .results-table, #draws")
        date_format = st.text_input("Format dată", placeholder="ex: DD.MM.YYYY sau YYYY-MM-DD", value="DD.MM.YYYY")
    
    if st.button("💾 Salvează Sursa", type="primary"):
        if source_name and source_url:
            new_source = {
                'name': source_name,
                'url': source_url,
                'type': source_type,
                'numbers_count': numbers_count,
                'numbers_range': numbers_range,
                'css_selector': css_selector if css_selector else None,
                'date_format': date_format
            }
            st.session_state.saved_sources.append(new_source)
            st.success(f"✅ Sursa '{source_name}' a fost salvată!")
        else:
            st.error("Te rog completează cel puțin numele și URL-ul!")

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
        
        use_api = st.checkbox("🚀 Încearcă extragere avansată (API/Ajax)", value=True, 
                             help="Folosește metode alternative pentru a încărca toate datele")
        
        if st.button("🔍 Extrage Date", type="primary"):
            with st.spinner(f"Extrag {num_rounds} runde de la {source['name']}..."):
                try:
                    results = []
                    soup = None
                    
                    # Pentru Sazka.cz - folosim API-ul lor direct
                    if 'sazka.cz' in source['url'] and use_api:
                        try:
                            st.info("🎯 Încerc să extrag direct din API Sazka...")
                            
                            # Sazka folosește un API pentru a încărca datele
                            api_url = "https://www.sazka.cz/api/v1/lottery-draws"
                            
                            headers = {
                                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                                'Accept': 'application/json',
                                'Referer': source['url']
                            }
                            
                            # Determină ID-ul loteriei din URL
                            lottery_id = None
                            if 'rychle-kacky' in source['url']:
                                lottery_id = 'rychle-kacky'
                            elif 'keno' in source['url']:
                                lottery_id = 'keno'
                            
                            if lottery_id:
                                # Încearcă să obții datele prin API
                                params = {
                                    'lottery': lottery_id,
                                    'limit': min(num_rounds, 1000),
                                    'offset': 0
                                }
                                
                                response = requests.get(api_url, headers=headers, params=params, timeout=15)
                                
                                if response.status_code == 200:
                                    data = response.json()
                                    st.success(f"✅ Am găsit API-ul! Procesez datele...")
                                    
                                    # Procesează datele JSON
                                    if 'draws' in data:
                                        for draw in data['draws'][:num_rounds]:
                                            row = []
                                            # Extrage ID
                                            if 'drawId' in draw:
                                                row.append(str(draw['drawId']))
                                            # Extrage data
                                            if 'drawTime' in draw:
                                                row.append(draw['drawTime'])
                                            # Extrage numerele
                                            if 'numbers' in draw:
                                                numbers = ', '.join(map(str, draw['numbers']))
                                                row.append(numbers)
                                            
                                            if row:
                                                results.append(row)
                                else:
                                    st.warning(f"API status: {response.status_code}, încerc metoda standard...")
                        
                        except Exception as e:
                            st.warning(f"Nu am putut folosi API-ul: {str(e)}")
                            st.info("📝 Încerc metoda standard...")
                    
                    # Dacă nu am rezultate din API, folosește scraping HTML
                    if not results:
                        headers = {
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                            'Accept-Language': 'cs,en;q=0.9',
                            'Referer': 'https://www.sazka.cz/'
                        }
                        
                        response = requests.get(source['url'], headers=headers, timeout=15)
                        response.raise_for_status()
                        soup = BeautifulSoup(response.content, 'html.parser')
    
                    # Extrage datele din HTML (dacă nu am rezultate din API)
                    if not results and soup:
                        # Metodă generică - caută tabele și liste
                        tables = soup.find_all('table')
                        
                        if tables:
                            st.info(f"Am găsit {len(tables)} tabel(e) pe pagină")
                            
                            # Procesează primul tabel
                            for row in tables[0].find_all('tr')[1:num_rounds+1]:  # Skip header
                                cells = row.find_all(['td', 'th'])
                                if len(cells) >= 2:
                                    row_data = [cell.get_text(strip=True) for cell in cells]
                                    results.append(row_data)
                        
                        # Dacă nu găsim tabele, căutăm alte structuri
                        if not results:
                            # Caută div-uri sau span-uri cu clase comune
                            divs = soup.find_all('div', class_=re.compile(r'result|draw|number|winning|vysledk'))
                            if divs:
                                st.info(f"Am găsit {len(divs)} elemente cu rezultate")
                                
                                # Încearcă să extragă din div-uri
                                for div in divs[:num_rounds]:
                                    text = div.get_text(strip=True)
                                    if text:
                                        # Încearcă să găsească pattern-uri de numere
                                        numbers = re.findall(r'\d+', text)
                                        if len(numbers) >= 5:  # Are sens ca rezultat de loterie
                                            results.append([text])
                    
                    if results:
                        # Crează DataFrame
                        df = pd.DataFrame(results)
                        st.session_state.extracted_data = df
                        
                        st.success(f"✅ Am extras {len(results)} runde!")
                        
                        st.dataframe(df, use_container_width=True)
                        
                        # Download buttons
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            csv = df.to_csv(index=False)
                            st.download_button(
                                "📥 Download CSV",
                                csv,
                                f"{source['name']}_data.csv",
                                "text/csv"
                            )
                        
                        with col2:
                            excel_buffer = pd.ExcelWriter('temp.xlsx', engine='openpyxl')
                            df.to_excel(excel_buffer, index=False)
                            excel_buffer.close()
                            
                        with col3:
                            json_str = df.to_json(orient='records', indent=2)
                            st.download_button(
                                "📥 Download JSON",
                                json_str,
                                f"{source['name']}_data.json",
                                "application/json"
                            )
                    else:
                        st.error("Nu am putut extrage date. Structura paginii ar putea fi diferită.")
                        st.info("💡 Sfat: Verifică URL-ul sau încearcă să adaugi un selector CSS în setările avansate")
                        
                        # Arată preview HTML pentru debugging
                        with st.expander("🔍 Vezi structura HTML (pentru debugging)"):
                            st.code(soup.prettify()[:5000], language='html')
                
                except requests.exceptions.RequestException as e:
                    st.error(f"Eroare la accesarea URL-ului: {str(e)}")
                except Exception as e:
                    st.error(f"Eroare: {str(e)}")

with tab3:
    st.header("ℹ️ Cum să folosești aplicația")
    
    st.markdown("""
    ### 📝 Pași:
    
    1. **Adaugă o sursă**
       - Mergi la tab-ul "Adaugă Sursă"
       - Completează numele loteriei și URL-ul complet
       - Alege tipul și configurează parametrii
       - Salvează sursa
    
    2. **Extrage date**
       - Mergi la tab-ul "Extrage Date"
       - Alege sursa din listă
       - Specifică câte runde vrei să extragi
       - Apasă "Extrage Date"
    
    3. **Download**
       - Descarcă datele în format CSV, Excel sau JSON
    
    ### 🎯 Exemple de surse:
    
    - **Cehia Keno**: https://www.fortunacr.cz/statistiky
    - **Loto România**: https://www.loto.ro/rezultate-loto
    - **Euro Jackpot**: https://www.euro-jackpot.net/ro/rezultate
    
    ### ⚠️ Note importante:
    
    - Unele site-uri pot avea protecție anti-scraping
    - Extragerea avansată încearcă să folosească API-uri pentru date complete
    - Pentru Sazka.cz, aplicația detectează automat API-ul lor
    - Dacă site-ul încarcă date dinamic (cu JavaScript), bifează opțiunea avansată
    - Prima încărcare poate fi mai lentă dar va extrage toate rundele disponibile
    
    ### 🔧 Setări Avansate:
    
    Dacă aplicația nu găsește automat datele:
    - Deschide site-ul în browser
    - Click dreapta pe tabelul cu rezultate → "Inspect"
    - Caută class sau id-ul containerului (ex: `.results-table`)
    - Adaugă acest selector în setările avansate
    """)
    
    st.divider()
    
    st.markdown("""
    ### 📦 Instalare pentru GitHub:
    
    Creează fișierul `requirements.txt`:
    ```
    streamlit
    requests
    beautifulsoup4
    pandas
    openpyxl
    lxml
    ```
    
    Rulează local:
    ```bash
    streamlit run app.py
    ```
    """)

# Footer
st.divider()
st.markdown("""
<div style='text-align: center; color: #666; padding: 20px;'>
    🎰 Lottery Data Extractor v1.0 | Made with Streamlit
</div>
""", unsafe_allow_html=True)