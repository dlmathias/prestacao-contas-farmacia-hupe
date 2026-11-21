import re
from decimal import Decimal
import pdfplumber


def br_to_decimal(valor_str: str) -> Decimal:
    """Converte string numérica PT-BR (ex: '1.234.567,8900') para Decimal."""
    if not valor_str:
        return Decimal("0.0000")
    limpo = valor_str.strip().replace(".", "").replace(",", ".")
    try:
        return Decimal(limpo)
    except Exception:
        return Decimal("0.0000")


def extrair_balancete_mv(arquivo_pdf) -> dict:
    """
    Lê o Relatório de Balancete Contábil Mensal - Analítico (SoulMV)
    extraindo a seção 'Total Geral por Tp. Documento:' (Página 2) ou o texto completo.
    """
    texto_completo = ""
    with pdfplumber.open(arquivo_pdf) as pdf:
        for pagina in pdf.pages:
            texto_completo += "\n" + (pagina.extract_text() or "")

    # Foca na seção consolidada "Total Geral por Tp. Documento:" se existir
    if "Total Geral por Tp. Documento:" in texto_completo:
        bloco = texto_completo.split("Total Geral por Tp. Documento:")[-1]
    else:
        bloco = texto_completo

    padrao_num = r"(\d{1,3}(?:\.\d{3})*,\d{4})"

    def buscar_valores(rotulo_regex: str) -> list[Decimal]:
        m = re.search(rotulo_regex + r"([^\n]*)", bloco)
        if m:
            return [br_to_decimal(n) for n in re.findall(padrao_num, m.group(1))]
        return []

    dados = {
        "estoque": "93 - CAF" if "93" in texto_completo else ("74 - CAQ" if "74" in texto_completo else "Desconhecido"),
        "saldo_anterior": Decimal("0.0000"),
        "nota_fiscal_total": Decimal("0.0000"),
        "transferencias_ent": Decimal("0.0000"),
        "transferencias_sai": Decimal("0.0000"),
        "contagem_ent": Decimal("0.0000"),
        "contagem_sai": Decimal("0.0000"),
        "saida_setor": Decimal("0.0000"),
        "baixa": Decimal("0.0000"),
        "emprestimo_recebido": Decimal("0.0000"),
        "pgto_emprestimo_recebido": Decimal("0.0000"),
        "pgto_emprestimo_concedido": Decimal("0.0000"),
        "emprestimo_concedido": Decimal("0.0000"),
        "devolucao_fornecedor": Decimal("0.0000"),
        "devolucao_setor": Decimal("0.0000"),
        "devolucao_paciente": Decimal("0.0000"),
        "doacao": Decimal("0.0000"),
        "ajuste_ent": Decimal("0.0000"),
        "ajuste_sai": Decimal("0.0000"),
        "total_entradas": Decimal("0.0000"),
        "total_saidas": Decimal("0.0000"),
        "saldo_atual": Decimal("0.0000"),
    }

    # Campos de 1 valor
    campos_simples = [
        (r"Nota Fiscal(?!\s+não\s+Cobrada)", "nota_fiscal_total"),
        (r"Saída para Setor", "saida_setor"),
        (r"Baixa", "baixa"),
        (r"Empréstimo Recebido", "emprestimo_recebido"),
        (r"Pagamento de Empréstimo Recebido", "pgto_emprestimo_recebido"),
        (r"Pagamento de Empréstimo Concedido", "pgto_emprestimo_concedido"),
        (r"Empréstimo Concedido", "emprestimo_concedido"),
        (r"Devolução de Fornecedor", "devolucao_fornecedor"),
        (r"Devolução de Setor", "devolucao_setor"),
        (r"Devolução de Paciente", "devolucao_paciente"),
        (r"Doação de Produtos", "doacao"),
    ]
    for regex, chave in campos_simples:
        vals = buscar_valores(regex)
        if vals:
            dados[chave] = vals[0]

    # Campos de 2 valores (Entrada e Saída)
    for regex, ch_ent, ch_sai in [
        (r"Transferências(?!\s+entre)", "transferencias_ent", "transferencias_sai"),
        (r"Contagem", "contagem_ent", "contagem_sai"),
        (r"Ajuste", "ajuste_ent", "ajuste_sai"),
    ]:
        vals = buscar_valores(regex)
        if len(vals) >= 2:
            dados[ch_ent], dados[ch_sai] = vals[0], vals[1]

    # Totais Gerais (4 valores: Saldo Anterior, Entradas, Saídas, Saldo Atual)
    totais = buscar_valores(r"Total Geral:")
    if len(totais) >= 4:
        dados["saldo_anterior"] = totais[0]
        dados["total_entradas"] = totais[1]
        dados["total_saidas"] = totais[2]
        dados["saldo_atual"] = totais[3]

    return dados


def extrair_total_sides(arquivo_pdf) -> Decimal:
    """
    Lê o Relatório de Entrada de Produtos Sintético por Fornecedor (NOTA FISCAL SIDES)
    e extrai o Total Geral em R$.
    """
    if arquivo_pdf is None:
        return Decimal("0.0000")

    texto_completo = ""
    with pdfplumber.open(arquivo_pdf) as pdf:
        for pagina in pdf.pages:
            texto_completo += "\n" + (pagina.extract_text() or "")

    match = re.search(r"Total Geral:\s*(\d{1,3}(?:\.\d{3})*,\d{2})", texto_completo)
    if match:
        return br_to_decimal(match.group(1) + "00")
    return Decimal("0.0000")
