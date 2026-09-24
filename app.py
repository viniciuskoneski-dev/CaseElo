import streamlit as st
import pandas as pd
from datetime import datetime

# ==========================================
# Configuração e Banco de Dados Temporário
# ==========================================
st.set_page_config(page_title="Sistema de Reembolso EloGroup", page_icon="💸", layout="wide")

# Inicializando o "banco de dados" na sessão para manter os registros entre as abas
if 'banco_reembolsos' not in st.session_state:
    st.session_state['banco_reembolsos'] = pd.DataFrame(columns=[
        "ID", "Colaborador", "Centro de Custo", "Data Despesa", "Tipo", 
        "Descrição", "Valor", "Comprovante", "Status"
    ])

# ==========================================
# Navegação Lateral (Simulando Perfis)
# ==========================================
st.sidebar.title("Navegação de Perfis")
st.sidebar.markdown("Selecione sua visão para testar o fluxo completo.")
perfil_selecionado = st.sidebar.radio("Acessar como:", 
    ["1. Colaborador (Solicitante)", 
     "2. Gestor (Aprovação)", 
     "3. Técnico Administrativo (Conformidade)", 
     "4. Financeiro (Pagamento)"]
)

st.sidebar.divider()
st.sidebar.markdown("**Métricas do Sistema:**")
st.sidebar.metric("Total de Solicitações", len(st.session_state['banco_reembolsos']))

# ==========================================
# TELA 1: COLABORADOR
# ==========================================
if perfil_selecionado == "1. Colaborador (Solicitante)":
    st.title("💸 Nova Solicitação de Reembolso")
    st.markdown("Preencha os dados abaixo. O formulário não apagará seus dados em caso de erro.")
    
    # clear_on_submit=False mantém os dados preenchidos
    with st.form(key="form_colaborador", clear_on_submit=False):
        col1, col2 = st.columns(2)
        with col1:
            nome = st.text_input("Nome do Colaborador *")
            centro_custo = st.text_input("Centro de Custo (ID do Projeto) *")
            data_despesa = st.date_input("Data da Despesa *")
        with col2:
            valor = st.number_input("Valor (R$) *", min_value=0.0, format="%.2f")
            tipo_despesa = st.selectbox("Tipo de Despesa *", 
                ["1 - Transporte", "2 - Refeições", "3 - Gráfica e material", "4 - Outros (especificar na descrição)"])
        
        descricao = st.text_input("Descrição e Observações *")
        comprovante = st.file_uploader("Anexar Comprovante Fiscal *", type=["pdf", "png", "jpg"])
        
        submit_btn = st.form_submit_button("Enviar Solicitação")
        
    if submit_btn:
        erros = []
        if not nome.strip(): erros.append("Nome é obrigatório.")
        if not centro_custo.strip(): erros.append("Centro de Custo é obrigatório.")
        if valor <= 0: erros.append("O valor deve ser maior que zero.")
        if not descricao.strip(): erros.append("A descrição é obrigatória.")
        if not comprovante: erros.append("O comprovante é obrigatório para conformidade.")
        if tipo_despesa.startswith("4") and len(descricao.strip()) < 5:
            erros.append("Ao selecionar 'Outros', detalhe a despesa na descrição.")
            
        # Regra de negócio: 90 dias
        dias_passados = (datetime.now().date() - data_despesa).days
        if dias_passados > 90:
            erros.append(f"A despesa ocorreu há {dias_passados} dias. O limite é 90 dias.")
            
        if erros:
            st.error("⚠️ Corrija os erros abaixo para continuar:")
            for erro in erros: st.warning(f"- {erro}")
        else:
            novo_id = len(st.session_state['banco_reembolsos']) + 1
            novo_registro = {
                "ID": novo_id,
                "Colaborador": nome,
                "Centro de Custo": centro_custo,
                "Data Despesa": data_despesa.strftime("%d/%m/%Y"),
                "Tipo": tipo_despesa.split(" - ")[1],
                "Descrição": descricao,
                "Valor": valor,
                "Comprovante": comprovante.name,
                "Status": "Aguardando Técnico"
            }
            # Adiciona ao dataframe na sessão
            df = st.session_state['banco_reembolsos']
            st.session_state['banco_reembolsos'] = pd.concat([df, pd.DataFrame([novo_registro])], ignore_index=True)
            st.success("✅ Solicitação enviada com sucesso! Você pode acompanhar o status com o Técnico Administrativo.")

