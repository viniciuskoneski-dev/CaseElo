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
        "Descrição", "Observações", "Valor", "Comprovante", "Alerta", "Status", "Justificativa Gestor"
    ])

# Inicializando limites de gastos padrão configuráveis pelo Gestor
if 'limites_despesa' not in st.session_state:
    st.session_state['limites_despesa'] = {
        "1": 300.0,  # Transporte
        "2": 75.0,   # Refeições
        "3": 100.0,  # Gráfica e Material
        "4": 50.0    # Outros
    }

# Variável para o fluxo de confirmação (sem nota/limite excedido)
if 'temp_solicitacao' not in st.session_state:
    st.session_state['temp_solicitacao'] = None

# ==========================================
# Navegação Lateral (Simulando Perfis)
# ==========================================
st.sidebar.title("Navegação de Perfis")
st.sidebar.markdown("Selecione sua visão para testar o fluxo.")
perfil_selecionado = st.sidebar.radio("Acessar como:", 
    ["1. Colaborador (Solicitante)", 
     "2. Gestor / Técnico (Avaliação)", 
     "3. Financeiro (Pagamento)"]
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
                "Status": "Aguardando Avaliação",
                "Justificativa Gestor": "-"
            }

    if st.session_state['temp_solicitacao'] is not None:
        st.info("🔎 **Validação Concluída! Verifique os avisos abaixo antes de confirmar o envio.**")
        temp = st.session_state['temp_solicitacao']
        
        codigo_tipo = tipo_despesa.split(" - ")[0]
        limite_teto = st.session_state['limites_despesa'].get(codigo_tipo, 0.0)
        
        # Mensagens de alerta ou sucesso (Nova funcionalidade)
        if temp['Valor'] > limite_teto:
            st.warning(f"⚠️ **Inadequação de Valor:** Sua despesa de R$ {temp['Valor']:.2f} excede o limite estipulado de R$ {limite_teto:.2f} para esta categoria. Sua solicitação ficará destacada para análise.")
        
        if temp['Comprovante'] == "Não Anexado":
            st.warning("⚠️ **Falta de Comprovante:** Você não anexou o cupom fiscal. O envio prosseguirá para fins de teste, mas a equipe avaliará as justificativas.")

        if temp['Valor'] <= limite_teto and temp['Comprovante'] != "Não Anexado":
            st.success("✅ **Tudo Certo!** Sua solicitação está totalmente de acordo com as políticas da empresa (Comprovante anexado e valor dentro do limite).")

        if st.button("Confirmar e Enviar Definitivamente", type="primary"):
            st.session_state['banco_reembolsos'] = pd.concat([df_geral, pd.DataFrame([temp])], ignore_index=True)
            st.session_state['temp_solicitacao'] = None
            st.success("✅ Solicitação enviada com sucesso!")
            st.rerun()

    st.divider()

    # ==========================================
    # SEÇÃO DE CORREÇÃO (NOVA FUNCIONALIDADE)
    # ==========================================
    df_rejeitados = df_geral[df_geral['Status'] == "Rejeitado Parcialmente"]
    if not df_rejeitados.empty:
        st.subheader("✏️ Correção de Solicitações Rejeitadas Parcialmente")
        st.markdown("O Gestor solicitou ajustes nestes pedidos. Edite-os abaixo para reenviar.")
        st.dataframe(df_rejeitados, use_container_width=True, hide_index=True)
        
        id_editar = st.selectbox("Selecione o ID para corrigir:", df_rejeitados['ID'])
        row_editar = df_rejeitados[df_rejeitados['ID'] == id_editar].iloc[0]
        
        with st.form(key="form_editar", clear_on_submit=False):
            st.info(f"**Justificativa do Gestor para o ID {id_editar}:** {row_editar['Justificativa Gestor']}")
            
            c1, c2 = st.columns(2)
            with c1:
                e_nome = st.text_input("Nome", value=row_editar['Colaborador'])
                e_cc = st.text_input("Centro de Custo", value=row_editar['Centro de Custo'])
                data_obj = datetime.strptime(row_editar['Data Despesa'], "%d/%m/%Y").date()
                e_data = st.date_input("Data da Despesa", value=data_obj)
            with c2:
                e_valor = st.number_input("Valor Ajustado (R$)", min_value=0.0, format="%.2f", value=float(row_editar['Valor']))
                tipos_lista = ["1 - Transporte", "2 - Refeições", "3 - Gráfica e material", "4 - Outros (especificar na descrição)"]
                tipo_idx = 0
                for i, t in enumerate(tipos_lista):
                    if row_editar['Tipo'] in t:
                        tipo_idx = i
                        break
                e_tipo = st.selectbox("Tipo de Despesa", tipos_lista, index=tipo_idx)
                
            e_desc = st.text_input("Descrição", value=row_editar['Descrição'])
            e_obs = st.text_area("Novas Observações", value=row_editar['Observações'])
            
            btn_salvar = st.form_submit_button("Reenviar Solicitação ao Gestor")
            
        if btn_salvar:
            if not e_nome.strip() or not e_cc.strip() or e_valor <= 0 or not e_desc.strip():
                st.error("Preencha todos os campos obrigatórios corretamente.")
            else:
                idx = df_geral[df_geral['ID'] == id_editar].index[0]
                
                # Recalcula limite para o novo valor
                cod_tipo = e_tipo.split(" - ")[0]
                novo_limite = st.session_state['limites_despesa'].get(cod_tipo, 0.0)
                comp_atual = row_editar['Comprovante']
                
                novo_alerta = "✅ OK"
                if e_valor > novo_limite: novo_alerta = "⚠️ Valor Excedente"
                if comp_atual == "Não Anexado":
                    if e_valor > novo_limite: novo_alerta = "⚠️ Valor Excedente e Sem Comprovante"
                    else: novo_alerta = "⚠️ Sem Comprovante"
                
                # Atualiza o banco de dados
                st.session_state['banco_reembolsos'].at[idx, 'Colaborador'] = e_nome
                st.session_state['banco_reembolsos'].at[idx, 'Centro de Custo'] = e_cc
                st.session_state['banco_reembolsos'].at[idx, 'Data Despesa'] = e_data.strftime("%d/%m/%Y")
                st.session_state['banco_reembolsos'].at[idx, 'Tipo'] = e_tipo.split(" - ")[1]
                st.session_state['banco_reembolsos'].at[idx, 'Descrição'] = e_desc
                st.session_state['banco_reembolsos'].at[idx, 'Observações'] = e_obs
                st.session_state['banco_reembolsos'].at[idx, 'Valor'] = e_valor
                st.session_state['banco_reembolsos'].at[idx, 'Alerta'] = novo_alerta
                st.session_state['banco_reembolsos'].at[idx, 'Status'] = "Aguardando Avaliação"
                st.session_state['banco_reembolsos'].at[idx, 'Justificativa Gestor'] = "-" # Zera a justificativa após correção
                
                st.success(f"Solicitação {id_editar} atualizada e reenviada ao gestor com sucesso!")
                st.rerun()

    st.subheader("Histórico Global de Solicitações")
    st.dataframe(df_geral, use_container_width=True, hide_index=True)

