import os
import shutil
import pytest
import dateutil
import xarray as xr
import numpy as np
from quantify.data.types import TUID
import quantify.data.handling as dh
from quantify.measurement.control import MeasurementControl
from datetime import datetime
from qcodes import ManualParameter
from quantify.utilities._tests_helpers import get_test_data_dir


test_datadir = get_test_data_dir()


def test_gen_tuid():
    ts = datetime.now()
    tuid = dh.gen_tuid(ts)

    assert TUID.is_valid(tuid)
    assert isinstance(tuid, str)
    assert isinstance(tuid, TUID)


def test_initialize_dataset():
    setpar = ManualParameter("x", unit="m", label="X position")
    getpar = ManualParameter("y", unit="V", label="Signal amplitude")
    setable_pars = [setpar]
    setpoints = np.arange(0, 100, 32)
    setpoints = setpoints.reshape((len(setpoints), 1))

    getable_pars = [getpar]
    dataset = dh.initialize_dataset(setable_pars, setpoints, getable_pars)

    assert isinstance(dataset, xr.Dataset)
    assert len(dataset.data_vars) == 2
    assert dataset.attrs.keys() == {"tuid"}
    assert dataset.variables.keys() == {"x0", "y0"}

    x0 = dataset["x0"]
    assert isinstance(x0, xr.DataArray)
    assert x0.attrs["units"] == "m"
    assert x0.attrs["name"] == "x"
    assert x0.attrs["long_name"] == "X position"

    y0 = dataset["y0"]
    assert isinstance(y0, xr.DataArray)
    assert y0.attrs["units"] == "V"
    assert y0.attrs["name"] == "y"
    assert y0.attrs["long_name"] == "Signal amplitude"


