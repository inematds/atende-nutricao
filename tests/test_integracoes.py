"""Seções 19 e 20: WhatsApp pela Evolution API (texto e foto) e atendimento interno pelo Telegram (contra servidor falso local)."""
import json
import time
import urllib.error
import urllib.request

from conftest import CHAT_EQUIPE, SEGREDO_TG, SEGREDO_WH, esperar, norm

TEL = "41988887777"
NUM = "5541988887777"
ESTAC = "Temos convênio com o estacionamento ao lado (1 hora grátis)."

_ids = iter(range(1, 10 ** 6))


def evo(api, texto=None, numero=NUM, msg_id=None, from_me=False, sufixo="@s.whatsapp.net",
        evento="messages.upsert", message=None, tipo="conversation", segredo=SEGREDO_WH):
    if message is None:
        message = {"conversation": texto}
    corpo = {"event": evento, "instance": "nutricao",
             "data": {"key": {"remoteJid": numero + sufixo, "fromMe": from_me, "id": msg_id or f"M{next(_ids)}"},
                      "pushName": "Paciente", "message": message, "messageType": tipo}}
    st, _ = api.post(f"/webhook/evolution/{segredo}", corpo, token=None)
    return st


def tg(api, texto, reply_to=None, chat=CHAT_EQUIPE, segredo=SEGREDO_TG):
    """Entrega um update do Telegram no webhook; devolve o status HTTP."""
    msg = {"message_id": next(_ids), "chat": {"id": chat}, "from": {"id": 7, "first_name": "Rita"}, "text": texto}
    if reply_to:
        msg["reply_to_message"] = {"message_id": reply_to}
    q = urllib.request.Request(api.base + "/webhook/telegram", method="POST",
                               data=json.dumps({"update_id": next(_ids), "message": msg}).encode(),
                               headers={"Content-Type": "application/json", "X-Telegram-Bot-Api-Secret-Token": segredo})
    try:
        with urllib.request.urlopen(q, timeout=10) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        return e.code


def textos_whats(externo):
    return [p["json"]["text"] for p in externo.whats()]


def textos_tg(externo):
    return [p["json"]["text"] for p in externo.telegram()]


def abre_atendimento(api, externo, tel=TEL):
    api.msg(tel, "quero falar com um atendente")
    assert esperar(lambda: len(externo.telegram()) >= 1)
    at = next(f for f in api.get("/api/atendimento-humano")[1]["fila"] if f["telefone"] == "+55" + tel)
    abertura = next(p for p in externo.telegram() if f"#{at['id']}" in p["json"]["text"])
    return at, abertura


# --- WhatsApp (Evolution) ---------------------------------------------------------------

def test_whatsapp_responde_pela_evolution(api_int, externo):
    assert evo(api_int, "tem estacionamento?") == 200
    assert esperar(lambda: len(externo.whats()) == 1)
    [p] = externo.whats()
    assert p["json"]["number"] == NUM and p["json"]["text"] == ESTAC
    assert p["headers"].get("apikey") == "chave-evo"


def test_whatsapp_ignora_o_que_nao_e_do_paciente(api_int, externo):
    assert evo(api_int, "tem estacionamento?", segredo="errado") == 404
    evo(api_int, "tem estacionamento?", msg_id="DUP1")
    evo(api_int, "tem estacionamento?", msg_id="DUP1")            # reenvio da Evolution
    evo(api_int, "tem estacionamento?", from_me=True)              # mensagem do próprio consultório
    evo(api_int, "tem estacionamento?", numero="1203630", sufixo="@g.us")  # grupo
    evo(api_int, "tem estacionamento?", evento="connection.update")
    time.sleep(0.8)
    assert textos_whats(externo) == [ESTAC]


def test_whatsapp_sem_texto_nem_foto(api_int, externo):
    evo(api_int, message={"audioMessage": {"seconds": 5}}, tipo="audioMessage")
    assert esperar(lambda: textos_whats(externo) == ["Por enquanto só consigo ler mensagens de texto e fotos."])


