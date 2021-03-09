import numpy as np
import sympy as sp
from scipy.optimize import least_squares

import enum
from collections import OrderedDict
import time

from app.resources import resources
from app.model import domain

INDEPENDENT_VARIABLE = "t"

DELTA = "\u0394"
LAMBDA = "\u03BB"
BETA = "\u03B2"
SIGMA = "\u03C3"
ALPHA = "\u03B1"
PHI = "\u03A6"
PI = "\u03C0"
NAUGHT = "\u2080"

SIMPLE_EXPONENTIAL = "exp(-\u03BB*t)"
STRETCHED_EXPONENTIAL = "exp(-(\u03BB*t)^\u03B2)"
SIMPLE_GAUSSIAN = "exp(-1/2*(\u03C3*t)^2)"
GAUSSIAN_KT = "1/3 + 2/3*(1 - (\u03C3*t)^2)*exp(-1/2*(\u03C3*t)^2)"
LORENTZIAN_KT = "1/3 + 2/3*(1 - \u03BB*t)*exp(-\u03BB*t)"
COMBINED_KT = "1/3 + 2/3*(1-\u03C3^2*t^2-\u03BB*t)*exp(-\u03C3^2*t^2/2-\u03BB*t)"
STRETCHED_KT = "1/3 + 2/3*(1-(\u03C3*t)^\u03B2)*exp(-(\u03C3*t)^\u03B2/\u03B2)"
COSINE = "a*cos(2*\u03C0*v*t + \u03C0*\u03A6/180)*exp(-\u03B2*t)"
INTERNAL_COSINE = "\u03B1*cos(2*\u03C0*v*t + \u03C0*\u03A6/180)*exp(-\u03BB*t) + (1-\u03B1)*exp(-\u03BB*t)"
BESSEL = "j\u2080*(2*\u03C0*v*t + \u03C0*\u03A6/180)"
INTERNAL_BESSEL = "\u03B1*j\u2080*(2*\u03C0*v*t + \u03C0*\u03A6/180)*exp(-\u03BB*t) + (1-\u03B1)*exp(-\u03BB*t)"

ALPHA_CORRECTION = '((1-\u03B1)+((1+\u03B1)*({})))/((1+\u03B1)+((1-\u03B1)*({})))'

EQUATION_DICTIONARY = {"Simple Exponential": SIMPLE_EXPONENTIAL,
                       "Stretched Exponential": STRETCHED_EXPONENTIAL,
                       "Simple Gaussian": SIMPLE_GAUSSIAN,
                       "Gaussian KT": GAUSSIAN_KT,
                       "Lorentzian KT": LORENTZIAN_KT,
                       "Combined KT": COMBINED_KT,
                       "Stretched KT": STRETCHED_KT,
                       "Cosine": COSINE,
                       "Internal Cosine": INTERNAL_COSINE,
                       "Bessel": BESSEL,
                       "Internal Bessel": INTERNAL_BESSEL}

if "funs" in resources.SAVED_USER_DATA.keys():
    USER_EQUATION_DICTIONARY = resources.SAVED_USER_DATA["funs"]
else:
    USER_EQUATION_DICTIONARY = {}

resources.SAVED_USER_DATA["funs"] = USER_EQUATION_DICTIONARY


class FitOptions(enum.IntEnum):
    GLOBAL = 0
    LEAST_SQUARES = 1
    ALPHA_CORRECT = 2


class FitVar:
    def __init__(self, symbol, name, value, is_fixed, lower, upper, is_global, independent):
        self.symbol = symbol
        self.name = name
        self.value = value
        self.is_fixed = is_fixed
        self.lower = lower
        self.upper = upper
        self.is_global = is_global
        self.independent = independent

    def __repr__(self):
        return "FitVar(symbol={}, name={}, value={}, fixed={}, lower={}, upper={}, global={}, independent={})".format(
            self.symbol, self.name, self.value, self.is_fixed, self.lower, self.upper, self.is_global, self.independent
        )


