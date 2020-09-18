"""
Author: Remi Lafage <remi.lafage@onera.fr>

This package is distributed under New BSD license.
"""
import numpy as np
from smt.surrogate_models.surrogate_model import SurrogateModel
from smt.sampling_methods.sampling_method import SamplingMethod
from smt.utils.checks import check_2d_array

FLOAT = "float_type"
INT = "int_type"
ENUM = "enum_type"


def check_xspec_consistency(xtypes, xlimits):
    if len(xlimits) != len(xtypes):
        raise ValueError(
            "number of x limits ({}) do not"
            "correspond to number of specified types ({})".format(
                len(xlimits), len(xtypes)
            )
        )

    for i, xtyp in enumerate(xtypes):
        if (not isinstance(xtyp, tuple)) and len(xlimits[i]) != 2:
            raise ValueError(
                "Bad x limits ({}) for variable type {} (index={})".format(
                    xlimits[i], xtyp, i
                )
            )

        if (
            xtyp != FLOAT
            and xtyp != INT
            and (not isinstance(xtyp, tuple) or xtyp[0] != ENUM)
        ):
            raise ValueError("Bad type specification {}".format(xtyp))

        if isinstance(xtyp, tuple) and len(xlimits[i]) != xtyp[1]:
            raise ValueError(
                "Bad x limits and x types specs not consistent. "
                "Got a categorical type with {} levels "
                "while x limits contains {} values (index={})".format(
                    xtyp[1], len(xlimits[i]), i
                )
            )


def compute_x_unfold_dimension(xtypes):
    res = 0
    for xtyp in xtypes:
        if xtyp == FLOAT or xtyp == INT:
            res += 1
        elif isinstance(xtyp, tuple) and xtyp[0] == ENUM:
            res += xtyp[1]
        else:
            raise ValueError(
                "Bad var type specification: "
                "should be FLOAT, INT or (ENUM, n), got {}".format(xtyp)
            )
    return res


def unfold_with_continuous_limits(xtypes, xlimits):
    """
    Expand xlimits to add continuous dimensions for enumerate x features
    Each level of an enumerate gives a new continuous dimension in [0, 1].
    Each integer dimensions are relaxed continuously.
    
    Parameters
    ---------
    xlimits : list
        bounds of each original dimension (bounds of enumerates being the list of levels).

    Returns
    -------
    np.ndarray [nx continuous, 2]
        bounds of the each dimension where limits for enumerates (ENUM) 
        are expanded ([0, 1] for each level).
    """

    # Continuous optimization : do nothing
    xlims = []
    for i, xtyp in enumerate(xtypes):
        if xtyp == FLOAT or xtyp == INT:
            xlims.append(xlimits[i])
        elif isinstance(xtyp, tuple) and xtyp[0] == ENUM:
            if xtyp[1] == len(xlimits[i]):
                xlims.extend(xtyp[1] * [[0, 1]])
            else:
                raise ValueError(
                    "Bad xlimits for categorical var[{}] "
                    "should have {} categories, got only {} in {}".format(
                        i, xtyp[1], len(xlimits[i]), xlimits[i]
                    )
                )
        else:
            raise ValueError(
                "Bad var type specification: "
                "should be FLOAT, INT or (ENUM, n), got {}".format(xtyp)
            )
    return np.array(xlims).astype(
        float
    )  # avoid possible weird typing of initial xlimits ndarray


