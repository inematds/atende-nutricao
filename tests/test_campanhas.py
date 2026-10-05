"""Seção 11: campanha só com consentimento e trava mínima de publicidade (promessa de resultado, antes e depois)."""
import pytest

CASOS = [
    # texto, violações esperadas (None = permitido)
    ("Emagreça 10 kg com resultado garantido", {"promessa_resultado"}),
    ("Veja o antes e depois das nossas pacientes", {"antes_depois"}),
    ("Dieta 100% eficaz: veja o antes e depois", {"promessa_resultado", "antes_depois"}),
    ("Semana da alimentação saudável: agende sua consulta.", None),
]


@pytest.mark.parametrize("texto,esperado", CASOS, ids=[f"caso-{i}" for i in range(len(CASOS))])
def test_trava_minima_de_publicidade(api, texto, esperado):
    api.paciente("Maria", "41999990001", marketing=True)
    st, r = api.post("/api/campanhas", {"texto": texto})
    if esperado is None:
        assert st == 200 and r["enviadas"] == 1, (st, r)
        [m] = api.saida("campanha")
        assert m["texto"] == texto and m["telefone"] == "+5541999990001"
    else:
        assert st == 422, (st, r)
        assert set(r["violacoes"]) == esperado
        assert api.saida("campanha") == []


def test_publico_so_com_consentimento_e_sem_parar(api):
    api.paciente("Com", "41999990001", marketing=True)
    api.paciente("Sem", "41999990002", marketing=False)
    api.paciente("Parou", "41999990003", marketing=True)
    api.msg("41999990003", "parar")
    st, r = api.post("/api/campanhas", {"texto": "Semana da alimentação saudável: agende sua consulta."})
    assert st == 200 and r["enviadas"] == 1
    assert [m["telefone"] for m in api.saida("campanha")] == ["+5541999990001"]
    assert api.post("/api/campanhas", {"texto": "   "})[0] == 422