class FitSpec:
    def __init__(self):
        self.function = ''
        self.variables = dict()
        self.asymmetries = dict()
        self.options = {FitOptions.GLOBAL: False,
                        FitOptions.LEAST_SQUARES: True,
                        FitOptions.ALPHA_CORRECT: False}

    def get_lower_bounds(self):
        return [var.lower for var in self.variables.values()]

    def get_upper_bounds(self):
        return [var.upper for var in self.variables.values()]

    def get_symbols(self):
        return [var.symbol for var in self.variables.values()]

    def get_guesses(self):
        return [var.value for var in self.variables.values()]

    def get_fixed_symbols(self):
        symbols = []
        for var in self.variables.values():
            if var.is_fixed:
                symbols.append(var.symbol)
        return symbols

    def get_fixed_guesses(self):
        guesses = []
        for var in self.variables.values():
            if var.is_fixed:
                guesses.append(var.value)
        return guesses

    def get_unfixed_symbols(self):
        symbols = []
        for var in self.variables.values():
            if not var.is_fixed:
                symbols.append(var.symbol)
        return symbols

    def get_unfixed_lower_bounds(self):
        lowers = []
        for var in self.variables.values():
            if not var.is_fixed:
                lowers.append(var.lower)
        return lowers

    def get_unfixed_upper_bounds(self):
        uppers = []
        for var in self.variables.values():
            if not var.is_fixed:
                uppers.append(var.upper)
        return uppers

    def get_unfixed_guesses(self):
        guesses = []
        for var in self.variables.values():
            if not var.is_fixed:
                guesses.append(var.value)
        return guesses

    def get_non_global_symbols(self):
        symbols = []
        for var in self.variables.values():
            if not var.is_global:
                symbols.append(var.symbol)

        return symbols

    def get_global_symbols(self):
        symbols = []
        for var in self.variables.values():
            if var.is_global and not var.is_fixed:
                symbols.append(var.symbol)

        return symbols

    def get_global_fit_variable_set(self):
        symbols = set()
        for var in self.get_non_global_symbols():
            if self.variables[var].is_fixed:
                continue

            symbols.update([var + _shortened_run_id(run_id) for run_id, _ in self.asymmetries.items()])

        symbols.update(self.get_global_symbols())

        return symbols

    def get_global_fit_symbols(self):
        symbols = []
        for symbol, variable in self.variables.items():
            if variable.is_fixed:
                continue

            if not variable.is_global:
                for run_id, _ in self.asymmetries.items():
                    symbols.append(symbol + _shortened_run_id(run_id))
            else:
                symbols.append(symbol)

        return symbols

    def get_global_fit_guesses(self):
        guesses = []
        for _, variable in self.variables.items():
            if variable.is_fixed:
                continue

            if not variable.is_global:
                for run_id, _ in self.asymmetries.items():
                    guesses.append(variable.value)
            else:
                guesses.append(variable.value)

        return guesses

    def get_global_fit_lowers(self):
        lowers = []
        for _, variable in self.variables.items():
            if variable.is_fixed:
                continue

            if not variable.is_global:
                for run_id, _ in self.asymmetries.items():
                    lowers.append(variable.lower)
            else:
                lowers.append(variable.lower)

        return lowers

    def get_global_fit_uppers(self):
        uppers = []
        for _, variable in self.variables.items():
            if variable.is_fixed:
                continue

            if not variable.is_global:
                for run_id, _ in self.asymmetries.items():
                    uppers.append(variable.upper)
            else:
                uppers.append(variable.upper)

        return uppers

    def get_data(self):
        return self.asymmetries

    def get_data_length(self):
        return len(list(self.asymmetries.values())[0])

    def get_num_datasets(self):
        return len(self.asymmetries)

    def get_bin_size(self):
        return list(self.asymmetries.values())[0].bin_size

    def get_time_zero(self):
        return list(self.asymmetries.values())[0].time[0]


class FitDataset:
    def __init__(self):
        t = time.localtime()
        current_time = time.strftime("%d.%m.%Y at %H.%M.%S", t)

        self.id = str(current_time)
        self.fits = {}
        self.options = {}
        self.function = None


class Fit:
    def __init__(self):
        self.__variables = dict()
        self.kwargs = dict()
        self.expression_as_string = None
        self.expression_as_lambda = None
        self.title = None
        self.run_id = None

    @property
    def variables(self):
        return self.__variables

    @variables.setter
    def variables(self, variables):
        self.__variables = variables
        self.kwargs = {}
        for var in self.__variables.values():
            if not var.is_fixed:
                self.kwargs[var.symbol] = var.value

    def __call__(self, *args, **kwargs):
        if len(args) < 1 or type(args[0]) != np.ndarray:
            raise ValueError("Only takes numpy array of values as an input.")
        return self.expression_as_lambda(args[0], **self.kwargs)


