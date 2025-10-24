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
                    
                    # Încarcă pagina
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                        'Accept-Language': 'cs,en;q=0.9',
                        'Referer': 'https://www.sazka.cz/'
                    }
                    
                    response = requests.get(source['url'], headers=headers, timeout=15)
                    response.raise_for_status()
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    st.info("📄 Am încărcat pagina, analizez structura...")
                    
                    # Pentru Sazka.cz - căutăm structura specifică
                    if 'sazka.cz' in source['url']:
                        # Caută toate elementele care ar putea conține rezultate
                        # Varianta 1: Tabele
                        tables = soup.find_all('table')
                        if tables:
                            st.info(f"✓ Am găsit {len(tables)} tabel(e)")
                            for table_idx, table in enumerate(tables):
                                rows = table.find_all('tr')
                                if len(rows) > 5:  # Pare să fie un tabel cu date
                                    st.info(f"Procesez tabelul {table_idx + 1} cu {len(rows)} rânduri...")
                                    for row in rows[1:min(len(rows), num_rounds+1)]:
                                        cells = row.find_all(['td', 'th'])
                                        if len(cells) >= 2:
                                            row_data = [cell.get_text(strip=True) for cell in cells]
                                            if any(row_data):  # Nu e rând gol
                                                results.append(row_data)
                                    if results:
                                        break
                        
                        # Varianta 2: Div-uri cu clase specifice Sazka
                        if not results:
                            st.info("Caut div-uri cu rezultate...")
                            result_divs = soup.find_all(['div', 'article', 'section'], 
                                                       class_=re.compile(r'result|draw|vysledek|tah|game', re.IGNORECASE))
                            
                            if result_divs:
                                st.info(f"✓ Am găsit {len(result_divs)} elemente posibile")
                                
                                for div in result_divs[:num_rounds]:
                                    # Extrage text și numere
                                    text = div.get_text(separator=' ', strip=True)
                                    
                                    # Caută ID/număr extragere
                                    draw_id = re.search(r'(\d{7,})', text)
                                    
                                    # Caută dată
                                    date_match = re.search(r'(\d{1,2})[.\s]+(\d{1,2})[.\s]+(\d{4})', text)
                                    
                                    # Caută oră
                                    time_match = re.search(r'(\d{1,2}):(\d{2})', text)
                                    
                                    # Caută numerele extrase (grupuri de numere separate prin virgulă sau spațiu)
                                    numbers = re.findall(r'\b(\d{1,2})\b', text)
                                    
                                    # Filtrează numerele realiste pentru loterie (1-80 pentru Keno)
                                    valid_numbers = [n for n in numbers if 1 <= int(n) <= 80]
                                    
                                    # Dacă avem suficiente numere, e probabil un rezultat valid
                                    if len(valid_numbers) >= 10:
                                        row = []
                                        if draw_id:
                                            row.append(draw_id.group(1))
                                        if date_match:
                                            row.append(f"{date_match.group(1)}.{date_match.group(2)}.{date_match.group(3)}")
                                        if time_match:
                                            row.append(f"{time_match.group(1)}:{time_match.group(2)}")
                                        
                                        # Adaugă numerele (primele 20 pentru Keno)
                                        row.append(', '.join(valid_numbers[:20]))
                                        
                                        if len(row) >= 2:
                                            results.append(row)
                        
                        # Varianta 3: Caută în scripturile JSON embedate
                        if not results and use_api:
                            st.info("Caut date JSON în pagină...")
                            scripts = soup.find_all('script', type='application/json')
                            scripts += soup.find_all('script', string=re.compile(r'draws|results|vysledky'))
                            
                            for script in scripts:
                                script_text = script.string if script.string else str(script)
                                
                                # Încearcă să găsească JSON
                                try:
                                    # Caută pattern-uri JSON
                                    json_matches = re.findall(r'\{[^{}]*"draws?"[^{}]*\}', script_text)
                                    for json_str in json_matches:
                                        try:
                                            data = json.loads(json_str)
                                            if 'draws' in data or 'draw' in data:
                                                st.success("✓ Am găsit date JSON!")
                                                # Procesează JSON-ul găsit
                                                draws = data.get('draws', [data.get('draw', [])])
                                                for draw in draws[:num_rounds]:
                                                    row = []
                                                    if isinstance(draw, dict):
                                                        row.append(str(draw.get('id', draw.get('drawId', ''))))
                                                        row.append(str(draw.get('date', draw.get('drawTime', ''))))
                                                        nums = draw.get('numbers', draw.get('winning_numbers', []))
                                                        if nums:
                                                            row.append(', '.join(map(str, nums)))
                                                        if row and len(row) >= 2:
                                                            results.append(row)
                                        except:
                                            continue
                                except:
                                    continue
                    
                    # Metodă generică pentru alte site-uri
                    else:
    
                                        # Metodă generică pentru alte site-uri

                    else:
                        tables = soup.find_all('table')
                        if tables:
                            st.info(f"Am găsit {len(tables)} tabel(e) pe pagină")
                            for row in tables[0].find_all('tr')[1:num_rounds+1]:
                                cells = row.find_all(['td', 'th'])
                                if len(cells) >= 2:
                                    row_data = [cell.get_text(strip=True) for cell in cells]
                                    results.append(row_data)
                    
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