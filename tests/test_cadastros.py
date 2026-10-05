"""Seções 16, 17 e 18: cadastros, gestão de agenda e banco de dados."""
import subprocess

from conftest import RAIZ, Servidor


def horarios(api, servico, data, profissional=None):
    rota = f"/api/horarios?servico={servico}&data={data}" + (f"&profissional={profissional}" if profissional else "")
    st, r = api.get(rota, token=None)
    assert st == 200, (st, r)
    return [(h["inicio"], h["profissional"]) for h in r["horarios"]]


def test_profissional_novo_com_horario_proprio(api):
    st, r = api.post("/api/profissionais", {
        "id": "carla", "nome": "Carla Nutri", "servicos": ["retorno"], "registro": "CRN-8 12345",
        "horarios": {"seg": [], "ter": [], "qua": [["13:00", "15:00"]], "qui": [], "sex": [], "sab": [], "dom": []}})
    assert st == 201, r
    h = [i for i, p in horarios(api, "retorno", "2026-10-07") if p == "carla"]   # quarta
    assert h == ["2026-10-07T13:00", "2026-10-07T13:30", "2026-10-07T14:00", "2026-10-07T14:30"]
    assert [i for i, p in horarios(api, "retorno", "2026-10-08") if p == "carla"] == []
    st, lista = api.get("/api/profissionais")
    assert [p["id"] for p in lista["profissionais"]] == ["lia", "marcos", "carla"]
    c = lista["profissionais"][2]
    assert c["registro"] == "CRN-8 12345" and c["ativo"] is True
    assert lista["profissionais"][0]["horarios"] is None


def test_profissional_validacoes(api):
    assert api.post("/api/profissionais", {"id": "lia", "nome": "X", "servicos": ["retorno"]})[0] == 409
    assert api.post("/api/profissionais", {"id": "z", "nome": "Z", "servicos": ["xyz"]})[0] == 422
    assert api.put("/api/profissionais/naoexiste", {"nome": "Q"})[0] == 404


def test_editar_e_desativar_profissional(api):
    st, r = api.put("/api/profissionais/marcos", {"servicos": ["primeira", "retorno", "bioimpedancia"]})
    assert st == 200 and "bioimpedancia" in r["servicos"]
    assert {p for _, p in horarios(api, "bioimpedancia", "2026-10-07")} == {"lia", "marcos"}
    pid = api.paciente()
    _, a = api.agenda(pid, "2026-10-08T09:00", "retorno", "marcos")
    st, r = api.delete("/api/profissionais/marcos")
    assert st == 200 and r["ativo"] is False
    assert {p for _, p in horarios(api, "retorno", "2026-10-09")} == {"lia"}
    assert api.agenda(pid, "2026-10-09T09:00", "retorno", "marcos")[0] == 422
    assert [x["id"] for x in api.agendamentos("2026-10-08")] == [a["id"]]   # o já feito continua


def test_servicos_crud_e_chat_usa_so_ativos(api):
    assert api.post("/api/servicos", {"id": "avaliacao", "nome": "Avaliação física", "duracao_min": 90, "retorno_dias": None})[0] == 201
    assert api.post("/api/servicos", {"id": "retorno", "nome": "X", "duracao_min": 30})[0] == 409
    api.put("/api/profissionais/lia", {"servicos": ["primeira", "retorno", "bioimpedancia", "avaliacao"]})
    assert ("2026-10-07T08:00", "lia") in horarios(api, "avaliacao", "2026-10-07")
    assert api.put("/api/servicos/avaliacao", {"duracao_min": 120})[0] == 200
    assert ("2026-10-07T10:30", "lia") not in horarios(api, "avaliacao", "2026-10-07")  # 10:30 + 120 > 12:00
    assert ("2026-10-07T10:00", "lia") in horarios(api, "avaliacao", "2026-10-07")
    assert api.delete("/api/servicos/bioimpedancia")[0] == 200
    st, r = api.get("/api/servicos", token=None)
    assert [s["id"] for s in r["servicos"]] == ["primeira", "retorno", "avaliacao"]
    api.paciente("Maria", "41988887777")
    r = api.msg("41988887777", "quero agendar")
    assert "1 - Primeira consulta" in r and "3 - Avaliação física" in r and "Bioimpedância" not in r


def test_pacientes_busca_e_edicao(api):
    p1 = api.paciente("José Antônio Souza", "41999990001")
    p2 = api.paciente("Maria Lima", "41999990002")
    st, r = api.get("/api/pacientes?busca=antonio")
    assert st == 200 and [p["id"] for p in r["pacientes"]] == [p1]
    st, r = api.get("/api/pacientes?busca=990002")
    assert [p["id"] for p in r["pacientes"]] == [p2]
    assert [p["id"] for p in api.get("/api/pacientes")[1]["pacientes"]] == [p1, p2]
    st, r = api.put(f"/api/pacientes/{p2}", {"email": "maria@exemplo.com", "nascimento": "1980-05-02",
                                              "consentimento_marketing": True})
    assert st == 200 and r["email"] == "maria@exemplo.com" and r["consentimento_marketing"] is True
    assert api.put(f"/api/pacientes/{p2}", {"telefone": "41999990001"})[0] == 409
    assert api.put(f"/api/pacientes/{p2}", {"telefone": "12"})[0] == 400
    assert api.put("/api/pacientes/9999", {"nome": "Z"})[0] == 404