class FitEngine:
    def __init__(self):
        self.__run_service = domain.RunService()

    def fit(self, spec: FitSpec) -> FitDataset:
        if len(set([len(asymmetry) for asymmetry in spec.get_data()])) != 1:
            raise ValueError("Must have one or more datasets all of equal length to fit")

        if spec.function == '':
            raise ValueError("Empty function attribute")

        if spec.options[FitOptions.GLOBAL]:
            if spec.options[FitOptions.LEAST_SQUARES]:
                return self._least_squares_fit_global(spec)
        else:
            if spec.options[FitOptions.LEAST_SQUARES]:
                return self._least_squares_fit_non_global(spec)

    def _least_squares_fit_global(self, spec):
        guesses = spec.get_global_fit_guesses()
        lowers = spec.get_global_fit_lowers()
        uppers = spec.get_global_fit_uppers()

        concatenated_asymmetry = np.array([])
        concatenated_uncertainty = np.array([])
        concatenated_time = np.array([])
        for _, asymmetry in spec.get_data().items():
            concatenated_asymmetry = np.concatenate((concatenated_asymmetry, asymmetry))
            concatenated_uncertainty = np.concatenate((concatenated_uncertainty, asymmetry.uncertainty))
            concatenated_time = np.concatenate((concatenated_time, asymmetry.time))

        global_lambda_expression = FitEngine._lambdify_global(spec, concatenated_time)
        residual = FitEngine._residual(global_lambda_expression)

        dataset = FitDataset()

        opt = least_squares(residual, guesses, bounds=[lowers, uppers], args=(concatenated_time, concatenated_asymmetry, concatenated_uncertainty))

        values = {}
        for i, symbol in enumerate(spec.get_global_fit_symbols()):
            values[symbol] = opt.x[i]

        for run_id, _ in spec.get_data().items():
            new_fit = Fit()
            final_variables = {k: FitVar(v.symbol, v.name, v.value,
                                         v.is_fixed, v.lower, v.upper,
                                         v.is_global, v.independent) for k, v in spec.variables.items()}

            for symbol, var in final_variables.items():
                if not var.is_global:
                    final_variables[symbol].value = values[symbol + _shortened_run_id(run_id)]
                else:
                    final_variables[symbol].value = values[symbol]

            new_fit.variables = final_variables
            new_fit.expression_as_lambda = lambdify(spec.function, list(final_variables.keys()), INDEPENDENT_VARIABLE)
            new_fit.expression_as_string = spec.function
            new_fit.run_id = run_id
            new_fit.title = self.__run_service.get_runs_by_ids([run_id])[0].meta['Title']
            dataset.fits[run_id] = new_fit

        dataset.options = spec.options.copy()
        dataset.function = spec.function

        return dataset

    def _least_squares_fit_non_global(self, spec) -> FitDataset:
        if spec.options[FitOptions.ALPHA_CORRECT]:
            alpha_corrected_function = ALPHA_CORRECTION.format(spec.function, spec.function)
            function = FitEngine._replace_fixed(alpha_corrected_function, spec.get_fixed_symbols(), spec.get_fixed_guesses())
        else:
            function = FitEngine._replace_fixed(spec.function, spec.get_fixed_symbols(), spec.get_fixed_guesses())

        lambda_expression = lambdify(function, spec.get_unfixed_symbols(), INDEPENDENT_VARIABLE)
        residual = FitEngine._residual(lambda_expression)

        guesses = spec.get_unfixed_guesses()
        lowers = spec.get_unfixed_lower_bounds()
        uppers = spec.get_unfixed_upper_bounds()

        dataset = FitDataset()
        for run_id, asymmetry in spec.get_data().items():
            new_fit = Fit()
            final_variables = {k: FitVar(v.symbol, v.name, v.value, v.is_fixed, v.lower, v.upper, v.is_global, v.independent) for k, v in spec.variables.items()}

            if len(spec.get_unfixed_symbols()) != 0:
                opt = least_squares(residual, guesses, bounds=[lowers, uppers],
                                    args=(asymmetry.time, asymmetry, asymmetry.uncertainty))
                for i, symbol in enumerate(spec.get_unfixed_symbols()):
                    final_variables[symbol].value = opt.x[i]

            lambda_expression_without_alpha = lambdify(FitEngine._replace_fixed(spec.function, spec.get_fixed_symbols(), spec.get_fixed_guesses()),
                                                       list(spec.get_unfixed_symbols()), INDEPENDENT_VARIABLE)

            new_fit.variables = final_variables
            new_fit.expression_as_lambda = lambda_expression_without_alpha
            new_fit.expression_as_string = spec.function
            new_fit.run_id = run_id
            new_fit.title = self.__run_service.get_runs_by_ids([run_id])[0].meta['Title']
            dataset.fits[run_id] = new_fit

        dataset.options = spec.options.copy()
        dataset.function = spec.function

        return dataset

    @staticmethod
    def _lambdify_global(spec: FitSpec, concatenated_time):
        if spec.options[FitOptions.ALPHA_CORRECT]:
            alpha_corrected_function = ALPHA_CORRECTION.format(spec.function, spec.function)
            function = FitEngine._replace_fixed(alpha_corrected_function, spec.get_fixed_symbols(), spec.get_fixed_guesses())
        else:
            function = FitEngine._replace_fixed(spec.function, spec.get_fixed_symbols(), spec.get_fixed_guesses())

        print('Initial Function : ', function)
        lambdas = OrderedDict()
        run_id_order = []
        for i, (run_id, asymmetry) in enumerate(spec.get_data().items()):
            new_function = function
            for var in spec.get_non_global_symbols():
                new_function = FitEngine._replace_var_with(new_function, var, var + _shortened_run_id(run_id))

            print('For run (' + run_id + ') we have function : ', new_function)
            new_lambda_expression = lambdify(new_function, spec.get_global_fit_symbols(), INDEPENDENT_VARIABLE)
            lambdas[run_id] = new_lambda_expression
            run_id_order.append(run_id)

            print('\tThis function will apply until time : ', concatenated_time[((i + 1) * spec.get_data_length()) - 1])

        def _lambda_expression(arr, *pars, **kwargs):
            values = []
            length = len(arr)
            section_length = length / len(lambdas)
            for i_x, x in enumerate(arr):
                n = i_x // section_length
                values.append(lambdas[run_id_order[int(n)]](x, *pars, **kwargs))
            return values

        return _lambda_expression

    @staticmethod
    def _residual(lambda_expression):
        def residual(pars, x, y_data, dy_data):
            y_calc = lambda_expression(x, *pars)
            return (y_data - y_calc) / dy_data
        return residual

    @staticmethod
    # fixme bug when smaller variable names (like 'd') occur in other variables.
    def _replace_fixed(function, symbols, values):
        for symbol, value in zip(symbols, values):
            function = function.replace(symbol, str(value))
        return function

    @staticmethod
    # fixme bug when smaller variable names (like 'd') occur in other variables.
    def _replace_var_with(function, old_symbol, new_symbol):
        return function.replace(old_symbol, new_symbol)


