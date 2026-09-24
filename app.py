import streamlit as st
import pandas as pd
from datetime import datetime

# ==========================================
# Configuração e Banco de Dados Temporário
# ==========================================
st.set_page_config(page_title="Sistema de Reembolso EloGroup", page_icon="💸", layout="wide")

# Inicializando o "banco de dados" de reembolsos
if 'banco_reembolsos' not in st.session_state:
    st.session_state['banco_reembolsos'] = pd.DataFrame(columns=[
        "ID", "Colaborador", "Centro de Custo", "Data Despesa", "Tipo", 
        "Descrição", "Observações", "Valor", "Comprovante", "Alerta", "Status"
    ])

# Inicializando limites de gastos padrão configuráveis pelo Gestor
if 'limites_despesa' not in st.session_state:
    st.session_state['limites_despesa'] = {
        "1": 300.0,  # Transporte
        "2": 75.0,   # Refeições
        "3": 100.0,  # Gráfica e Material
        "4": 50.0    # Outros
    }

# Váriavel para o fluxo de confirmação (sem nota/limite excedido)
if 'temp_solicitacao' not in st.session_state:
    st.session_state['temp_solicitacao'] = None

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

df_geral = st.session_state['banco_reembolsos']

# ==========================================
# TELA 1: COLABORADOR
# ==========================================
if perfil_selecionado == "1. Colaborador (Solicitante)":
    st.title("💸 Nova Solicitação de Reembolso")
    st.markdown("Preencha os dados abaixo.")
    
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
        
        descricao = st.text_input("Descrição *", help="O que foi gasto? (Obrigatório)")
        observacao = st.text_area("Observações / Justificativas", help="Por que houve esse gasto ou justifique valores anômalos/falta de nota.")
        comprovante = st.file_uploader("Anexar Comprovante Fiscal (Opcional para testes)", type=["pdf", "png", "jpg"])
        
        submit_btn = st.form_submit_button("Validar Solicitação")
        
    # Validação inicial ao clicar no formulário
    if submit_btn:
        erros = []
        if not nome.strip(): erros.append("O campo 'Nome' é obrigatório.")
        if not centro_custo.strip(): erros.append("O campo 'Centro de Custo' é obrigatório.")
        if valor <= 0: erros.append("O valor deve ser maior que zero.")
        if not descricao.strip(): erros.append("O campo 'Descrição' é obrigatório.")
        
        dias_passados = (datetime.now().date() - data_despesa).days
        if dias_passados > 90:
            erros.append(f"A despesa ocorreu há {dias_passados} dias. A política bloqueia envios com mais de 90 dias.")
        elif dias_passados < 0:
            erros.append("A data da despesa não pode ser no futuro.")
            
        if erros:
            st.error("🚫 Corrija os erros abaixo para continuar:")
            for erro in erros: st.warning(f"- {erro}")
            st.session_state['temp_solicitacao'] = None
        else:
            # Pega o limite configurado pelo gestor
            codigo_tipo = tipo_despesa.split(" - ")[0]
            limite = st.session_state['limites_despesa'].get(codigo_tipo, 0.0)
            alerta = "⚠️ Valor Excedente" if valor > limite else ("⚠️ Sem Comprovante" if not comprovante else "✅ OK")
            if valor > limite and not comprovante: alerta = "⚠️ Valor Excedente e Sem Comprovante"

            st.session_state['temp_solicitacao'] = {
                "ID": len(st.session_state['banco_reembolsos']) + 1,
                "Colaborador": nome,
                "Centro de Custo": centro_custo,
                "Data Despesa": data_despesa.strftime("%d/%m/%Y"),
                "Tipo": tipo_despesa.split(" - ")[1],
                "Descrição": descricao,
                "Observações": observacao,
                "Valor": valor,
                "Comprovante": comprovante.name if comprovante else "Não Anexado",
                "Alerta": alerta,
                "Status": "Aguardando Técnico"
            }

    # Fluxo de Confirmação Final (Mostrando Avisos Amarelos)
    if st.session_state['temp_solicitacao'] is not None:
        st.info("🔎 **Validação Concluída! Verifique os avisos abaixo antes de confirmar o envio.**")
        temp = st.session_state['temp_solicitacao']
        
        codigo_tipo = tipo_despesa.split(" - ")[0]
        limite_teto = st.session_state['limites_despesa'].get(codigo_tipo, 0.0)
        
        if temp['Valor'] > limite_teto:
            st.warning(f"⚠️ **Inadequação de Valor:** Sua despesa de R$ {temp['Valor']:.2f} excede o limite estipulado de R$ {limite_teto:.2f} para esta categoria. Sua solicitação ficará destacada para análise do Técnico e do Gestor.")
        
        if temp['Comprovante'] == "Não Anexado":
            st.warning("⚠️ **Falta de Comprovante:** Você não anexou o cupom fiscal. O envio prosseguirá para fins de teste, mas a equipe de conformidade avaliará as justificativas.")

        if st.button("Confirmar e Enviar Definitivamente", type="primary"):
            st.session_state['banco_reembolsos'] = pd.concat([df_geral, pd.DataFrame([temp])], ignore_index=True)
            st.session_state['temp_solicitacao'] = None
            st.success("✅ Solicitação enviada com sucesso!")
            st.rerun()

    st.divider()
    st.subheader("Histórico Global de Solicitações (Visão Colaborador)")
    st.dataframe(df_geral, use_container_width=True, hide_index=True)

