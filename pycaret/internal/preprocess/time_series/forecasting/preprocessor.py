from typing import Union, Optional, List

from sklearn.preprocessing import (
    StandardScaler,
    MinMaxScaler,
    MaxAbsScaler,
    RobustScaler,
)

from sktime.transformations.series.compose import ColumnwiseTransformer
from sktime.transformations.series.adapt import TabularToSeriesAdaptor
from sktime.transformations.series.impute import Imputer
from sktime.transformations.series.boxcox import BoxCoxTransformer, LogTransformer
from sktime.transformations.series.exponent import ExponentTransformer, SqrtTransformer
from sktime.transformations.series.cos import CosineTransformer
from sktime.transformations.series.scaledlogit import ScaledLogitTransformer
from sktime.base import BaseEstimator

from pycaret.utils.time_series import TSApproachTypes, TSExogenousPresent


class TSForecastingPreprocessor:
    """Class for preprocessing Time Series Forecasting Experiments."""

    def __init__(self):
        # Initialize empty steps ----
        self.pipe_steps_target = []
        self.pipe_steps_exogenous = []

        # Pipeline which is trained only on the training split
        self.pipeline = None

        # Pipeline which is trained only on the complete data
        # Used when model has been finalized
        self.pipeline_fully_trained = None

    def _imputation(
        self,
        numeric_imputation_target: Optional[Union[str, int, float]],
        numeric_imputation_exogenous: Optional[Union[str, int, float]],
        exogenous_present: bool,
    ):
        #### Impute target ----
        if numeric_imputation_target is not None:
            self._add_imputation_steps(
                numeric_imputation=numeric_imputation_target, target=True
            )

        #### Impute Exogenous ----
        # Only add exogenous pipeline steps if exogenous variables are present.
        if (
            exogenous_present == TSExogenousPresent.YES
            and numeric_imputation_exogenous is not None
        ):
            self._add_imputation_steps(
                numeric_imputation=numeric_imputation_exogenous, target=False
            )

    def _add_imputation_steps(
        self, numeric_imputation: Union[str, int, float], target: bool = True
    ):
        """Perform numeric imputation of missing values.

        Parameters
        ----------
        numeric_imputation : Union[str, int, float]
            The method to be used for imputation.
            If str, then passed as is to the underlying `sktime` imputer.
            Allowed values are:
                "drift", "linear", "nearest", "mean", "median", "backfill",
                "bfill", "pad", "ffill", "random"
            If int or float, imputation method is set to "constant" with the given value.
        target : bool, optional
            If True, imputation is added to the target variable steps
            If False, imputation is added to the exogenous variable steps,
            by default True

        Raises
        ------
        ValueError
            (1) `numeric_imputation` is of type str but not of one of the allowed values.
            (2) `numeric_imputation` is not of one of the allowed types.
        """
        type_ = "Target" if target else "Exogenous"
        self.logger.info(f"Set up imputation for {type_} variable(s).")

        if isinstance(numeric_imputation, str):
            allowed_values = [
                "drift",
                "linear",
                "nearest",
                "mean",
                "median",
                "backfill",
                "bfill",
                "pad",
                "ffill",
                "random",
            ]
            if numeric_imputation not in allowed_values:
                raise ValueError(
                    f"{type_} Imputation Type '{numeric_imputation}' not allowed."
                )
            num_estimator = Imputer(method=numeric_imputation, random_state=self.seed)
        elif isinstance(numeric_imputation, (int, float)):
            num_estimator = Imputer(method="constant", value=numeric_imputation)
        else:
            raise ValueError(
                f"{type_} Imputation Type '{type(numeric_imputation)}' is not of allowed type."
            )

        if target:
            self.pipe_steps_target.extend([("numerical_imputer", num_estimator)])
        else:
            self.pipe_steps_exogenous.extend([("numerical_imputer", num_estimator)])

    def _limitation(self,
                    limit_target: Optional[List[Union[int,float,None]]],
                    limit_exogenous: Optional[List[Union[int,float,None]]],
                    exogenous_present: bool
                    ):

     #### Limit target ----
        if limit_target is not None:
            self._add_limitation_steps(
                limits=limit_target)

    #### Limit exogenous ----
        # TODO: Not yet implemented
        # Will raise an error
        # Only add exogenous pipeline steps if exogenous variables are present.
        if (
            exogenous_present == TSExogenousPresent.YES
            and limit_exogenous is not None
        ):
            # self._add_limitation_steps(
            #     limits=limit_exogenous, target=False
            self.logger.warning("Applying limits to exogenous variables is not yet implemented.")
            

    def _add_limitation_steps(self,
                              limits: List[Union[int,float,None]],
                              target: bool = True):
        """Limit/scale Possible forecast values using sktime's ScaledLogitTransformer

        Example:
        --------
        >>> limits = None # default - no limits
        >>> limits = [0, 10000000] # lower and upper limit
        >>> limits = [0, None]  # lower limit only
        >>> limits = [None, 10000000] # upper limit only

        Parameters
        ----------
        limits : List[Union[int,float,None]]
            A list (of two values) of the minimum and maximum values
            
        target : bool, optional
            If True, limit is added to the target variable steps
            If False, limit is added to the exogenous variable steps,
            (not implemented yet)
            by default True

        Raises
        ------
        TypeError
            (1)  value in `limits` is not None or float or int.
            (2) `limits` is not a list.
        ValueError
            (1) `limits` is a list of length not equal to 2.
        NotImplementedError
            (1) `limits` is a subclass of BaseEstimator.
            (2) `target` is False, as exogenous limiting is not implemented yet.
        """

        type_ = "Target" if target else "Exogenous"
        self.logger.info(f"Setting up limits for {type_} variable(s).")
        if isinstance(limits, list):
            if len(limits) == 2:
                # Valid limits length
                for i in limits:
                    if not (isinstance(i, (int, float)) or i is None):
                        raise TypeError(
                            f"{type_} limit value {i}, '{type(i)}' is not of allowed type.")
                if all([i is None for i in limits]):
                    # No limits as both is none, but exit silently
                    return
                # create limiter
                limiter = ScaledLogitTransformer(*limits)

            else:
                raise ValueError(f"{type_} limits list must be of length 2.")

        elif issubclass(limits, BaseEstimator):
            # TODO: Implement passing sktime compatible transformer directly.
            raise NotImplementedError(
                "Using transformers directly is not yet implemented,\
                    please use numeric limits only for now.")
        else:
            raise TypeError(
                f"{type_} forecast limit Type '{type(limits)}' is not of allowed type."
            )

        if target:
            print("creating pipeline limit step")
            self.pipe_steps_target.extend([("target_limiter", limiter)])
        else:
            raise NotImplementedError(
                "Limiting exogenous variables is not yet implemented."
            )

    def _transformation(
        self,
        transform_target: Optional[Union[str, int, float]],
        transform_exogenous: Optional[Union[str, int, float]],
        exogenous_present: bool,
    ):
        #### Impute target ----
        if transform_target is not None:
            self._add_transformation_steps(transform=transform_target, target=True)

        #### Impute Exogenous ----
        # Only add exogenous pipeline steps if exogenous variables are present.
        if (
            exogenous_present == TSExogenousPresent.YES
            and transform_exogenous is not None
        ):
            self._add_transformation_steps(transform=transform_exogenous, target=False)

    def _add_transformation_steps(self, transform: str, target: bool = True):
        """Power transform the data to be more Gaussian-like.

        Parameters
        ----------
        transform : str
            The method to be used for transformation. Allowed values and
            corresponding transformers are:
                "box-cox": BoxCoxTransformer(),
                "log": LogTransformer(),
                "sqrt": SqrtTransformer(),
                "exp": ExponentTransformer(),
                "cos": CosineTransformer(),
        target : bool, optional
            If True, transformation is added to the target variable steps
            If False, transformation is added to the exogenous variable steps,
            by default True

        Raises
        ------
        ValueError
            (1) `transform` is not of one of the allowed values.
            (2) `transform` is not of one of the allowed types.
        """
        type_ = "Target" if target else "Exogenous"
        self.logger.info(f"Set up transformation for {type_} variable(s).")

        if isinstance(transform, str):
            transform_dict = {
                "box-cox": BoxCoxTransformer(),
                "log": LogTransformer(),
                "sqrt": SqrtTransformer(),
                "exp": ExponentTransformer(),
                "cos": CosineTransformer(),
            }

            if transform not in transform_dict:
                raise ValueError(
                    f"{type_} transformaton method '{transform}' not allowed."
                )

        else:
            raise ValueError(
                f"{type_} transformaton method '{type(transform)}' is not of allowed type."
            )

        if target:
            transformer = transform_dict[transform]
            self.pipe_steps_target.extend([("transformer", transformer)])
        else:
            transformer = ColumnwiseTransformer(transform_dict[transform])
            self.pipe_steps_exogenous.extend([("transformer", transformer)])

    def _scaling(
        self,
        scale_target: Optional[Union[str, int, float]],
        scale_exogenous: Optional[Union[str, int, float]],
        exogenous_present: bool,
    ):
        #### Scale target ----
        if scale_target:
            self._add_scaling_steps(scale=scale_target, target=True)

        #### Scale Exogenous ----
        # Only add exogenous pipeline steps if exogenous variables are present.
        if exogenous_present == TSExogenousPresent.YES and scale_exogenous is not None:
            self._add_scaling_steps(scale=scale_exogenous, target=False)

    def _add_scaling_steps(self, scale: str, target: bool = True):
        """Scale the data.

        Parameters
        ----------
        scale : str
            The method to be used for scaling. Allowed values and corresponding scalers are:
                "zscore": StandardScaler(),
                "minmax": MinMaxScaler(),
                "maxabs": MaxAbsScaler(),
                "robust": RobustScaler(),
        target : bool, optional
            If True, scaling is added to the target variable steps
            If False, scaling is added to the exogenous variable steps,
            by default True

        Raises
        ------
        ValueError
            (1) `scale` is not of one of the allowed values.
            (2) `scale` is not of one of the allowed types.
        """
        type_ = "Target" if target else "Exogenous"
        self.logger.info(f"Set up scaling for {type_} variable(s).")

        if isinstance(scale, str):
            scale_dict = {
                "zscore": StandardScaler(),
                "minmax": MinMaxScaler(),
                "maxabs": MaxAbsScaler(),
                "robust": RobustScaler(),
            }

            if scale not in scale_dict:
                raise ValueError(f"{type_} scale method '{scale}' not allowed.")

            scaler = TabularToSeriesAdaptor(scale_dict[scale])

        else:
            raise ValueError(
                f"{type_} transformaton method '{type(scale)}' is not of allowed type."
            )

        if target:
            self.pipe_steps_target.extend([("scaler", scaler)])
        else:
            self.pipe_steps_exogenous.extend([("scaler", scaler)])

    # def _feature_selection(
    #     self,
    #     feature_selection_method,
    #     feature_selection_estimator,
    #     n_features_to_select,
    # ):
    #     """Select relevant features."""
    #     self.logger.info("Set up feature selection.")
    #     # TODO: Maybe implement https://github.com/pycaret/pycaret/issues/2230
    #     # self.pipeline.steps.append(("feature_selection", feature_selector))

    # def _add_custom_pipeline(self, custom_pipeline):
    #     """Add custom transformers to the pipeline."""
    #     self.logger.info("Set up custom pipeline.")
    #     for name, estimator in normalize_custom_transformers(custom_pipeline):
    #         self.pipeline.steps.append((name, TransfomerWrapper(estimator)))
