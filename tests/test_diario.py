"""Seção 10 (+ lembretes da seção 8): peso, água, refeições, resumo/adesão, metas, lembretes opt-in."""
from conftest import Servidor, chaves, norm

TEL = "41988887777"
JULGAMENTO = ("parabens", "otimo", "muito bem", "que pena", "cuidado", "engordou", "emagreceu", "ganhou", "perdeu", "ruim")


def rodar(api, agora=None):
    st, r = api.post("/api/tarefas/rodar", {"agora": agora} if agora else {})
    assert st == 200, (st, r)
    return r["enviadas"]


def test_peso_registra_serie_e_resposta_neutra(api):
    pid = api.paciente("Maria", TEL)
    assert "nenhum peso" in norm(api.msg(TEL, "qual meu peso?"))
    r = norm(api.msg(TEL, "peso 82,5"))
    assert "registrad" in r and "82,5 kg" in r
    for palavra in JULGAMENTO:
        assert palavra not in r, palavra
    r = norm(api.msg(TEL, "hoje pesei 82 kg"))
    assert "registrad" in r and "82,0 kg" in r
    for palavra in JULGAMENTO:
        assert palavra not in r, palavra
    st, r = api.post(f"/api/pacientes/{pid}/pesos", {"peso": 80, "quando": "2026-11-05T10:00"})
    assert st == 201 and "id" in r
    assert api.post(f"/api/pacientes/{pid}/pesos", {"peso": 10})[0] == 422
    assert api.post(f"/api/pacientes/{pid}/pesos", {"peso": "x"})[0] == 422
    assert api.post(f"/api/pacientes/{pid}/pesos", {"peso": 70, "quando": "ontem"})[0] == 422
    assert api.post("/api/pacientes/9999/pesos", {"peso": 70})[0] == 404
    st, s = api.get(f"/api/pacientes/{pid}/pesos")
    assert [(p["peso"], p["origem"], p["quando"]) for p in s["pesos"]] == \
        [(82.5, "chat", "2026-10-06T09:00"), (82.0, "chat", "2026-10-06T09:00"), (80.0, "equipe", "2026-11-05T10:00")]
    assert s["variacao"] == -2.5
    assert "80,0 kg" in norm(api.msg(TEL, "qual meu peso?"))   # último = maior `quando`


def test_peso_fora_da_faixa_e_sem_cadastro(api):
    pid = api.paciente("Maria", TEL)
    r = norm(api.msg(TEL, "peso 500"))
    assert "entre 20 e 400" in r
    assert api.get(f"/api/pacientes/{pid}/pesos")[1]["pesos"] == [] and api.get(f"/api/pacientes/{pid}/pesos")[1]["variacao"] is None
    assert "cadastro" in norm(api.msg("41900001111", "pesei 70 kg"))   # telefone sem paciente
    assert "cadastro" in norm(api.msg("41900001111", "2 copos"))


def test_agua_copos_total_do_dia_e_meta(api):
    pid = api.paciente("Maria", TEL)
    r = norm(api.msg(TEL, "2 copos"))
    assert "registrad" in r and "2 copos" in r
    r = norm(api.msg(TEL, "tomei 1 copo de água"))   # "tomei" não vira refeição: a regra da água vem antes
    assert "3 copos" in r
    api.put(f"/api/pacientes/{pid}/metas", {"meta_agua_copos": 8})
    assert "4 de 8 copos" in norm(api.msg(TEL, "mais 1 copo"))
    st, d = api.get(f"/api/pacientes/{pid}/diario")
    assert [(x["tipo"], x["valor"]) for x in d["registros"]] == [("agua", 2), ("agua", 1), ("agua", 1)]
    assert d["resumo"]["agua_copos"] == 4 and d["resumo"]["refeicoes_feitas"] == 0


