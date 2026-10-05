"""Seção 6: conversa — FAQ, não entendi, humano, emergência, alerta, parar, agendamento pelo chat (com modalidade), link."""
from conftest import Servidor, com_config, norm

TEL = "41988887777"
TEL_N = "+5541988887777"
LINK = "https://meet.exemplo/sala-xyz"


def fila(api):
    st, r = api.get("/api/atendimento-humano")
    assert st == 200
    return r["fila"]


def test_faq_responde_exatamente(api):
    assert api.msg(TEL, "Oi, vcs aceitam convenio?") == "Atendemos Unimed e particular, com recibo para reembolso."
    assert api.msg(TEL, "Onde fica o consultório de vocês?") == "Rua das Flores, 100, sala 5, Batel, Curitiba."
    assert api.msg(TEL, "tem estacionamento aí?") == "Temos convênio com o estacionamento ao lado (1 hora grátis)."


def test_nao_entendi_e_depois_passa_para_humano(api):
    r = norm(api.msg(TEL, "posso tomar whey depois do treino?"))   # fora do FAQ e do plano: o bot não orienta
    assert "nao entendi" in r and "atendente" in r
    assert fila(api) == []
    api.msg(TEL, "e creatina serve?")
    [f] = fila(api)
    assert f["telefone"] == TEL_N and f["prioridade"] == "normal" and f["motivo"] == "nao_entendi"


def test_pedido_de_atendente(api):
    assert "atendente" in norm(api.msg(TEL, "quero falar com um atendente"))
    [f] = fila(api)
    assert f["prioridade"] == "normal" and f["motivo"] == "atendente"


def test_emergencia_fisica(api):
    r = norm(api.msg(TEL, "Estou com DOR NO PEITO e falta de ar"))
    assert "192" in r and "pronto-socorro" in r
    [f] = fila(api)
    assert f["prioridade"] == "alta" and f["telefone"] == TEL_N and f["motivo"] == "emergencia"


def test_alerta_comportamental(api):
    pid = api.paciente("Maria", TEL)
    api.plano(pid)
    r = norm(api.msg(TEL, "vomitei de proposito depois do almoço"))
    assert "188" in r and "nutricionista" in r
    [f] = fila(api)
    assert f["prioridade"] == "alta" and f["motivo"] == "alerta"
    assert api.get(f"/api/pacientes/{pid}/diario")[1]["registros"] == []   # "almoço" não virou registro


def test_emergencia_vence_agendamento(api):
    r = norm(api.msg(TEL, "quero marcar consulta, estou sangrando muito"))
    assert "192" in r
    assert api.agendamentos("2026-10-06") == []


def test_agendamento_pelo_chat_paciente_novo_online(api):
    assert "nome" in norm(api.msg(TEL, "quero marcar uma consulta"))
    r = api.msg(TEL, "João Souza")
    assert "1 - Primeira consulta" in r and "2 - Retorno" in r and "3 - Bioimpedância" in r
    r = api.msg(TEL, "1")   # primeira consulta = 60 min: 11:00 lia, 11:00 marcos, 14:00 lia
    assert "1) 06/10 11:00 com Dra. Lia" in r
    assert "2) 06/10 11:00 com Dr. Marcos" in r
    assert "3) 06/10 14:00 com Dra. Lia" in r
    r = api.msg(TEL, "2")
    assert "1 - Presencial" in r and "2 - Online" in r
    r = norm(api.msg(TEL, "2"))
    assert "agendad" in r and "06/10" in r and "11:00" in r and "online" in r
    [a] = api.agendamentos("2026-10-06")
    assert (a["telefone"], a["servico"], a["profissional"], a["inicio"], a["status"], a["modalidade"], a["link"]) == \
        (TEL_N, "primeira", "marcos", "2026-10-06T11:00", "agendado", "online", None)
    st, d = api.get(f"/api/pacientes/{a['paciente_id']}/dados")
    assert d["paciente"]["nome"] == "João Souza"
    assert d["paciente"]["consentimento_marketing"] is False