def get_std_unc(result, data, error=None, num_constraints=0):
    """Return the standard uncertainty of refined parameters.
    This method is based on the scipy.optimize.least_squares routine.

    Args:
        result: Output from scipy.optimize.least_squares routine
        data (numpy array): The data against which the fit is performed
        error (numpy array): Experimental uncertainties on the data points
            (set to unity if not provided)
        num_constraints (int): Number of constraints used in the model
    Returns:
        p_unc (numpy array): standard uncertainties of the refined parameters.
        chisq (float): Value of chi^2 for the fit.
    """
    if error is None:
        error = np.ones_like(data)
    weights = 1.0 / error ** 2
    rw = np.sqrt((result.fun ** 2).sum() / (data ** 2 * weights).sum())
    num_params = len(result.x)
    r_exp = np.sqrt((data.shape[0] - num_params + num_constraints) / (data ** 2 * weights).sum())
    j = result.jac
    jac = np.dot(j.transpose(), j)
    cov = np.linalg.inv(jac) * rw ** 2 / r_exp ** 2
    p_unc = np.sqrt(cov.diagonal())
    chisq = rw ** 2 / r_exp ** 2
    return p_unc, chisq


def parse(s):
    """ Takes in an expression as a string and returns a set of the free variables. """

    # Add to these sets any keywords you want to be recognized as not variables.
    # Keep keywords lowercase, user input will be cast to lowercase for comparison.
    operator_set = ('+', '-', '/', '*', '(', ')', '[', ']', '{', '}', '^', '!')
    key_1_char_set = ('e', 'i', PI)
    key_2_char_set = ('pi')
    key_3_char_set = ('sin', 'cos', 'tan', 'exp')
    key_4_char_set = ('sinh', 'cosh', 'tanh')

    free_set = set()
    free_variable = []
    skip_chars = 0

    for i, character in enumerate(s):
        if skip_chars > 0:
            skip_chars -= 1
            continue

        if character.isspace() or character in operator_set:
            free_variable_joined = "".join(free_variable)
            free_set.add(free_variable_joined)
            free_variable = []

        elif character.isalpha():
            if s[i:i + 4].lower() in key_4_char_set:
                skip_chars = 3
                continue
            elif s[i:i + 3].lower() in key_3_char_set:
                skip_chars = 2
                continue
            elif s[i:i + 2].lower() in key_2_char_set:
                skip_chars = 1
                continue
            elif len(free_variable) == 0 and (s[i] in key_1_char_set or s[i].lower() in key_1_char_set) and \
                    (i == len(s) - 1 or s[i + 1] in operator_set or s[i + 1].isspace()):
                continue
            else:
                free_variable.append(character)

        elif character.isdigit():
            if free_variable:
                free_variable.append(character)

    free_variable_joined = "".join(free_variable)
    free_set.add(free_variable_joined)
    free_set.remove('')

    return free_set


