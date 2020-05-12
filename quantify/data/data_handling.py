"""
Module for handling data.

This module contains  utilities to handle the data files in quantify.

"""
import os
import numpy as np
import xarray as xr
from quantify.data.core_data import TUID
from qcodes import Instrument
from quantify.utilities.general import delete_keys_from_dict
from datetime import datetime
from uuid import uuid4
import sys


# this is a pointer to the module object instance itself.
this = sys.modules[__name__]

_default_datadir = os.path.abspath(os.path.join(
    __file__, '..', '..', '..', 'data'))

this._datadir = None


def gen_tuid(ts=None):
    """
    Generates a :class:`~quantify.data.core_data.TUID` based on current time.

    Args:
        ts (datetime) : optional :class:`~python:datetime.datetime`  can be
            passed to ensure the tuid is based on a specific time.

    Returns:
        tuid (:class:`~quantify.data.core_data.TUID`): timestamp based uid.
    """
    if ts is None:
        ts = datetime.now()
    # ts gives microsecs by default
    (dt, micro) = ts.strftime('%Y%m%d-%H%M%S-.%f').split('.')
    # this ensures the string is formatted correctly as some systems return 0
    # for micro
    dt = "%s%03d-" % (dt, int(micro) / 1000)
    # the tuid is composed of the timestamp and a 6 character uuid.
    tuid = TUID(dt + str(uuid4())[:6])

    return tuid


def get_datadir():
    """Returns the current data directory."""

    if this._datadir is None:
        this._datadir = this._default_datadir

    return this._datadir


def set_datadir(datadir):
    """
    Sets the data directory.

    Args:
        datadir (str):
            path of the data directory. If set to None, resets
            the datadir to the default datadir (quantify/data).
    """
    this._datadir = datadir


def load_dataset(tuid, datadir=None):
    """
    Loads a dataset specified by a tuid.

    Args:
        tuid (str): a :class:`~quantify.data.core_data.TUID` string.
            it is also possible to specify only the first part of a tuid.

        datadir (str):
            path of the data directory. If `None`, uses `get_datadir()` to
            determine the data directory.

    Returns:
        dataset

    .. tip::

        This method also works when specifying only the first part of a
        :class:`~quantify.data.core_data.TUID`.

    .. note::

        This method uses :func:`xarray.load_dataset` to ensure the file is
        closed after loading as datasets are intended to be immutable after
        performing the initial experiment.
    """

    if datadir is None:
        datadir = get_datadir()

    daydir = os.path.join(datadir, tuid[:8])

    # This will raise a file not found error if no data exists on the specified
    # date
    exp_folders = list(filter(lambda x: tuid[9:] in x, os.listdir(daydir)))
    if len(exp_folders) == 0:

        print(os.listdir(daydir))
        raise FileNotFoundError(
            "File with tuid: {} was not found.".format(tuid))

    # We assume that the length is 1 as tuid is assumed to be unique
    exp_folder = exp_folders[0]

    dataset = xr.load_dataset(os.path.join(daydir, exp_folder, 'dataset.hdf5'))
    return dataset


def create_exp_folder(tuid,  name='', datadir=None):
    """
    Creates an empty folder to store an experiment container.

    If the folder already exists, simple return the experiment folder
    corresponding to the :class:`~quantify.data.core_data.TUID`.

    Args:
        tuid (:class:`~quantify.data.core_data.TUID`) :
            a timestamp based human-readable unique identifier.
        name (str) : optional name to identify the folder
        datadir (str):
            path of the data directory. If `None`, uses `get_datadir()` to
            determine the data directory.

    Returns:
        exp_folder (str):
            the full path of the experiment folder following the following
            convention: /datadir/YYMMDD/HHMMSS-******-name/
    """
    assert TUID.is_valid(tuid)

    if datadir is None:
        datadir = get_datadir()
    exp_folder = os.path.join(datadir, tuid[:8], tuid[9:])
    if name != '':
        exp_folder += '-'+name

    os.makedirs(exp_folder, exist_ok=True)
    return exp_folder


