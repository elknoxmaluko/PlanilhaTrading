import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date
import numpy as np
import json
import os

# Nome do arquivo para salvar os dados
DATA_FILE = "dados_apostas.json"


def convert_numpy_types(value):
    """Converte tipos numpy para tipos nativos do Python"""
    if isinstance(value, (np.integer, np.floating, np.bool_)):
        return value.item()
    elif isinstance(value, np.ndarray):
        return value.tolist()
    return value


def format_currency(value):
    """Formata valores como moeda"""
    try:
        return f"€{float(value):.2f}"
    except (ValueError, TypeError):
        return value


def format_percent(value):
    """Formata valores como porcentagem"""
    try:
        return f"{float(value):.2f}%"
    except (ValueError, TypeError):
        return value


def carregar_dados():
    """Carrega os dados do arquivo JSON se existir"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                # Verifica se o arquivo não está vazio
                if os.stat(DATA_FILE).st_size == 0:
                    return None

                dados = json.load(f)

                # Verifica se os dados têm a estrutura esperada
                if not all(key in dados for key in ['equipas', 'campeonatos', 'estrategias', 'tags', 'mensal']):
                    st.warning("Estrutura de dados inválida no arquivo. Criando nova estrutura.")
                    return None

                # Converter os DataFrames
                dados['equipas'] = pd.DataFrame(dados['equipas'])
                dados['campeonatos'] = pd.DataFrame(dados['campeonatos'])
                dados['estrategias'] = pd.DataFrame(dados['estrategias'])

                # Converter os DataFrames mensais
                for mes in dados['mensal']:
                    df = pd.DataFrame(dados['mensal'][mes])
                    if 'Data' in df.columns:
                        try:
                            df['Data'] = pd.to_datetime(df['Data']).dt.date
                        except:
                            df['Data'] = datetime.now().date()
                    dados['mensal'][mes] = df

                return dados
        except json.JSONDecodeError:
            st.warning("Arquivo de dados corrompido. Criando nova estrutura.")
            return None
        except Exception as e:
            st.error(f"Erro inesperado ao carregar dados: {str(e)}")
            return None
    return None


def salvar_dados():
    """Salva os dados no arquivo JSON"""
    try:
        # Função para converter objetos date para string
        def date_converter(obj):
            if isinstance(obj, date):
                return obj.isoformat()
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

        dados_para_salvar = {
            'equipas': st.session_state.dados['equipas'].to_dict(),
            'campeonatos': st.session_state.dados['campeonatos'].to_dict(),
            'estrategias': st.session_state.dados['estrategias'].to_dict(),
            'tags': st.session_state.dados['tags'],
            'mensal': {}
        }

        # Converter DataFrames mensais, tratando as datas
        for mes in st.session_state.dados['mensal']:
            df = st.session_state.dados['mensal'][mes].copy()
            if 'Data' in df.columns:
                df['Data'] = df['Data'].astype(str)  # Converte datas para string
            dados_para_salvar['mensal'][mes] = df.to_dict()

        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(dados_para_salvar, f, default=date_converter, ensure_ascii=False, indent=4)
    except Exception as e:
        st.error(f"Erro ao salvar dados: {str(e)}")


# Initialize data structure
if 'dados' not in st.session_state:
    dados_carregados = carregar_dados()
    meses = [
        'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
        'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
    ]

    if dados_carregados:
        st.session_state.dados = dados_carregados
    else:
        st.session_state.dados = {
            'equipas': pd.DataFrame(columns=['Nome']),
            'campeonatos': pd.DataFrame(columns=['Nome', 'Temporada', 'Jogos']),
            'estrategias': pd.DataFrame(columns=['Nome', 'Descrição', 'Equipa', 'Tags']),
            'tags': ["Normal", "Arbitrage", "Value Bet", "Sure Bet"],
            'mensal': {
                mes: pd.DataFrame(columns=[
                    'Data', 'Competição', 'Casa', 'Visitante',
                    'Estrategia', 'Tag', 'Stake', 'Profit/Loss', '% Stake'
                ])
                for mes in meses
            }
        }


def calcular_stats_campeonato(nome_campeonato):
    """Calculate statistics for a specific championship"""
    stats = {
        'total_jogos': 0,
        'total_stake': 0,
        'total_profit': 0,
        'greens': 0,
        'reds': 0,
        'roi': 0
    }

    for mes in st.session_state.dados['mensal'].values():
        jogos_camp = mes[mes['Competição'] == nome_campeonato]
        if not jogos_camp.empty:
            stats['total_jogos'] += len(jogos_camp)
            stats['total_stake'] += jogos_camp['Stake'].sum()
            stats['total_profit'] += jogos_camp['Profit/Loss'].sum()
            stats['greens'] += len(jogos_camp[jogos_camp['Profit/Loss'] >= 0])
            stats['reds'] += len(jogos_camp[jogos_camp['Profit/Loss'] < 0])

    if stats['total_stake'] > 0:
        stats['roi'] = (stats['total_profit'] / stats['total_stake']) * 100

    # Converter valores numpy para tipos nativos do Python
    return {k: convert_numpy_types(v) for k, v in stats.items()}


def calcular_stats_equipa(nome_equipa):
    """Calculate statistics for a specific team"""
    stats = {
        'Mercados': 0,
        'Greens': 0,
        'Reds': 0,
        'Stake Total': 0,
        'Profit/Loss': 0,
        'ROI (%)': 0
    }

    for mes in st.session_state.dados['mensal'].values():
        jogos_equipa = mes[(mes['Casa'] == nome_equipa) | (mes['Visitante'] == nome_equipa)]
        if not jogos_equipa.empty:
            stats['Mercados'] += len(jogos_equipa)
            stats['Stake Total'] += jogos_equipa['Stake'].sum()
            stats['Profit/Loss'] += jogos_equipa['Profit/Loss'].sum()
            stats['Greens'] += len(jogos_equipa[jogos_equipa['Profit/Loss'] >= 0])
            stats['Reds'] += len(jogos_equipa[jogos_equipa['Profit/Loss'] < 0])

    if stats['Stake Total'] > 0:
        stats['ROI (%)'] = (stats['Profit/Loss'] / stats['Stake Total']) * 100

    # Converter valores numpy para tipos nativos do Python
    return {k: convert_numpy_types(v) for k, v in stats.items()}


def atualizar_campeonatos():
    """Update championship data based on games"""
    campeonatos = st.session_state.dados['campeonatos'].copy()

    for idx, campeonato in campeonatos.iterrows():
        stats = calcular_stats_campeonato(campeonato['Nome'])
        st.session_state.dados['campeonatos'].at[idx, 'Jogos'] = stats['total_jogos']

    salvar_dados()


def adicionar_equipa_se_nao_existir(nome_equipa):
    """Automatically add team if it doesn't exist"""
    if nome_equipa and nome_equipa not in st.session_state.dados['equipas']['Nome'].tolist():
        nova_equipa = pd.DataFrame([{'Nome': nome_equipa}])
        st.session_state.dados['equipas'] = pd.concat(
            [st.session_state.dados['equipas'], nova_equipa],
            ignore_index=True
        )
        salvar_dados()


