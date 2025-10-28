from app.models.service import Service, _parse_date


def test_past_start_rejected(monkeypatch):
    from app.models.store import Store
    store = Store.instance()
    renter = next(iter(store.users))  # 随便拿一个已有用户
    vehicle = next(iter(store.vehicles))  # 假设已存在
    ok, msg, rid = Service.rent(renter, vehicle, "1999-01-01", "1999-01-02")
    assert not ok and "past" in msg.lower()


def test_overlap_rejected(monkeypatch):
    from app.models.store import Store
    store = Store.instance()
    renter = next(iter(store.users))
    vehicle = next(iter(store.vehicles))

    # 先创建一单
    ok, msg, rid = Service.rent(renter, vehicle, "2030-01-10", "2030-01-15")
    assert ok

    # 与其重叠的请求应失败
    ok2, msg2, _ = Service.rent(renter, vehicle, "2030-01-14", "2030-01-20")
    assert not ok2 and "overlap" in msg2.lower()


def test_touching_ok(monkeypatch):
    from app.models.store import Store
    store = Store.instance()
    renter = next(iter(store.users))
    vehicle = next(iter(store.vehicles))

    # 已有一单 2030-01-10 → 2030-01-15
    ok, msg, rid = Service.rent(renter, vehicle, "2030-01-15", "2030-01-18")
    # 正好“无缝衔接”，应该允许
    assert ok