def cast_to_discrete_values(xtypes, x):
    """
    Project continuously relaxed values to their closer assessable values.
    Note: categorical (or enum) x dimensions are still expanded that is 
    there are still as many columns as categorical possible values for the given x dimension. 
    For instance, if an input dimension is typed ["blue", "red", "green"] in xlimits a sample/row of 
    the input x may contain the values (or mask) [..., 0, 0, 1, ...] to specify "green" for 
    this original dimension.

    Parameters
    ----------
    x : np.ndarray [n_evals, dim]
        continuous evaluation point input variable values 
    
    Returns
    -------
    np.ndarray
        feasible evaluation point value in categorical space.
    """
    ret = x.copy()
    x_col = 0
    for xtyp in xtypes:
        if xtyp == FLOAT:
            x_col += 1
            continue

        elif xtyp == INT:
            ret[:, x_col] = np.round(ret[:, x_col])
            x_col += 1

        elif isinstance(xtyp, tuple) and xtyp[0] == ENUM:
            # Categorial : The biggest level is selected.
            xenum = ret[:, x_col : x_col + xtyp[1]]
            maxx = np.max(xenum, axis=1).reshape((-1, 1))
            mask = xenum < maxx
            xenum[mask] = 0
            xenum[~mask] = 1
            x_col = x_col + xtyp[1]
        else:
            raise ValueError(
                "Bad var type specification: "
                "should be FLOAT, INT or (ENUM, n), got {}".format(xtyp)
            )
    return ret


def fold_with_enum_index(xtypes, x):
    """
    Reduce categorical inputs from discrete unfolded space to  
    initial x dimension space where categorical x dimensions are valued by the index
    in the corresponding enumerate list.
    For instance, if an input dimension is typed ["blue", "red", "green"] a sample/row of 
    the input x may contain the mask [..., 0, 0, 1, ...] which will be contracted in [..., 2, ...]
    meaning the "green" value.
    This function is the opposite of unfold_with_enum_mask().
            
    Parameters
    ---------
    x: np.ndarray [n_evals, dim]
        continuous evaluation point input variable values 
    xlimits: np.ndarray
        the bounds of the each original dimension and their labels .
    
    Returns
    -------
    np.ndarray [n_evals, dim]
        evaluation point input variable values with enumerate index for categorical variables
    """
    xfold = np.zeros((x.shape[0], len(xtypes)))
    unfold_index = 0
    for i, xtyp in enumerate(xtypes):
        if xtyp == FLOAT or xtyp == INT:
            xfold[:, i] = x[:, unfold_index]
            unfold_index += 1
        elif isinstance(xtyp, tuple) and xtyp[0] == ENUM:
            index = np.argmax(x[:, unfold_index : unfold_index + xtyp[1]], axis=1)
            xfold[:, i] = index
            unfold_index += xtyp[1]
        else:
            raise ValueError(
                "Bad var type specification: "
                "should be FLOAT, INT or (ENUM, n), got {}".format(xtyp)
            )
    return xfold


def unfold_with_enum_mask(xtypes, x):
    """
    Expand categorical inputs from initial x dimension space where categorical x dimensions 
    are valued by the index in the corresponding enumerate list to the discrete unfolded space.
    For instance, if an input dimension is typed ["blue", "red", "green"] a sample/row of 
    the input x may contain [..., 2, ...] which will be expanded in [..., 0, 0, 1, ...].
    This function is the opposite of fold_with_enum_index().
            
    Parameters
    ---------
    x: np.ndarray [n_evals, nx]
        continuous evaluation point input variable values 
    xlimits: np.ndarray
        the bounds of the each original dimension and their labels .
    
    Returns
    -------
    np.ndarray [n_evals, nx continuous]
        evaluation point input variable values with enumerate index for categorical variables
    """
    xunfold = np.zeros((x.shape[0], compute_x_unfold_dimension(xtypes)))
    for i, xtyp in enumerate(xtypes):
        if xtyp == FLOAT or xtyp == INT:
            xunfold[:, i] = x[:, i]
        elif isinstance(xtyp, tuple) and xtyp[0] == ENUM:
            enum_slice = xunfold[:, i : i + xtyp[1]]
            for row in range(x.shape[0]):
                enum_slice[row, x[row, i].astype(int)] = 1
        else:
            raise ValueError(
                "Bad var type specification: "
                "should be FLOAT, INT or (ENUM, n), got {}".format(xtyp)
            )
    return xunfold


def cast_to_enum_value(xlimits, x_col, enum_indexes):
    """
    Return enumerate level from indices for the given x feature.

    Parameters
    ----------
        xlimits: array-like
            bounds of x features
        x_col: int 
            index of the feature typed as enum
        enum_indexes: list
            list of indexes in the possible values for the enum

    Returns
    -------
        list of levels (labels) for the given enum feature
    """
    return [xlimits[x_col][index] for index in enum_indexes]


