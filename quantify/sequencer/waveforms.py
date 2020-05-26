"""
Contains function to generate most basic waveforms, basic means having a
few parameters and a straightforward translation to AWG amplitude, i.e.,
no knowledge of qubit parameters, channels, etc.

These functions are intened to be used to generate waveforms defined in the :mod:`.pulse_library`.


Examples of waveforms that are too advanced are flux pulses that require
knowledge of the flux sensitivity and interaction strengths and qubit
frequencies.
"""
import numpy as np


def drag(t,
         G_amp: float,
         D_amp: float,
         duration: float,
         nr_sigma: int = 4,
         phase: float = 0,
         subtract_offset: str = 'average'):
    '''
    All inputs are in s and Hz.
    phases are in degree.

    Args:
        t (np.array): times at which to evaluate the function
        G_amp (float):
            Amplitude of the Gaussian envelope.
        D_amp (float):
            Amplitude of the derivative component, the DRAG-pulse parameter.
        duration (float):
            Duration of the pulse in seconds.
        nr_sigma (int):
            After how many sigma the Gaussian is cut off.
        phase (float):
            Phase of the pulse in degrees.
        subtract_offset (str):
            Instruction on how to subtract the offset in order to avoid jumps
            in the waveform due to the cut-off.
            'average': subtract the average of the first and last point.
            'first': subtract the value of the waveform at the first sample.
            'last': subtract the value of the waveform at the last sample.
            'none', None: don't subtract any offset.

    Returns:
        pulse_I, pulse_Q: Two quadratures of the waveform.
    '''

    mu = t[0] + duration/2
    sigma = duration/nr_sigma

    gauss_env = G_amp*np.exp(-(0.5 * ((t-mu)**2) / sigma**2))
    deriv_gauss_env = D_amp * -1 * (t-mu)/(sigma**1) * gauss_env

    # Subtract offsets
    if subtract_offset.lower() == 'none' or subtract_offset is None:
        # Do not subtract offset
        pass
    elif subtract_offset.lower() == 'average':
        gauss_env -= (gauss_env[0]+gauss_env[-1])/2.
        deriv_gauss_env -= (deriv_gauss_env[0]+deriv_gauss_env[-1])/2.
    elif subtract_offset.lower() == 'first':
        gauss_env -= gauss_env[0]
        deriv_gauss_env -= deriv_gauss_env[0]
    elif subtract_offset.lower() == 'last':
        gauss_env -= gauss_env[-1]
        deriv_gauss_env -= deriv_gauss_env[-1]
    else:
        raise ValueError('Unknown value "{}" for keyword argument '
                         '"subtract_offset".'.format(subtract_offset))

    # generate pulses
    G = gauss_env
    D = deriv_gauss_env

    # Apply phase rotation
    pulse_I, pulse_Q = rotate_wave(G, D, phase=phase)

    return pulse_I, pulse_Q


def rotate_wave(wave_I, wave_Q, phase: float):
    """
    Rotate a wave in the complex plane
        wave_I (array) : real component
        wave_Q (array) : imaginary component
        phase (float)  : desired rotation angle in degrees

    returns:
        (rot_I, rot_Q) : arrays containing the rotated waves
    """

    angle = np.deg2rad(phase)

    rot_I = np.cos(angle)*wave_I - np.sin(angle)*wave_Q
    rot_Q = np.sin(angle)*wave_I + np.cos(angle)*wave_Q
    return rot_I, rot_Q