def adicionar_campeonato_se_nao_existir(nome_campeonato):
    """Automatically add championship if it doesn't exist"""
    if nome_campeonato and nome_campeonato not in st.session_state.dados['campeonatos']['Nome'].tolist():
        novo_campeonato = pd.DataFrame([{
            'Nome': nome_campeonato,
            'Temporada': datetime.now().year,
            'Jogos': 0
        }])
        st.session_state.dados['campeonatos'] = pd.concat(
            [st.session_state.dados['campeonatos'], novo_campeonato],
            ignore_index=True
        )
        salvar_dados()


def show_painel():
    st.title("🏠 Painel Principal")
    atualizar_campeonatos()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total de Equipas", len(st.session_state.dados['equipas']))
    with col2:
        st.metric("Total de Campeonatos", len(st.session_state.dados['campeonatos']))
    with col3:
        st.metric("Total de Estratégias", len(st.session_state.dados['estrategias']))

    st.subheader("📊 Desempenho Mensal")
    performance = []
    total_stake = total_profit = 0

    for month, df in st.session_state.dados['mensal'].items():
        if not df.empty:
            stake = df['Stake'].sum()
            profit = df['Profit/Loss'].sum()
            roi = (profit / stake * 100) if stake != 0 else 0

            performance.append({
                'Mês': month,
                'Stake Total': stake,
                'Profit Total': profit,
                'ROI (%)': roi
            })

            total_stake += stake
            total_profit += profit

    total_roi = (total_profit / total_stake * 100) if total_stake != 0 else 0
    performance.append({
        'Mês': 'TOTAL',
        'Stake Total': total_stake,
        'Profit Total': total_profit,
        'ROI (%)': total_roi
    })

    df_perf = pd.DataFrame(performance)

    # Formatar valores
    df_perf['Stake Total'] = df_perf['Stake Total'].apply(format_currency)
    df_perf['Profit Total'] = df_perf['Profit Total'].apply(
        lambda x: format_currency(x).replace('€', '€+') if x >= 0 else format_currency(x)
    )
    df_perf['ROI (%)'] = df_perf['ROI (%)'].apply(format_percent)

    st.dataframe(
        df_perf,
        hide_index=True
    )

    st.subheader("📈 Evolução do ROI Mensal")
    if len(df_perf) > 1:
        df_plot = df_perf[df_perf['Mês'] != 'TOTAL'].copy()
        df_plot['ROI (%)'] = df_plot['ROI (%)'].str.replace('%', '').astype(float)

        fig = px.line(
            df_plot,
            x='Mês', y='ROI (%)',
            title="ROI por Mês",
            markers=True
        )
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("📅 Últimos Jogos")
    all_games = []
    for month, df in st.session_state.dados['mensal'].items():
        if not df.empty:
            all_games.extend(df.to_dict('records'))

    if all_games:
        df_games = pd.DataFrame(all_games).sort_values('Data', ascending=False).head(5)
        df_games['Stake'] = df_games['Stake'].apply(format_currency)
        df_games['Profit/Loss'] = df_games['Profit/Loss'].apply(
            lambda x: format_currency(x).replace('€', '€+') if x >= 0 else format_currency(x)
        )
        df_games['% Stake'] = df_games['% Stake'].apply(format_percent)

        st.dataframe(df_games, hide_index=True)
    else:
        st.info("Nenhum jogo registrado ainda.")


