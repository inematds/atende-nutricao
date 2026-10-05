#!/usr/bin/env python3
"""Verificação independente (nível 4) — rodar DEPOIS que o loop disser concluído. O agente não vê este arquivo no prompt.

1. Procura valores do fixture copiados no código (atalho para passar nos testes).
2. Sobe o sistema com um consultório NUNCA visto (passo de 20 min, consulta de 40 min, retorno em 15 dias, tolerância
   de lembrete 30 min, sem atendimento online, outro token/horário/relógio, plano com refeições de outros nomes)
   e confere regras que só passam se a lógica for geral. Tudo explícito: nenhum atalho do conftest com padrão do fixture.
3. docker build + healthcheck do container.
Saída: INDEPENDENTE OK, ou a lista do que falhou.
"""
import json
import pathlib
import subprocess
import sys
import tempfile
import threading
import unicodedata

RAIZ = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "tests"))
from conftest import Servidor  # noqa: E402

falhas = []


def confere(cond, msg):
    if not cond:
        falhas.append(msg)


def norm(s):
    return "".join(c for c in unicodedata.normalize("NFD", (s or "").lower()) if unicodedata.category(c) != "Mn")


# 1. valores fixos do fixture no código
alvo = [p for p in ("atende", "src", "web") if (RAIZ / p).exists()]
for trecho in ("Unimed", "Rua das Flores", "segredo-teste", "Dra. Lia", "Dr. Marcos", "2026-10-06", "Nutri Bem",
               "41999990001", "41988887777", "Lanche da tarde", "ovos mexidos", "meet.exemplo"):
    r = subprocess.run(["grep", "-rnF", trecho, *alvo], cwd=RAIZ, capture_output=True, text=True)
    confere(r.stdout == "", f"valor do fixture no código: {trecho!r}")