class MixedIntegerSamplingMethod(SamplingMethod):
    def __init__(self, xtypes, xlimits, sampling_method_class, **kwargs):
        super()
        check_xspec_consistency(xtypes, xlimits)
        self._xtypes = xtypes
        self._xlimits = unfold_with_continuous_limits(xtypes, xlimits)
        self._output_in_folded_space = kwargs.get("output_in_folded_space", True)
        kwargs.pop("output_in_folded_space", None)
        self._sampling_method = sampling_method_class(xlimits=self._xlimits, **kwargs)

    def __call__(self, nt):
        doe = self._sampling_method(nt)
        unfold_xdoe = cast_to_discrete_values(self._xtypes, doe)
        if self._output_in_folded_space:
            return fold_with_enum_index(self._xtypes, unfold_xdoe)
        else:
            return unfold_xdoe


class MixedIntegerSurrogate(SurrogateModel):
    def __init__(self, xtypes, xlimits, surrogate, input_in_folded_space=True):
        super().__init__()
        check_xspec_consistency(xtypes, xlimits)
        self._surrogate = surrogate
        self._xtypes = xtypes
        self._xlimits = xlimits
        self._input_in_folded_space = input_in_folded_space
        self.name = "MixedInteger" + self._surrogate.name
        self.supports = self._surrogate.supports
        self.options["print_global"] = False

    def _initialize(self):
        self.supports["derivatives"] = False

    def set_training_values(self, xt, yt, name=None):
        xt = check_2d_array(xt, "xt")
        if self._input_in_folded_space:
            xt2 = unfold_with_enum_mask(self._xtypes, xt)
        else:
            xt2 = xt
        super().set_training_values(xt2, yt)
        self._surrogate.set_training_values(xt2, yt, name)

    def update_training_values(self, yt, name=None):
        super().update_training_values(yt, name)
        self._surrogate.update_training_values(yt, name)

    def _train(self):
        self._surrogate._train()

    def _predict_values(self, x):
        if self._input_in_folded_space:
            x2 = unfold_with_enum_mask(self._xtypes, x)
        else:
            x2 = x
        return self._surrogate.predict_values(cast_to_discrete_values(self._xtypes, x2))

    def _predict_variances(self, x):
        if self._input_in_folded_space:
            x2 = unfold_with_enum_mask(self._xtypes, x)
        else:
            x2 = x
        return self._surrogate.predict_variances(
            cast_to_discrete_values(self._xtypes, x2)
        )


class MixedIntegerContext(object):
    def __init__(self, xtypes, xlimits, work_in_folded_space=True):
        check_xspec_consistency(xtypes, xlimits)
        self._xtypes = xtypes
        self._xlimits = xlimits
        self._work_in_folded_space = work_in_folded_space

    def build_sampling_method(self, sampling_method_class, **kwargs):
        kwargs["output_in_folded_space"] = self._work_in_folded_space
        return MixedIntegerSamplingMethod(
            self._xtypes, self._xlimits, sampling_method_class, **kwargs
        )

    def build_surrogate(self, surrogate):
        return MixedIntegerSurrogate(
            self._xtypes,
            self._xlimits,
            surrogate,
            input_in_folded_space=self._work_in_folded_space,
        )

    def unfold_with_continuous_limits(self, xlimits):
        return unfold_with_continuous_limits(self._xtypes, xlimits)

    def cast_to_discrete_values(self, x):
        return cast_to_discrete_values(self._xtypes, x)

    def fold_with_enum_index(self, x):
        return fold_with_enum_index(self._xtypes, x)

    def unfold_with_enum_mask(self, x):
        return unfold_with_enum_mask(self._xtypes, x)

    def cast_to_enum_value(self, x_col, enum_indexes):
        return cast_to_enum_value(self._xlimits, x_col, enum_indexes)
