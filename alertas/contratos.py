"""Contrato entre o módulo de detecção (PB02/PB03) e o painel de alertas (PB04)."""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class AnomaliaDetectada:
    """Uma semana com ``ResultadoDeteccao.anomalia = True`` pronta para virar alerta (RF004).

    ``semana_inicio`` é a segunda-feira armazenada pela ingestão; ``ano_epi`` e
    ``semana_epi`` são a SE real (domingo a sábado), calculada pelo calendário.
    """

    agravo_codigo: str
    agravo_nome: str
    municipio_codigo: str
    municipio_nome: str
    ano_epi: int
    semana_epi: int
    semana_inicio: date
    observado: int
    media: float
    desvio: float
    limite: float
    janela_semanas: int
    fator_desvio: int
    resultado_id: str
    carga_id: str = ""

    def assinatura(self) -> tuple:
        """Insumos do cálculo. Iguais => reprocessar a carga não muda o alerta (RNF005)."""
        return (
            self.observado,
            round(self.media, 6),
            round(self.desvio, 6),
            round(self.limite, 6),
            self.janela_semanas,
            self.fator_desvio,
        )