def test_refeicao_feita_e_pulada_por_nome(api):
    pid = api.paciente("Maria", TEL)
    api.plano(pid)
    r = norm(api.msg(TEL, "pulei o lanche da tarde"))
    assert "registrad" in r and "lanche da tarde" in r
    r = norm(api.msg(TEL, "comi tudo no café da manhã"))
    assert "registrad" in r and "cafe da manha" in r
    st, d = api.get(f"/api/pacientes/{pid}/diario")
    assert [(x["tipo"], x["refeicao"], x["status"]) for x in d["registros"]] == \
        [("refeicao", "Lanche da tarde", "pulada"), ("refeicao", "Café da manhã", "feita")]
    assert d["resumo"]["refeicoes_feitas"] == 1 and d["resumo"]["refeicoes_puladas"] == 1 and d["resumo"]["adesao_pct"] == 50.0


def test_refeicao_sem_nome_usa_horario_e_exige_plano(dados):
    s = Servidor(dados)   # 09:00 (um servidor por vez no mesmo --dados: parar antes de subir o próximo)
    api = s.subir()
    pid = api.paciente("Maria", TEL)
    assert "nutricionista" in norm(api.msg(TEL, "comi"))
    assert api.get(f"/api/pacientes/{pid}/diario")[1]["registros"] == []
    api.plano(pid)
    assert "cafe da manha" in norm(api.msg(TEL, "comi"))     # última refeição com horário ≤ 09:00 = 07:30
    assert "cafe da manha" in norm(api.msg(TEL, "pulei"))
    s.parar()
    s2 = Servidor(dados, agora="2026-10-06T13:00")
    api2 = s2.subir()
    assert "almoco" in norm(api2.msg(TEL, "ja fiz"))         # 12:30 ≤ 13:00
    s2.parar()
    api3 = Servidor(dados, agora="2026-10-06T06:00").subir()
    assert "cafe da manha" in norm(api3.msg(TEL, "comi"))    # nenhuma ≤ 06:00 → a primeira do plano
    regs = api3.get(f"/api/pacientes/{pid}/diario")[1]["registros"]
    assert [(x["refeicao"], x["status"]) for x in regs] == \
        [("Café da manhã", "feita"), ("Café da manhã", "pulada"), ("Almoço", "feita"), ("Café da manhã", "feita")]


def test_diario_resumo_e_filtro_por_dia(dados):
    s = Servidor(dados)   # 06/10
    api = s.subir()
    pid = api.paciente("Maria", TEL)
    api.plano(pid)
    api.msg(TEL, "2 copos")
    api.msg(TEL, "pulei o jantar")
    s.parar()
    api2 = Servidor(dados, agora="2026-10-07T21:00").subir()
    api2.msg(TEL, "3 copos")
    api2.msg(TEL, "fiz o jantar")
    api2.msg(TEL, "peso 80 kg")
    st, d = api2.get(f"/api/pacientes/{pid}/diario")
    assert [x["tipo"] for x in d["registros"]] == ["agua", "refeicao", "agua", "refeicao", "peso"]
    assert [x["quando"][:10] for x in d["registros"]] == ["2026-10-06"] * 2 + ["2026-10-07"] * 3
    chaves(d["resumo"], agua_copos=5, refeicoes_feitas=1, refeicoes_puladas=1, adesao_pct=50.0, fotos=0)
    st, d = api2.get(f"/api/pacientes/{pid}/diario?de=2026-10-07&ate=2026-10-07")
    assert len(d["registros"]) == 3 and d["resumo"]["agua_copos"] == 3 and d["resumo"]["adesao_pct"] == 100.0
    st, d = api2.get(f"/api/pacientes/{pid}/diario?de=2026-10-08&ate=2026-10-08")
    assert d["registros"] == [] and d["resumo"]["adesao_pct"] == 0