def test_whatsapp_foto_vira_registro_no_diario(api_int, externo):
    pid = api_int.paciente("Maria", TEL)
    foto = {"imageMessage": {"mimetype": "image/jpeg", "caption": "almoço de hoje", "url": "https://mmg.exemplo/abc.enc",
                             "fileLength": "12345"}}
    evo(api_int, message=foto, tipo="imageMessage", msg_id="FOTO-77")
    assert esperar(lambda: any("foto" in norm(t) and "registrad" in norm(t) for t in textos_whats(externo)))
    st, d = api_int.get(f"/api/pacientes/{pid}/diario")
    [reg] = d["registros"]
    assert (reg["tipo"], reg["mimetype"], reg["caption"], reg["message_id"], reg["origem"]) == \
        ("foto", "image/jpeg", "almoço de hoje", "FOTO-77", "whatsapp")
    assert d["resumo"]["fotos"] == 1
    assert not any(p["rota"].endswith("getBase64FromMediaMessage") for p in externo.pedidos)   # nunca baixa a mídia
    evo(api_int, numero="5541900001111", message=foto, tipo="imageMessage")   # telefone sem paciente
    assert esperar(lambda: any("cadastro" in norm(t) for t in textos_whats(externo)))


def test_whatsapp_agenda_e_avisa_equipe(api_int, externo):
    def tem(trecho):
        return esperar(lambda: any(trecho in norm(t) for t in textos_whats(externo)))

    evo(api_int, "quero marcar uma consulta")
    assert tem("nome")
    evo(api_int, "João Souza")
    assert tem("1 - primeira consulta")
    evo(api_int, "1")
    assert tem("2) 06/10 11:00 com dr. marcos")
    evo(api_int, "2")
    assert tem("1 - presencial")
    evo(api_int, "2")
    assert tem("agendad")
    [a] = api_int.agendamentos("2026-10-06")
    assert (a["telefone"], a["profissional"], a["inicio"], a["modalidade"]) == ("+" + NUM, "marcos", "2026-10-06T11:00", "online")
    assert esperar(lambda: any("Novo agendamento: 06/10 11:00 João Souza — Primeira consulta com Dr. Marcos" in t and "online" in t
                               for t in textos_tg(externo)))
    assert all(str(p["json"]["chat_id"]) == str(CHAT_EQUIPE) for p in externo.telegram())


def test_saida_pela_evolution_com_reenvio_e_plano_sincrono(api_int, externo):
    pid = api_int.paciente("Maria", TEL)
    api_int.agenda(pid, "2026-10-07T09:00", profissional="lia")
    externo.falhas = 1
    st, r = api_int.post("/api/tarefas/rodar", {})
    assert r["enviadas"] == 1                 # criada, mesmo com o envio falhando
    [m] = api_int.saida("confirmacao")
    assert m["status"] == "pendente"
    st, r = api_int.post("/api/tarefas/rodar", {})
    assert r["enviadas"] == 0 and r["reenviadas"] == 1
    assert api_int.saida("confirmacao")[0]["status"] == "enviado"
    [p] = externo.whats()
    assert p["json"]["number"] == NUM and "07/10" in p["json"]["text"]
    api_int.plano(pid)
    assert api_int.post(f"/api/pacientes/{pid}/plano/enviar")[0] == 200
    assert api_int.saida("plano")[0]["status"] == "enviado"   # rota síncrona: já tentou o envio
    assert any("Seu plano alimentar" in t and "16:00 Lanche da tarde" in t for t in textos_whats(externo))


# --- Telegram (equipe) ------------------------------------------------------------------

def test_abertura_vai_ao_grupo(api_int, externo):
    at, abertura = abre_atendimento(api_int, externo)
    t = abertura["json"]["text"]
    assert TEL in t.replace(" ", "").replace("-", "") and f"#{at['id']}" in t
    assert str(abertura["json"]["chat_id"]) == str(CHAT_EQUIPE)
    assert at["status"] == "aberto"


def test_alerta_marca_alta_e_comando_alertas(api_int, externo):
    normal, _ = abre_atendimento(api_int, externo)
    api_int.msg("41988880000", "parei de comer ha dias")
    assert esperar(lambda: any("ALTA" in t for t in textos_tg(externo)))
    alta = next(f for f in api_int.get("/api/atendimento-humano")[1]["fila"] if f["prioridade"] == "alta")
    assert alta["motivo"] == "alerta" and alta["id"] != normal["id"]
    n = len(externo.telegram())
    tg(api_int, "/alertas")
    assert esperar(lambda: any(f"#{alta['id']}" in t and f"#{normal['id']}" not in t for t in textos_tg(externo)[n:]))
    tg(api_int, f"/encerrar {alta['id']}")
    n = len(externo.telegram())
    tg(api_int, "/alertas")
    assert esperar(lambda: any("nenhum" in norm(t) for t in textos_tg(externo)[n:]))


