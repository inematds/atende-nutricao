"""Seção 9: plano alimentar — registro pela equipe, versões, envio ao paciente, consulta pelo chat (só o que está no plano)."""
import copy

from conftest import PLANO, norm

TEL = "41988887777"
NOMES = ["Café da manhã", "Lanche da manhã", "Almoço", "Lanche da tarde", "Jantar"]
LINHA_CAFE = "07:30 Café da manhã: ovos mexidos com pão integral / iogurte natural com aveia — sem açúcar"
LINHA_ALMOCO = "12:30 Almoço: arroz, feijão, frango grelhado e salada / quinoa com legumes e peixe"
LINHA_TARDE = "16:00 Lanche da tarde: iogurte com granola / pão integral com queijo branco"


def fila(api):
    return api.get("/api/atendimento-humano")[1]["fila"]


def test_criar_e_ler_plano_ordenado_por_horario(api):
    pid = api.paciente("Maria", TEL)
    desordenado = copy.deepcopy(PLANO)
    desordenado["refeicoes"] = [desordenado["refeicoes"][2]] + desordenado["refeicoes"][:2] + desordenado["refeicoes"][3:]
    st, r = api.post(f"/api/pacientes/{pid}/plano", desordenado)
    assert st == 201 and r["versao"] == 1
    st, p = api.get(f"/api/pacientes/{pid}/plano")
    assert st == 200 and p["id"] == r["id"] and p["versao"] == 1
    assert [x["nome"] for x in p["refeicoes"]] == NOMES
    assert p["refeicoes"][0]["observacoes"] == "sem açúcar" and p["refeicoes"][1]["observacoes"] == ""
    assert p["refeicoes"][2]["opcoes"] == ["arroz, feijão, frango grelhado e salada", "quinoa com legumes e peixe"]
    assert p["observacoes"] == "Beba água ao longo do dia."
    assert p["criado_em"] == "2026-10-06T09:00" and p["enviado_em"] is None


def test_plano_validacoes(api):
    pid = api.paciente("Maria", TEL)
    assert api.get(f"/api/pacientes/{pid}/plano")[0] == 404   # ainda sem plano
    assert api.post(f"/api/pacientes/{pid}/plano", {})[0] == 422
    assert api.post(f"/api/pacientes/{pid}/plano", {"refeicoes": []})[0] == 422
    for ruim in ({"horario": "7h30", "nome": "Café", "opcoes": ["x"]},
                 {"horario": "07:30", "nome": "", "opcoes": ["x"]},
                 {"horario": "07:30", "nome": "Café", "opcoes": []}):
        assert api.post(f"/api/pacientes/{pid}/plano", {"refeicoes": [ruim]})[0] == 422, ruim
    assert api.post("/api/pacientes/9999/plano", PLANO)[0] == 404
    assert api.get(f"/api/pacientes/{pid}/plano")[0] == 404   # nada foi criado


def test_nova_versao_substitui_e_historico(api):
    pid = api.paciente("Maria", TEL)
    api.plano(pid)
    st, r = api.post(f"/api/pacientes/{pid}/plano", {"refeicoes": [{"horario": "08:00", "nome": "Desjejum", "opcoes": ["mingau de aveia"]}]})
    assert st == 201 and r["versao"] == 2
    st, p = api.get(f"/api/pacientes/{pid}/plano")
    assert p["versao"] == 2 and [x["nome"] for x in p["refeicoes"]] == ["Desjejum"] and p["observacoes"] == ""
    st, h = api.get(f"/api/pacientes/{pid}/planos")
    assert [x["versao"] for x in h["planos"]] == [1, 2]
    assert "08:00 Desjejum: mingau de aveia" in api.msg(TEL, "meu plano") and "Almoço" not in api.msg(TEL, "meu plano")


def test_enviar_plano_cria_mensagem_com_o_texto(api):
    pid = api.paciente("Maria", TEL)
    api.plano(pid)
    st, r = api.post(f"/api/pacientes/{pid}/plano/enviar")
    assert st == 200 and r["enviadas"] == 1
    [m] = api.saida("plano")
    assert m["telefone"] == "+5541988887777" and m["paciente_id"] == pid and m["agendamento_id"] is None
    assert m["status"] == "simulado"
    t = m["texto"]
    assert "Seu plano alimentar (versão 1, de 06/10/2026):" in t
    for linha in (LINHA_CAFE, "10:00 Lanche da manhã: 1 fruta / castanhas", LINHA_ALMOCO, LINHA_TARDE,
                  "20:00 Jantar: sopa de legumes com carne / omelete com salada", "Beba água ao longo do dia."):
        assert linha in t, linha
    assert t.index(LINHA_CAFE) < t.index(LINHA_ALMOCO) < t.index(LINHA_TARDE)
    assert api.get(f"/api/pacientes/{pid}/plano")[1]["enviado_em"] == "2026-10-06T09:00"


def test_enviar_sem_plano_404_e_nao_contatar_409(api):
    pid = api.paciente("Maria", TEL)
    assert api.post(f"/api/pacientes/{pid}/plano/enviar")[0] == 404
    api.plano(pid)
    api.msg(TEL, "parar")
    st, r = api.post(f"/api/pacientes/{pid}/plano/enviar")
    assert st == 409 and r["erro"] == "nao_contatar"
    assert api.saida("plano") == []


def test_chat_meu_plano_sem_e_com_plano(api):
    assert "nutricionista" in norm(api.msg(TEL, "qual é a minha dieta?"))   # telefone sem paciente
    pid = api.paciente("Maria", TEL)
    assert "nutricionista" in norm(api.msg(TEL, "meu plano"))              # paciente sem plano
    api.plano(pid)
    r = api.msg(TEL, "meu plano")
    assert "Seu plano alimentar (versão 1, de 06/10/2026):" in r
    for nome in NOMES:
        assert nome in r, nome
    assert LINHA_CAFE in r and "Beba água ao longo do dia." in r
    r2 = api.msg(TEL, "me manda o cardápio de novo")
    assert LINHA_ALMOCO in r2 and LINHA_TARDE in r2
    assert fila(api) == []


def test_chat_refeicao_especifica_responde_so_ela(api):
    pid = api.paciente("Maria", TEL)
    api.plano(pid)
    r = api.msg(TEL, "O que posso comer no lanche da tarde?")
    assert LINHA_TARDE in r
    for outro in ("Café da manhã", "Lanche da manhã", "Almoço", "Jantar"):
        assert outro not in r, outro
    r = api.msg(TEL, "o que como no lanche?")   # "lanche" casa os dois lanches: empate → menor horário
    assert "10:00 Lanche da manhã: 1 fruta / castanhas" in r and "Lanche da tarde" not in r
    r = api.msg(TEL, "posso comer o que de manhã?")   # "manha" casa café e lanche da manhã: empate → 07:30
    assert LINHA_CAFE in r and "Lanche" not in r
    assert fila(api) == []


def test_chat_duvida_fora_do_plano_vai_para_humano(api):
    pid = api.paciente("Maria", TEL)
    api.plano(pid)
    r = norm(api.msg(TEL, "posso comer chocolate?"))
    assert "plano" in r and "nutricionista" in r and "atendente" in r
    [f] = fila(api)
    assert f["motivo"] == "duvida_plano" and f["prioridade"] == "normal" and f["telefone"] == "+5541988887777"
    assert api.get(f"/api/pacientes/{pid}/diario")[1]["registros"] == []
