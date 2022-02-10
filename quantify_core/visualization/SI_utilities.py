# Repository: https://gitlab.com/quantify-os/quantify-core
# Licensed according to the LICENCE file on the main branch
# pylint: disable=invalid-name  # disabled because of capital SI in module name
"""
Utilities for managing SI units with plotting systems.
"""
import string
from typing import Tuple, Union

import lmfit
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import uncertainties

golden_mean = (np.sqrt(5) - 1.0) / 2.0  # Aesthetic ratio
single_col_figsize = (3.39, golden_mean * 3.39)
double_col_figsize = (6.9, golden_mean * 6.9)
thesis_col_figsize = (12.2 / 2.54, golden_mean * 12.2 / 2.54)


def set_xlabel(axis, label, unit=None, **kw):
    """
    Add a unit aware x-label to an axis object.

    Parameters
    ----------
    axis
        matplotlib axis object to set label on
    label
        the desired label
    unit
        the unit
    **kw
        keyword argument to be passed to matplotlib.set_xlabel
    """
    if unit is not None and unit != "":
        xticks = axis.get_xticks()
        scale_factor, unit = SI_prefix_and_scale_factor(val=max(abs(xticks)), unit=unit)
        formatter = matplotlib.ticker.FuncFormatter(
            lambda x, pos: f"{x * scale_factor:.4g}"
        )

        axis.xaxis.set_major_formatter(formatter)
        axis.set_xlabel(label + f" [{unit}]", **kw)
    else:
        axis.set_xlabel(label, **kw)
    return axis


def set_ylabel(axis, label, unit=None, **kw):
    """
    Add a unit aware y-label to an axis object.

    Parameters
    ----------
    axis
        matplotlib axis object to set label on
    label
        the desired label
    unit
        the unit
    **kw
        keyword argument to be passed to matplotlib.set_ylabel
    """
    if unit is not None and unit != "":
        yticks = axis.get_yticks()
        scale_factor, unit = SI_prefix_and_scale_factor(val=max(abs(yticks)), unit=unit)
        formatter = matplotlib.ticker.FuncFormatter(
            lambda x, pos: f"{x * scale_factor:.6g}"
        )

        axis.yaxis.set_major_formatter(formatter)

        axis.set_ylabel(label + f" [{unit}]", **kw)
    else:
        axis.set_ylabel(label, **kw)
    return axis


def set_cbarlabel(cbar, label, unit=None, **kw):
    """
    Add a unit aware z-label to a colorbar object

    Parameters
    ----------
    cbar
        colorbar object to set label on
    label
        the desired label
    unit
        the unit
    **kw
        keyword argument to be passed to cbar.set_label
    """
    if unit is not None and unit != "":
        zticks = cbar.get_ticks()
        scale_factor, unit = SI_prefix_and_scale_factor(val=max(abs(zticks)), unit=unit)
        formatter = matplotlib.ticker.FuncFormatter(
            lambda x, pos: f"{x * scale_factor:.6g}"
        )
        cbar.ax.yaxis.set_major_formatter(formatter)
        cbar.set_label(label + f" [{unit}]")

    else:
        cbar.set_label(label, **kw)
    return cbar


# pylint: disable=invalid-name
def adjust_axeslabels_SI(ax) -> None:
    """
    Auto adjust the labels of a plot generated by xarray to SI-unit aware labels.
    """
    xlabel = ax.get_xlabel()
    idxl = xlabel.find("[")
    idxr = xlabel.find("]")

    # only update the label if brackets are present
    if idxl != -1 and idxr != -1:
        # extract unit
        xunit = xlabel[idxl + 1 : idxr]
        xlabel = xlabel[: -(len(xunit) + 3)]
        # replace by a unit aware label formatter
        set_xlabel(ax, xlabel, xunit)

    ylabel = ax.get_ylabel()
    idxl = ylabel.find("[")
    idxr = ylabel.find("]")
    # only update the label if brackets are present
    if idxl != -1 and idxr != -1:
        yunit = ylabel[idxl + 1 : idxr]
        ylabel = ylabel[: -(len(yunit) + 3)]
        # replace by a unit aware label formatter
        set_ylabel(ax, ylabel, yunit)


