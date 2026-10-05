"""Seções 3 e 5: horários, agendamento, conflito, cancelamento, remarcação, modalidade/link, pacientes.
Agora = ter 06/10/2026 09:00; antecedência 2 h → primeiro horário 11:00. Fixture: lia (primeira, retorno,
bioimpedância) e marcos (primeira, retorno); primeira = 60 min, retorno e bioimpedância = 30 min."""
import threading

from conftest import Servidor, com_config

LINK = "https://meet.exemplo/sala-abc"


def horarios(api, servico, data, profissional=None):
    rota = f"/api/horarios?servico={servico}&data={data}"
    if profissional:
        rota += f"&profissional={profissional}"
    st, r = api.get(rota, token=None)
    assert st == 200, (st, r)
    return [(h["inicio"], h["profissional"]) for h in r["horarios"]]


def test_horarios_respeitam_antecedencia_e_ordem(api):
    h = horarios(api, "retorno", "2026-10-06")
    assert h[:3] == [("2026-10-06T11:00", "lia"), ("2026-10-06T11:00", "marcos"), ("2026-10-06T11:30", "lia")]
    assert len(h) == 20  # manhã 11:00 e 11:30 + tarde 14:00..17:30 (8), dois profissionais


def test_horarios_cabem_na_janela(api):
    h = horarios(api, "primeira", "2026-10-06")   # 60 min: 11:00 cabe (termina 12:00); 11:30 não; tarde até 17:00
    assert [i for i, p in h if p == "lia"] == ["2026-10-06T11:00"] + [f"2026-10-06T{x}" for x in
                                                                      ("14:00", "14:30", "15:00", "15:30", "16:00", "16:30", "17:00")]
    assert {p for _, p in h} == {"lia", "marcos"} and len(h) == 16


def test_horarios_so_de_quem_faz_o_servico(api):
    h = horarios(api, "bioimpedancia", "2026-10-07")   # quarta inteira, só a Dra. Lia faz
    assert len(h) == 16 and {p for _, p in h} == {"lia"}
    assert h[0] == ("2026-10-07T08:00", "lia") and h[-1] == ("2026-10-07T17:30", "lia")
    assert ("2026-10-07T12:00", "lia") not in h
    assert horarios(api, "bioimpedancia", "2026-10-07", "marcos") == []
    assert api.get("/api/horarios?servico=retorno&data=2026-10-07&profissional=zeca", token=None)[0] == 404


def test_sem_horario_em_feriado_domingo_e_sabado_reduzido(api):
    assert horarios(api, "retorno", "2026-10-12") == []   # feriado (segunda)
    assert horarios(api, "retorno", "2026-10-11") == []   # domingo
    assert len(horarios(api, "retorno", "2026-10-10")) == 16   # sábado 08–12: 8 × 2 profissionais


def test_agendar_e_listar(api):
    pid = api.paciente()
    st, r = api.agenda(pid, "2026-10-07T09:00", servico="primeira", profissional="lia")
    assert st == 201, r
    assert r["status"] == "agendado" and r["inicio"] == "2026-10-07T09:00" and r["fim"] == "2026-10-07T10:00"
    assert r["modalidade"] == "presencial" and r["link"] is None
    [a] = api.agendamentos("2026-10-07")
    assert (a["paciente_id"], a["nome"], a["telefone"], a["servico"], a["profissional"], a["modalidade"]) == \
        (pid, "Maria Silva", "+5541999990001", "primeira", "lia", "presencial")
    assert ("2026-10-07T09:00", "lia") not in horarios(api, "retorno", "2026-10-07")
    assert ("2026-10-07T09:30", "lia") not in horarios(api, "retorno", "2026-10-07")
    assert ("2026-10-07T10:00", "lia") in horarios(api, "retorno", "2026-10-07")


def test_invalidos_422(api):
    pid = api.paciente()
    for inicio, servico, prof, extra in [
        ("2026-10-07T12:00", "retorno", "lia", {}),        # almoço
        ("2026-10-07T09:15", "retorno", "lia", {}),        # fora da grade
        ("2026-10-07T11:30", "primeira", "lia", {}),       # 60 min não cabe até 12:00
        ("2026-10-06T10:00", "retorno", "lia", {}),        # antes da antecedência (agora 09:00 + 2 h)
        ("2026-10-12T09:00", "retorno", "lia", {}),        # feriado
        ("2026-10-07T09:00", "bioimpedancia", "marcos", {}),  # profissional não faz
        ("2026-10-07T09:00", "retorno", "lia", {"modalidade": "telefone"}),  # modalidade inválida
    ]:
        assert api.agenda(pid, inicio, servico, prof, **extra)[0] == 422, (inicio, servico, prof, extra)


def test_inexistentes_404(api):
    pid = api.paciente()
    assert api.agenda(9999, "2026-10-07T09:00")[0] == 404
    assert api.agenda(pid, "2026-10-07T09:00", servico="xyz")[0] == 404
    assert api.agenda(pid, "2026-10-07T09:00", profissional="zeca")[0] == 404
    assert api.get("/api/horarios?servico=xyz&data=2026-10-07", token=None)[0] == 404
    assert api.post("/api/agendamentos/9999/cancelar")[0] == 404


def test_sobreposicao_409(api):
    pid = api.paciente()
    assert api.agenda(pid, "2026-10-07T09:00", "retorno", "lia")[0] == 201
    assert api.agenda(pid, "2026-10-07T08:30", "primeira", "lia")[0] == 409   # 08:30–09:30 sobrepõe 09:00–09:30
    assert api.agenda(pid, "2026-10-07T09:30", "retorno", "lia")[0] == 201    # encosta, não sobrepõe
    assert api.agenda(pid, "2026-10-07T09:00", "retorno", "marcos")[0] == 201


