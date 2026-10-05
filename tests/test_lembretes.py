"""Seções 7 e 8: confirmação automática (presencial e online), resposta à confirmação, lista de espera, retorno programado."""
from conftest import Servidor, norm

LINK = "https://meet.exemplo/sala-123"


def rodar(api, agora=None):
    st, r = api.post("/api/tarefas/rodar", {"agora": agora} if agora else {})
    assert st == 200, (st, r)
    return r["enviadas"]


def test_confirmacao_dentro_de_48h_uma_vez(api):
    p1 = api.paciente("Maria", "41999990001")
    p2 = api.paciente("José", "41999990002")
    _, a = api.agenda(p1, "2026-10-07T09:00", profissional="lia")   # 24 h depois de 06/10 09:00
    _, b = api.agenda(p2, "2026-10-09T09:00", profissional="lia")   # 72 h
    assert rodar(api) == 1
    [m] = api.saida("confirmacao")
    assert m["agendamento_id"] == a["id"] and m["telefone"] == "+5541999990001" and m["paciente_id"] == p1
    assert m["status"] == "simulado" and m["quando"] == "2026-10-06T09:00"
    t = norm(m["texto"])
    for trecho in ("retorno", "07/10", "09:00", "1", "2"):
        assert trecho in t, trecho
    assert "r$" not in t and "online" not in t
    assert rodar(api) == 0
    assert rodar(api, "2026-10-07T10:00") == 1   # 09/10 09:00 fica a 47 h
    assert [x["agendamento_id"] for x in api.saida("confirmacao")] == [a["id"], b["id"]]


def test_confirmacao_online_traz_link_ou_avisa(api):
    p = api.paciente("Maria", "41999990001")
    _, a = api.agenda(p, "2026-10-07T09:00", "retorno", "lia", modalidade="online")
    _, b = api.agenda(p, "2026-10-07T10:00", "retorno", "lia", modalidade="online")
    api.post(f"/api/agendamentos/{b['id']}/link", {"link": LINK})
    assert rodar(api) == 2
    por_ag = {m["agendamento_id"]: m["texto"] for m in api.saida("confirmacao")}
    assert "online" in norm(por_ag[a["id"]]) and "link" in norm(por_ag[a["id"]]) and LINK not in por_ag[a["id"]]
    assert "online" in norm(por_ag[b["id"]]) and LINK in por_ag[b["id"]]


def test_responder_1_confirma_so_com_texto_igual(api):
    p = api.paciente("Maria", "41999990001")
    _, a = api.agenda(p, "2026-10-07T09:00", profissional="lia")
    rodar(api)
    assert "registrad" in norm(api.msg("41999990001", "1 copo"))   # não é resposta à confirmação: vira registro de água
    assert api.por_id("2026-10-07", a["id"])["status"] == "agendado"
    assert "confirmad" in norm(api.msg("41999990001", "1"))
    assert api.por_id("2026-10-07", a["id"])["status"] == "confirmado"


def test_responder_2_cancela(api):
    p = api.paciente("Maria", "41999990001")
    _, a = api.agenda(p, "2026-10-07T09:00", profissional="lia")
    rodar(api)
    api.msg("41999990001", "nao comi nada hoje")   # contém "nao", mas não é igual a "nao": não cancela
    assert api.por_id("2026-10-07", a["id"])["status"] == "agendado"
    assert "cancelad" in norm(api.msg("41999990001", "2"))
    assert api.por_id("2026-10-07", a["id"])["status"] == "cancelado"


