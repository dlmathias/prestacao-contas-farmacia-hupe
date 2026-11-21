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
    e retorna os valores por rubrica e os totais gerais.
    """
    texto_completo = ""
    with pdfplumber.open(arquivo_pdf) as pdf:
        for pagina in pdf.pages:
            texto_completo += "\n" + (pagina.extract_text() or "")

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

    padrao_num = r"(\d{1,3}(?:\.\d{3})*,\d{4})"

    for linha in texto_completo.splitlines():
        nums = [br_to_decimal(n) for n in re.findall(padrao_num, linha)]
        if not nums:
            continue

        if linha.startswith("Nota Fiscal ") and "não Cobrada" not in linha:
            dados["nota_fiscal_total"] = nums[0]
        elif linha.startswith("Transferências ") and "entre empresas" not in linha:
            if len(nums) >= 2:
                dados["transferencias_ent"], dados["transferencias_sai"] = nums[0], nums[1]
        elif linha.startswith("Contagem "):
            if len(nums) >= 2:
                dados["contagem_ent"], dados["contagem_sai"] = nums[0], nums[1]
        elif linha.startswith("Saída para Setor"):
            dados["saida_setor"] = nums[0]
        elif linha.startswith("Baixa "):
            dados["baixa"] = nums[0]
        elif linha.startswith("Empréstimo Recebido"):
            dados["emprestimo_recebido"] = nums[0]
        elif linha.startswith("Pagamento de Empréstimo Recebido"):
            dados["pgto_emprestimo_recebido"] = nums[0]
        elif linha.startswith("Pagamento de Empréstimo Concedido"):
            dados["pgto_emprestimo_concedido"] = nums[0]
        elif linha.startswith("Empréstimo Concedido"):
            dados["emprestimo_concedido"] = nums[0]
        elif linha.startswith("Devolução de Fornecedor"):
            dados["devolucao_fornecedor"] = nums[0]
        elif linha.startswith("Devolução de Setor"):
            dados["devolucao_setor"] = nums[0]
        elif linha.startswith("Devolução de Paciente"):
            dados["devolucao_paciente"] = nums[0]
        elif linha.startswith("Doação de Produtos"):
            dados["doacao"] = nums[0]
        elif linha.startswith("Ajuste "):
            if len(nums) >= 2:
                dados["ajuste_ent"], dados["ajuste_sai"] = nums[0], nums[1]
        elif linha.startswith("Total Geral:") or linha.startswith("Total da Espécie:"):
            if len(nums) >= 4:
                dados["saldo_anterior"] = nums[0]
                dados["total_entradas"] = nums[1]
                dados["total_saidas"] = nums[2]
                dados["saldo_atual"] = nums[3]

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