SI_PREFIXES = dict(zip(range(-24, 25, 3), "yzafpnμm kMGTPEZY"))
SI_PREFIXES[0] = ""

# N.B. not all of these are SI units, however, all of these support SI prefixes
SI_UNITS = (
    "SI_PREFIX_ONLY,m,s,g,W,J,V,A,F,T,Hz,Ohm,S,N,C,px,b,B,K,Bar,"
    r"Vpeak,Vpp,Vp,Vrms,$\Phi_0$,A/s".split(",")
)  # noqa: W605


def SI_prefix_and_scale_factor(val, unit=None):
    """
    Takes in a value and unit and if applicable returns the proper scale factor
    and SI prefix.

    If the unit is None, no scaling is done.
    If the unit is "SI_PREFIX_ONLY", the value is scaled and an SI prefix is applied
    without a base unit.

    Parameters
    ----------
    val : float
        the value
    unit : str
        the unit of the value
    Returns
    -------
    scale_factor : float
        scale_factor needed to convert value
    scaled_unit : str
        unit including the prefix
    """
    if unit in SI_UNITS:
        try:
            with np.errstate(all="ignore"):
                prefix_power = np.log10(abs(val)) // 3 * 3
                prefix = SI_PREFIXES[prefix_power]
                # Greek symbols not supported in tex
                if plt.rcParams["text.usetex"] and prefix == "μ":
                    prefix = r"$\mu$"
            if unit == "SI_PREFIX_ONLY":
                scale_factor, scaled_unit = 10**-prefix_power, prefix
            else:
                scale_factor, scaled_unit = 10**-prefix_power, prefix + unit
        # this exception can be triggered in the pyqtgraph multi processing
        except (KeyError, TypeError):
            scale_factor, scaled_unit = 1, unit

    elif unit is None:
        scale_factor, scaled_unit = 1, ""
    else:
        scale_factor, scaled_unit = 1, unit
    return scale_factor, scaled_unit


def SI_val_to_msg_str(val: float, unit: str = None, return_type=str):
    """
    Takes in a value  with optional unit and returns a string tuple consisting of
    (value_str, unit) where the value and unit are rescaled according to SI prefixes,
    IF the unit is an SI unit (according to the comprehensive list of
    SI units in this file ;).

    the value_str is of the type specified in return_type (str) by default.
    """
    sc, new_unit = SI_prefix_and_scale_factor(val, unit)
    try:
        new_val = sc * val
    except TypeError:
        return return_type(val), unit

    return return_type(new_val), new_unit


class SafeFormatter(string.Formatter):
    def __init__(self, missing: str = "~~", bad_fmt: str = "!!"):
        # pylint: disable=line-too-long
        """
        A formatter that replaces "missing" values and "bad_fmt" to prevent unexpected
        Exceptions being raised.

        Parameters
        ----------
        missing
            Replaces missing values with specified string.
        bad_fmt
            Replaces values that cannot be formatted with specified string.

        Based on https://stackoverflow.com/questions/20248355/how-to-get-python-to-gracefully-format-none-and-non-existing-fields
        """
        self.missing, self.bad_fmt = missing, bad_fmt

    def get_field(self, field_name, args, kwargs):
        # Handle a key not found
        try:
            val = super().get_field(field_name, args, kwargs)
            # Python 3, 'super().get_field(field_name, args, kwargs)' works
        except (KeyError, AttributeError):
            val = None, field_name
        return val

    def format_field(self, value, format_spec):
        # handle an invalid format
        if value is None:
            return self.missing
        try:
            return super().format_field(value, format_spec)
        except ValueError as e:
            if self.bad_fmt is not None:
                return self.bad_fmt
            raise e


