"""Seções 12 e 13: direitos do titular (LGPD, dado de saúde) e exportação para o Painel de Recuperação do Raio-X."""
import json
import subprocess

from conftest import RAIZ, Servidor, chaves, norm

# minutos disponíveis em out/2026: 21 dias úteis (sem o feriado 12/10) × 480 + 5 sábados × 240 = 11280, × 2 profissionais
DISPONIVEL_OUT = 22560


def test_dados_e_exclusao(api):
    tel = "41999990001"
    pid = api.paciente("Maria Silva", tel, marketing=True, email="maria@exemplo.com")
    _, a = api.agenda(pid, "2026-10-07T09:00", profissional="lia")
    _, b = api.agenda(pid, "2026-10-08T09:00", profissional="lia")
    api.post(f"/api/agendamentos/{b['id']}/presenca", {"compareceu": True})
    api.plano(pid)
    api.put(f"/api/pacientes/{pid}/metas", {"lembretes_agua": ["09:00"]})
    api.msg(tel, "peso 82,5")
    api.msg(tel, "2 copos")
    api.msg(tel, "tem estacionamento")
    st, d = api.get(f"/api/pacientes/{pid}/dados")
    assert st == 200
    assert d["paciente"]["nome"] == "Maria Silva" and d["paciente"]["telefone"] == "+5541999990001"
    assert {x["id"] for x in d["agendamentos"]} == {a["id"], b["id"]}
    assert {"entrada", "saida"} <= {m["direcao"] for m in d["mensagens"]}
    assert any("estacionamento" in m["texto"] for m in d["mensagens"])
    assert len(d["planos"]) == 1 and len(d["planos"][0]["refeicoes"]) == 5
    assert [x["tipo"] for x in d["diario"]] == ["peso", "agua"] and [p["peso"] for p in d["pesos"]] == [82.5]
    assert d["metas"]["lembretes_agua"] == ["09:00"]

    assert api.delete(f"/api/pacientes/{pid}")[0] == 204
    st, d = api.get(f"/api/pacientes/{pid}/dados")
    assert st == 200
    assert d["paciente"]["nome"] == "removido" and d["paciente"]["telefone"] is None and d["paciente"]["email"] is None
    status = {x["id"]: x["status"] for x in d["agendamentos"]}
    assert status == {a["id"]: "cancelado", b["id"]: "realizado"}
    assert d["mensagens"] and all(m["texto"] == "" for m in d["mensagens"])
    assert d["planos"] == [] and d["diario"] == [] and d["pesos"] == []
    chaves(d["metas"], lembretes_agua=[], lembretes_refeicoes=False, meta_agua_copos=None)
    assert api.get(f"/api/pacientes/{pid}/plano")[0] == 404
    st, r = api.get("/api/raiox?mes=2026-10")
    assert r["valores"]["atendimentos_mes"] == 1
    assert "nome" in norm(api.msg(tel, "quero agendar"))   # telefone virou desconhecido