# ==========================================
# TELA 2: TÉCNICO ADMINISTRATIVO
# ==========================================
elif perfil_selecionado == "3. Técnico Administrativo (Conformidade)":
    st.title("📋 Validação de Conformidade")
    st.markdown("Analise os comprovantes e a validade das políticas antes de enviar ao Gestor.")
    
    df = st.session_state['banco_reembolsos']
    pendentes_tec = df[df['Status'] == "Aguardando Técnico"]
    
    if pendentes_tec.empty:
        st.info("Nenhuma solicitação aguardando validação de conformidade no momento.")
    else:
        st.dataframe(pendentes_tec, use_container_width=True, hide_index=True)
        
        # Simulação de aprovação
        id_selecionado = st.selectbox("Selecione o ID para validar:", pendentes_tec['ID'])
        acao = st.radio("Ação:", ["Validar e Enviar ao Gestor", "Rejeitar (Falta de Documentação)"])
        
        if st.button("Executar Ação"):
            novo_status = "Aguardando Gestor" if "Validar" in acao else "Rejeitado pelo Técnico"
            idx = df[df['ID'] == id_selecionado].index[0]
            st.session_state['banco_reembolsos'].at[idx, 'Status'] = novo_status
            st.success(f"Status do ID {id_selecionado} atualizado para: {novo_status}")
            st.rerun()

# ==========================================
# TELA 3: GESTOR
# ==========================================
elif perfil_selecionado == "2. Gestor (Aprovação)":
    st.title("👔 Aprovação de Centro de Custo")
    st.markdown("Revise os gastos validados pelo Técnico Administrativo referentes aos seus projetos.")
    
    df = st.session_state['banco_reembolsos']
    pendentes_gestor = df[df['Status'] == "Aguardando Gestor"]
    
    if pendentes_gestor.empty:
        st.info("Nenhuma solicitação aguardando sua aprovação no momento.")
    else:
        st.dataframe(pendentes_gestor, use_container_width=True, hide_index=True)
        
        id_selecionado = st.selectbox("Selecione o ID para avaliar:", pendentes_gestor['ID'])
        acao = st.radio("Ação do Gestor:", ["Aprovar Totalmente", "Aprovar Parcialmente", "Rejeitar Pedido"])
        
        if st.button("Confirmar Decisão"):
            if "Aprovar" in acao:
                novo_status = "Aprovado - Aguardando Financeiro"
            else:
                novo_status = "Rejeitado pelo Gestor"
                
            idx = df[df['ID'] == id_selecionado].index[0]
            st.session_state['banco_reembolsos'].at[idx, 'Status'] = novo_status
            st.success(f"Status do ID {id_selecionado} atualizado para: {novo_status}")
            st.rerun()

# ==========================================
# TELA 4: FINANCEIRO
# ==========================================
elif perfil_selecionado == "4. Financeiro (Pagamento)":
    st.title("💰 Agendamento e Pagamento")
    st.markdown("Realize o pagamento das solicitações aprovadas pelos gestores.")
    
    df = st.session_state['banco_reembolsos']
    pendentes_fin = df[df['Status'] == "Aprovado - Aguardando Financeiro"]
    
    if pendentes_fin.empty:
        st.info("Nenhuma aprovação pendente de pagamento.")
    else:
        st.dataframe(pendentes_fin, use_container_width=True, hide_index=True)
        
        id_selecionado = st.selectbox("Selecione o ID para processar pagamento:", pendentes_fin['ID'])
        
        if st.button("Confirmar Pagamento e Arquivar"):
            idx = df[df['ID'] == id_selecionado].index[0]
            st.session_state['banco_reembolsos'].at[idx, 'Status'] = "Pago e Arquivado"
            st.success(f"Pagamento do ID {id_selecionado} processado com sucesso!")
            st.balloons()
            st.rerun()

    st.divider()
    st.subheader("Histórico Geral (Visão Financeira/Auditoria)")
    st.dataframe(df, use_container_width=True, hide_index=True)
