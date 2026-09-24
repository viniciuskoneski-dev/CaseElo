import streamlit as st
import pandas as pd
from datetime import datetime
import io

# ==========================================
# Configuração e Banco de Dados Temporário
# ==========================================
st.set_page_config(page_title="Sistema de Reembolso EloGroup", page_icon="💸", layout="wide")

if 'banco_reembolsos' not in st.session_state:
    st.session_state['banco_reembolsos'] = pd.DataFrame(columns=[
        "ID", "Colaborador", "Centro de Custo", "Data Despesa", "Tipo", 
        "Descrição", "Observações", "Valor", "Comprovante", "Alerta", "Status", "Justificativa Gestor"
    ])

if 'limites_despesa' not in st.session_state:
    st.session_state['limites_despesa'] = {
        "1": 300.0, "2": 75.0, "3": 100.0, "4": 50.0    
    }

if 'temp_solicitacao' not in st.session_state:
    st.session_state['temp_solicitacao'] = None

df_geral = st.session_state['banco_reembolsos']

# Função para gerar o template Excel atualizado com legendas e status
def gerar_planilha_modelo():
    output = io.BytesIO()
    # Estruturando o DataFrame como uma matriz para posicionar as legendas acima da tabela
    layout = [
        ["Funcionário:", "", "TD", "Tipos de despesa:", "STATUS", "Legenda de Status:"],
        ["Mês-Base:", "", "1", "Transporte", "1", "Aguardando Gestor"],
        ["", "", "2", "Refeições", "2", "Rejeitada Parcialmente (Volta ao solicitante)"],
        ["", "", "3", "Gráfica e material", "3", "Rejeitada Totalmente"],
        ["", "", "4", "Outros (especificar)", "4", "Aguardando Financeiro"],
        ["", "", "", "", "5", "Paga e Arquivada"],
        ["", "", "", "", "", ""], # Linha em branco para respiro visual
        ["Data de Execução", "TD", "Descrição", "Valor R$", "Centro Custo", "Obs (opcional)", "Status"]
    ]
    df_layout = pd.DataFrame(layout)
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_layout.to_excel(writer, index=False, header=False, sheet_name="Reembolso")
    return output.getvalue()

# Dicionários de conversão dos códigos numéricos da planilha para o padrão do sistema
mapa_td = {
    1: "Transporte",
    2: "Refeições",
    3: "Gráfica e material",
    4: "Outros (especificar na descrição)"
}

mapa_status = {
    1: "Aguardando Avaliação",
    2: "Rejeitado Parcialmente",
    3: "Rejeitado Totalmente",
    4: "Aprovado - Aguardando Financeiro",
    5: "Pago e Arquivado"
}

# ==========================================
# Navegação Lateral
# ==========================================
st.sidebar.title("Navegação de Perfis")
st.sidebar.markdown("Selecione sua visão para testar o fluxo.")
perfil_selecionado = st.sidebar.radio("Acessar como:", 
    ["1. Colaborador (Solicitante)", 
     "2. Gestor / Técnico (Avaliação)", 
     "3. Migração Legado (Excel)",
     "4. Financeiro (Pagamento)"]
)