def format_value_string(
    par_name: str,
    parameter: Union[
        lmfit.Parameter,
        uncertainties.core.Variable,
        uncertainties.core.AffineScalarFunc,
        float,
    ],
    end_char="",
    unit=None,
) -> str:
    """
    Format an lmfit parameter or uncertainties ufloat to a string of value with
    uncertainty.

    If there is no stderr, use 5 significant figures.
    If there is a standard error use a precision one order of magnitude more precise
    than the size of the error and display the stderr itself to two significant figures
    in standard index notation in the same units as the value.

    Parameters
    ----------
    par_name :
        the name of the parameter to use in the string
    parameter : :class:`lmfit.parameter.Parameter`,
        :class:`!uncertainties.core.Variable` or float.
        A :class:`~lmfit.parameter.Parameter` object or an object e.g.,
        returned by :func:`!uncertainties.ufloat`. The value and stderr of this
        parameter will be used. If a float is given, the stderr is taken to be None.
    end_char :
        A character that will be put at the end of the line.
    unit :
        a unit. If this is an SI unit it will be used in automatically
        determining a prefix for the unit and rescaling accordingly.

    Returns
    -------
    :
        The parameter and its error formatted as a string
    """
    if isinstance(
        parameter, (uncertainties.core.Variable, uncertainties.core.AffineScalarFunc)
    ):
        value = parameter.nominal_value
        stderr = parameter.std_dev
        if np.isnan(stderr):
            stderr = None
    elif isinstance(parameter, lmfit.Parameter):
        value = parameter.value
        stderr = parameter.stderr
    else:
        value = parameter
        stderr = None

    scale_factor, unit = SI_prefix_and_scale_factor(value, unit)
    val = value * scale_factor
    if stderr is not None:
        stderr = stderr * scale_factor
    else:
        stderr = None

    (val_format_specifier, err_format_specifier) = value_precision(val, stderr)

    fmt = SafeFormatter(missing="NaN")
    if stderr is not None:
        val_string = rf": {val_format_specifier}$\pm${err_format_specifier} {{}}{{}}"
        # par name is excluded from the format command to allow latex {} characters.
        val_string = par_name + fmt.format(val_string, val, stderr, unit, end_char)
    else:
        val_string = f": {val_format_specifier} {{}}{{}}"
        # par name is excluded from the format command to allow latex {} characters.
        val_string = par_name + fmt.format(val_string, val, unit, end_char)
    return val_string


def value_precision(val, stderr=None) -> Tuple[str]:
    """
    Calculate the precision to which a parameter is to be specified, according to
    its standard error. Returns the appropriate format specifier string.

    If there is no stderr, use 5 significant figures.
    If there is a standard error use a precision one order of magnitude more precise
    than the size of the error and display the stderr itself to two significant figures
    in standard index notation in the same units as the value.

    Parameters
    ----------
    val: float
        the nominal value of the parameter
    stderr: float
        the standard error on the parameter

    Returns
    ----------
    val_format_specifier: str
        python format specifier which sets the precision of the parameter value
    err_format_specifier: str
        python format specifier which set the precision of the error
    """

    if stderr is None or stderr == 0:
        return "{:.5g}", "{:.1f}"

    value_mag = np.floor(np.log10(abs(val))) + 1
    err_mag = np.floor(np.log10(abs(stderr))) + 1
    # pylint: disable=no-else-return
    if err_mag == 2:
        return "{:.0f}", "{:.0f}"
    elif err_mag == 1:
        return "{:.1f}", "{:.1f}"
    else:
        sig_figs = int(
            max(value_mag - err_mag + 2, 2)
        )  # If the error is the same size as the value or larger, use 2 sig figs
        return "{:#." + "{:d}".format(sig_figs) + "g}", "{:#.2g}"