def test_metas_put_get_e_validacoes(api):
    pid = api.paciente("Maria", TEL)
    chaves(api.get(f"/api/pacientes/{pid}/metas")[1], lembretes_agua=[], lembretes_refeicoes=False, meta_agua_copos=None)
    st, r = api.put(f"/api/pacientes/{pid}/metas", {"lembretes_agua": ["09:00", "15:00"]})
    assert st == 200
    chaves(r, lembretes_agua=["09:00", "15:00"], lembretes_refeicoes=False, meta_agua_copos=None)
    st, r = api.put(f"/api/pacientes/{pid}/metas", {"meta_agua_copos": 8, "lembretes_refeicoes": True})
    chaves(r, lembretes_agua=["09:00", "15:00"], lembretes_refeicoes=True, meta_agua_copos=8)
    assert api.put(f"/api/pacientes/{pid}/metas", {"lembretes_agua": ["9h"]})[0] == 422
    assert api.put(f"/api/pacientes/{pid}/metas", {"meta_agua_copos": 0})[0] == 422
    assert api.put(f"/api/pacientes/{pid}/metas", {"meta_agua_copos": None})[1]["meta_agua_copos"] is None
    assert api.put("/api/pacientes/9999/metas", {"meta_agua_copos": 8})[0] == 404
    assert api.get(f"/api/pacientes/{pid}/dados")[1]["metas"]["lembretes_agua"] == ["09:00", "15:00"]


def test_lembretes_de_agua_so_na_janela_de_tolerancia(api):
    pid = api.paciente("Maria", TEL)
    api.put(f"/api/pacientes/{pid}/metas", {"lembretes_agua": ["09:00", "15:00"]})
    assert rodar(api) == 1                            # agora 09:00: 09:00 ≤ 09:00 ≤ 10:00
    [m] = api.saida("lembrete")
    assert m["telefone"] == "+5541988887777" and "agua" in norm(m["texto"]) and m["agendamento_id"] is None
    assert rodar(api) == 0                            # já enviado hoje
    assert rodar(api, "2026-10-06T10:30") == 0        # 09:00 + 60 min = 10:00 < 10:30: perdeu, não acumula; 15:00 ainda não
    assert rodar(api, "2026-10-06T15:59") == 1        # 15:00 ≤ 15:59 ≤ 16:00
    assert rodar(api, "2026-10-06T16:01") == 0
    assert rodar(api, "2026-10-07T09:30") == 1        # outro dia, 09:00 de novo
    assert len(api.saida("lembrete")) == 3


def test_lembretes_de_refeicao_seguem_o_plano(api):
    pid = api.paciente("Maria", TEL)
    api.plano(pid)
    api.put(f"/api/pacientes/{pid}/metas", {"lembretes_refeicoes": True})
    assert rodar(api) == 0                            # 07:30 + 60 = 08:30 < 09:00; 10:00 > 09:00
    assert rodar(api, "2026-10-06T12:45") == 1        # almoço 12:30
    [m] = api.saida("lembrete")
    t = norm(m["texto"])
    assert "almoco" in t and "arroz, feijao, frango grelhado e salada" in t and "quinoa com legumes e peixe" in t
    assert rodar(api, "2026-10-06T12:50") == 0
    api.put(f"/api/pacientes/{pid}/metas", {"lembretes_refeicoes": False})
    assert rodar(api, "2026-10-06T16:10") == 0


def test_parar_lembretes_e_nao_contatar(api):
    p1 = api.paciente("Maria", "41999990001")
    p2 = api.paciente("José", "41999990002")
    for p in (p1, p2):
        api.put(f"/api/pacientes/{p}/metas", {"lembretes_agua": ["09:00"], "meta_agua_copos": 8})
    api.agenda(p2, "2026-10-07T09:00", profissional="lia")
    assert "lembretes" in norm(api.msg("41999990002", "parar lembretes"))
    chaves(api.get(f"/api/pacientes/{p2}/metas")[1], lembretes_agua=[], lembretes_refeicoes=False, meta_agua_copos=8)
    assert api.get(f"/api/pacientes/{p2}/dados")[1]["paciente"]["nao_contatar"] is False
    api.msg("41999990001", "parar")
    assert rodar(api) == 1                            # só a confirmação do José; nenhum lembrete
    assert api.saida("lembrete") == []
    assert [m["tipo"] for m in api.saida()] == ["confirmacao"]