# 2. consultório nunca visto
TOKEN = "token-verde-xyz"
TEL = "11987654321"
TEL_N = "+5511987654321"
cfg = {
    "nome": "Consultório Verde", "token": TOKEN, "passo_min": 20, "antecedencia_min_horas": 1, "janela_dias": 7,
    "confirmacao_horas": 24, "retorno_aviso_dias": 3, "lembrete_tolerancia_min": 30, "atende_online": False,
    "feriados": ["2026-11-02"],
    "horarios": {d: [["07:00", "11:00"]] for d in ("seg", "ter", "qua", "qui", "sex")} | {"sab": [], "dom": []},
    "profissionais": [{"id": "bia", "nome": "Bia Nutri", "servicos": ["consulta"]}],
    "servicos": [{"id": "consulta", "nome": "Consulta de acompanhamento", "duracao_min": 40, "retorno_dias": 15}],
    "faq": [{"id": "cartao", "perguntas": ["aceitam cartão de crédito"], "resposta": "Sim, débito e crédito."}],
}
PLANO = {"refeicoes": [
    {"horario": "06:30", "nome": "Desjejum", "opcoes": ["mingau de aveia"]},
    {"horario": "12:00", "nome": "Refeição principal", "opcoes": ["arroz integral com feijão", "batata-doce com frango"], "observacoes": "sem fritura"},
    {"horario": "19:00", "nome": "Ceia leve", "opcoes": ["chá e torrada"]},
]}
with tempfile.TemporaryDirectory() as tmp:
    d = pathlib.Path(tmp)
    (d / "nutricao.json").write_text(json.dumps(cfg, ensure_ascii=False))
    s = Servidor(d, agora="2026-11-03T06:00")  # terça; antecedência 1 h → a partir das 07:00
    try:
        api = s.subir()
        original = api.req

        def req_outro_token(metodo, rota, corpo=None, token=TOKEN):
            return original(metodo, rota, corpo, token=token)
        api.req = req_outro_token

        def msg(texto, tel=TEL):
            st, r = api.post("/api/mensagens", {"telefone": tel, "texto": texto}, token=None)
            return "\n".join(r.get("respostas", [])) if st == 200 else f"HTTP {st}"

        def saida(tipo):
            return [m for m in api.get("/api/saida")[1].get("mensagens", []) if m["tipo"] == tipo]

        # agenda com passo 20 e consulta de 40 min
        st, r = api.get("/api/horarios?servico=consulta&data=2026-11-03", token=None)
        h = [x["inicio"][11:] for x in r.get("horarios", [])]
        confere(h[:2] == ["07:00", "07:20"] and h[-1] == "10:20" and len(h) == 11, f"grade de 20 min errada: {h}")
        confere(api.get("/api/horarios?servico=consulta&data=2026-11-02", token=None)[1].get("horarios") == [], "feriado novo ignorado")
        confere(api.get("/api/saida", token="segredo-teste")[0] == 401, "token do fixture aceito")
        confere(api.get("/api/saida")[0] == 200, "token novo recusado")
        st, r = api.post("/api/pacientes", {"nome": "Teste Verde", "telefone": TEL, "consentimento_marketing": False})
        confere(st == 201, f"paciente: {st} {r}")
        pid = r.get("id")
        st, a = api.post("/api/agendamentos", {"paciente_id": pid, "servico": "consulta", "inicio": "2026-11-03T07:00", "profissional": "bia"})
        confere(st == 201 and a.get("fim") == "2026-11-03T07:40" and a.get("modalidade") == "presencial", f"agendar 07:00 → {st} {a}")
        confere(api.post("/api/agendamentos", {"paciente_id": pid, "servico": "consulta", "inicio": "2026-11-03T07:20", "profissional": "bia"})[0] == 409,
                "sobreposição com passo 20 / duração 40 não detectada")
        confere(api.post("/api/agendamentos", {"paciente_id": pid, "servico": "consulta", "inicio": "2026-11-03T08:00", "profissional": "bia",
                                               "modalidade": "online"})[0] == 422, "online aceito com atende_online=false")

        # lembrete de água com tolerância de 30 min (antes de criar outros agendamentos, para contar por tipo)
        confere(api.put(f"/api/pacientes/{pid}/metas", {"lembretes_agua": ["06:00"], "meta_agua_copos": 10})[0] == 200, "metas novas recusadas")
        api.post("/api/tarefas/rodar", {})
        confere(len(saida("lembrete")) == 1, f"lembrete 06:00 às 06:00: {saida('lembrete')}")
        api.post("/api/tarefas/rodar", {"agora": "2026-11-03T06:31"})
        confere(len(saida("lembrete")) == 1, "lembrete fora da tolerância de 30 min foi enviado")

        # FAQ e plano com outros nomes
        confere(msg("vocês aceitam cartão de crédito?") == "Sim, débito e crédito.", "FAQ novo não respondido")
        confere("nutricionista" in norm(msg("meu plano")), "sem plano: não apontou o nutricionista")
        st, r = api.post(f"/api/pacientes/{pid}/plano", PLANO)
        confere(st == 201 and r.get("versao") == 1, f"plano: {st} {r}")
        r = msg("o que posso comer na ceia?")
        confere("19:00 Ceia leve: chá e torrada" in r and "Desjejum" not in r and "Refeição principal" not in r, f"refeição específica: {r!r}")
        r = msg("meu plano")
        confere("06:30 Desjejum: mingau de aveia" in r and "12:00 Refeição principal: arroz integral com feijão / batata-doce com frango — sem fritura" in r
                and "19:00 Ceia leve: chá e torrada" in r, f"plano inteiro: {r!r}")
        r = norm(msg("posso comer pizza?"))
        fila = api.get("/api/atendimento-humano")[1].get("fila", [])
        confere("nutricionista" in r and "atendente" in r and any(f["motivo"] == "duvida_plano" for f in fila), f"dúvida fora do plano: {r!r} {fila}")
        for f in fila:
            api.post(f"/api/atendimento-humano/{f['id']}/encerrar")

        # peso, água, refeição
        r = norm(msg("pesei 91,3 kg"))
        confere("registrad" in r and "91,3 kg" in r, f"peso: {r!r}")
        confere(not any(p in r for p in ("parabens", "otimo", "muito bem", "que pena", "cuidado", "engordou", "emagreceu", "ganhou", "perdeu", "ruim")),
                f"peso com julgamento: {r!r}")
        confere("entre 20 e 400" in norm(msg("peso 15")), "peso fora da faixa aceito")
        confere(api.post(f"/api/pacientes/{pid}/pesos", {"peso": 89.9, "quando": "2026-11-10T08:00"})[0] == 201, "peso pela equipe recusado")
        st, r = api.get(f"/api/pacientes/{pid}/pesos")
        confere([p["peso"] for p in r.get("pesos", [])] == [91.3, 89.9] and r.get("variacao") == -1.4, f"série de peso: {r}")
        confere("3 de 10 copos" in norm(msg("tomei 3 copos")), "total de água com meta nova errado")
        r = norm(msg("pulei o desjejum"))
        confere("registrad" in r and "desjejum" in r, f"refeição pulada: {r!r}")
        st, r = api.get(f"/api/pacientes/{pid}/diario")
        confere(r.get("resumo", {}).get("refeicoes_puladas") == 1 and r.get("resumo", {}).get("adesao_pct") == 0, f"resumo: {r.get('resumo')}")

        # agendamento pelo chat sem pergunta de modalidade (atende_online=false): 07:00 ocupado → 07:40 é o 1º livre
        msg("quero marcar consulta")
        r = msg("1")
        confere("1) 03/11 07:40 com Bia Nutri" in r, f"horários do chat: {r!r}")
        r = norm(msg("1"))
        confere("agendad" in r and "1 - presencial" not in r, f"chat agendou sem perguntar modalidade: {r!r}")
        ags = api.get("/api/agendamentos?data=2026-11-03")[1].get("agendamentos", [])
        confere(any(x["inicio"] == "2026-11-03T07:40" and x["modalidade"] == "presencial" for x in ags), f"agendamento do chat: {ags}")

        # retorno em 15 dias: 03/11 + 15 = 18/11; aviso a partir de 15/11
        api.post(f"/api/agendamentos/{a['id']}/presenca", {"compareceu": True})
        api.post("/api/tarefas/rodar", {"agora": "2026-11-14T08:00"})
        confere(saida("retorno") == [], "retorno cedo demais")
        api.post("/api/tarefas/rodar", {"agora": "2026-11-15T08:00"})
        confere(len(saida("retorno")) == 1, "retorno não avisado em 15/11")

        # campanha: trava mínima e consentimento
        st, r = api.post("/api/pacientes", {"nome": "Com Consentimento", "telefone": "11912345678", "consentimento_marketing": True})
        st, r = api.post("/api/campanhas", {"texto": "Emagreça 5 kg garantido"})
        confere(st == 422 and set(r.get("violacoes", [])) == {"promessa_resultado"}, f"trava promessa: {st} {r}")
        st, r = api.post("/api/campanhas", {"texto": "Chá detox: veja o antes e depois"})
        confere(st == 422 and set(r.get("violacoes", [])) == {"antes_depois"}, f"trava antes/depois: {st} {r}")
        st, r = api.post("/api/campanhas", {"texto": "Agende sua consulta de acompanhamento."})
        confere(st == 200 and r.get("enviadas") == 1, f"campanha permitida: {st} {r}")

        # concorrência num horário novo
        codigos = []

        def tenta():
            codigos.append(api.post("/api/agendamentos", {"paciente_id": pid, "servico": "consulta", "inicio": "2026-11-04T09:00", "profissional": "bia"})[0])
        ts = [threading.Thread(target=tenta) for _ in range(6)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        confere(sorted(codigos) == [201] + [409] * 5, f"concorrência: {sorted(codigos)}")

        # raio-x novembro: 1 realizado (07:00), 1 cliente novo, retorno de 18/11 sem outro realizado depois de 03/11 → 0
        st, rx = api.get("/api/raiox?mes=2026-11")
        v = rx.get("valores", {})
        confere(v.get("atendimentos_mes") == 1 and v.get("clientes_novos_mes") == 1 and v.get("retorno_atual_pct") == 0, f"raiox: {rx}")

        # LGPD: apaga plano, diário e pesos
        confere(api.delete(f"/api/pacientes/{pid}")[0] == 204, "DELETE recusado")
        st, dd = api.get(f"/api/pacientes/{pid}/dados")
        confere(st == 200 and dd.get("planos") == [] and dd.get("diario") == [] and dd.get("pesos") == [] and dd.get("paciente", {}).get("telefone") is None,
                f"dados após exclusão: {st} {dd}")
    finally:
        s.parar()

# 3. container de verdade (precisa de docker; baixa a imagem python na 1ª vez)
import time  # noqa: E402
import urllib.request  # noqa: E402

b = subprocess.run(["docker", "build", "-q", "-t", "atende-nutricao-verif", "."], cwd=RAIZ, capture_output=True, text=True)
confere(b.returncode == 0, f"docker build falhou: {b.stderr[-300:]}")
if b.returncode == 0:
    c = subprocess.run(["docker", "run", "-d", "--rm", "-p", "127.0.0.1::8080", "atende-nutricao-verif"],
                       capture_output=True, text=True)
    cid = c.stdout.strip()
    try:
        porta = subprocess.run(["docker", "port", cid, "8080"], capture_output=True, text=True).stdout.split(":")[-1].strip()
        ok = False
        for _ in range(40):
            try:
                ok = urllib.request.urlopen(f"http://127.0.0.1:{porta}/api/saude", timeout=2).status == 200
                break
            except Exception:
                time.sleep(0.5)
        confere(ok, "container não respondeu /api/saude")
    finally:
        subprocess.run(["docker", "stop", cid], capture_output=True)

if falhas:
    print("INDEPENDENTE FALHOU:")
    for f in falhas:
        print(" -", f)
    sys.exit(1)
print("INDEPENDENTE OK")
