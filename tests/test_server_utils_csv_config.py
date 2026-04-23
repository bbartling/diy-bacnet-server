"""Tests for CSV-configured object Instance and CovIncrement behavior."""

import pytest

from bacpypes_server import server_utils


class _DummyApp:
    def __init__(self) -> None:
        self.objects = []

    def add_object(self, obj) -> None:
        self.objects.append(obj)


@pytest.fixture(autouse=True)
def _reset_globals():
    server_utils.point_map.clear()
    server_utils.commandable_point_names.clear()
    yield
    server_utils.point_map.clear()
    server_utils.commandable_point_names.clear()


@pytest.mark.asyncio
async def test_loader_uses_explicit_instance_and_covincrement(tmp_path, monkeypatch):
    csv_path = tmp_path / "points.csv"
    csv_path.write_text(
        "\n".join(
            [
                "Name,PointType,Units,Commandable,Default,Instance,CovIncrement",
                "supply-air-temp,AV,degreesFahrenheit,N,72.5,120,0.25",
                "enable-opt,BV,Status,Y,active,42,",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(server_utils, "CSV_FILE", str(csv_path))

    app = _DummyApp()
    await server_utils.load_csv_and_create_objects(app)

    av = server_utils.point_map["supply-air-temp"]
    bv = server_utils.point_map["enable-opt"]
    assert int(tuple(av.objectIdentifier)[1]) == 120
    assert float(av.covIncrement) == 0.25
    assert int(tuple(bv.objectIdentifier)[1]) == 42


@pytest.mark.asyncio
async def test_loader_invalid_covincrement_skips_row(tmp_path, monkeypatch):
    csv_path = tmp_path / "points.csv"
    csv_path.write_text(
        "\n".join(
            [
                "Name,PointType,Units,Commandable,Default,Instance,CovIncrement",
                "bad-cov,AV,degreesFahrenheit,N,72.5,10,0",
                "good-point,BV,Status,N,inactive,11,",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(server_utils, "CSV_FILE", str(csv_path))

    app = _DummyApp()
    await server_utils.load_csv_and_create_objects(app)

    assert "bad-cov" not in server_utils.point_map
    assert "good-point" in server_utils.point_map


@pytest.mark.asyncio
async def test_loader_duplicate_instance_skips_conflicting_row(tmp_path, monkeypatch):
    csv_path = tmp_path / "points.csv"
    csv_path.write_text(
        "\n".join(
            [
                "Name,PointType,Units,Commandable,Default,Instance,CovIncrement",
                "av-1,AV,degreesFahrenheit,N,72.0,20,1.0",
                "av-duplicate,AV,degreesFahrenheit,N,73.0,20,1.0",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(server_utils, "CSV_FILE", str(csv_path))

    app = _DummyApp()
    await server_utils.load_csv_and_create_objects(app)

    assert "av-1" in server_utils.point_map
    assert "av-duplicate" not in server_utils.point_map


@pytest.mark.asyncio
async def test_loader_mixed_explicit_and_auto_instance_uses_next_available(tmp_path, monkeypatch):
    csv_path = tmp_path / "points.csv"
    csv_path.write_text(
        "\n".join(
            [
                "Name,PointType,Units,Commandable,Default,Instance,CovIncrement",
                "sat,AV,degreesFahrenheit,N,70.0,1,0.5",
                "rat,AV,degreesFahrenheit,N,71.0,,0.5",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(server_utils, "CSV_FILE", str(csv_path))

    app = _DummyApp()
    await server_utils.load_csv_and_create_objects(app)

    sat = server_utils.point_map["sat"]
    rat = server_utils.point_map["rat"]
    assert int(tuple(sat.objectIdentifier)[1]) == 1
    assert int(tuple(rat.objectIdentifier)[1]) == 2


@pytest.mark.asyncio
async def test_loader_invalid_covincrement_nan_skips_row(tmp_path, monkeypatch):
    csv_path = tmp_path / "points.csv"
    csv_path.write_text(
        "\n".join(
            [
                "Name,PointType,Units,Commandable,Default,Instance,CovIncrement",
                "bad-nan,AV,degreesFahrenheit,N,70.0,30,nan",
                "good,AV,degreesFahrenheit,N,71.0,31,0.5",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(server_utils, "CSV_FILE", str(csv_path))

    app = _DummyApp()
    await server_utils.load_csv_and_create_objects(app)

    assert "bad-nan" not in server_utils.point_map
    assert "good" in server_utils.point_map


@pytest.mark.asyncio
async def test_loader_invalid_row_does_not_reserve_instance(tmp_path, monkeypatch):
    csv_path = tmp_path / "points.csv"
    csv_path.write_text(
        "\n".join(
            [
                "Name,PointType,Units,Commandable,Default,Instance,CovIncrement",
                "bad,AV,degreesFahrenheit,N,70.0,40,0",
                "good-explicit,AV,degreesFahrenheit,N,71.0,40,0.5",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(server_utils, "CSV_FILE", str(csv_path))

    app = _DummyApp()
    await server_utils.load_csv_and_create_objects(app)

    assert "bad" not in server_utils.point_map
    # Instance 40 should still be available because invalid rows must not reserve it.
    assert int(tuple(server_utils.point_map["good-explicit"].objectIdentifier)[1]) == 40


@pytest.mark.asyncio
async def test_loader_schedule_pointtype_is_accepted(tmp_path, monkeypatch):
    csv_path = tmp_path / "points.csv"
    csv_path.write_text(
        "\n".join(
            [
                "Name,PointType,Units,Commandable,Default,Instance,CovIncrement",
                "occupancy-schedule,Schedule,Status,N,0,1,",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(server_utils, "CSV_FILE", str(csv_path))

    app = _DummyApp()
    await server_utils.load_csv_and_create_objects(app)

    assert "occupancy-schedule" in server_utils.point_map
    schedule = server_utils.point_map["occupancy-schedule"]
    assert int(tuple(schedule.objectIdentifier)[1]) == 1
    assert getattr(schedule, "weeklySchedule", None) is not None
    assert schedule in getattr(app, "objects", [])
    # If supported by BACpypes3 build, this should exist as an empty list.
    # On older builds the loader falls back without this property.
    if hasattr(schedule, "exceptionSchedule"):
        assert schedule.exceptionSchedule == []
