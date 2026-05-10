"""Campos WTForms customizados para o padrão brasileiro."""
from decimal import Decimal, InvalidOperation
from wtforms import DecimalField


class BRDecimalField(DecimalField):
    """DecimalField que aceita formato brasileiro (1.234,56) e americano (1234.56)."""

    def process_formdata(self, valuelist):
        if not valuelist:
            self.data = None
            return
        raw = valuelist[0].strip().replace('\xa0', '').replace(' ', '')
        if not raw:
            self.data = None
            return
        # Detecta formato: se há vírgula, ela é o separador decimal (PT-BR)
        if ',' in raw:
            raw = raw.replace('.', '').replace(',', '.')
        # Se só há ponto, pode ser decimal americano ou separador de milhar
        # Heurística: se o ponto aparece exatamente a cada 3 dígitos sem parte decimal,
        # é separador de milhar → remove. Caso contrário, é decimal.
        elif raw.count('.') == 1:
            pass  # ponto como decimal americano — mantém
        else:
            raw = raw.replace('.', '')  # múltiplos pontos → separadores de milhar
        try:
            self.data = Decimal(raw)
        except (InvalidOperation, ValueError, ArithmeticError):
            self.data = None
            raise ValueError(self.gettext(
                'Valor inválido. Use vírgula como separador decimal (ex: 1.500,00 ou 1500,00).'
            ))