def show_equipas():
    st.title("⚽ Equipas")

    col1, col2 = st.columns(2)

    # Seção para adicionar nova equipa (inicia fechada)
    with col1:
        with st.expander("➕ Adicionar Nova Equipa", expanded=False):
            with st.form("nova_equipa_form", clear_on_submit=True):
                new_name = st.text_input("Nome da Equipa*").strip()

                if st.form_submit_button("Adicionar"):
                    if not new_name:
                        st.error("O nome da equipa é obrigatório!")
                    elif new_name in st.session_state.dados['equipas']['Nome'].tolist():
                        st.warning("Esta equipa já existe!")
                    else:
                        nova_equipa = pd.DataFrame([{'Nome': new_name}])
                        st.session_state.dados['equipas'] = pd.concat(
                            [st.session_state.dados['equipas'], nova_equipa],
                            ignore_index=True
                        )
                        salvar_dados()
                        st.success("Equipa adicionada com sucesso!")
                        st.rerun()

    # Seção para editar/remover equipas (inicia fechada)
    with col2:
        with st.expander("✏️ Editar/Remover Equipas", expanded=False):
            if not st.session_state.dados['equipas'].empty:
                equipa_selecionada = st.selectbox(
                    "Selecione uma equipa para editar",
                    options=st.session_state.dados['equipas']['Nome'].tolist(),
                    key="select_edit_equipa"
                )

                idx = st.session_state.dados['equipas'][
                    st.session_state.dados['equipas']['Nome'] == equipa_selecionada
                    ].index[0]

                with st.form("editar_equipa_form"):
                    novo_nome = st.text_input(
                        "Novo nome",
                        value=equipa_selecionada,
                        key="edit_equipa_name"
                    )

                    col_save, col_del = st.columns(2)
                    with col_save:
                        if st.form_submit_button("💾 Salvar Alterações"):
                            if not novo_nome:
                                st.error("O nome não pode ser vazio!")
                            elif novo_nome != equipa_selecionada and novo_nome in st.session_state.dados['equipas'][
                                'Nome'].tolist():
                                st.warning("Já existe uma equipa com este nome!")
                            else:
                                # Atualiza o nome da equipa
                                st.session_state.dados['equipas'].at[idx, 'Nome'] = novo_nome

                                # Atualiza todos os jogos que referenciam esta equipa
                                for mes in st.session_state.dados['mensal']:
                                    df_mes = st.session_state.dados['mensal'][mes]
                                    df_mes.loc[df_mes['Casa'] == equipa_selecionada, 'Casa'] = novo_nome
                                    df_mes.loc[df_mes['Visitante'] == equipa_selecionada, 'Visitante'] = novo_nome

                                salvar_dados()
                                st.success("Equipa atualizada com sucesso!")
                                st.rerun()

                    with col_del:
                        if st.form_submit_button("🗑️ Remover Equipa"):
                            # Verifica se a equipa está sendo usada em algum jogo
                            em_uso = False
                            for mes in st.session_state.dados['mensal']:
                                df_mes = st.session_state.dados['mensal'][mes]
                                if (equipa_selecionada in df_mes['Casa'].values or
                                        equipa_selecionada in df_mes['Visitante'].values):
                                    em_uso = True
                                    break

                            if em_uso:
                                st.warning("Esta equipa está em uso e não pode ser removida!")
                            else:
                                st.session_state.dados['equipas'] = st.session_state.dados['equipas'].drop(
                                    idx).reset_index(drop=True)
                                salvar_dados()
                                st.success("Equipa removida com sucesso!")
                                st.rerun()
            else:
                st.info("Nenhuma equipa cadastrada para edição")

    # Seção de estatísticas (permanece igual)
    st.subheader("📋 Estatísticas das Equipas")
    if not st.session_state.dados['equipas'].empty:
        equipas_stats = []

        for _, equipa in st.session_state.dados['equipas'].iterrows():
            stats = calcular_stats_equipa(equipa['Nome'])
            equipas_stats.append({
                'Equipa': equipa['Nome'],
                **stats
            })

        df_stats = pd.DataFrame(equipas_stats)

        # Formatar valores
        df_stats['Stake Total'] = df_stats['Stake Total'].apply(format_currency)
        df_stats['Profit/Loss'] = df_stats['Profit/Loss'].apply(
            lambda x: format_currency(x).replace('€', '€+') if x >= 0 else format_currency(x)
        )
        df_stats['ROI (%)'] = df_stats['ROI (%)'].apply(format_percent)

        st.dataframe(
            df_stats,
            column_config={
                "Greens": st.column_config.ProgressColumn(
                    "Greens",
                    format="%d",
                    min_value=0,
                    max_value=int(df_stats['Mercados'].max()) if not df_stats.empty else 0
                ),
                "Reds": st.column_config.ProgressColumn(
                    "Reds",
                    format="%d",
                    min_value=0,
                    max_value=int(df_stats['Mercados'].max()) if not df_stats.empty else 0
                )
            },
            hide_index=True,
            use_container_width=True
        )

        st.subheader("📊 Performance por Equipa")
        if len(df_stats) > 1:
            df_plot = df_stats.copy()
            df_plot['Profit/Loss'] = df_plot['Profit/Loss'].str.replace('€+', '').str.replace('€', '').astype(float)
            df_plot['ROI (%)'] = df_plot['ROI (%)'].str.replace('%', '').astype(float)

            fig = px.bar(
                df_plot.sort_values('Profit/Loss', ascending=False),
                x='Equipa',
                y='Profit/Loss',
                color='ROI (%)',
                title="Lucro/Prejuízo por Equipa",
                labels={'Profit/Loss': 'Lucro/Prejuízo (€)'},
                color_continuous_scale='RdYlGn'
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Nenhuma equipa cadastrada ainda.")


def show_campeonatos():
    st.title("🏆 Campeonatos")
    atualizar_campeonatos()

    col_add, col_edit = st.columns(2)

    # Seção para adicionar novo campeonato (inicia fechada)
    with col_add:
        with st.expander("➕ Adicionar Novo Campeonato", expanded=False):
            with st.form("novo_campeonato_form", clear_on_submit=True):
                name = st.text_input("Nome do Campeonato*").strip()
                season = st.text_input("Temporada*", str(datetime.now().year)).strip()

                if st.form_submit_button("Salvar") and name and season:
                    if name in st.session_state.dados['campeonatos']['Nome'].tolist():
                        st.warning("Este campeonato já existe!")
                    else:
                        new_comp = pd.DataFrame([{
                            'Nome': name,
                            'Temporada': season,
                            'Jogos': 0
                        }])
                        st.session_state.dados['campeonatos'] = pd.concat(
                            [st.session_state.dados['campeonatos'], new_comp],
                            ignore_index=True
                        )
                        st.success("Campeonato adicionado com sucesso!")
                        salvar_dados()
                        st.rerun()

    # Seção para editar/remover campeonatos (inicia fechada)
    with col_edit:
        with st.expander("✏️ Editar/Remover Campeonatos", expanded=False):
            if not st.session_state.dados['campeonatos'].empty:
                campeonato_selecionado = st.selectbox(
                    "Selecione um campeonato",
                    st.session_state.dados['campeonatos']['Nome'].tolist(),
                    key="select_edit_camp"
                )

                idx = st.session_state.dados['campeonatos'][
                    st.session_state.dados['campeonatos']['Nome'] == campeonato_selecionado
                    ].index[0]

                with st.form("editar_campeonato_form"):
                    novo_nome = st.text_input(
                        "Novo nome",
                        value=campeonato_selecionado,
                        key="edit_camp_name"
                    )
                    nova_temporada = st.text_input(
                        "Nova temporada",
                        value=st.session_state.dados['campeonatos'].loc[idx, 'Temporada'],
                        key="edit_camp_season"
                    )

                    col_save, col_del = st.columns(2)
                    with col_save:
                        if st.form_submit_button("💾 Salvar Alterações"):
                            if not novo_nome:
                                st.error("O nome não pode ser vazio!")
                            elif novo_nome != campeonato_selecionado and novo_nome in \
                                    st.session_state.dados['campeonatos']['Nome'].tolist():
                                st.warning("Já existe um campeonato com este nome!")
                            else:
                                # Atualiza o campeonato
                                st.session_state.dados['campeonatos'].at[idx, 'Nome'] = novo_nome
                                st.session_state.dados['campeonatos'].at[idx, 'Temporada'] = nova_temporada

                                # Atualiza todos os jogos que referenciam este campeonato
                                for mes in st.session_state.dados['mensal']:
                                    df_mes = st.session_state.dados['mensal'][mes]
                                    df_mes.loc[df_mes['Competição'] == campeonato_selecionado, 'Competição'] = novo_nome

                                salvar_dados()
                                st.success("Campeonato atualizado com sucesso!")
                                st.rerun()

                    with col_del:
                        if st.form_submit_button("🗑️ Remover"):
                            # Verifica se o campeonato está sendo usado em algum jogo
                            em_uso = False
                            for mes in st.session_state.dados['mensal']:
                                if campeonato_selecionado in st.session_state.dados['mensal'][mes]['Competição'].values:
                                    em_uso = True
                                    break

                            if em_uso:
                                st.warning("Este campeonato está em uso e não pode ser removido!")
                            else:
                                st.session_state.dados['campeonatos'] = st.session_state.dados['campeonatos'].drop(idx)
                                salvar_dados()
                                st.success("Campeonato removido com sucesso!")
                                st.rerun()
            else:
                st.info("Nenhum campeonato cadastrado para edição")

    # Seção de estatísticas (mantida igual)
    st.subheader("📋 Estatísticas dos Campeonatos")
    if not st.session_state.dados['campeonatos'].empty:
        campeonatos_stats = []

        for _, camp in st.session_state.dados['campeonatos'].iterrows():
            stats = calcular_stats_campeonato(camp['Nome'])
            campeonatos_stats.append({
                'Campeonato': camp['Nome'],
                'Temporada': camp['Temporada'],
                **stats
            })

        df_stats = pd.DataFrame(campeonatos_stats)

        # Formatar valores
        df_stats['total_stake'] = df_stats['total_stake'].apply(format_currency)
        df_stats['total_profit'] = df_stats['total_profit'].apply(
            lambda x: format_currency(x).replace('€', '€+') if x >= 0 else format_currency(x)
        )
        df_stats['roi'] = df_stats['roi'].apply(format_percent)

        st.dataframe(
            df_stats,
            column_config={
                "greens": st.column_config.ProgressColumn(
                    "Greens",
                    format="%d",
                    min_value=0,
                    max_value=int(df_stats['total_jogos'].max()) if not df_stats.empty else 0
                ),
                "reds": st.column_config.ProgressColumn(
                    "Reds",
                    format="%d",
                    min_value=0,
                    max_value=int(df_stats['total_jogos'].max()) if not df_stats.empty else 0
                )
            },
            hide_index=True,
            use_container_width=True
        )

        st.subheader("📊 Performance por Campeonato")
        if len(df_stats) > 1:
            df_plot = df_stats.copy()
            df_plot['total_profit'] = df_plot['total_profit'].str.replace('€+', '').str.replace('€', '').astype(float)
            df_plot['roi'] = df_plot['roi'].str.replace('%', '').astype(float)

            fig = px.bar(
                df_plot.sort_values('total_profit', ascending=False),
                x='Campeonato',
                y='total_profit',
                color='roi',
                title="Lucro/Prejuízo por Campeonato",
                labels={'total_profit': 'Lucro/Prejuízo (€)'},
                color_continuous_scale='RdYlGn'
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Nenhum campeonato cadastrado ainda.")


def show_estrategias():
    st.title("🧠 Estratégias e Análise de Performance")

    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 Estratégias",
        "📊 Tags",
        "📈 Desempenho das Estratégias",
        "🏷️ Desempenho das Tags"
    ])

    # Aba 1: Gestão de Estratégias
    with tab1:
        st.subheader("Gestão de Estratégias")

        col_add, col_edit = st.columns(2)

        # Formulário para adicionar nova estratégia (inicia fechado)
        with col_add:
            with st.expander("➕ Adicionar Nova Estratégia", expanded=False):
                with st.form("nova_estrategia_form", clear_on_submit=True):
                    new_name = st.text_input("Nome da Estratégia*", key="new_strat_name")
                    new_desc = st.text_area("Descrição", key="new_strat_desc")

                    if st.form_submit_button("Adicionar Estratégia"):
                        if not new_name:
                            st.error("O nome da estratégia é obrigatório!")
                        elif new_name in st.session_state.dados['estrategias']['Nome'].values:
                            st.warning("Esta estratégia já existe!")
                        else:
                            nova_estrategia = pd.DataFrame([{
                                'Nome': new_name,
                                'Descrição': new_desc,
                                'Equipa': '',
                                'Tags': ''
                            }])
                            st.session_state.dados['estrategias'] = pd.concat(
                                [st.session_state.dados['estrategias'], nova_estrategia],
                                ignore_index=True
                            )
                            salvar_dados()
                            st.success("Estratégia adicionada com sucesso!")
                            st.rerun()

        # Formulário para editar/remover estratégias (inicia fechado)
        with col_edit:
            with st.expander("✏️ Editar/Remover Estratégias", expanded=False):
                if not st.session_state.dados['estrategias'].empty:
                    estrategia_selecionada = st.selectbox(
                        "Selecione uma estratégia",
                        st.session_state.dados['estrategias']['Nome'].tolist(),
                        key="select_edit_strat"
                    )

                    idx = st.session_state.dados['estrategias'][
                        st.session_state.dados['estrategias']['Nome'] == estrategia_selecionada
                    ].index[0]

                    with st.form("editar_estrategia_form"):
                        edit_name = st.text_input(
                            "Nome",
                            value=st.session_state.dados['estrategias'].loc[idx, 'Nome'],
                            key="edit_strat_name"
                        )
                        edit_desc = st.text_area(
                            "Descrição",
                            value=st.session_state.dados['estrategias'].loc[idx, 'Descrição'],
                            key="edit_strat_desc"
                        )

                        col_save, col_del = st.columns(2)
                        with col_save:
                            if st.form_submit_button("💾 Salvar"):
                                if not edit_name:
                                    st.error("O nome não pode ser vazio!")
                                else:
                                    st.session_state.dados['estrategias'].loc[idx, 'Nome'] = edit_name
                                    st.session_state.dados['estrategias'].loc[idx, 'Descrição'] = edit_desc
                                    salvar_dados()
                                    st.success("Estratégia atualizada!")
                                    st.rerun()

                        with col_del:
                            if st.form_submit_button("🗑️ Remover"):
                                st.session_state.dados['estrategias'] = st.session_state.dados['estrategias'].drop(idx).reset_index(drop=True)
                                salvar_dados()
                                st.success("Estratégia removida!")
                                st.rerun()
                else:
                    st.info("Nenhuma estratégia cadastrada")

        # Lista de estratégias
        st.subheader("📋 Lista de Estratégias")
        if not st.session_state.dados['estrategias'].empty:
            st.dataframe(
                st.session_state.dados['estrategias'][['Nome', 'Descrição']],
                column_config={
                    "Nome": "Estratégia",
                    "Descrição": "Descrição"
                },
                hide_index=True,
                use_container_width=True
            )
        else:
            st.info("Nenhuma estratégia cadastrada ainda.")

    # Aba 2: Gestão de Tags
    with tab2:
        st.subheader("🏷️ Gestão de Tags")

        col_tag_add, col_tag_edit = st.columns(2)

        # Formulário para adicionar nova tag (inicia fechado)
        with col_tag_add:
            with st.expander("➕ Adicionar Nova Tag", expanded=False):
                with st.form("nova_tag_form", clear_on_submit=True):
                    new_tag = st.text_input("Nome da Nova Tag*", key="new_tag_name")

                    if st.form_submit_button("Adicionar Tag"):
                        if not new_tag:
                            st.error("O nome da tag é obrigatório!")
                        elif new_tag in st.session_state.dados['tags']:
                            st.warning("Esta tag já existe!")
                        else:
                            st.session_state.dados['tags'].append(new_tag.strip())
                            salvar_dados()
                            st.success(f"Tag '{new_tag}' adicionada com sucesso!")
                            st.rerun()

        # Formulário para editar/remover tags (inicia fechado)
        with col_tag_edit:
            with st.expander("✏️ Editar/Remover Tags", expanded=False):
                if st.session_state.dados['tags']:
                    tag_selecionada = st.selectbox(
                        "Selecione uma tag",
                        st.session_state.dados['tags'],
                        key="select_edit_tag"
                    )

                    with st.form("editar_tag_form"):
                        edit_tag = st.text_input(
                            "Novo nome",
                            value=tag_selecionada,
                            key="edit_tag_name"
                        )

                        col_tag_save, col_tag_del = st.columns(2)
                        with col_tag_save:
                            if st.form_submit_button("💾 Salvar"):
                                if not edit_tag:
                                    st.error("O nome não pode ser vazio!")
                                elif edit_tag in st.session_state.dados['tags'] and edit_tag != tag_selecionada:
                                    st.warning("Esta tag já existe!")
                                else:
                                    idx = st.session_state.dados['tags'].index(tag_selecionada)
                                    st.session_state.dados['tags'][idx] = edit_tag.strip()
                                    salvar_dados()
                                    st.success("Tag atualizada com sucesso!")
                                    st.rerun()

                        with col_tag_del:
                            if st.form_submit_button("🗑️ Remover"):
                                st.session_state.dados['tags'].remove(tag_selecionada)
                                salvar_dados()
                                st.success(f"Tag '{tag_selecionada}' removida!")
                                st.rerun()
                else:
                    st.info("Nenhuma tag cadastrada")

        # Visualização das tags
        st.subheader("📌 Tags Existentes")
        if st.session_state.dados['tags']:
            cols = st.columns(4)
            for i, tag in enumerate(st.session_state.dados['tags']):
                with cols[i % 4]:
                    st.markdown(
                        f"""<div style='
                            padding: 0.5rem;
                            border-radius: 0.5rem;
                            background-color: #f0f2f6;
                            margin-bottom: 0.5rem;
                            border-left: 5px solid #4e79a7;
                        '>
                        <b>{tag}</b>
                        </div>""",
                        unsafe_allow_html=True
                    )
        else:
            st.info("Nenhuma tag cadastrada ainda.")

    # Aba 3: Desempenho das Estratégias
    with tab3:
        st.subheader("📈 Desempenho por Estratégia")

        if not st.session_state.dados['estrategias'].empty:
            estrategias_stats = []
            for estrategia in st.session_state.dados['estrategias']['Nome'].unique():
                total_profit = 0
                total_stake = 0
                greens = 0
                reds = 0

                for mes in st.session_state.dados['mensal'].values():
                    if not mes.empty and 'Estrategia' in mes.columns:
                        jogos_estrategia = mes[mes['Estrategia'] == estrategia]
                        if not jogos_estrategia.empty:
                            total_profit += float(jogos_estrategia['Profit/Loss'].sum())
                            total_stake += float(jogos_estrategia['Stake'].sum())
                            greens += int(len(jogos_estrategia[jogos_estrategia['Profit/Loss'] >= 0]))
                            reds += int(len(jogos_estrategia[jogos_estrategia['Profit/Loss'] < 0]))

                roi = (total_profit / total_stake * 100) if total_stake != 0 else 0
                estrategias_stats.append({
                    'Estratégia': estrategia,
                    'Profit Total': total_profit,
                    'Stake Total': total_stake,
                    'ROI (%)': float(roi),
                    'Greens': greens,
                    'Reds': reds
                })

            if estrategias_stats:
                df_estrategias = pd.DataFrame(estrategias_stats)

                fig1 = px.bar(
                    df_estrategias.sort_values('Profit Total', ascending=False),
                    x='Estratégia',
                    y='Profit Total',
                    color='ROI (%)',
                    title="Lucro/Prejuízo por Estratégia",
                    color_continuous_scale='RdYlGn'
                )
                st.plotly_chart(fig1, use_container_width=True)

                st.subheader("📊 Estatísticas Detalhadas")

                df_display = df_estrategias.copy()
                df_display['Profit Total'] = df_display['Profit Total'].apply(
                    lambda x: f"€{x:+.2f}".replace('€+', '€+') if x >= 0 else f"€{x:.2f}"
                )
                df_display['Stake Total'] = df_display['Stake Total'].apply(lambda x: f"€{x:.2f}")
                df_display['ROI (%)'] = df_display['ROI (%)'].apply(lambda x: f"{x:.2f}%")

                max_total = int((df_estrategias['Greens'] + df_estrategias['Reds']).max())
                st.dataframe(
                    df_display,
                    column_config={
                        "Greens": st.column_config.ProgressColumn(
                            "Greens",
                            format="%d",
                            min_value=0,
                            max_value=max_total if not pd.isna(max_total) else 0
                        ),
                        "Reds": st.column_config.ProgressColumn(
                            "Reds",
                            format="%d",
                            min_value=0,
                            max_value=max_total if not pd.isna(max_total) else 0
                        )
                    },
                    hide_index=True
                )
        else:
            st.warning("Nenhum dado disponível para análise. Registre jogos com estratégias primeiro.")

    # Aba 4: Desempenho das Tags
    with tab4:
        st.subheader("🏷️ Desempenho por Tag")

        if st.session_state.dados['tags']:
            tags_stats = []
            for tag in st.session_state.dados['tags']:
                total_profit = 0
                total_stake = 0
                greens = 0
                reds = 0

                for mes in st.session_state.dados['mensal'].values():
                    if not mes.empty and 'Tag' in mes.columns:
                        jogos_tag = mes[mes['Tag'] == tag]
                        if not jogos_tag.empty:
                            total_profit += float(jogos_tag['Profit/Loss'].sum())
                            total_stake += float(jogos_tag['Stake'].sum())
                            greens += int(len(jogos_tag[jogos_tag['Profit/Loss'] >= 0]))
                            reds += int(len(jogos_tag[jogos_tag['Profit/Loss'] < 0]))

                roi = (total_profit / total_stake * 100) if total_stake != 0 else 0
                tags_stats.append({
                    'Tag': tag,
                    'Profit Total': total_profit,
                    'Stake Total': total_stake,
                    'ROI (%)': float(roi),
                    'Greens': greens,
                    'Reds': reds
                })

            if tags_stats:
                df_tags = pd.DataFrame(tags_stats)

                fig1 = px.bar(
                    df_tags.sort_values('Profit Total', ascending=False),
                    x='Tag',
                    y='Profit Total',
                    color='ROI (%)',
                    title="Lucro/Prejuízo por Tag",
                    color_continuous_scale='RdYlGn'
                )
                st.plotly_chart(fig1, use_container_width=True)

                st.subheader("📊 Estatísticas Detalhadas")

                df_display = df_tags.copy()
                df_display['Profit Total'] = df_display['Profit Total'].apply(
                    lambda x: f"€{x:+.2f}".replace('€+', '€+') if x >= 0 else f"€{x:.2f}"
                )
                df_display['Stake Total'] = df_display['Stake Total'].apply(lambda x: f"€{x:.2f}")
                df_display['ROI (%)'] = df_display['ROI (%)'].apply(lambda x: f"{x:.2f}%")

                max_total = int((df_tags['Greens'] + df_tags['Reds']).max())
                st.dataframe(
                    df_display,
                    column_config={
                        "Greens": st.column_config.ProgressColumn(
                            "Greens",
                            format="%d",
                            min_value=0,
                            max_value=max_total if not pd.isna(max_total) else 0
                        ),
                        "Reds": st.column_config.ProgressColumn(
                            "Reds",
                            format="%d",
                            min_value=0,
                            max_value=max_total if not pd.isna(max_total) else 0
                        )
                    },
                    hide_index=True
                )
        else:
            st.warning("Nenhum dado disponível para análise. Registre jogos com tags primeiro.")


