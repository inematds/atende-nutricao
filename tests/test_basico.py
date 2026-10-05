"""Seções 1, 4, 5 (saúde/serviços), 15 e persistência."""
from conftest import RAIZ, Servidor


def test_saude_traz_versao_do_arquivo(api):
    st, r = api.get("/api/saude", token=None)
    assert st == 200
    assert r["ok"] is True
    assert r["versao"] == (RAIZ / "VERSION").read_text().strip()


def test_servicos_na_ordem_da_config(api):
    st, r = api.get("/api/servicos", token=None)
    assert st == 200
    assert [s["id"] for s in r["servicos"]] == ["primeira", "retorno", "bioimpedancia"]
    assert r["servicos"][0]["duracao_min"] == 60 and r["servicos"][1]["duracao_min"] == 30


def test_rotas_da_equipe_exigem_token_antes_de_tudo(api):
    # corpo vazio e id inexistente: mesmo assim 401 (a checagem do token vem antes de 404/422)
    for metodo, rota in [("GET", "/api/saida"), ("GET", "/api/agendamentos?data=2026-10-07"),
                         ("POST", "/api/pacientes"), ("GET", "/api/atendimento-humano"),
                         ("GET", "/api/raiox?mes=2026-10"), ("POST", "/api/campanhas"),
                         ("GET", "/api/pacientes/1/plano"), ("POST", "/api/pacientes/1/plano"),
                         ("GET", "/api/pacientes/1/diario"), ("GET", "/api/pacientes/1/pesos"),
                         ("POST", "/api/pacientes/1/pesos"), ("PUT", "/api/pacientes/1/metas"),
                         ("POST", "/api/agendamentos/1/link"), ("GET", "/api/profissionais")]:
        corpo = {} if metodo in ("POST", "PUT") else None
        assert api.req(metodo, rota, corpo, token=None)[0] == 401, rota
        assert api.req(metodo, rota, corpo, token="errado")[0] == 401, rota
    # públicas
    assert api.get("/api/horarios?servico=retorno&data=2026-10-07", token=None)[0] == 200
    assert api.get("/api/servicos", token=None)[0] == 200
    assert api.post("/api/mensagens", {"telefone": "41911112222", "texto": "oi"}, token=None)[0] == 200


def test_paginas(api):
    st, html = api.get("/", token=None)
    assert st == 200 and 'id="chat"' in html
    st, html = api.get("/equipe", token=None)
    assert st == 200
    for el in ('id="agenda"', 'id="fila-humano"', 'id="saida"', 'id="pacientes"', 'id="plano"',
               'id="diario"', 'id="pesos"', 'id="faq"'):
        assert el in html, el


def test_estado_persiste_ao_reiniciar(dados):
    s = Servidor(dados)
    api = s.subir()
    pid = api.paciente()
    st, ag = api.agenda(pid, "2026-10-07T09:00", profissional="lia")
    assert st == 201
    api.plano(pid)
    api.msg("41999990001", "peso 82,5")
    s.parar()
    s2 = Servidor(dados)
    api2 = s2.subir()
    assert [a["id"] for a in api2.agendamentos("2026-10-07")] == [ag["id"]]
    assert api2.agenda(pid, "2026-10-07T09:00", profissional="lia")[0] == 409
    assert api2.get(f"/api/pacientes/{pid}/plano")[1]["versao"] == 1
    assert [p["peso"] for p in api2.get(f"/api/pacientes/{pid}/pesos")[1]["pesos"]] == [82.5]


def test_cria_nutricao_json_do_exemplo_se_faltar(tmp_path):
    d = tmp_path / "vazio"   # nem a pasta existe: o serve cria (seção 1)
    s = Servidor(d)
    api = s.subir()
    assert api.get("/api/saude", token=None)[0] == 200
    assert (d / "nutricao.json").exists()
