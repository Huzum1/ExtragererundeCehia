import streamlit as st
import pandas as pd
import io
from datetime import datetime
from collections import Counter

st.set_page_config(
    page_title="Loteria Cehia 12/66 - Manager Runde",
    page_icon="🎰",
    layout="wide"
)

# CSS customizat
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 2rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .stat-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        text-align: center;
    }
    .stat-value {
        font-size: 3rem;
        font-weight: bold;
        margin: 0;
    }
    .stat-label {
        font-size: 1.2rem;
        margin-top: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="main-header">
    <h1>🎰 Loteria Cehia 12/66</h1>
    <h3>Manager Runde - Identificare Duplicate</h3>
</div>
""", unsafe_allow_html=True)

# Inițializare session state
if 'runde_df' not in st.session_state:
    st.session_state.runde_df = None
if 'all_numbers' not in st.session_state:
    st.session_state.all_numbers = []

# Sidebar
with st.sidebar:
    st.header("ℹ️ Informații")
    st.markdown("""
    ### Format așteptat:
    - **12 numere** per rundă
    - Interval: **1-66**
    - Separate prin: virgulă, spațiu sau tab
    
    ### Tipuri fișiere:
    - CSV (.csv)
    - Excel (.xlsx, .xls)
    - Text (.txt)
    """)
    
    st.markdown("---")
    
    if st.session_state.runde_df is not None:
        df = st.session_state.runde_df
        unique_count = df['runda_unica'].sum()
        duplicate_count = len(df) - unique_count
        
        st.metric("📊 Total Runde", len(df))
        st.metric("✅ Runde Unice", unique_count)
        st.metric("❌ Runde Duplicate", duplicate_count)
        
        if duplicate_count > 0:
            percent = (duplicate_count / len(df)) * 100
            st.warning(f"⚠️ {percent:.1f}% duplicate")

# Tab-uri principale
tab1, tab2, tab3, tab4 = st.tabs(["📤 Import Runde", "📊 Analiză", "📈 Statistici", "💾 Export"])

# ===================== TAB 1: IMPORT =====================
with tab1:
    st.header("Import Runde")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        upload_file = st.file_uploader(
            "Încarcă fișierul cu runde",
            type=['csv', 'xlsx', 'xls', 'txt'],
            help="Acceptă CSV, Excel sau fișiere text"
        )
    
    with col2:
        separator = st.selectbox(
            "Separator numere",
            options=[',', ' ', '\t', ';', '|'],
            format_func=lambda x: {
                ',': 'Virgulă (,)',
                ' ': 'Spațiu ( )',
                '\t': 'Tab (\\t)',
                ';': 'Punct și virgulă (;)',
                '|': 'Pipe (|)'
            }[x],
            help="Cum sunt separate numerele în fișier"
        )
    
    if upload_file is not None:
        try:
            # Citire fișier
            if upload_file.name.endswith('.csv'):
                content = upload_file.read().decode('utf-8')
                lines = content.strip().split('\n')
            elif upload_file.name.endswith(('.xlsx', '.xls')):
                df_temp = pd.read_excel(upload_file, header=None)
                lines = df_temp.apply(lambda x: separator.join(map(str, x.dropna().astype(int))), axis=1).tolist()
            else:  # txt
                content = upload_file.read().decode('utf-8')
                lines = content.strip().split('\n')
            
            st.info(f"📁 S-au citit **{len(lines)}** linii din fișier")
            
            # Preview primele 5 linii
            with st.expander("👁️ Preview primele 5 linii"):
                for i, line in enumerate(lines[:5], 1):
                    st.code(f"Linia {i}: {line[:100]}")
            
            if st.button("🔄 Procesează Rundele", type="primary", use_container_width=True):
                with st.spinner("Se procesează rundele..."):
                    progress_bar = st.progress(0)
                    runde_list = []
                    erori = []
                    
                    total_lines = len(lines)
                    
                    for idx, line in enumerate(lines, 1):
                        # Update progress
                        if idx % 100 == 0:
                            progress_bar.progress(idx / total_lines)
                        
                        line = line.strip()
                        if not line:
                            continue
                        
                        # Separă numerele
                        if separator == ' ':
                            numere = [n.strip() for n in line.split() if n.strip()]
                        else:
                            numere = [n.strip() for n in line.split(separator) if n.strip()]
                        
                        # Validare
                        try:
                            numere_int = [int(n) for n in numere]
                            
                            if len(numere_int) != 12:
                                erori.append(f"Runda {idx}: {len(numere_int)} numere (se așteaptă 12)")
                                continue
                            
                            if any(n < 1 or n > 66 for n in numere_int):
                                erori.append(f"Runda {idx}: Numere în afara intervalului 1-66")
                                continue
                            
                            if len(set(numere_int)) != 12:
                                erori.append(f"Runda {idx}: Numere duplicate în aceeași rundă")
                                continue
                            
                            # Sortează numerele pentru comparație
                            numere_sortate = tuple(sorted(numere_int))
                            runde_list.append({
                                'runda_nr': idx,
                                'numere': numere_sortate,
                                'numere_str': ', '.join(map(str, numere_sortate)),
                                'numere_originale': ', '.join(map(str, numere_int))
                            })
                            
                        except ValueError:
                            erori.append(f"Runda {idx}: Valori invalide - {line}")
                    
                    progress_bar.progress(1.0)
                    
                    # Creează DataFrame
                    if runde_list:
                        df = pd.DataFrame(runde_list)
                        
                        # Identifică duplicate
                        df['runda_unica'] = ~df.duplicated(subset=['numere'], keep='first')
                        df['nr_aparitii'] = df.groupby('numere')['numere'].transform('count')
                        
                        # Salvează în session state
                        st.session_state.runde_df = df
                        
                        # Salvează toate numerele pentru statistici
                        all_nums = []
                        for numere in df['numere']:
                            all_nums.extend(numere)
                        st.session_state.all_numbers = all_nums
                        
                        st.success(f"✅ **{len(df)}** runde procesate cu succes!")
                        
                        # Afișează statistici
                        col1, col2, col3 = st.columns(3)
                        
                        unique_count = df['runda_unica'].sum()
                        duplicate_count = len(df) - unique_count
                        
                        with col1:
                            st.markdown(f"""
                            <div class="stat-card">
                                <div class="stat-value">{len(df)}</div>
                                <div class="stat-label">Total Runde</div>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        with col2:
                            st.markdown(f"""
                            <div class="stat-card">
                                <div class="stat-value">{unique_count}</div>
                                <div class="stat-label">Runde Unice</div>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        with col3:
                            st.markdown(f"""
                            <div class="stat-card">
                                <div class="stat-value">{duplicate_count}</div>
                                <div class="stat-label">Runde Duplicate</div>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        if erori:
                            with st.expander(f"⚠️ {len(erori)} erori de procesare (click pentru detalii)"):
                                for eroare in erori[:100]:  # Arată primele 100
                                    st.warning(eroare)
                                if len(erori) > 100:
                                    st.info(f"... și încă {len(erori) - 100} erori")
                    else:
                        st.error("❌ Nu s-au putut procesa runde valide")
                        
        except Exception as e:
            st.error(f"❌ Eroare la citirea fișierului: {str(e)}")

# ===================== TAB 2: ANALIZĂ =====================
with tab2:
    st.header("Analiză Runde")
    
    if st.session_state.runde_df is None:
        st.info("👆 Încarcă un fișier în tab-ul **Import** pentru a vedea analiza")
    else:
        df = st.session_state.runde_df
        
        # Filtre
        col1, col2 = st.columns([2, 1])
        
        with col1:
            show_filter = st.radio(
                "Afișează:",
                ["Toate rundele", "Doar runde unice", "Doar runde duplicate"],
                horizontal=True
            )
        
        with col2:
            search_num = st.number_input(
                "Caută număr:",
                min_value=1,
                max_value=66,
                value=None,
                help="Găsește runde care conțin acest număr"
            )
        
        # Filtrare
        df_filtered = df.copy()
        
        if show_filter == "Doar runde unice":
            df_filtered = df_filtered[df_filtered['runda_unica']]
        elif show_filter == "Doar runde duplicate":
            df_filtered = df_filtered[~df_filtered['runda_unica']]
        
        if search_num is not None:
            df_filtered = df_filtered[df_filtered['numere'].apply(lambda x: search_num in x)]
        
        st.write(f"**{len(df_filtered)}** runde afișate din **{len(df)}** total")
        
        # Afișare tabel
        df_display = df_filtered[['runda_nr', 'numere_str', 'runda_unica', 'nr_aparitii']].copy()
        df_display.columns = ['Nr. Rundă', 'Numere (sortate)', 'Unică', 'Apariții']
        df_display['Unică'] = df_display['Unică'].map({True: '✅', False: '❌'})
        
        st.dataframe(
            df_display,
            use_container_width=True,
            height=600,
            hide_index=True
        )
        
        # Statistici rapide
        if not df_filtered.empty:
            st.markdown("---")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                avg_appearances = df_filtered['nr_aparitii'].mean()
                st.metric("Media apariții", f"{avg_appearances:.2f}")
            
            with col2:
                max_appearances = df_filtered['nr_aparitii'].max()
                st.metric("Max apariții", int(max_appearances))
            
            with col3:
                unique_percent = (df_filtered['runda_unica'].sum() / len(df_filtered)) * 100
                st.metric("% Unice", f"{unique_percent:.1f}%")

# ===================== TAB 3: STATISTICI =====================
with tab3:
    st.header("📈 Statistici și Analiză Frecvență")
    
    if st.session_state.runde_df is None:
        st.info("👆 Încarcă un fișier în tab-ul **Import** pentru a vedea statisticile")
    else:
        df = st.session_state.runde_df
        all_numbers = st.session_state.all_numbers
        
        # Frecvență numere
        freq_counter = Counter(all_numbers)
        freq_df = pd.DataFrame([
            {'Număr': num, 'Frecvență': freq_counter.get(num, 0)}
            for num in range(1, 67)
        ]).sort_values('Frecvență', ascending=False)
        
        # Top statistici
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🏆 Top 20 Cele Mai Frecvente")
            top_20 = freq_df.head(20)
            
            # Bar chart
            st.bar_chart(top_20.set_index('Număr')['Frecvență'], height=400)
            
            # Tabel top 20
            st.dataframe(
                top_20.reset_index(drop=True),
                use_container_width=True,
                hide_index=True
            )
        
        with col2:
            st.subheader("📉 Top 20 Cele Mai Rare")
            bottom_20 = freq_df.tail(20).sort_values('Frecvență', ascending=True)
            
            # Bar chart
            st.bar_chart(bottom_20.set_index('Număr')['Frecvență'], height=400)
            
            # Tabel bottom 20
            st.dataframe(
                bottom_20.reset_index(drop=True),
                use_container_width=True,
                hide_index=True
            )
        
        st.markdown("---")
        
        # Distribuție completă
        st.subheader("📊 Distribuție Completă (1-66)")
        
        # Heatmap-style display
        cols_per_row = 11
        rows = []
        for i in range(0, 66, cols_per_row):
            row = freq_df.iloc[i:i+cols_per_row]
            rows.append(row)
        
        for row_df in rows:
            cols = st.columns(len(row_df))
            for idx, (_, row) in enumerate(row_df.iterrows()):
                with cols[idx]:
                    num = row['Număr']
                    freq = row['Frecvență']
                    # Color coding based on frequency
                    if freq >= freq_df['Frecvență'].quantile(0.75):
                        color = "#28a745"  # Verde
                    elif freq >= freq_df['Frecvență'].quantile(0.5):
                        color = "#ffc107"  # Galben
                    elif freq >= freq_df['Frecvență'].quantile(0.25):
                        color = "#fd7e14"  # Portocaliu
                    else:
                        color = "#dc3545"  # Roșu
                    
                    st.markdown(f"""
                    <div style='background-color: {color}; color: white; 
                                padding: 10px; border-radius: 5px; text-align: center;
                                margin: 2px;'>
                        <strong>{num}</strong><br>
                        <small>{freq}</small>
                    </div>
                    """, unsafe_allow_html=True)
        
        # Legendă
        st.markdown("---")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown("🟢 **Foarte frecvent** (top 25%)")
        with col2:
            st.markdown("🟡 **Mediu-frecvent** (25-50%)")
        with col3:
            st.markdown("🟠 **Mediu-rar** (50-75%)")
        with col4:
            st.markdown("🔴 **Rar** (bottom 25%)")

# ===================== TAB 4: EXPORT =====================
with tab4:
    st.header("💾 Export Runde")
    
    if st.session_state.runde_df is None:
        st.info("👆 Încarcă un fișier în tab-ul **Import** pentru a exporta date")
    else:
        df = st.session_state.runde_df
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            export_option = st.radio(
                "Ce dorești să exporți?",
                ["Doar runde unice", "Toate rundele", "Doar runde duplicate"],
                help="Alege ce tip de runde vrei în fișierul exportat"
            )
        
        with col2:
            include_stats = st.checkbox(
                "Include statistici",
                value=True,
                help="Adaugă coloane cu informații despre unicitate și apariții"
            )
        
        # Pregătire export
        if export_option == "Doar runde unice":
            df_export = df[df['runda_unica']].copy()
        elif export_option == "Doar runde duplicate":
            df_export = df[~df['runda_unica']].copy()
        else:
            df_export = df.copy()
        
        st.info(f"**Se vor exporta {len(df_export)} runde**")
        
        # Preview
        with st.expander("👁️ Preview date export"):
            st.dataframe(
                df_export.head(10),
                use_container_width=True,
                hide_index=True
            )
        
        st.markdown("---")
        
        # Export CSV
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📄 Export CSV")
            
            if include_stats:
                csv_data = df_export[['runda_nr', 'numere_str', 'runda_unica', 'nr_aparitii']].copy()
                csv_data.columns = ['Nr_Runda', 'Numere', 'Unica', 'Nr_Aparitii']
            else:
                csv_data = df_export[['runda_nr', 'numere_str']].copy()
                csv_data.columns = ['Nr_Runda', 'Numere']
            
            csv_buffer = io.StringIO()
            csv_data.to_csv(csv_buffer, index=False)
            
            st.download_button(
                label="📥 Descarcă CSV",
                data=csv_buffer.getvalue(),
                file_name=f"runde_loterie_{export_option.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col2:
            st.subheader("📊 Export Excel")
            
            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                if include_stats:
                    export_excel = df_export[['runda_nr', 'numere_str', 'runda_unica', 'nr_aparitii']].copy()
                    export_excel.columns = ['Nr_Runda', 'Numere', 'Unica', 'Nr_Aparitii']
                else:
                    export_excel = df_export[['runda_nr', 'numere_str']].copy()
                    export_excel.columns = ['Nr_Runda', 'Numere']
                
                export_excel.to_excel(writer, index=False, sheet_name='Runde')
                
                # Sheet cu statistici
                if include_stats:
                    stats_data = {
                        'Metric': ['Total Runde', 'Runde Unice', 'Runde Duplicate'],
                        'Valoare': [
                            len(df),
                            df['runda_unica'].sum(),
                            len(df) - df['runda_unica'].sum()
                        ]
                    }
                    stats_df = pd.DataFrame(stats_data)
                    stats_df.to_excel(writer, index=False, sheet_name='Statistici')
            
            st.download_button(
                label="📥 Descarcă Excel",
                data=excel_buffer.getvalue(),
                file_name=f"runde_loterie_{export_option.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray; padding: 20px;'>
    <p><strong>Loteria Cehia 12/66 - Manager Rund