# ==========================================
# TELA 2: GESTOR / TÉCNICO
# ==========================================
elif perfil_selecionado == "2. Gestor / Técnico (Avaliação)":
    st.title("👔 Área de Avaliação e Conformidade")
    
    with st.expander("⚙️ Configurar Limites de Valores (Políticas de Despesa)"):
        st.markdown("Defina os tetos de gastos. Valores excedentes gerarão alertas amarelos na solicitação.")
        col_L1, col_L2, col_L3, col_L4 = st.columns(4)
        with col_L1: st.session_state['limites_despesa']["1"] = st.number_input("1 - Transporte (R$)", value=st.session_state['limites_despesa']["1"], format="%.2f")
        with col_L2: st.session_state['limites_despesa']["2"] = st.number_input("2 - Refeições (R$)", value=st.session_state['limites_despesa']["2"], format="%.2f")
        with col_L3: st.session_state['limites_despesa']["3"] = st.number_input("3 - Gráfica (R$)", value=st.session_state['limites_despesa']["3"], format="%.2f")
        with col_L4: st.session_state['limites_despesa']["4"] = st.number_input("4 - Outros (R$)", value=st.session_state['limites_despesa']["4"], format="%.2f")
    
    st.divider()
    st.subheader("Análise de Solicitações")
    
    pendentes_gestor = df_geral[df_geral['Status'] == "Aguardando Avaliação"]
    
    if pendentes_gestor.empty:
        st.info("Nenhuma solicitação aguardando sua avaliação.")
    else:
        st.dataframe(pendentes_gestor, use_container_width=True, hide_index=True)
        
        col_acao1, col_acao2 = st.columns(2)
        with col_acao1: 
            id_selecionado = st.selectbox("Selecione o ID para avaliar:", pendentes_gestor['ID'])
        with col_acao2: 
            acao = st.radio("Ação:", ["Aprovar Pedido", "Rejeitar Parcialmente", "Rejeitar Totalmente"])
            
        justificativa_gestor = st.text_area("Justificativa (Opcional para Aprovação / Obrigatória sugerida para Rejeição)", help="Motivo em caso de rejeição parcial ou total.")
        
        if st.button("Confirmar Decisão"):
            if acao == "Aprovar Pedido":
                novo_status = "Aprovado - Aguardando Financeiro"
            elif acao == "Rejeitar Parcialmente":
                novo_status = "Rejeitado Parcialmente"
            else:
                novo_status = "Rejeitado Totalmente"
                
            idx = df_geral[df_geral['ID'] == id_selecionado].index[0]
            st.session_state['banco_reembolsos'].at[idx, 'Status'] = novo_status
            st.session_state['banco_reembolsos'].at[idx, 'Justificativa Gestor'] = justificativa_gestor if justificativa_gestor.strip() else "-"
            
            st.success(f"Status do ID {id_selecionado} atualizado para: {novo_status}!")
            st.rerun()

    st.divider()
    st.subheader("Histórico Global de Solicitações")
    st.dataframe(df_geral, use_container_width=True, hide_index=True)

# ==========================================
# TELA 3: FINANCEIRO
# ==========================================
elif perfil_selecionado == "3. Financeiro (Pagamento)":
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
