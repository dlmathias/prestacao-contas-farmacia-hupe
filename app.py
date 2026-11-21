import io
import json
from pathlib import Path
from decimal import Decimal
import pandas as pd
import streamlit as st
from parser_soulmv import extrair_balancete_mv, extrair_total_sides

st.set_page_config(page_title="Anexo III IN-42 | Farmácia HUPE", layout="wide")

ARQUIVO_DADOS = Path("data/historico_2026.json")
ARQUIVO_DADOS.parent.mkdir(parents=True, exist_ok=True)


def carregar_historico() -> dict:
    if ARQUIVO_DADOS.exists():
        return json.loads(ARQUIVO_DADOS.read_text(encoding="utf-8"))
    return {"CAF_93": {}, "CAQ_74": {}}


def salvar_historico(dados: dict):
    ARQUIVO_DADOS.write_text(json.dumps(dados, indent=2, ensure_ascii=False), encoding="utf-8")


def fmt_br(val: float) -> str:
    return f"{val:,.4f}".replace(",", "X").replace(".", ",").replace("X", ".")


st.title("Demonstrativo Mensal de Movimentação — Anexo III (IN-42)")
st.caption("HUPE / UERJ — Serviço de Farmácia (CAF Estoque 93 e CAQ Estoque 74)")

# Barra lateral: Seleção de Unidade e Período
with st.sidebar:
    st.header("Parâmetros da Prestação")
    unidade = st.radio(
        "Unidade / Estoque:",
        options=["CAF_93", "CAQ_74"],
        format_func=lambda x: "Estoque 93 — Farmácia CAF 1" if x == "CAF_93" else "Estoque 74 — CAQ (Produtos Químicos)"
    )
    ano = st.selectbox("Exercício:", ["2026", "2027"], index=0)
    mes = st.selectbox(
        "Mês Vigente:",
        ["01 - Janeiro", "02 - Fevereiro", "03 - Março", "04 - Abril",
         "05 - Maio", "06 - Junho", "07 - Julho", "08 - Agosto",
         "09 - Setembro", "10 - Outubro", "11 - Novembro", "12 - Dezembro"],
        index=6
    )
    sem_sides = st.checkbox("Mês sem compras SIDES (SIDES = R$ 0,00)", value=False)

historico = carregar_historico()
chave_periodo = f"{ano}-{mes[:2]}"

# Área de Upload dos Relatórios SoulMV
col1, col2 = st.columns(2)
with col1:
    pdf_balancete = st.file_uploader("1. Balancete Contábil Mensal (R_BALANCO_CONTABIL.pdf)", type=["pdf"])
with col2:
    pdf_sides = st.file_uploader(
        "2. Entrada Sintética SIDES (R_EST_ENT_PROD_SINT.pdf)",
        type=["pdf"],
        disabled=sem_sides
    )