def test_sem_profissional_pega_o_primeiro_livre(api):
    pid = api.paciente()
    st1, a1 = api.agenda(pid, "2026-10-07T09:00")
    st2, a2 = api.agenda(pid, "2026-10-07T09:00")
    st3, _ = api.agenda(pid, "2026-10-07T09:00")
    assert (st1, st2, st3) == (201, 201, 409)
    assert (a1["profissional"], a2["profissional"]) == ("lia", "marcos")


def test_concorrencia_um_so_vence(api):
    pid = api.paciente()
    codigos = []

    def tenta():
        codigos.append(api.agenda(pid, "2026-10-08T10:00", "retorno", "lia")[0])

    ts = [threading.Thread(target=tenta) for _ in range(10)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert sorted(codigos) == [201] + [409] * 9


def test_cancelar_libera(api):
    pid = api.paciente()
    _, a = api.agenda(pid, "2026-10-07T09:00", "retorno", "lia")
    st, r = api.post(f"/api/agendamentos/{a['id']}/cancelar")
    assert st == 200 and r["status"] == "cancelado"
    assert api.post(f"/api/agendamentos/{a['id']}/cancelar")[0] == 409
    assert ("2026-10-07T09:00", "lia") in horarios(api, "retorno", "2026-10-07")
    assert api.agenda(pid, "2026-10-07T09:00", "retorno", "lia")[0] == 201
    assert api.por_id("2026-10-07", a["id"])["status"] == "cancelado"   # cancelado continua na listagem


def test_remarcar_mantem_modalidade_e_link(api):
    pid = api.paciente()
    _, a = api.agenda(pid, "2026-10-07T09:00", "retorno", "lia", modalidade="online")
    api.post(f"/api/agendamentos/{a['id']}/link", {"link": LINK})
    api.agenda(pid, "2026-10-07T10:00", "retorno", "lia")
    assert api.post(f"/api/agendamentos/{a['id']}/remarcar", {"inicio": "2026-10-07T10:00"})[0] == 409
    assert api.post(f"/api/agendamentos/{a['id']}/remarcar", {"inicio": "2026-10-07T12:00"})[0] == 422
    assert api.post(f"/api/agendamentos/{a['id']}/remarcar", {"inicio": "2026-10-07T09:00"})[0] == 200  # o próprio horário
    st, r = api.post(f"/api/agendamentos/{a['id']}/remarcar", {"inicio": "2026-10-08T15:00"})
    assert st == 200 and r["id"] == a["id"] and r["inicio"] == "2026-10-08T15:00" and r["status"] == "agendado"
    assert r["modalidade"] == "online" and r["link"] == LINK
    assert ("2026-10-07T09:00", "lia") in horarios(api, "retorno", "2026-10-07")


def test_presenca(api):
    pid = api.paciente()
    _, a = api.agenda(pid, "2026-10-07T09:00", profissional="lia")
    _, b = api.agenda(pid, "2026-10-07T10:00", profissional="lia")
    assert api.post(f"/api/agendamentos/{a['id']}/presenca", {"compareceu": True})[1]["status"] == "realizado"
    assert api.post(f"/api/agendamentos/{b['id']}/presenca", {"compareceu": False})[1]["status"] == "falta"
    # falta continua ocupando o horário (ativo)
    assert ("2026-10-07T10:00", "lia") not in horarios(api, "retorno", "2026-10-07")


def test_consulta_online_e_link(api):
    pid = api.paciente()
    st, a = api.agenda(pid, "2026-10-07T09:00", "retorno", "lia", modalidade="online")
    assert st == 201 and a["modalidade"] == "online" and a["link"] is None
    st, r = api.post(f"/api/agendamentos/{a['id']}/link", {"link": LINK})
    assert st == 200 and r["id"] == a["id"] and r["link"] == LINK
    assert api.por_id("2026-10-07", a["id"])["link"] == LINK
    _, p = api.agenda(pid, "2026-10-07T10:00", "retorno", "lia")   # presencial por padrão
    assert api.post(f"/api/agendamentos/{p['id']}/link", {"link": LINK})[0] == 422
    assert api.post(f"/api/agendamentos/{a['id']}/link", {"link": ""})[0] == 422
    assert api.post("/api/agendamentos/9999/link", {"link": LINK})[0] == 404


def test_sem_atendimento_online_recusa_online(dados):
    com_config(dados, atende_online=False)
    api = Servidor(dados).subir()
    pid = api.paciente()
    assert api.agenda(pid, "2026-10-07T09:00", "retorno", "lia", modalidade="online")[0] == 422
    assert api.agenda(pid, "2026-10-07T09:00", "retorno", "lia")[0] == 201


def test_telefone_normalizado_e_duplicado(api):
    st, r = api.post("/api/pacientes", {"nome": "A", "telefone": "(41) 99999-0001"})
    assert st == 201
    st2, r2 = api.post("/api/pacientes", {"nome": "A", "telefone": "+55 41 99999 0001"})
    assert st2 == 200 and r2["id"] == r["id"]
    st3, r3 = api.post("/api/pacientes", {"nome": "B", "telefone": "41 3333-4444"})
    assert st3 == 201 and r3["id"] != r["id"]
    st, dados = api.get(f"/api/pacientes/{r3['id']}/dados")
    assert dados["paciente"]["telefone"] == "+554133334444"
    for ruim in ("123", "abc", "+55 41 9999", "4199999000112"):
        assert api.post("/api/pacientes", {"nome": "C", "telefone": ruim})[0] == 400, ruim