def test_lista_de_espera_oferece_e_agenda(api):
    p1 = api.paciente("Maria", "41999990001")
    p2 = api.paciente("José", "41999990002")
    p3 = api.paciente("Rita", "41999990003")
    _, a = api.agenda(p1, "2026-10-07T09:00", profissional="lia")
    assert api.post("/api/espera", {"paciente_id": p2, "servico": "retorno", "data": "2026-10-07"})[0] == 201
    assert api.post("/api/espera", {"paciente_id": p3, "servico": "retorno", "data": "2026-10-07"})[0] == 201
    api.post(f"/api/agendamentos/{a['id']}/cancelar")
    ofertas = api.saida("espera")
    assert [m["telefone"] for m in ofertas] == ["+5541999990002"]
    assert "09:00" in ofertas[0]["texto"] and "1" in ofertas[0]["texto"]
    assert "agendad" in norm(api.msg("41999990002", "1"))
    ativos = [x for x in api.agendamentos("2026-10-07") if x["status"] != "cancelado"]
    assert [(x["paciente_id"], x["inicio"], x["profissional"]) for x in ativos] == [(p2, "2026-10-07T09:00", "lia")]


def test_espera_horario_ja_ocupado_e_outro_dia_nao_recebe(api):
    p1 = api.paciente("Maria", "41999990001")
    p2 = api.paciente("José", "41999990002")
    p3 = api.paciente("Rita", "41999990003")
    p4 = api.paciente("Ana", "41999990004")
    _, a = api.agenda(p1, "2026-10-07T09:00", profissional="lia")
    api.post("/api/espera", {"paciente_id": p3, "servico": "retorno", "data": "2026-10-08"})   # outro dia
    api.post("/api/espera", {"paciente_id": p2, "servico": "retorno", "data": "2026-10-07"})
    api.post(f"/api/agendamentos/{a['id']}/cancelar")
    assert [m["telefone"] for m in api.saida("espera")] == ["+5541999990002"]
    assert api.agenda(p4, "2026-10-07T09:00", profissional="lia")[0] == 201
    assert "ocupado" in norm(api.msg("41999990002", "1"))


def test_cancelar_pela_conversa_dispara_espera(api):
    p1 = api.paciente("Maria", "41999990001")
    p2 = api.paciente("José", "41999990002")
    api.agenda(p1, "2026-10-07T09:00", profissional="lia")
    api.post("/api/espera", {"paciente_id": p2, "servico": "retorno", "data": "2026-10-07"})
    rodar(api)
    api.msg("41999990001", "2")
    assert [m["telefone"] for m in api.saida("espera")] == ["+5541999990002"]


def test_retorno_programado_e_servico_sem_retorno(api):
    p = api.paciente("Maria", "41999990001")
    p2 = api.paciente("José", "41999990002")
    _, a = api.agenda(p, "2026-10-07T09:00", servico="primeira", profissional="lia")
    _, b = api.agenda(p2, "2026-10-07T10:00", servico="bioimpedancia", profissional="lia")   # retorno_dias null
    api.post(f"/api/agendamentos/{a['id']}/presenca", {"compareceu": True})
    api.post(f"/api/agendamentos/{b['id']}/presenca", {"compareceu": True})
    # retorno = 07/10/2026 + 30 dias = 06/11/2026 (sexta); aviso a partir de 06/11 − 7 = 30/10
    assert rodar(api, "2026-10-29T09:00") == 0
    assert rodar(api, "2026-10-30T09:00") == 1
    [m] = api.saida("retorno")
    assert m["telefone"] == "+5541999990001" and "primeira consulta" in norm(m["texto"])
    assert rodar(api, "2026-10-31T09:00") == 0
    assert rodar(api, "2027-12-01T09:00") == 0   # bioimpedância nunca gera retorno; o da primeira já foi


def test_confirmacao_sobrevive_a_reinicio(dados):
    s = Servidor(dados)
    api = s.subir()
    p = api.paciente("Maria", "41999990001")
    _, a = api.agenda(p, "2026-10-07T09:00", profissional="lia")
    assert rodar(api) == 1
    s.parar()
    api2 = Servidor(dados).subir()
    assert rodar(api2) == 0
    assert "confirmad" in norm(api2.msg("41999990001", "sim"))