def show_mes(mes):
    st.title(f"🗓️ {mes}")

    # Seção para adicionar jogos do dia (inicia fechada)
    with st.expander("➕ Adicionar Jogos do Dia", expanded=False):
        with st.form(f"form_jogos_dia_{mes}"):
            st.subheader("📅 Registrar Jogos do Dia")

            # Selecionar data
            data = st.date_input("Data*", value=datetime.now())

            # Selecionar competição (com opção de adicionar nova)
            col1, col2 = st.columns([4, 1])
            with col1:
                competicao = st.selectbox(
                    "Competição*",
                    options=st.session_state.dados['campeonatos']['Nome'].tolist(),
                    index=0
                )
            with col2:
                nova_competicao = st.text_input("Nome da Nova Competição", key=f"nova_competicao_{mes}")
                if nova_competicao:
                    if st.form_submit_button("➕ Adicionar Competição"):
                        adicionar_campeonato_se_nao_existir(nova_competicao)
                        st.rerun()

            # Configurações padrão para os jogos do dia
            st.subheader("Configurações Padrão")
            col_config1, col_config2 = st.columns(2)
            with col_config1:
                estrategia = st.selectbox(
                    "Estratégia",
                    options=st.session_state.dados['estrategias']['Nome'].tolist() if not st.session_state.dados[
                        'estrategias'].empty else ["Nenhuma estratégia cadastrada"],
                    index=0,
                    disabled=st.session_state.dados['estrategias'].empty
                )
                stake_padrao = st.number_input(
                    "Stake Padrão (€)",
                    min_value=0.01,
                    value=1.0,
                    step=0.5,
                    format="%.2f"
                )
            with col_config2:
                tag = st.selectbox(
                    "Tag",
                    options=st.session_state.dados['tags'],
                    index=0
                )
                percent_stake_padrao = st.number_input(
                    "% Stake Padrão",
                    min_value=-100,
                    max_value=500,
                    value=0,
                    step=1
                )

            # Adicionar múltiplos jogos
            st.subheader("Jogos do Dia")
            num_jogos = st.number_input("Quantidade de Jogos", min_value=1, max_value=50, value=1)

            jogos = []
            for i in range(num_jogos):
                st.markdown(f"### Jogo {i + 1}")
                col_jogo1, col_jogo2 = st.columns(2)
                with col_jogo1:
                    casa = st.text_input(f"Equipa Casa {i + 1}", key=f"casa_{i}")
                with col_jogo2:
                    visitante = st.text_input(f"Equipa Visitante {i + 1}", key=f"visitante_{i}")

                col_res1, col_res2 = st.columns(2)
                with col_res1:
                    stake = st.number_input(
                        f"Stake {i + 1} (€)",
                        min_value=0.01,
                        value=stake_padrao,
                        step=0.5,
                        format="%.2f",
                        key=f"stake_{i}"
                    )
                with col_res2:
                    profit_loss = st.number_input(
                        f"Profit/Loss {i + 1} (€)",
                        value=0.0,
                        step=0.5,
                        format="%.2f",
                        key=f"profit_{i}"
                    )

                jogos.append({
                    'Data': data,
                    'Competição': competicao,
                    'Casa': casa,
                    'Visitante': visitante,
                    'Estrategia': estrategia,
                    'Tag': tag,
                    'Stake': stake,
                    'Profit/Loss': profit_loss,
                    '% Stake': (profit_loss / stake * 100) if stake != 0 else 0
                })

            # Botões de ação
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.form_submit_button("💾 Salvar Todos os Jogos"):
                    if competicao and data:
                        for jogo in jogos:
                            if jogo['Casa'] and jogo['Visitante']:
                                adicionar_equipa_se_nao_existir(jogo['Casa'])
                                adicionar_equipa_se_nao_existir(jogo['Visitante'])
                                novo_jogo = pd.DataFrame([jogo])

                                if st.session_state.dados['mensal'][mes].empty:
                                    st.session_state.dados['mensal'][mes] = novo_jogo
                                else:
                                    st.session_state.dados['mensal'][mes] = pd.concat(
                                        [st.session_state.dados['mensal'][mes], novo_jogo],
                                        ignore_index=True
                                    )

                        atualizar_campeonatos()
                        salvar_dados()
                        st.success(f"{len(jogos)} jogos salvos com sucesso!")
                        st.rerun()
                    else:
                        st.error("Data e Competição são obrigatórios!")

            with col_btn2:
                if st.form_submit_button("🔄 Limpar Campos"):
                    st.rerun()

    # Seção para edição/remoção individual de jogos (inicia fechada)
    with st.expander("✏️ Editar/Remover Jogos Existentes", expanded=False):
        if not st.session_state.dados['mensal'][mes].empty:
            jogos_mes = st.session_state.dados['mensal'][mes]
            options = ["Selecione um jogo"] + [
                f"{row['Data'].strftime('%d/%m')} - {row['Competição']}: {row['Casa']} vs {row['Visitante']} ({format_currency(row['Profit/Loss'])})"
                for _, row in jogos_mes.iterrows()
            ]

            jogo_para_editar = st.selectbox(
                "Selecionar jogo para editar",
                options=options,
                index=0
            )

            if jogo_para_editar != "Selecione um jogo":
                edit_index = options.index(jogo_para_editar) - 1
                jogo_data = jogos_mes.iloc[edit_index]

                with st.form(f"form_editar_jogo_{mes}_{edit_index}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        data = st.date_input("Data", value=jogo_data['Data'])
                        competicao = st.text_input("Competição*", value=jogo_data['Competição']).strip()
                        casa = st.text_input("Equipa Casa*", value=jogo_data['Casa']).strip()
                        visitante = st.text_input("Equipa Visitante*", value=jogo_data['Visitante']).strip()

                    with col2:
                        estrategia = st.selectbox(
                            "Estratégia",
                            options=st.session_state.dados['estrategias']['Nome'].tolist(),
                            index=st.session_state.dados['estrategias']['Nome'].tolist().index(jogo_data['Estrategia'])
                        )
                        tag = st.selectbox(
                            "Tag",
                            options=st.session_state.dados['tags'],
                            index=st.session_state.dados['tags'].index(jogo_data['Tag'])
                        )
                        stake = st.number_input(
                            "Stake (€)",
                            min_value=0.01,
                            value=float(jogo_data['Stake']),
                            format="%.2f",
                            step=0.5
                        )
                        profit_loss = st.number_input(
                            "Profit/Loss (€)",
                            value=float(jogo_data['Profit/Loss']),
                            format="%.2f",
                            step=0.5
                        )

                    col_botoes = st.columns(3)
                    with col_botoes[0]:
                        if st.form_submit_button("💾 Atualizar Jogo"):
                            st.session_state.dados['mensal'][mes].at[edit_index, 'Data'] = data
                            st.session_state.dados['mensal'][mes].at[edit_index, 'Competição'] = competicao
                            st.session_state.dados['mensal'][mes].at[edit_index, 'Casa'] = casa
                            st.session_state.dados['mensal'][mes].at[edit_index, 'Visitante'] = visitante
                            st.session_state.dados['mensal'][mes].at[edit_index, 'Estrategia'] = estrategia
                            st.session_state.dados['mensal'][mes].at[edit_index, 'Tag'] = tag
                            st.session_state.dados['mensal'][mes].at[edit_index, 'Stake'] = stake
                            st.session_state.dados['mensal'][mes].at[edit_index, 'Profit/Loss'] = profit_loss
                            st.session_state.dados['mensal'][mes].at[edit_index, '% Stake'] = (
                                        profit_loss / stake * 100) if stake != 0 else 0

                            salvar_dados()
                            st.success("Jogo atualizado com sucesso!")
                            st.rerun()

                    with col_botoes[1]:
                        if st.form_submit_button("🗑️ Remover Jogo"):
                            st.session_state.dados['mensal'][mes] = st.session_state.dados['mensal'][mes].drop(
                                jogos_mes.index[edit_index])
                            salvar_dados()
                            st.success("Jogo removido com sucesso!")
                            st.rerun()
        else:
            st.info("Nenhum jogo registrado para edição")

    # Visualização dos jogos e estatísticas
    st.subheader(f"📅 Jogos de {mes}")
    if not st.session_state.dados['mensal'][mes].empty:
        df_mes = st.session_state.dados['mensal'][mes].copy()

        # Formatar valores para exibição
        df_display = df_mes.copy()
        df_display['Stake'] = df_display['Stake'].apply(format_currency)
        df_display['Profit/Loss'] = df_display['Profit/Loss'].apply(
            lambda x: format_currency(x).replace('€', '€+') if x >= 0 else format_currency(x)
        )
        df_display['% Stake'] = df_display['% Stake'].apply(format_percent)

        st.dataframe(
            df_display,
            column_config={
                '% Stake': st.column_config.ProgressColumn(
                    '% Stake',
                    format='%.2f%%',
                    min_value=-100,
                    max_value=500
                )
            },
            hide_index=True,
            use_container_width=True
        )

        # Estatísticas de performance
        st.subheader(f"📊 Estatísticas de Performance - {mes}")

        # Converter a coluna Data para datetime se ainda não for
        if not pd.api.types.is_datetime64_any_dtype(df_mes['Data']):
            df_mes['Data'] = pd.to_datetime(df_mes['Data'])

        # Calcular estatísticas consolidadas
        dias_trabalhados = df_mes['Data'].nunique()
        daily_results = df_mes.groupby('Data')['Profit/Loss'].sum().reset_index()
        dias_green = len(daily_results[daily_results['Profit/Loss'] >= 0])
        dias_red = dias_trabalhados - dias_green

        mercados_totais = len(df_mes)
        mercados_green = len(df_mes[df_mes['Profit/Loss'] >= 0])
        mercados_red = mercados_totais - mercados_green

        total_stake = df_mes['Stake'].sum()
        total_profit = df_mes['Profit/Loss'].sum()
        roi = (total_profit / total_stake * 100) if total_stake != 0 else 0

        # Layout das métricas
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("💰 Stake Total", format_currency(total_stake))
            st.metric("📅 Dias Trabalhados", dias_trabalhados)

        with col2:
            st.metric("💸 Profit/Loss Total",
                      format_currency(total_profit).replace('€', '€+') if total_profit >= 0 else format_currency(
                          total_profit))
            st.metric("✅ Dias Green", dias_green,
                      delta=f"{dias_green / dias_trabalhados * 100:.1f}%" if dias_trabalhados > 0 else "0%")

        with col3:
            st.metric("📊 ROI", format_percent(roi))
            st.metric("❌ Dias Red", dias_red,
                      delta=f"{dias_red / dias_trabalhados * 100:.1f}%" if dias_trabalhados > 0 else "0%",
                      delta_color="inverse")

        # Segunda linha de métricas
        col4, col5, col6 = st.columns(3)

        with col4:
            st.metric("🔢 Total Mercados", mercados_totais)

        with col5:
            st.metric("🟢 Mercados Green", mercados_green,
                      delta=f"{mercados_green / mercados_totais * 100:.1f}%" if mercados_totais > 0 else "0%")

        with col6:
            st.metric("🔴 Mercados Red", mercados_red,
                      delta=f"{mercados_red / mercados_totais * 100:.1f}%" if mercados_totais > 0 else "0%",
                      delta_color="inverse")

        # Gráficos de análise
        st.subheader("📈 Análise Detalhada")

        tab1, tab2 = st.tabs(["Evolução Diária", "Performance por Estratégia"])

        with tab1:
            # Gráfico de evolução diária
            daily_stats = df_mes.groupby('Data').agg({
                'Profit/Loss': 'sum',
                'Stake': 'sum'
            }).reset_index()
            daily_stats['ROI'] = (daily_stats['Profit/Loss'] / daily_stats['Stake']) * 100

            fig1 = px.line(
                daily_stats,
                x='Data',
                y='Profit/Loss',
                title="Lucro/Prejuízo por Dia",
                labels={'Profit/Loss': 'Lucro/Prejuízo (€)', 'Data': 'Data'},
                markers=True
            )
            st.plotly_chart(fig1, use_container_width=True)

            # Gráfico de barras para stake diário
            fig2 = px.bar(
                daily_stats,
                x='Data',
                y='Stake',
                title="Stake por Dia",
                labels={'Stake': 'Stake (€)', 'Data': 'Data'}
            )
            st.plotly_chart(fig2, use_container_width=True)

        with tab2:
            # Performance por estratégia
            estrategia_stats = df_mes.groupby('Estrategia').agg({
                'Profit/Loss': 'sum',
                'Stake': 'sum'
            }).reset_index()
            estrategia_stats['ROI'] = (estrategia_stats['Profit/Loss'] / estrategia_stats['Stake']) * 100

            fig3 = px.bar(
                estrategia_stats,
                x='Estrategia',
                y='Profit/Loss',
                color='ROI',
                title="Performance por Estratégia",
                labels={'Profit/Loss': 'Lucro/Prejuízo (€)', 'Estrategia': 'Estratégia'},
                color_continuous_scale='RdYlGn'
            )
            st.plotly_chart(fig3, use_container_width=True)

    else:
        st.info(f"Nenhum jogo registrado em {mes}")


def main():
    st.sidebar.title("📊 Menu Navegação")

    pages = ["🏠 Painel", "⚽ Equipas", "🏆 Campeonatos", "🧠 Estratégias"]
    months = [
        "🗓️ Janeiro", "🗓️ Fevereiro", "🗓️ Março", "🗓️ Abril",
        "🗓️ Maio", "🗓️ Junho", "🗓️ Julho", "🗓️ Agosto",
        "🗓️ Setembro", "🗓️ Outubro", "🗓️ Novembro", "🗓️ Dezembro"
    ]

    option = st.sidebar.selectbox("Selecione uma página:", pages + months)

    if option == "🏠 Painel":
        show_painel()
    elif option == "⚽ Equipas":
        show_equipas()
    elif option == "🏆 Campeonatos":
        show_campeonatos()
    elif option == "🧠 Estratégias":
        show_estrategias()
    elif option in months:
        show_mes(option.split(" ")[1])


if __name__ == "__main__":
    main()