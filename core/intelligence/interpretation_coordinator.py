"""
AgroClima Café

Interpretation Coordinator

Camada de coordenação das interpretações produzidas pelas regras de
Inteligência. Não calcula indicadores, FRI ou severidade e não substitui
nenhuma regra especialista.

Versão..........: 1.3
"""

from copy import deepcopy


class InterpretationCoordinator:
    """
    Coordena os resultados das regras em uma representação única.

    Responsabilidades:
        - preservar a interpretação original;
        - garantir identidade mínima da regra;
        - preservar a versão da regra quando fornecida;
        - associar a interpretação ao município/contexto avaliado;
        - aplicar metadados de coordenação;
        - eliminar duplicação do mesmo rule_id dentro da execução;
        - manter canais e severidades produzidos pelas regras.

    Não é responsável por:
        - calcular FRI;
        - recalcular score;
        - alterar severity/confidence;
        - gerar regras;
        - gerar insights, recomendações ou alertas.
    """

    VERSION = "1.3"
    POLICY_VERSION = "1.0"

    def coordinate(self, context, rule_results):
        """
        Produz a representação coordenada dos resultados desta execução.

        O método é determinístico: preserva a ordem de chegada e mantém
        somente a primeira ocorrência de cada identificação de regra.

        A versão da regra é somente transportada do resultado original.
        O Coordinator não inventa nem infere uma versão ausente.
        """
        if not isinstance(context, dict):
            context = {}

        if not isinstance(rule_results, list):
            return []

        coordinated = []
        seen = set()

        for result in rule_results:
            if not isinstance(result, dict):
                continue

            item = deepcopy(result)
            rule_id = item.get("rule_id") or item.get("id")

            # Resultado sem identidade de regra não pode ser coordenado
            # como interpretação governada.
            if not rule_id:
                continue

            if rule_id in seen:
                continue

            seen.add(rule_id)

            item.setdefault("rule_id", rule_id)

            # Preserva exclusivamente a versão já fornecida pela regra.
            # None continua sendo None quando a regra não a fornece.
            item["rule_version"] = item.get("rule_version")

            item.setdefault("provenance", "rule_engine")
            item.setdefault("municipio_id", context.get("municipio_id"))
            item.setdefault("municipio_nome", context.get("municipio_nome"))
            item["coordinator_version"] = self.VERSION
            item["policy_version"] = self.POLICY_VERSION
            item["coordination_status"] = "coordinated"

            coordinated.append(item)

        return coordinated
