
"""Hubspot source helpers"""

from typing import Union

import urllib.parse
from typing import Any, Dict, Iterator, List, Optional

from dlt.common.schema.typing import TColumnSchema
from dlt.sources.helpers import requests

from .settings import OBJECT_TYPE_PLURAL, HS_TO_DLT_TYPE

BASE_URL = "https://api.hubapi.com/"


def get_url(endpoint: str) -> str:
    """Get absolute hubspot endpoint URL"""
    return urllib.parse.urljoin(BASE_URL, endpoint)


def _get_headers(api_key: str) -> Dict[str, str]:
    """Return headers for HubSpot API requests."""
    return dict(authorization=f"Bearer {api_key}")


def _check_response(response, url: str) -> None:
    """Print detailed HubSpot error information before raising HTTP errors."""
    if response.status_code >= 400:
        print("\n" + "=" * 60)
        print("HUBSPOT API ERROR")
        print("URL:", url)
        print("STATUS CODE:", response.status_code)
        print("ERROR DETAILS:", response.text)
        print("=" * 60 + "\n")

    response.raise_for_status()


def pagination(
    _data: Dict[str, Any], headers: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    _next = _data.get("paging", {}).get("next", None)

    if _next:
        next_url = _next["link"]
        r = requests.get(next_url, headers=headers)
        _check_response(r, next_url)
        return r.json()

    return None


def extract_association_data(
    _obj: Dict[str, Any],
    data: Dict[str, Any],
    association: str,
    headers: Dict[str, Any],
) -> List[Dict[str, Any]]:
    values = []

    while data is not None:
        for r in data["results"]:
            values.append(
                {
                    "value": _obj["hs_object_id"],
                    f"{association}_id": r["id"],
                }
            )

        data = pagination(data, headers)

    return values


def extract_property_history(
    objects: List[Dict[str, Any]]
) -> Iterator[Dict[str, Any]]:
    for item in objects:
        history = item.get("propertiesWithHistory")

        if not history:
            return

        for key, changes in history.items():
            if not changes:
                continue

            for entry in changes:
                yield {
                    "object_id": item["id"],
                    "property_name": key,
                    **entry,
                }


def fetch_property_history(
    endpoint: str,
    api_key: str,
    props: str,
    params: Optional[Dict[str, Any]] = None,
) -> Iterator[List[Dict[str, Any]]]:

    url = get_url(endpoint)
    headers = _get_headers(api_key)

    params = dict(params or {})
    params["propertiesWithHistory"] = props
    params["limit"] = 50

    r = requests.get(url, headers=headers, params=params)
    _check_response(r, url)

    _data = r.json()

    while _data is not None:
        if "results" in _data:
            yield list(extract_property_history(_data["results"]))

        _next = _data.get("paging", {}).get("next", None)

        if _next:
            next_url = _next["link"]
            r = requests.get(next_url, headers=headers)
            _check_response(r, next_url)
            _data = r.json()
        else:
            _data = None


def fetch_data(
    endpoint: str,
    api_key: str,
    params: Optional[Dict[str, Any]] = None,
    context: Optional[Dict[str, Any]] = None,
) -> Iterator[List[Dict[str, Any]]]:

    url = get_url(endpoint)
    headers = _get_headers(api_key)

    r = requests.get(url, headers=headers, params=params)

    # Print detailed error information for HubSpot API failures
    _check_response(r, url)

    _data = r.json()

    while _data is not None:

        if "results" in _data:
            _objects: List[Dict[str, Any]] = []

            for _result in _data["results"]:

                _obj = _result.get("properties", _result)

                if "id" not in _obj and "id" in _result:
                    _obj["id"] = _result["id"]

                if "associations" in _result:

                    for association in _result["associations"]:
                        __data = _result["associations"][association]

                        __values = extract_association_data(
                            _obj,
                            __data,
                            association,
                            headers,
                        )

                        __values = [
                            dict(t)
                            for t in {
                                tuple(d.items())
                                for d in __values
                            }
                        ]

                        _obj[association] = __values

                if context:
                    _obj.update(context)

                _objects.append(_obj)

            yield _objects

        _data = pagination(_data, headers)


def _get_property_names_types(
    api_key: str,
    object_type: str,
) -> Dict[str, Union[str, None]]:

    props_to_type: Dict[str, str] = {}

    endpoint = f"/crm/v3/properties/{OBJECT_TYPE_PLURAL[object_type]}"

    for page in fetch_data(endpoint, api_key):
        for prop in page:
            props_to_type[prop["name"]] = prop.get("type", None)

    return props_to_type


def get_properties_labels(
    api_key: str,
    object_type: str,
    property_name: str,
) -> Iterator[Dict[str, Any]]:

    endpoint = f"/crm/v3/properties/{object_type}/{property_name}"

    url = get_url(endpoint)
    headers = _get_headers(api_key)

    r = requests.get(url, headers=headers)
    _check_response(r, url)

    _data: Optional[Dict[str, Any]] = r.json()

    while _data is not None:
        yield _data
        _data = pagination(_data, headers)


def _to_dlt_columns_schema(
    col: Dict[str, str]
) -> TColumnSchema:

    col_name, col_type = next(iter(col.items()))

    return (
        {
            "name": col_name,
            "data_type": HS_TO_DLT_TYPE[col_type],
        }
        if col_type in HS_TO_DLT_TYPE
        else {}
    )

