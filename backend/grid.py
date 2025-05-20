import logging
from typing import Any, Optional

from grid_api import AsyncGrid

logger = logging.getLogger(__name__)


class GRIDExecutionException(Exception):
    pass


class ProjectXRevenueModel:
    """ " This is a class implementing GRID API calls to a spreadsheet model called "Project X Revenue Model" """

    def __init__(self, grid_client: AsyncGrid):
        self._grid_client = grid_client
        self._workbook_id = "44f4e920-9e5b-45d5-a9a4-4c7d4ff933e2"
        # These parameter references could be potentially built from the GRID API labels/parameters endpoints
        # when they become available in the public API, although I suspect some codegen would be required in
        # order to generate python-compliant variable names for them, and to use them nicely in methods like the
        # ones on this class.
        self._parameter_references = {
            "ad_budget": "B4",
            "ad_cpc": "B5",
            "registration_conversion_rate": "B8",
            "subscription_conversion_rate": "B9",
            "registration_conversion_lag_in_months": "B12",
            "subscription_conversion_lag_in_months": "B13",
            "churn_rate": "B16",
            "customer_lifetime_length_in_months": "B17",
            "virality_per_registered_user": "B20",
            "virality_per_subscribed_user": "B21",
            "subscription_price": "B23",
        }

        self._data_ranges = {
            # "Registrations": "Sheet1!C31:AL31",
            # "Registered users": "Sheet1!C36:AL36",
            "Subscribers": "Sheet1!C37:AL37",
            "ARR (month 36)": "Sheet1!C43",
            "Monthly Recurring Revenue": "Sheet1!C39:AL39",
            "Revenue from Existing subscribers": "Sheet1!C40:AL40",
            "Revenue from New subscribers": "Sheet1!C41:AL41",
            # "New subscriptions": "Sheet1!C32:AL32",
            # "Visitors": "Sheet1!C28:AL28",
            # "Churned users": "Sheet1!C34:AL34",
            # "Organic": "Sheet1!C29:AL29",
            # "Paid": "Sheet1!C30:AL30",
        }
        self._cell_ref_labels = {
            value: key for key, value in list(self._data_ranges.items()) + list(self._parameter_references.items())
        }

    async def get_model_defaults(self) -> dict[str, str | int | float | bool | None]:
        """Get the default values for all the model parameters used in 'forecast_revenue'"""
        reads = list(self._parameter_references.values())
        results = await self._grid_client.workbooks.calc(id=self._workbook_id, read=reads)
        logger.debug("results=", results)
        response = {}
        for cell, result in results.items():
            if isinstance(result, list):
                logger.warning(f"Got range response for model default for {cell}, expected single value")
                continue
            response[self._cell_ref_labels[cell]] = result.value
        logger.debug(f"get_model_defaults response={response}")
        return response

    async def forecast_revenue(
        self,
        ad_budget: Optional[float] = None,
        ad_cpc: Optional[float] = None,
        registration_conversion_rate: Optional[float] = None,
        subscription_conversion_rate: Optional[float] = None,
        registration_conversion_lag_in_months: Optional[float] = None,
        subscription_conversion_lag_in_months: Optional[float] = None,
        churn_rate: Optional[float] = None,
        customer_lifetime_length_in_months: Optional[float] = None,
        virality_per_registered_user: Optional[float] = None,
        virality_per_subscribed_user: Optional[float] = None,
        subscription_price: Optional[float] = None,
    ) -> dict[str, list[Any]]:
        f"""
        Calculate the revenue for a business model with the given parameters.  Returns a timeseries of values
        for each of the following:
        - Monthly Recurring Revenue
        - Revenue from Existing subscribers
        - Revenue from New subscribers

        Accepts the following model parameters, none are required -- the business model has built-in defaults,
        so supply a null value for any of the parameters you don't have yet for the user.
        {list(self._parameter_references.keys())}
        """
        reads = [
            # self._data_ranges["ARR (month 36)"],  # create a range for ARR so we can answer ARR for any month
            self._data_ranges["Monthly Recurring Revenue"],
            self._data_ranges["Revenue from Existing subscribers"],
            self._data_ranges["Revenue from New subscribers"],
        ]

        parameters: dict[str, str | int | float | bool | None] = {
            "ad_budget": ad_budget,
            "ad_cpc": ad_cpc,
            "registration_conversion_rate": registration_conversion_rate,
            "subscription_conversion_rate": subscription_conversion_rate,
            "registration_conversion_lag_in_months": registration_conversion_lag_in_months,
            "subscription_conversion_lag_in_months": subscription_conversion_lag_in_months,
            "churn_rate": churn_rate,
            "customer_lifetime_length_in_months": customer_lifetime_length_in_months,
            "virality_per_registered_user": virality_per_registered_user,
            "virality_per_subscribed_user": virality_per_subscribed_user,
            "subscription_price": subscription_price,
        }

        results = await self._grid_client.workbooks.calc(
            id=self._workbook_id,
            read=reads,
            apply={
                self._parameter_references[key]: value
                for key, value in parameters.items()
                if value is not None and key in self._parameter_references
            },
        )
        response = {}
        for source, result in results.items():
            source_label = self._cell_ref_labels.get(source, source)
            logger.debug(f"read_result={result}")
            if isinstance(result, list):
                response[source_label] = [r.value for r in result]
            else:
                response[source_label] = [result.value]

        return response
