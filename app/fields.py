"""Campos WTForms customizados para o padrão brasileiro."""
from decimal import Decimal, InvalidOperation
from wtforms import DecimalField
from wtforms.widgets import TextInput


class _BRDecimalWidget(TextInput):
    """Renderiza como <input type="text" inputmode="decimal"> em vez de type="number".

    O type="number" do navegador descarta a vírgula ao colar valores no formato
    brasileiro (ex.: 56.816,74 → 56.81674). Como texto, o valor colado é preservado
    e o parsing no servidor (BRDecimalField) resolve o formato.
    """
    def __call__(self, field, **kwargs):
        kwargs.setdefault('inputmode', 'decimal')
        return super().__call__(field, **kwargs)


class BRDecimalField(DecimalField):
    """DecimalField que aceita formato brasileiro (1.234,56) e americano (1234.56)."""

    widget = _BRDecimalWidget()

    def _value(self):
        """Exibe o valor no formato brasileiro (1.234,56)."""
        if self.raw_data:
            return self.raw_data[0]
        if self.data is None:
            return ''
        casas = self.places if self.places is not None else 2
        try:
            texto = f'{self.data:,.{casas}f}'  # formato en: 1,234.56
        except (ValueError, TypeError):
            return str(self.data)
        # en (1,234.56) → pt-BR (1.234,56)
        return texto.replace(',', 'X').replace('.', ',').replace('X', '.')

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