def test_faq_crud_vale_na_hora(api):
    st, r = api.post("/api/faq", {"perguntas": ["atendem criança"], "resposta": "Sim, a partir de 3 anos."})
    assert st == 201
    assert api.msg("41988887777", "vocês atendem criança?") == "Sim, a partir de 3 anos."
    assert api.delete(f"/api/faq/{r['id']}")[0] == 204
    assert api.msg("41988887777", "vocês atendem criança?") != "Sim, a partir de 3 anos."
    ids = [f["id"] for f in api.get("/api/faq")[1]["faq"]]
    assert ids[:3] == ["convenios", "endereco", "estacionamento"] and r["id"] not in ids


def test_bloqueio_tira_horarios_e_avisa_conflito(api):
    pid = api.paciente()
    _, a = api.agenda(pid, "2026-10-08T09:00", "retorno", "lia")
    st, r = api.post("/api/bloqueios", {"profissional": "lia", "inicio": "2026-10-08T08:00",
                                         "fim": "2026-10-09T00:00", "motivo": "congresso"})
    assert st == 201 and r["conflitos"] == [a["id"]]
    assert [p for _, p in horarios(api, "retorno", "2026-10-08")] and \
        {p for _, p in horarios(api, "retorno", "2026-10-08")} == {"marcos"}
    assert api.agenda(pid, "2026-10-08T15:00", "retorno", "lia")[0] == 422
    st, lista = api.get("/api/bloqueios?profissional=lia")
    assert [b["motivo"] for b in lista["bloqueios"]] == ["congresso"]
    assert api.delete(f"/api/bloqueios/{r['id']}")[0] == 204
    assert ("2026-10-08T15:00", "lia") in horarios(api, "retorno", "2026-10-08")


def test_agenda_por_periodo_e_profissional(api):
    pid = api.paciente()
    api.agenda(pid, "2026-10-09T09:00", "retorno", "lia")
    api.agenda(pid, "2026-10-07T09:00", "retorno", "marcos")
    api.agenda(pid, "2026-10-08T09:00", "retorno", "lia")
    api.agenda(pid, "2026-10-13T09:00", "retorno", "lia")
    st, r = api.get("/api/agendamentos?de=2026-10-07&ate=2026-10-09")
    assert [a["inicio"] for a in r["agendamentos"]] == ["2026-10-07T09:00", "2026-10-08T09:00", "2026-10-09T09:00"]
    st, r = api.get("/api/agendamentos?de=2026-10-07&ate=2026-10-13&profissional=lia")
    assert [a["inicio"][:10] for a in r["agendamentos"]] == ["2026-10-08", "2026-10-09", "2026-10-13"]


def test_semente_so_na_primeira_vez(dados):
    s = Servidor(dados)
    api = s.subir()
    api.post("/api/servicos", {"id": "exame", "nome": "Exame", "duracao_min": 30})
    s.parar()
    api2 = Servidor(dados).subir()
    ids = [x["id"] for x in api2.get("/api/servicos", token=None)[1]["servicos"]]
    assert ids == ["primeira", "retorno", "bioimpedancia", "exame"]


def test_backup_e_restaurar(dados, tmp_path):
    s = Servidor(dados)
    api = s.subir()
    pid = api.paciente("Guardada", "41999990009")
    api.agenda(pid, "2026-10-07T09:00", "retorno", "lia")
    api.plano(pid)
    arq = tmp_path / "copia.bak"
    r = subprocess.run([str(RAIZ / "atende"), "backup", "--dados", str(dados), "--saida", str(arq)],
                       cwd=RAIZ, capture_output=True, timeout=30)
    assert r.returncode == 0 and arq.exists() and arq.stat().st_size > 0
    api.delete(f"/api/pacientes/{pid}")
    api.paciente("Depois do backup", "41999990010")
    s.parar()
    r = subprocess.run([str(RAIZ / "atende"), "restaurar", "--dados", str(dados), "--entrada", str(arq)],
                       cwd=RAIZ, capture_output=True, timeout=30)
    assert r.returncode == 0
    api2 = Servidor(dados).subir()
    nomes = [p["nome"] for p in api2.get("/api/pacientes")[1]["pacientes"]]
    assert nomes == ["Guardada"]
    assert len(api2.agendamentos("2026-10-07")) == 1
    assert api2.get(f"/api/pacientes/{pid}/plano")[1]["versao"] == 1
