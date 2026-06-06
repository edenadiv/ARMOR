from cdmas.common.config import Settings


def test_defaults():
    s = Settings()
    assert s.kafka_bootstrap == "localhost:9092"
    assert s.sim_speed == 1.0
    assert s.log_json is True


def test_env_override(monkeypatch):
    monkeypatch.setenv("CDMAS_KAFKA_BOOTSTRAP", "kafka:9092")
    monkeypatch.setenv("CDMAS_SIM_SPEED", "5.0")
    s = Settings()
    assert s.kafka_bootstrap == "kafka:9092"
    assert s.sim_speed == 5.0
