import inspect
import logging
from typing import Callable, Optional

from grid_api import AsyncGrid
from pydantic import create_model

from .config import AppConfig
from .types import ToolBinding


logger = logging.getLogger(__name__)




class GRIDExecutionException(Exception):
    pass


def create_toolbinding(method: Callable, name: Optional[str] = None) -> ToolBinding:
    """
    Create a ToolBinding object for a given method and name.
    If no name is provided, the method's name will be used.
    """
    name = name or method.__name__
    if not name:
        raise ValueError("Can't determine a tool name from the given method, consider providing one")

    signature = inspect.signature(method)
    fields = {
        param_name: (param.annotation, ...)
        for param_name, param in signature.parameters.items()
        if param_name != "self" and param.annotation is not inspect.Parameter.empty
    }

    parameter_schema = {
        "type": "object",
        "properties": {key: {"type": param.annotation.__name__.lower()} for key, (param.annotation, _) in fields.items()},
        "required": list(fields.keys()),
        "additionalProperties": False,
    }

    return {
        "ref": method,
        "schema": {
            "type": "function",
            "name": name,
            "description": (method.__doc__ or "").strip(),
            "parameters": parameter_schema,
        },
    }


class GridAPI:
    def __init__(self, config: AppConfig):
        self._config = config
        self._client = AsyncGrid(api_key=config.GRID_API_KEY)
        self._project_x = ProjectXRevenueModel(self._client)
        self._tools: dict[str, ToolBinding] = {
            "make_calculation": create_toolbinding(self.make_calculation),
            "forecast_revenue": create_toolbinding(self._project_x.forecast_revenue, name="forecast_revenue"),
        }
        import pprint
        pprint.pprint(self._tools)

    def make_calculation(self, A: int, B: int, C: Optional[int] = 10) -> int:
        """
        Perform a calculation using three numbers A, B, and C.
        """
        print(f"Calculating({A=}, {B=}, {C=})")
        return A + B + C

    @property
    def tools(self) -> dict[str, ToolBinding]:
        return self._tools


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
            "ad_budget": "B1",
            "ad_cpc": "B2",
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
            #"Registrations": "Sheet1!C31:AL31",
            #"Registered users": "Sheet1!C36:AL36",
            "Subscribers": "Sheet1!C37:AL37",
            "ARR (month 36)": "Sheet1!C43",
            "Monthly Recurring Revenue": "Sheet1!C39:AL39",
            "Revenue from Existing subscribers": "Sheet1!C40:AL40",
            "Revenue from New subscribers": "Sheet1!C41:AL41",
            #"New subscriptions": "Sheet1!C32:AL32",
            #"Visitors": "Sheet1!C28:AL28",
            #"Churned users": "Sheet1!C34:AL34",
            #"Organic": "Sheet1!C29:AL29",
            #"Paid": "Sheet1!C30:AL30",
        }
        self._cell_ref_labels = {value: key for key, value in list(self._data_ranges.items()) + list(self._parameter_references.items())}

    async def get_model_defaults(self):
        """ Get the default values for all the model parameters used in 'forecast_revenue'
        """
        reads = []

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
    ) -> dict[str, list[str]]:
        f"""
        Calculage the revenue for the a business model with the given parameters.  Returns a timeseries of values
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

        apply = []
        parameters = {
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
        for key, value in parameters.items():
            if key not in self._parameter_references:
                logger.warning(
                    f"Warning, requested a parameter '{key}' which is not found in parameter references"
                )
            else:
                if value is None:
                    continue
                apply.append(
                    {
                        "target": self._parameter_references[key],
                        "value": value,
                    }
                )

        result = await self._grid_client.workbooks.query(id=self._workbook_id, read=reads, apply=apply)
        response = {}
        for read_result in result.read:
            source = read_result.source
            source_label = self._cell_ref_labels.get(source, source)
            print("read_result=", read_result)
            if len(read_result.data) != 1:
                logger.warning("Received incorrect number of rows, only one row (series) for each source expected. "
                               f"Using the first row in response (source: {source})")
            response[source_label] = [cell.w for cell in read_result.data[0]]
        return response