def test_atendimento_aberto_silencia_bot_e_repassa(api_int, externo):
    at, abertura = abre_atendimento(api_int, externo)
    st, r = api_int.post("/api/mensagens", {"telefone": TEL, "texto": "tem estacionamento?"}, token=None)
    assert r["respostas"] == []
    assert esperar(lambda: any(p["json"].get("reply_to_message_id") == abertura["message_id"]
                               and "tem estacionamento" in p["json"]["text"] for p in externo.telegram()))
    # emergência e alerta continuam respondendo
    assert "192" in api_int.msg(TEL, "agora estou com falta de ar")
    assert "188" in api_int.msg(TEL, "estou pensando em me machucar")


def test_equipe_responde_em_cima_da_mensagem(api_int, externo):
    at, abertura = abre_atendimento(api_int, externo)
    assert tg(api_int, "Olá, aqui é a Rita. Como posso ajudar?", reply_to=abertura["message_id"]) == 200
    assert esperar(lambda: any(m["texto"] == "Olá, aqui é a Rita. Como posso ajudar?" for m in api_int.saida("humano")))
    assert api_int.saida("humano")[0]["telefone"] == "+" + NUM
    assert esperar(lambda: "Olá, aqui é a Rita. Como posso ajudar?" in textos_whats(externo))


def test_webhook_telegram_protegido(api_int, externo):
    at, abertura = abre_atendimento(api_int, externo)
    assert tg(api_int, "invasor", reply_to=abertura["message_id"], segredo="errado") == 401
    assert tg(api_int, "outro grupo", reply_to=abertura["message_id"], chat=-1009999) == 200
    time.sleep(0.5)
    assert api_int.saida("humano") == []


def test_comandos_responder_encerrar_fila(api_int, externo):
    at, _ = abre_atendimento(api_int, externo)
    tg(api_int, f"/responder {at['id']} Já te ligo")
    assert esperar(lambda: [m["texto"] for m in api_int.saida("humano")] == ["Já te ligo"])
    n = len(externo.telegram())
    tg(api_int, "/fila")
    assert esperar(lambda: any(f"#{at['id']}" in t for t in textos_tg(externo)[n:]))
    tg(api_int, f"/encerrar {at['id']}")
    assert esperar(lambda: api_int.get("/api/atendimento-humano")[1]["fila"] == [])
    assert api_int.msg(TEL, "tem estacionamento?") == ESTAC


def test_comando_agenda(api_int, externo):
    pid = api_int.paciente("Maria Lima", "41999990001")
    api_int.agenda(pid, "2026-10-07T09:00", "retorno", "lia")
    api_int.agenda(pid, "2026-10-07T14:00", "primeira", "lia", modalidade="online")
    _, c = api_int.agenda(pid, "2026-10-07T15:00", "retorno", "marcos")
    api_int.post(f"/api/agendamentos/{c['id']}/cancelar")
    tg(api_int, "/agenda 2026-10-07")

    def achou():
        return any("09:00 Maria Lima — Retorno (Dra. Lia)" in t and "14:00 Maria Lima — Primeira consulta (Dra. Lia) [online]" in t
                   and "15:00" not in t for t in textos_tg(externo))
    assert esperar(achou)


def test_equipe_responde_e_encerra_pela_pagina(api_int, externo):
    at, _ = abre_atendimento(api_int, externo)
    assert api_int.post(f"/api/atendimento-humano/{at['id']}/responder", {"texto": "Pode vir às 10h"})[0] == 200
    assert [m["texto"] for m in api_int.saida("humano")] == ["Pode vir às 10h"]
    assert api_int.saida("humano")[0]["status"] == "enviado"   # rota síncrona
    assert api_int.post(f"/api/atendimento-humano/{at['id']}/encerrar")[0] == 200
    assert api_int.get("/api/atendimento-humano")[1]["fila"] == []


def test_cancelamento_pelo_chat_avisa_equipe(api_int, externo):
    pid = api_int.paciente("Maria", TEL)
    api_int.agenda(pid, "2026-10-07T09:00", profissional="lia")
    api_int.post("/api/tarefas/rodar", {})
    assert "cancelad" in norm(api_int.msg(TEL, "2"))
    assert esperar(lambda: any(t.startswith("Cancelado:") and "07/10 09:00" in t for t in textos_tg(externo)))