def test_initialize_dataset_2D():
    xpar = ManualParameter("x", unit="m", label="X position")
    ypar = ManualParameter("y", unit="m", label="Y position")
    getpar = ManualParameter("z", unit="V", label="Signal amplitude")
    setable_pars = [xpar, ypar]
    setpoints = np.arange(0, 100, 32)
    setpoints = setpoints.reshape((len(setpoints) // 2, 2))
    getable_pars = [getpar]

    dataset = dh.initialize_dataset(setable_pars, setpoints, getable_pars)

    assert isinstance(dataset, xr.Dataset)
    assert len(dataset.data_vars) == 3
    assert dataset.attrs.keys() == {"tuid"}
    assert set(dataset.variables.keys()) == {"x0", "x1", "y0"}


def test_getset_datadir():
    # here to ensure we always start with default datadir
    dh._datadir = None

    with pytest.raises(NotADirectoryError):
        # Ensure users are forced to pick a datadir in order to avoid
        # potential dataloss
        dh.get_datadir()

    new_dir_path = os.path.join(test_datadir, "test_datadir2")
    os.mkdir(new_dir_path)
    dh.set_datadir(new_dir_path)
    assert os.path.split(dh.get_datadir())[-1] == "test_datadir2"
    os.rmdir(new_dir_path)

    # Test setting to None
    with pytest.raises(TypeError):
        dh.set_datadir(None)

    # Test setting to empty str
    with pytest.raises(FileNotFoundError):
        dh.set_datadir("")


def test_load_dataset():
    dh.set_datadir(test_datadir)
    tuid = "20200430-170837-001-315f36"
    dataset = dh.load_dataset(tuid=tuid)
    assert dataset.attrs["tuid"] == tuid

    tuid_short = "20200430-170837"
    dataset = dh.load_dataset(tuid=tuid_short)
    assert dataset.attrs["tuid"] == tuid

    with pytest.raises(FileNotFoundError):
        tuid = "20200430-170837-001-3b5f36"
        dh.load_dataset(tuid=tuid)

    with pytest.raises(FileNotFoundError):
        tuid = "20200230-001-170837"
        dh.load_dataset(tuid=tuid)


def test_get_latest_tuid_empty_datadir():
    valid_dir_but_no_data = get_test_data_dir() / "empty"
    dh.set_datadir(valid_dir_but_no_data)
    with pytest.raises(FileNotFoundError) as excinfo:
        dh.get_latest_tuid()
    assert "There are no valid day directories" in str(excinfo.value)


def test_get_latest_tuid_no_match():
    dh.set_datadir(test_datadir)
    with pytest.raises(FileNotFoundError) as excinfo:
        dh.get_latest_tuid(contains="nonexisting_label")
    assert "No experiment found containing" in str(excinfo.value)


def test_get_latest_tuid_correct_tuid():
    dh.set_datadir(test_datadir)
    tuid = dh.get_latest_tuid(contains="36-Cosine")
    exp_tuid = "20200430-170837-001-315f36"
    assert tuid == exp_tuid


def test_get_tuids_containing():
    dh.set_datadir(test_datadir)
    tuids = dh.get_tuids_containing("Cosine test")
    assert len(tuids) == 2
    assert tuids[0] == "20200430-170837-001-315f36"
    assert tuids[1] == "20200504-191556-002-4209ee"


def test_get_tuids_containing_between_strings():
    dh.set_datadir(test_datadir)

    t_start = "20201124"
    t_stop = "20201125"

    tuids = dh.get_tuids_containing("", t_start=t_start, t_stop=t_stop)
    assert tuids == [
        "20201124-184709-137-8a5112",
        "20201124-184716-237-918bee",
        "20201124-184722-988-0463d4",
        "20201124-184729-618-85970f",
        "20201124-184736-341-3628d4",
    ]

    t_start = "20201124-180000"
    t_stop = "20201124-190000"

    tuids = dh.get_tuids_containing("", t_start=t_start, t_stop=t_stop)
    assert tuids == [
        "20201124-184709-137-8a5112",
        "20201124-184716-237-918bee",
        "20201124-184722-988-0463d4",
        "20201124-184729-618-85970f",
        "20201124-184736-341-3628d4",
    ]

    t_start = "20201124-18:00:00"
    t_stop = "20201124-18:47:30"

    tuids = dh.get_tuids_containing("", t_start=t_start, t_stop=t_stop)
    assert tuids == [
        "20201124-184709-137-8a5112",
        "20201124-184716-237-918bee",
        "20201124-184722-988-0463d4",
        "20201124-184729-618-85970f",
    ]

    t_start = "2020/11/24 18:00:00"
    t_stop = "2020/11/24 18:47:30"

    tuids = dh.get_tuids_containing("", t_start=t_start, t_stop=t_stop)
    assert tuids == [
        "20201124-184709-137-8a5112",
        "20201124-184716-237-918bee",
        "20201124-184722-988-0463d4",
        "20201124-184729-618-85970f",
    ]

    t_start = "20201124-180000"
    t_stop = "20201124-184725"

    tuids = dh.get_tuids_containing("", t_start=t_start, t_stop=t_stop)
    assert tuids == [
        "20201124-184709-137-8a5112",
        "20201124-184716-237-918bee",
        "20201124-184722-988-0463d4",
    ]


def test_get_tuids_containing_between_exclusive_t_stop():
    t_start = "20201124-180000"
    t_stop = "20201124-184722"  # test if t_stop is inclusive

    tuids = dh.get_tuids_containing("", t_start=t_start, t_stop=t_stop)
    assert tuids == [
        "20201124-184709-137-8a5112",
        "20201124-184716-237-918bee",
    ]


def test_get_tuids_containing_between_inclusive_t_start():
    t_start = "20201124-184709"  # test if t_stop is inclusive
    t_stop = "20201124-184723"

    tuids = dh.get_tuids_containing("", t_start=t_start, t_stop=t_stop)
    assert tuids == [
        "20201124-184709-137-8a5112",
        "20201124-184716-237-918bee",
        "20201124-184722-988-0463d4",
    ]


def test_get_tuids_containing_reverse():
    t_start = "20200814"
    t_stop = "20201124-190000"

    tuids = dh.get_tuids_containing("", t_start=t_start, t_stop=t_stop, reverse=True)
    assert tuids == [
        "20201124-184736-341-3628d4",
        "20201124-184729-618-85970f",
        "20201124-184722-988-0463d4",
        "20201124-184716-237-918bee",
        "20201124-184709-137-8a5112",
        "20200814-134652-492-fbf254",
    ]


def test_get_tuids_containing_between_datetimes():
    t_start = "20200430-170836"
    t_stop = "20200504-200000"
    t_start = dateutil.parser.parse(t_start)
    t_stop = dateutil.parser.parse(t_stop)

    tuids = dh.get_tuids_containing("Cosine test", t_start=t_start, t_stop=t_stop)
    assert tuids[0] == "20200430-170837-001-315f36"
    assert tuids[1] == "20200504-191556-002-4209ee"


def test_get_tuids_containing_options():
    dh.set_datadir(test_datadir)

    tuids = dh.get_tuids_containing("Cosine test", t_start="20200501")
    assert len(tuids) == 1
    assert tuids[0] == "20200504-191556-002-4209ee"

    tuids = dh.get_tuids_containing("Cosine test", t_stop="20200501")
    assert len(tuids) == 1
    assert tuids[0] == "20200430-170837-001-315f36"

    tuids = dh.get_tuids_containing("Cosine test", t_start="20200430")
    assert tuids == ["20200430-170837-001-315f36", "20200504-191556-002-4209ee"]

    tuids = dh.get_tuids_containing(
        "Cosine test", t_start="20200430", t_stop="20200504"
    )
    assert len(tuids) == 1
    assert tuids[0] == "20200430-170837-001-315f36"


def test_get_tuids_containing_max_results():
    dh.set_datadir(test_datadir)
    tuids = dh.get_tuids_containing(
        "Cosine test",
        t_start="20200430",
        t_stop="20200505",
        max_results=1,
        reverse=True,
    )
    assert len(tuids) == 1
    assert tuids == ["20200504-191556-002-4209ee"]


def test_get_tuids_containing_None_arg():
    dh.set_datadir(test_datadir)
    for empties in [
        ("20200505", None),
        (None, "20200430"),
        ("20200410", "20200415"),
        ("20200510", "20200520"),
    ]:
        with pytest.raises(FileNotFoundError):
            dh.get_tuids_containing(
                "Cosine test", t_start=empties[0], t_stop=empties[1]
            )


def test_misplaced_exp_container():
    """
    Ensures user is warned if a dataset was misplaced
    """
    tmp_data_path = os.path.join(
        test_datadir,
        "misplaced_exp_container",
    )
    date = "20201006"
    container = "20201008-191556-002-4209eg-Experiment from my colleague"
    os.makedirs(os.path.join(tmp_data_path, date, container), exist_ok=True)
    dh.set_datadir(tmp_data_path)
    with pytest.raises(FileNotFoundError):
        dh.get_tuids_containing(contains="colleague")

    # cleanup
    shutil.rmtree(tmp_data_path)


def test_snapshot():
    empty_snap = dh.snapshot()
    assert empty_snap == {"instruments": {}, "parameters": {}}
    test_MC = MeasurementControl(name="MC")

    test_MC.soft_avg(5)
    snap = dh.snapshot()
    assert snap["instruments"].keys() == {"MC"}
    assert snap["instruments"]["MC"]["parameters"]["soft_avg"]["value"] == 5

    test_MC.close()


def test_dynamic_dataset():
    x = ManualParameter("x", unit="m", label="X position")
    y = ManualParameter("y", unit="m", label="Y position")
    z = ManualParameter("z", unit="V", label="Signal amplitude")
    settables = [x, y]
    gettables = [z]
    dset = dh.initialize_dataset(settables, np.empty((8, len(settables))), gettables)

    x0_vals = np.random.random(8)
    x1_vals = np.random.random(8)
    y0_vals = np.random.random(8)
    dset["x0"].values[:] = x0_vals
    dset["x1"].values[:] = x1_vals
    dset["y0"].values[:] = y0_vals

    dset = dh.grow_dataset(dset)
    assert len(dset["x0"]) == len(dset["x1"]) == len(dset["y0"]) == 16
    assert np.isnan(dset["x0"][8:]).all()
    assert np.isnan(dset["x1"][8:]).all()
    assert np.isnan(dset["y0"][8:]).all()

    x0_vals_ext = np.random.random(3)
    x1_vals_ext = np.random.random(3)
    y0_vals_ext = np.random.random(3)

    dset["x0"].values[8:11] = x0_vals_ext
    dset["x1"].values[8:11] = x1_vals_ext
    dset["y0"].values[8:11] = y0_vals_ext

    dset = dh.trim_dataset(dset)
    assert len(dset["x0"]) == len(dset["x1"]) == len(dset["y0"]) == 11
    np.array_equal(dset["x0"], np.concatenate([x0_vals, x0_vals_ext]))
    np.array_equal(dset["x1"], np.concatenate([x1_vals, x1_vals_ext]))
    np.array_equal(dset["y0"], np.concatenate([y0_vals, y0_vals_ext]))

    assert not np.isnan(dset["x0"]).any()
    assert not np.isnan(dset["x1"]).any()
    assert not np.isnan(dset["y0"]).any()
