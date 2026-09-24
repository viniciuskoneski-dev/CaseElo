import streamlit as st
import pandas as pd
import datetime

# Configuração da página
st.set_page_config(page_title="EloGroup - Sistema de Reembolso", layout="wide")

# Inicializando um "banco de dados" em memória (simulado via session_state)
if 'db' not in st.session_state:
    st.session_state.db = pd.DataFrame(columns=[
        "ID", "Colaborador", "Centro_Custo", "Data_Despesa", "Valor", "Status"
    ])
    st.session_state.next_id = 1

# Barra Lateral - Simulação de Perfis de Usuário
st.sidebar.title("Navegação")
perfil = st.sidebar.selectbox(
    "Acessar o sistema como:",
    ["Colaborador", "Técnico Administrativo", "Gestor", "Financeiro"]
)

st.title(f"Portal de Reembolsos - Visão: {perfil}")

# -------------------------------------------------------------
# VISÃO: COLABORADOR
# -------------------------------------------------------------
if perfil == "Colaborador":
    st.header("Nova Solicitação de Reembolso")
    
    with st.form("form_reembolso", clear_on_submit=True):
        nome = st.text_input("Nome do Colaborador")
        centro_custo = st.text_input("Centro de Custo (Ex: Projeto X)")
        
        col1, col2 = st.columns(2)
        with col1:
            data_despesa = st.date_input("Data da Despesa")
        with col2:
            valor = st.number_input("Valor (R$)", min_value=0.01, format="%.2f")
            
        comprovante = st.file_uploader("Anexar Comprovante (PDF/Imagem)")
        
        submit = st.form_submit_button("Enviar Solicitação")
        
        if submit:
            # CHECAGEM AUTOMÁTICA: Regra dos 90 dias
            dias_passados = (datetime.date.today() - data_despesa).days
            
            if dias_passados > 90:
                st.error("ERRO: A política da empresa não permite reembolso de despesas com mais de 90 dias.")
            elif not comprovante:
                st.error("ERRO: O anexo do comprovante é obrigatório.")
            elif not nome or not centro_custo:
                st.warning("Preencha todos os campos.")
            else:
                # Salva no "banco de dados"
                novo_registro = {
                    "ID": st.session_state.next_id,
                    "Colaborador": nome,
                    "Centro_Custo": centro_custo,
                    "Data_Despesa": data_despesa,
                    "Valor": valor,
                    "Status": "Pendente - Análise Técnico"
                }
                st.session_state.db = pd.concat([st.session_state.db, pd.DataFrame([novo_registro])], ignore_index=True)
                st.session_state.next_id += 1
                st.success("Solicitação enviada com sucesso!")

    st.divider()
    st.header("Minhas Solicitações")
    st.dataframe(st.session_state.db)

# -------------------------------------------------------------
# VISÃO: TÉCNICO ADMINISTRATIVO
# -------------------------------------------------------------
elif perfil == "Técnico Administrativo":
    st.header("Aprovação de Conformidade")
    pendentes = st.session_state.db[st.session_state.db["Status"] == "Pendente - Análise Técnico"]
    
    if pendentes.empty:
        st.info("Nenhuma solicitação pendente de conferência.")
    else:
        st.dataframe(pendentes)
        
        req_id = st.selectbox("Selecione o ID para avaliar:", pendentes["ID"])
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Aprovar Conformidade (Enviar p/ Gestor)", type="primary"):
                st.session_state.db.loc[st.session_state.db["ID"] == req_id, "Status"] = "Pendente - Aprovação Gestor"
                st.success("Aprovado e enviado para o Gestor!")
                st.rerun()
        with col2:
            if st.button("Rejeitar / Solicitar Ajuste"):
                st.session_state.db.loc[st.session_state.db["ID"] == req_id, "Status"] = "Rejeitado pelo Técnico"
                st.warning("Solicitação rejeitada.")
                st.rerun()

# -------------------------------------------------------------
# VISÃO: GESTOR
# -------------------------------------------------------------
elif perfil == "Gestor":
    st.header("Aprovação de Despesas")
    pendentes_gestor = st.session_state.db[st.session_state.db["Status"] == "Pendente - Aprovação Gestor"]
    
    if pendentes_gestor.empty:
        st.info("Nenhuma solicitação aguardando sua aprovação.")
    else:
        st.dataframe(pendentes_gestor)
        
        req_id_gestor = st.selectbox("Selecione o ID para avaliar:", pendentes_gestor["ID"])
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Aprovar Reembolso", type="primary"):
                st.session_state.db.loc[st.session_state.db["ID"] == req_id_gestor, "Status"] = "Aprovado - Aguardando Pagamento"
                st.success("Reembolso aprovado e enviado ao Financeiro!")
                st.rerun()
        with col2:
            if st.button("Rejeitar Despesa"):
                st.session_state.db.loc[st.session_state.db["ID"] == req_id_gestor, "Status"] = "Rejeitado pelo Gestor"
                st.warning("Despesa rejeitada.")
                st.rerun()

# -------------------------------------------------------------
# VISÃO: FINANCEIRO
# -------------------------------------------------------------
elif perfil == "Financeiro":
    st.header("Pagamentos Pendentes")
    aprovados = st.session_state.db[st.session_state.db["Status"] == "Aprovado - Aguardando Pagamento"]
    
    if aprovados.empty:
        st.info("Nenhum pagamento pendente no momento.")
    else:
        st.dataframe(aprovados)
        
        req_id_fin = st.selectbox("Selecione o ID para dar baixa:", aprovados["ID"])
        if st.button("Confirmar Pagamento e Arquivar", type="primary"):
            st.session_state.db.loc[st.session_state.db["ID"] == req_id_fin, "Status"] = "Pago e Arquivado"
            st.success("Pagamento confirmado. Documentos arquivados automaticamente no sistema.")
            st.rerun()