def test_agendamento_pelo_chat_paciente_conhecido_e_opcao_invalida(api):
    api.paciente("Maria", TEL)
    r = api.msg(TEL, "quero agendar")
    assert "1 - Primeira consulta" in r
    r = api.msg(TEL, "2")   # retorno (30 min)
    assert "1) 06/10 11:00 com Dra. Lia" in r
    r = api.msg(TEL, "9")
    assert "1) 06/10 11:00 com Dra. Lia" in r   # repete as opções
    r = api.msg(TEL, "1")
    assert "1 - Presencial" in r
    r = api.msg(TEL, "7")
    assert "1 - Presencial" in r   # repete
    r = norm(api.msg(TEL, "1"))
    assert "agendad" in r and "online" not in r
    [a] = api.agendamentos("2026-10-06")
    assert (a["servico"], a["profissional"], a["inicio"], a["modalidade"]) == ("retorno", "lia", "2026-10-06T11:00", "presencial")


def test_chat_nao_pergunta_modalidade_sem_atendimento_online(dados):
    com_config(dados, atende_online=False)
    api = Servidor(dados).subir()
    api.paciente("Maria", TEL)
    api.msg(TEL, "quero agendar")
    api.msg(TEL, "2")
    r = norm(api.msg(TEL, "1"))   # escolheu o horário: agenda direto, sem perguntar presencial/online
    assert "agendad" in r and "06/10" in r and "11:00" in r
    assert "1 - presencial" not in r and "2 - online" not in r
    [a] = api.agendamentos("2026-10-06")
    assert a["modalidade"] == "presencial"


def test_chat_oferece_proximos_dias_quando_hoje_lota(api):
    pid = api.paciente("Ocupa", "41900000001")
    for prof in ("lia", "marcos"):
        for h in ("11:00", "11:30", "14:00", "14:30", "15:00", "15:30", "16:00", "16:30", "17:00", "17:30"):
            assert api.agenda(pid, f"2026-10-06T{h}", "retorno", prof)[0] == 201
    api.msg(TEL, "quero agendar")
    api.msg(TEL, "Pedro")
    r = api.msg(TEL, "2")
    assert "1) 07/10 08:00 com Dra. Lia" in r and "2) 07/10 08:00 com Dr. Marcos" in r and "3) 07/10 08:30 com Dra. Lia" in r


def test_cancelar_sai_do_fluxo(api):
    api.paciente("Maria", TEL)
    api.msg(TEL, "quero agendar")
    assert "cancelad" in norm(api.msg(TEL, "cancelar"))
    assert api.msg(TEL, "tem estacionamento") == "Temos convênio com o estacionamento ao lado (1 hora grátis)."
    assert api.agendamentos("2026-10-06") == []


def test_parar_bloqueia_contato(api):
    pid = api.paciente("Maria", TEL)
    api.agenda(pid, "2026-10-07T09:00", profissional="lia")
    api.put(f"/api/pacientes/{pid}/metas", {"lembretes_agua": ["09:00"]})
    assert "nao vai mais receber" in norm(api.msg(TEL, "PARAR"))
    st, r = api.post("/api/tarefas/rodar", {})
    assert st == 200 and r["enviadas"] == 0
    assert api.saida() == []   # nem confirmação nem lembrete foram criados
    st, d = api.get(f"/api/pacientes/{pid}/dados")
    assert d["paciente"]["nao_contatar"] is True


def test_link_da_consulta_pelo_chat(api):
    pid = api.paciente("Maria", TEL)
    assert "nao encontrei" in norm(api.msg(TEL, "qual o link da consulta?"))
    _, a = api.agenda(pid, "2026-10-07T09:00", "retorno", "lia", modalidade="online")
    assert "equipe" in norm(api.msg(TEL, "me manda o link"))
    api.post(f"/api/agendamentos/{a['id']}/link", {"link": LINK})
    assert LINK in api.msg(TEL, "qual o link da consulta?")
    api.post(f"/api/agendamentos/{a['id']}/cancelar")
    assert "nao encontrei" in norm(api.msg(TEL, "link"))