def is_valid_dset(dset):
    """
    Asserts if dset adheres to quantify Dataset specification.

    Args:
        dset: an xarray dset object

    Returns:
        is_valid (bool)
    """
    if not isinstance(dset, xr.Dataset):
        raise TypeError
    assert TUID.is_valid(dset.attrs['tuid'])

    return True


def append_to_Xarr():
    raise NotImplementedError()


def initialize_dataset(setable_pars, setpoints, getable_pars):
    """
    Initialize an empty dataset based on
        setable_pars, setpoints and getable_pars

    Args:
        setable_pars (list):    a list of M setables
        setpoints (np.array):   an (N*M) array
        getable_pars (list):    a list of getables

    Returns:
        Dataset

    """
    darrs = []
    for i, setpar in enumerate(setable_pars):
        darrs.append(xr.DataArray(
            data=setpoints[:, i],
            name='x{}'.format(i),
            attrs={'name': setpar.name, 'long_name': setpar.label,
                   'unit': setpar.unit}))

    numpoints = len(setpoints[:, 0])
    for j, getpar in enumerate(getable_pars):
        empty_arr = np.empty(numpoints)
        empty_arr[:] = np.nan
        darrs.append(xr.DataArray(
            data=empty_arr,
            name='y{}'.format(j),
            attrs={'name': getpar.name, 'long_name': getpar.label,
                   'unit': getpar.unit}))

    dataset = xr.merge(darrs)
    dataset.attrs['tuid'] = gen_tuid()
    return dataset


########################################################################


def get_latest_tuid(contains=''):
    """
    Returns the most recent tuid.

    Args:
        contains (str): an optional string that is contained in the experiment
            name

    .. tip::

        This function is similar to :func:`~get_tuids_containing` but is
        preferred if one is only interested in the most recent
        :class:`~quantify.data.core_data.TUID` for performace reasons.

    """

    datadir = get_datadir()
    # Create a sorted list of
    daydirs = list(filter(
        lambda x: (x.isdigit() and len(x) == 8), os.listdir(datadir)))
    daydirs.sort(reverse=True)
    if len(daydirs) == 0:
        raise FileNotFoundError('There are no valid day directories in '
                                'the data folder "{}".'.format(datadir))
    else:
        for dd in daydirs:
            expdirs = list(
                filter(lambda x:
                       (x[:6].isdigit() and x[6] == '-' and len(x) > 12 and
                        contains in x), os.listdir(os.path.join(datadir, dd))))
            expdirs.sort(reverse=True)
            if len(expdirs) > 0:
                # convert to tuid
                tuid = TUID('{}-{}'.format(dd, expdirs[0][:17]))

                return tuid

                expdirs[0]
        raise FileNotFoundError('No experiment found containing "{}"'.format(
            contains))


def get_tuids_containing(contains=''):
    pass


def snapshot(update: bool = False, clean: bool = True) -> dict:
    """
    State of all instruments setup as a JSON-compatible dictionary (everything
        that the custom JSON encoder class
        :class:`qcodes.utils.helpers.NumpyJSONEncoder` supports).

    Args:
        update (bool) : if True, first gets all values before filling the
            snapshot.
        clean (bool)  : if True, removes certain keys from the snapshot to
            create a more readible and compact snapshot.

    """

    snap = {
        'instruments': {},
        'parameters': {},
    }
    for ins_name, ins_ref in Instrument._all_instruments.items():
        snap['instruments'][ins_name] = ins_ref().snapshot(update=update)

    if clean:
        exclude_keys = {
            "inter_delay",
            "post_delay",
            "vals",
            "instrument",
            "submodules",
            "functions",
            "__class__",
            "raw_value",
            "instrument_name",
            "full_name",
            "val_mapping",
        }
        snap = delete_keys_from_dict(snap, exclude_keys)

    return snap