st.sidebar.divider()
st.sidebar.metric("Total de Solicitações", len(st.session_state['banco_reembolsos']))

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
        
        if temp['Valor'] > limite_teto:
            st.warning(f"⚠️ **Inadequação de Valor:** R$ {temp['Valor']:.2f} excede o limite de R$ {limite_teto:.2f}.")
        if temp['Comprovante'] == "Não Anexado":
            st.warning("⚠️ **Falta de Comprovante:** Você não anexou o cupom fiscal.")
        if temp['Valor'] <= limite_teto and temp['Comprovante'] != "Não Anexado":
            st.success("✅ **Tudo Certo!** Sua solicitação está de acordo com as políticas.")

        if st.button("Confirmar e Enviar Definitivamente", type="primary"):
            st.session_state['banco_reembolsos'] = pd.concat([st.session_state['banco_reembolsos'], pd.DataFrame([temp])], ignore_index=True)
            st.session_state['temp_solicitacao'] = None
            st.success("✅ Solicitação enviada com sucesso!")
            st.rerun()

    st.divider()

    df_rejeitados = st.session_state['banco_reembolsos'][st.session_state['banco_reembolsos']['Status'] == "Rejeitado Parcialmente"]
    if not df_rejeitados.empty:
        st.subheader("✏️ Correção de Solicitações Rejeitadas Parcialmente")
        st.dataframe(df_rejeitados, use_container_width=True, hide_index=True)
        
        id_editar = st.selectbox("Selecione o ID para corrigir:", df_rejeitados['ID'])
        row_editar = df_rejeitados[df_rejeitados['ID'] == id_editar].iloc[0]
        
        with st.form(key="form_editar", clear_on_submit=False):
            st.info(f"**Justificativa do Gestor:** {row_editar['Justificativa Gestor']}")
            c1, c2 = st.columns(2)
            with c1:
                e_nome = st.text_input("Nome", value=row_editar['Colaborador'])
                e_cc = st.text_input("Centro de Custo", value=row_editar['Centro de Custo'])
                data_obj = datetime.strptime(row_editar['Data Despesa'], "%d/%m/%Y").date()
                e_data = st.date_input("Data da Despesa", value=data_obj)
            with c2:
                e_valor = st.number_input("Valor Ajustado (R$)", min_value=0.0, format="%.2f", value=float(row_editar['Valor']))
                tipos_lista = ["1 - Transporte", "2 - Refeições", "3 - Gráfica e material", "4 - Outros (especificar na descrição)"]
                tipo_idx = next(i for i, t in enumerate(tipos_lista) if row_editar['Tipo'] in t)
                e_tipo = st.selectbox("Tipo de Despesa", tipos_lista, index=tipo_idx)
                
            e_desc = st.text_input("Descrição", value=row_editar['Descrição'])
            e_obs = st.text_area("Novas Observações", value=row_editar['Observações'])
            
            if st.form_submit_button("Reenviar Solicitação ao Gestor"):
                if not e_nome.strip() or not e_cc.strip() or e_valor <= 0 or not e_desc.strip():
                    st.error("Preencha todos os campos obrigatórios corretamente.")
                else:
                    idx = st.session_state['banco_reembolsos'][st.session_state['banco_reembolsos']['ID'] == id_editar].index[0]
                    cod_tipo = e_tipo.split(" - ")[0]
                    novo_limite = st.session_state['limites_despesa'].get(cod_tipo, 0.0)
                    comp_atual = row_editar['Comprovante']
                    
                    novo_alerta = "✅ OK"
                    if e_valor > novo_limite: novo_alerta = "⚠️ Valor Excedente"
                    if comp_atual == "Não Anexado":
                        novo_alerta = "⚠️ Valor Excedente e Sem Comprovante" if e_valor > novo_limite else "⚠️ Sem Comprovante"
                    
                    st.session_state['banco_reembolsos'].loc[idx, ['Colaborador', 'Centro de Custo', 'Data Despesa', 'Tipo', 'Descrição', 'Observações', 'Valor', 'Alerta', 'Status', 'Justificativa Gestor']] = [
                        e_nome, e_cc, e_data.strftime("%d/%m/%Y"), e_tipo.split(" - ")[1], e_desc, e_obs, e_valor, novo_alerta, "Aguardando Avaliação", "-"
                    ]
                    st.success("Solicitação atualizada e reenviada!")
                    st.rerun()

    st.subheader("Histórico Global de Solicitações")
    st.dataframe(st.session_state['banco_reembolsos'], use_container_width=True, hide_index=True)

# ==========================================
# TELA 2: GESTOR / TÉCNICO
# ==========================================
elif perfil_selecionado == "2. Gestor / Técnico (Avaliação)":
    st.title("👔 Área de Avaliação e Conformidade")
    
    with st.expander("⚙️ Configurar Limites de Valores (Políticas de Despesa)"):
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
            
        justificativa_gestor = st.text_area("Justificativa (Opcional para Aprovação / Obrigatória sugerida para Rejeição)")
        
        if st.button("Confirmar Decisão"):
            novo_status = "Aprovado - Aguardando Financeiro" if acao == "Aprovar Pedido" else acao
            idx = df_geral[df_geral['ID'] == id_selecionado].index[0]
            st.session_state['banco_reembolsos'].at[idx, 'Status'] = novo_status
            st.session_state['banco_reembolsos'].at[idx, 'Justificativa Gestor'] = justificativa_gestor if justificativa_gestor.strip() else "-"
            st.success("Status atualizado!")
            st.rerun()

    st.divider()
    st.subheader("Histórico Global de Solicitações")
    st.dataframe(df_geral, use_container_width=True, hide_index=True)