def montar_mes(dados):
    """Setembro: duas primeiras consultas que geram retorno em 05/10 e 08/10. Outubro: o cenário medido."""
    s = Servidor(dados, agora="2026-09-01T09:00")
    api = s.subir()
    p6 = api.paciente("Seis", "41900000006")
    p7 = api.paciente("Sete", "41900000007")
    for pid, inicio in ((p6, "2026-09-05T09:00"), (p7, "2026-09-08T09:00")):   # sábado 08–12 e terça
        st, a = api.agenda(pid, inicio, "primeira", "lia")
        assert st == 201, a
        api.post(f"/api/agendamentos/{a['id']}/presenca", {"compareceu": True})
    s.parar()

    s = Servidor(dados)  # agora = 06/10/2026 09:00
    api = s.subir()
    p1, p2, p3, p4, p5 = (api.paciente(n, f"4190000000{i}") for i, n in enumerate(["Um", "Dois", "Tres", "Quatro", "Cinco"], 1))

    def marca(pid, inicio, servico, prof, compareceu=None):
        st, a = api.agenda(pid, inicio, servico, prof)
        assert st == 201, (inicio, a)
        if compareceu is not None:
            api.post(f"/api/agendamentos/{a['id']}/presenca", {"compareceu": compareceu})
        return a

    marca(p1, "2026-10-07T08:00", "primeira", "lia", True)    # 60 min, novo
    marca(p1, "2026-10-07T09:00", "retorno", "lia", True)     # 30 min
    marca(p2, "2026-10-07T08:00", "retorno", "marcos", False) # 30 min, falta (ativo)
    marca(p3, "2026-10-08T08:00", "retorno", "marcos", True)  # 30 min, novo
    marca(p4, "2026-10-08T08:00", "retorno", "lia")           # 30 min, agendado (ativo)
    c = marca(p5, "2026-10-08T09:00", "retorno", "lia")       # cancelado: não conta
    api.post(f"/api/agendamentos/{c['id']}/cancelar")
    marca(p6, "2026-10-07T10:00", "retorno", "lia", True)     # 30 min; cumpre o retorno de 05/10 (origem 05/09): 07/10 ∈ (05/09, 04/11]
    return s, api


def test_raiox_numeros_do_mes(dados):
    s, api = montar_mes(dados)
    st, r = api.get("/api/raiox?mes=2026-10")
    assert st == 200 and r["pacote"] == "clinica" and r["mes"] == "2026-10"
    v = r["valores"]
    assert set(v) == {"atendimentos_mes", "falta_pct", "ocupacao_pct", "clientes_novos_mes", "retorno_atual_pct"}
    assert v["atendimentos_mes"] == 4            # p1 ×2, p3, p6
    assert v["falta_pct"] == 20.0                # 1 falta ÷ (4 + 1)
    assert v["clientes_novos_mes"] == 2          # p1 e p3 (o primeiro realizado do p6 foi em setembro)
    assert v["retorno_atual_pct"] == 50.0        # retornos de 05/10 (p6, cumprido) e 08/10 (p7, não)
    assert abs(v["ocupacao_pct"] - 210 / DISPONIVEL_OUT * 100) <= 0.06   # 60+30+30+30+30+30 min ativos
    st, setembro = api.get("/api/raiox?mes=2026-09")
    assert setembro["valores"]["atendimentos_mes"] == 2 and setembro["valores"]["clientes_novos_mes"] == 2
    assert setembro["valores"]["falta_pct"] == 0 and setembro["valores"]["retorno_atual_pct"] == 0


def test_cli_grava_mes_no_acompanhamento_do_painel(dados, tmp_path):
    s, _ = montar_mes(dados)
    s.parar()
    arq = tmp_path / "acompanhamento.json"
    arq.write_text(json.dumps({
        "tipo": "acompanhamento", "pacote": "clinica", "cliente": "Nutri Bem",
        "base": {"data": "2026-09-01", "valores": {"falta_pct": 18, "ticket_medio": 250, "atendimentos_mes": 400}},
        "meses": [],
    }))
    cmd = [str(RAIZ / "atende"), "raiox", "--dados", str(dados), "--mes", "2026-10", "--acompanhamento", str(arq)]
    for _ in range(2):  # rodar duas vezes substitui o mês, não duplica
        assert subprocess.run(cmd, cwd=RAIZ, capture_output=True, timeout=30).returncode == 0
    acomp = json.loads(arq.read_text())
    assert acomp["tipo"] == "acompanhamento" and acomp["base"]["valores"]["falta_pct"] == 18
    [m] = acomp["meses"]
    assert m["mes"] == "2026-10" and m["obs"] == "atende-nutricao"
    assert m["valores"]["ticket_medio"] == 250          # mesclado da base
    assert m["valores"]["falta_pct"] == 20.0            # medido
    assert m["valores"]["atendimentos_mes"] == 4