if pdf_balancete is not None:
    bal = extrair_balancete_mv(pdf_balancete)
    val_sides = Decimal("0.0000") if sem_sides else extrair_total_sides(pdf_sides)
    val_nao_sides = bal["nota_fiscal_total"] - val_sides

    # Consolidação no padrão Anexo III (Entradas C, Saídas D/O e Saídas E)
    entradas_c = (
        bal["contagem_ent"]
        + bal["transferencias_ent"]
        + bal["emprestimo_recebido"]
        + bal["pgto_emprestimo_concedido"]
        + bal["devolucao_setor"]
        + bal["devolucao_paciente"]
        + bal["doacao"]
        + bal["ajuste_ent"]
    )
    saidas_e = (
        bal["contagem_sai"]
        + bal["transferencias_sai"]
        + bal["baixa"]
        + bal["emprestimo_concedido"]
        + bal["pgto_emprestimo_recebido"]
        + bal["devolucao_fornecedor"]
        + bal["ajuste_sai"]
    )
    # Coluna O (Requisição de Uso NE - SIAFE) = Saída para Setor (M) - Requisição SIDES (Q = D)
    req_uso_ne = bal["saida_setor"] - val_sides
    saldo_calculado = bal["saldo_anterior"] + val_nao_sides + val_sides + entradas_c - (req_uso_ne + val_sides + saidas_e)
    conciliado = abs(saldo_calculado - bal["saldo_atual"]) < Decimal("0.001")

    st.divider()
    st.subheader(f"Pré-visualização e Conciliação — {mes} / {ano}")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Saldo Anterior", f"R$ {fmt_br(float(bal['saldo_anterior']))}")
    m2.metric("Total Entradas", f"R$ {fmt_br(float(bal['total_entradas']))}")
    m3.metric("Total Saídas", f"R$ {fmt_br(float(bal['total_saidas']))}")
    m4.metric("Saldo Final", f"R$ {fmt_br(float(bal['saldo_atual']))}")

    if conciliado:
        st.success("Conciliação 100% fechada com o Balancete Contábil do SoulMV.")
    else:
        st.error(f"Divergência detectada! Saldo calculado: {fmt_br(float(saldo_calculado))}")

    registro = {
        "Periodo": chave_periodo,
        "Unidade": unidade,
        "Saldo_Anterior": float(bal["saldo_anterior"]),
        "Compras_NE_Nao_SIDES": float(val_nao_sides),
        "Compras_SIDES": float(val_sides),
        "Entradas_C_Contagem": float(bal["contagem_ent"]),
        "Entradas_C_Transferencias": float(bal["transferencias_ent"]),
        "Entradas_C_Emp_Recebido": float(bal["emprestimo_recebido"]),
        "Entradas_C_Pgto_Emp_Concedido": float(bal["pgto_emprestimo_concedido"]),
        "Entradas_C_Dev_Setor": float(bal["devolucao_setor"]),
        "Entradas_C_Dev_Paciente": float(bal["devolucao_paciente"]),
        "Entradas_C_Doacao": float(bal["doacao"]),
        "Entradas_C_Ajuste": float(bal["ajuste_ent"]),
        "Total_Entradas": float(bal["total_entradas"]),
        "Saida_Setor_Total_M": float(bal["saida_setor"]),
        "Req_Uso_NE_SIAFE_O": float(req_uso_ne),
        "Req_Uso_SIDES_Q": float(val_sides),
        "Saidas_E_Contagem": float(bal["contagem_sai"]),
        "Saidas_E_Transferencias": float(bal["transferencias_sai"]),
        "Saidas_E_Baixa": float(bal["baixa"]),
        "Saidas_E_Emp_Concedido": float(bal["emprestimo_concedido"]),
        "Saidas_E_Pgto_Emp_Recebido": float(bal["pgto_emprestimo_recebido"]),
        "Saidas_E_Dev_Compras": float(bal["devolucao_fornecedor"]),
        "Saidas_E_Ajuste": float(bal["ajuste_sai"]),
        "Total_Saidas": float(bal["total_saidas"]),
        "Saldo_Final": float(bal["saldo_atual"]),
    }

    st.dataframe(pd.DataFrame([registro]), use_container_width=True)

    if st.button("Gravar Mês no Painel Consolidado", type="primary"):
        historico[unidade][chave_periodo] = registro
        salvar_historico(historico)
        st.toast(f"Período {chave_periodo} salvo em {unidade}!")

# Painel Consolidado e Exportação para SEI-RJ
st.divider()
st.subheader(f"Painel Consolidado — {unidade.replace('_', ' ')}")

registros_unidade = list(historico.get(unidade, {}).values())
if registros_unidade:
    df_consol = pd.DataFrame(registros_unidade).sort_values("Periodo")
    st.dataframe(df_consol, use_container_width=True)

    # Exportação Excel (.xlsx)
    buffer_xlsx = io.BytesIO()
    with pd.ExcelWriter(buffer_xlsx, engine="openpyxl") as writer:
        df_consol.to_excel(writer, sheet_name="Anexo_III_Consolidado", index=False)

    st.download_button(
        label="Exportar Planilha Excel (.xlsx) para Conferência / SEI",
        data=buffer_xlsx.getvalue(),
        file_name=f"Anexo_III_IN42_{unidade}_{ano}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
else:
    st.info("Nenhum mês gravado ainda para esta unidade. Envie o PDF acima para alimentar o painel.")