# ==========================================
# TELA 3: MIGRAÇÃO LEGADO (EXCEL)
# ==========================================
elif perfil_selecionado == "3. Migração Legado (Excel)":
    st.title("📂 Importação de Planilha Histórica")
    st.markdown("Importe os registros antigos baseados na planilha padrão. O sistema validará a conformidade das informações.")
    
    st.download_button(
        label="📥 Baixar Planilha Modelo",
        data=gerar_planilha_modelo(),
        file_name="Modelo_Reembolso_Legado.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    
    arquivo_upload = st.file_uploader("Faça o upload da planilha de reembolso (.xlsx)", type=["xlsx"])
    
    if arquivo_upload is not None:
        try:
            # Lendo a primeira linha para extrair o cabeçalho (Funcionário)
            df_cabecalho = pd.read_excel(arquivo_upload, header=None, nrows=1)
            funcionario_legado = str(df_cabecalho.iloc[0, 1]).strip() if pd.notna(df_cabecalho.iloc[0, 1]) else ""
            
            # Lendo a tabela de dados a partir da linha 8 (onde estão as colunas de dados)
            df_dados = pd.read_excel(arquivo_upload, skiprows=7)
            colunas_esperadas = ["Data de Execução", "TD", "Descrição", "Valor R$", "Centro Custo", "Obs (opcional)", "Status"]
            
            erros_planilha = []
            
            # Validação Estrutural
            if not funcionario_legado or funcionario_legado == "nan":
                erros_planilha.append("Cabeçalho: O nome do funcionário não foi preenchido na célula B1.")
            
            faltam_colunas = [col for col in colunas_esperadas if col not in df_dados.columns]
            if faltam_colunas:
                erros_planilha.append(f"Erro estrutural: As seguintes colunas não foram encontradas: {', '.join(faltam_colunas)}")
            
            registros_validos = []
            if not erros_planilha:
                df_dados.dropna(how='all', inplace=True) 
                
                for index, row in df_dados.iterrows():
                    linha_excel = index + 9 # Ajuste visual para a linha real do Excel
                    
                    data_exec = row['Data de Execução']
                    desc = str(row['Descrição'])
                    valor = row['Valor R$']
                    centro = str(row['Centro Custo'])
                    obs = str(row['Obs (opcional)']) if pd.notna(row['Obs (opcional)']) else ""
                    
                    # Validação e Cast das variáveis numéricas (TD e Status)
                    try:
                        td_val = int(row['TD'])
                        if td_val not in mapa_td:
                            erros_planilha.append(f"Linha {linha_excel}: O 'TD' deve ser de 1 a 4.")
                    except (ValueError, TypeError):
                        erros_planilha.append(f"Linha {linha_excel}: O 'TD' deve ser um número válido de 1 a 4.")
                        td_val = None

                    try:
                        status_val = int(row['Status'])
                        if status_val not in mapa_status:
                            erros_planilha.append(f"Linha {linha_excel}: O 'Status' deve ser de 1 a 5.")
                    except (ValueError, TypeError):
                        erros_planilha.append(f"Linha {linha_excel}: O 'Status' deve ser um número válido de 1 a 5.")
                        status_val = None
                    
                    # Demais validações
                    if pd.isna(data_exec): erros_planilha.append(f"Linha {linha_excel}: 'Data de Execução' inválida.")
                    if pd.isna(valor) or valor <= 0: erros_planilha.append(f"Linha {linha_excel}: O 'Valor' deve ser maior que zero.")
                    if pd.isna(row['Descrição']) or desc.strip() == "": erros_planilha.append(f"Linha {linha_excel}: A 'Descrição' é obrigatória.")
                    if pd.isna(row['Centro Custo']) or centro.strip() == "": erros_planilha.append(f"Linha {linha_excel}: O 'Centro Custo' é obrigatório.")
                    
                    if not erros_planilha and td_val and status_val:
                        limite = st.session_state['limites_despesa'].get(str(td_val), 0.0)
                        alerta_legado = "⚠️ Valor Excedente e Sem Comprovante" if valor > limite else "⚠️ Sem Comprovante (Legado)"
                        
                        registros_validos.append({
                            "ID": 0,
                            "Colaborador": funcionario_legado,
                            "Centro de Custo": centro,
                            "Data Despesa": pd.to_datetime(data_exec).strftime("%d/%m/%Y"),
                            "Tipo": mapa_td[td_val],
                            "Descrição": desc,
                            "Observações": obs,
                            "Valor": valor,
                            "Comprovante": "Importação Excel",
                            "Alerta": alerta_legado,
                            "Status": mapa_status[status_val],
                            "Justificativa Gestor": "Importado via sistema legado"
                        })
            
            if erros_planilha:
                st.error("🚨 A planilha contém erros de conformidade e não pode ser importada. Corrija os pontos abaixo e tente novamente:")
                for e in erros_planilha:
                    st.warning(e)
            elif not registros_validos:
                st.warning("A planilha não contém dados preenchidos para importação.")
            else:
                st.success("✅ Planilha validada com sucesso! As solicitações estão prontas para importação.")
                st.dataframe(pd.DataFrame(registros_validos)[['Colaborador', 'Data Despesa', 'Tipo', 'Valor', 'Centro de Custo', 'Status']], use_container_width=True)
                
                if st.button("Confirmar Importação para o Sistema", type="primary"):
                    proximo_id = len(st.session_state['banco_reembolsos']) + 1
                    for reg in registros_validos:
                        reg['ID'] = proximo_id
                        proximo_id += 1
                        
                    st.session_state['banco_reembolsos'] = pd.concat([st.session_state['banco_reembolsos'], pd.DataFrame(registros_validos)], ignore_index=True)
                    st.success("Registros legados importados com sucesso!")
                    
        except Exception as e:
            st.error(f"Erro ao processar o arquivo. Certifique-se de usar o Modelo padrão baixado. Detalhe técnico: {e}")

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
