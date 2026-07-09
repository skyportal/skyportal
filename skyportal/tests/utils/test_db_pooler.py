from baselayer.app.models import _resolve_pooler


def test_pooler_disabled_is_unchanged():
    host, port, engine_args = _resolve_pooler(
        "db", 5432, {"pool_size": 10}, {"enabled": False}
    )
    assert (host, port) == ("db", 5432)
    assert engine_args == {"pool_size": 10}


def test_pooler_none_is_unchanged():
    assert _resolve_pooler("db", 5432, {}, None) == ("db", 5432, {})


def test_pooler_enabled_routes_and_disables_prepared_statements():
    host, port, engine_args = _resolve_pooler(
        "db",
        5432,
        {"pool_size": 10},
        {"enabled": True, "host": "pooler", "port": 6432},
    )
    assert (host, port) == ("pooler", 6432)
    assert engine_args["pool_pre_ping"] is True
    # prepared statements are per-connection; must be off under transaction pooling
    assert engine_args["connect_args"]["prepare_threshold"] is None
    # existing engine_args are preserved
    assert engine_args["pool_size"] == 10


def test_pooler_defaults_port_and_keeps_backend_host():
    # no pooler host/port given -> keep the backend host, default the pooler port
    host, port, _ = _resolve_pooler("db", 5432, {}, {"enabled": True})
    assert (host, port) == ("db", 6432)


def test_pooler_preserves_caller_connect_args():
    _, _, engine_args = _resolve_pooler(
        "db", 5432, {"connect_args": {"sslmode": "require"}}, {"enabled": True}
    )
    assert engine_args["connect_args"]["sslmode"] == "require"
    assert engine_args["connect_args"]["prepare_threshold"] is None


def test_resolve_pooler_does_not_mutate_inputs():
    engine_args = {"pool_size": 10}
    _resolve_pooler("db", 5432, engine_args, {"enabled": True})
    assert engine_args == {"pool_size": 10}