def is_valid_expression(expression):
    if "=" not in expression:
        return False

    independent_variable = ""
    open_paren = False
    for i, c in enumerate(expression):
        if open_paren:
            if c == "=":
                return False
            elif c == ")":
                if len(independent_variable) == 0:
                    return False
                for j, k in enumerate(expression):
                    if k == "=":
                        try:
                            sp.sympify(expression[j+1:])
                            return True
                        except Exception:
                            return False
            else:
                independent_variable += c

        if c == "(":
            open_paren = True
    else:
        return False


def split_expression(expression):
    independent_variable = ""
    open_paren = False
    for i, c in enumerate(expression):
        if open_paren:
            if c == "=":
                return None
            elif c == ")":
                if len(independent_variable) == 0:
                    return None
                for j, k in enumerate(expression):
                    if k == "=":
                        try:
                            sp.sympify(expression[j + 1:])
                            return independent_variable, expression[j + 1:]
                        except Exception:
                            return None
            else:
                independent_variable += c
        if c == "(":
            open_paren = True
    else:
        return None


def replace_symbols(expression):
    expression_string = ""

    for c in expression:
        if c == PI:
            expression_string += "pi"
        elif c == '^':
            expression_string += "**"
        elif c == NAUGHT:
            expression_string += "0"
        else:
            expression_string += c

    return expression_string


def lambdify(expression, variables, independent_variable):
    expression_string = replace_symbols(expression)

    if independent_variable in variables:
        variables.pop(independent_variable)

    var_names = [independent_variable]
    var_names.extend([replace_symbols(var) for var in variables])

    lambda_expression = sp.lambdify(var_names, sp.sympify(expression_string), "numpy")

    return lambda_expression


def _shortened_run_id(run_id):
    return run_id.split('-')[0]


# tspec = FitSpec()
# tfunction = 't + az - bz - dz + cz'
# tvara = FitVar('az', 'a', 1, False, 0, 4, True, False)
# tvarb = FitVar('bz', 'b', 1, False, 0, 4, False, False)
# tvarc = FitVar('cz', 'c', 1, True, 0, 4, True, False)
# tvard = FitVar('dz', 'd', 1, False, 0, 4, False, False)
# tdata1 = [1, 2, 3, 4, 5]
# tdata2 = [2, 3, 4, 5, 6]
# tdataid1 = 'data1'
# tdataid2 = 'data2'
# tspec.function = tfunction
# tspec.variables = {'az': tvara, 'bz': tvarb, 'cz': tvarc, 'dz': tvard}
# tspec.asymmetries = {tdataid1: tdata1, tdataid2: tdata2}
# # tspec.options[FitOptions.ALPHA_CORRECT] = True
# ttime = [3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
#
# # print(tspec.get_data())
# # for i, j in enumerate(tspec.get_data().items()):
# #     print(i, j)
#
# print(tspec.get_global_fit_symbols())
# texpr = FitEngine._lambdify_global(tspec, ttime)
# print(texpr(4, az=2, bzdata1=3, bzdata2=4, dzdata1=5, dzdata2=6), texpr(11, az=2, bzdata1=3, bzdata2=4, dzdata1=5, dzdata2=6))


# test_expression = 't + c - b'
# test_variables = {'c', 'b', 'd'}
# test_independent = 't'
# test_lambda = lambdify(test_expression, test_variables, test_independent)
# print(test_lambda(1, d=3, b=7, c=11))
# # print(np.array([4.2, 3, 2, 1]).dtype)
# # print(test_lambda(np.array([4.2,3,2,1]), **{'c': 4, 'b': 1}))
#
# fit = Fit()
# fit.variables = {'c': FitVar('c', 'c', 0, 1, -3, 3, True, False), 'b': FitVar('b', 'b', 1, 1, -3, 3, True, False)}
# fit.expression_as_lambda = test_lambda
# time = np.array([1,2,3,4])
# asy = fit(time)
# print(asy)

# f(x, t)