# ==========================================
# TELA 2: TÉCNICO ADMINISTRATIVO
# ==========================================
elif perfil_selecionado == "3. Técnico Administrativo (Conformidade)":
    st.title("📋 Validação de Conformidade")
    st.markdown("Analise os comprovantes e os alertas de violação de política antes de enviar ao Gestor.")
    
    pendentes_tec = df_geral[df_geral['Status'] == "Aguardando Técnico"]
    
    if pendentes_tec.empty:
        st.info("Nenhuma solicitação aguardando validação de conformidade no momento.")
    else:
        st.dataframe(pendentes_tec, use_container_width=True, hide_index=True)
        
        col_acao1, col_acao2 = st.columns(2)
        with col_acao1: id_selecionado = st.selectbox("Selecione o ID para validar:", pendentes_tec['ID'])
        with col_acao2: acao = st.radio("Ação:", ["Validar e Enviar ao Gestor", "Rejeitar Pedido"])
        
        if st.button("Executar Ação"):
            novo_status = "Aguardando Gestor" if "Validar" in acao else "Rejeitado pelo Técnico"
            idx = df_geral[df_geral['ID'] == id_selecionado].index[0]
            st.session_state['banco_reembolsos'].at[idx, 'Status'] = novo_status
            st.success(f"Status do ID {id_selecionado} atualizado!")
            st.rerun()
            
    st.divider()
    st.subheader("Histórico Global de Solicitações")
    st.dataframe(df_geral, use_container_width=True, hide_index=True)

# ==========================================
# TELA 3: GESTOR
# ==========================================
elif perfil_selecionado == "2. Gestor (Aprovação)":
    st.title("👔 Área do Gestor")
    
    with st.expander("⚙️ Configurar Limites de Valores (Políticas de Despesa)"):
        st.markdown("Defina os tetos de gastos. Valores excedentes gerarão alertas amarelos na solicitação.")
        col_L1, col_L2, col_L3, col_L4 = st.columns(4)
        with col_L1: st.session_state['limites_despesa']["1"] = st.number_input("1 - Transporte (R$)", value=st.session_state['limites_despesa']["1"], format="%.2f")
        with col_L2: st.session_state['limites_despesa']["2"] = st.number_input("2 - Refeições (R$)", value=st.session_state['limites_despesa']["2"], format="%.2f")
        with col_L3: st.session_state['limites_despesa']["3"] = st.number_input("3 - Gráfica (R$)", value=st.session_state['limites_despesa']["3"], format="%.2f")
        with col_L4: st.session_state['limites_despesa']["4"] = st.number_input("4 - Outros (R$)", value=st.session_state['limites_despesa']["4"], format="%.2f")
    
    st.divider()
    st.subheader("Aprovação de Centro de Custo")
    
    pendentes_gestor = df_geral[df_geral['Status'] == "Aguardando Gestor"]
    
    if pendentes_gestor.empty:
        st.info("Nenhuma solicitação aguardando sua aprovação.")
    else:
        st.dataframe(pendentes_gestor, use_container_width=True, hide_index=True)
        
        col_acao1, col_acao2 = st.columns(2)
        with col_acao1: id_selecionado = st.selectbox("Selecione o ID para avaliar:", pendentes_gestor['ID'])
        with col_acao2: acao = st.radio("Ação do Gestor:", ["Aprovar Totalmente", "Aprovar Parcialmente", "Rejeitar Pedido"])
        
        if st.button("Confirmar Decisão"):
            novo_status = "Aprovado - Aguardando Financeiro" if "Aprovar" in acao else "Rejeitado pelo Gestor"
            idx = df_geral[df_geral['ID'] == id_selecionado].index[0]
            st.session_state['banco_reembolsos'].at[idx, 'Status'] = novo_status
            st.success(f"Status do ID {id_selecionado} atualizado!")
            st.rerun()

    st.divider()
    st.subheader("Histórico Global de Solicitações")
    st.dataframe(df_geral, use_container_width=True, hide_index=True)

# ==========================================
# TELA 4: FINANCEIRO
# ==========================================
elif perfil_selecionado == "4. Financeiro (Pagamento)":
    st.title("💰 Agendamento e Pagamento")
    
    pendentes_fin = df_geral[df_geral['Status'] == "Aprovado - Aguardando Financeiro"]
    
    if pendentes_fin.empty:
        st.info("Nenhuma aprovação pendente de pagamento.")
    else:
        st.dataframe(pendentes_fin, use_container_width=True, hide_index=True)
        
        id_selecionado = st.selectbox("Selecione o ID para processar pagamento:", pendentes_fin['ID'])
        if st.button("Confirmar Pagamento e Arquivar", type="primary"):
            idx = df_geral[df_geral['ID'] == id_selecionado].index[0]
            st.session_state['banco_reembolsos'].at[idx, 'Status'] = "Pago e Arquivado"
            st.success("Pagamento processado com sucesso!")
            st.balloons()
            st.rerun()

    st.divider()
    st.subheader("Histórico Geral de Solicitações (Auditoria)")
    st.dataframe(df_geral, use_container_width=True, hide_index=True)
