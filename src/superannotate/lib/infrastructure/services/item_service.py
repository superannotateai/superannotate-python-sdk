import base64
import copy
from typing import Optional

from lib.core.entities import BaseItemEntity
from lib.core.jsx_conditions import EmptyQuery
from lib.core.jsx_conditions import Filter
from lib.core.jsx_conditions import Join
from lib.core.jsx_conditions import OperatorEnum
from lib.core.jsx_conditions import Query
from lib.core.service_types import BaseItemResponse
from lib.core.serviceproviders import SuperannotateServiceProvider
from superannotate import AppException


class ItemService(SuperannotateServiceProvider):
    MAX_URI_LENGTH = 15_000
    URL_LIST = "items"
    URL_GET = "items/{item_id}"

    def get(self, project_id: int, item_id: int):
        result = self.client.request(
            url=self.URL_GET.format(item_id=item_id),
            method="GET",
            content_type=BaseItemResponse,
            headers={
                "x-sa-entity-context": base64.b64encode(
                    f'{{"team_id":{self.client.team_id},'
                    f'"project_id":{project_id}}}'.encode("utf-8")
                ).decode()
            },
        )
        return result

    def old_list(self, project_id: int, folder_id: Optional[int], query: Query):
        query &= Join("metadata", ["path"])
        entity_context = [
            f'"team_id":{self.client.team_id}',
            f'"project_id":{project_id}',
        ]
        if folder_id:
            entity_context.append(f'"folder_id":{folder_id}')
        result = self.client.paginate(
            f"{self.URL_LIST}?{query.build_query()}",
            item_type=BaseItemEntity,
            headers={
                "x-sa-entity-context": base64.b64encode(
                    f"{{{','.join(entity_context)}}}".encode("utf-8")
                ).decode()
            },
        )
        return result

    def list(self, project_id: int, folder_id: Optional[int], query: Query):
        query &= Join("metadata", ["path"])
        entity_context = [
            f'"team_id":{self.client.team_id}',
            f'"project_id":{project_id}',
        ]
        if folder_id:
            entity_context.append(f'"folder_id":{folder_id}')

        base_uri = f"{self.URL_LIST}?"
        query_string = query.build_query()
        if len(base_uri) + len(query_string) > self.MAX_URI_LENGTH:
            in_filters, base_filters = [], []
            for condition in query.condition_set:
                if (
                    isinstance(condition, Filter)
                    and condition.operator == OperatorEnum.IN
                ):
                    in_filters.append(condition)
                else:
                    base_filters.append(condition)
            base_filter = EmptyQuery()
            for i in base_filters:
                base_filter &= i
            if not in_filters:
                raise ValueError(
                    "The URI exceeds the maximum allowed length and cannot be divided without an 'IN' filter."
                )
            length_in_filter_map = {}
            for i in in_filters:
                length_in_filter_map[len(i.build_query())] = i
            available_slots = self.MAX_URI_LENGTH - len(base_uri)
            cumulative_length = 0
            long_filters = []
            while length_in_filter_map:
                key_len, v = length_in_filter_map.popitem()
                if cumulative_length + key_len < available_slots:
                    cumulative_length += key_len
                    base_filter &= length_in_filter_map[key_len]
                else:
                    long_filters.append(v)
            if len(long_filters) > 1:
                raise AppException("The filter is too complicated.")
            long_filter = long_filters[0]
            available_slots = available_slots - cumulative_length
            values = list(long_filter.value)
            results = []
            chunks = []
            current_chunk = []
            char_counter = 0
            while values:
                val = values.pop()
                _len = len(str(val)) + 1  # computing ,
                if char_counter + _len < available_slots:
                    current_chunk.append(val)
                    char_counter += _len
                else:
                    chunks.append(current_chunk)
                    current_chunk = [val]
                    char_counter = _len
            if current_chunk:
                chunks.append(current_chunk)
            for chunk in chunks:
                chunk_filter = Filter(long_filter.key, chunk, OperatorEnum.IN)
                chunk_query = copy.deepcopy(base_filter) & chunk_filter
                uri = f"{base_uri}?{chunk_query.build_query()}"
                response = self.client.paginate(
                    uri,
                    item_type=BaseItemEntity,
                    headers={
                        "x-sa-entity-context": base64.b64encode(
                            f"{{{','.join(entity_context)}}}".encode("utf-8")
                        ).decode()
                    },
                )
                if not response.ok:
                    raise AppException(response.error)
                results.extend(response.data)
            return results
        response = self.client.paginate(
            f"{base_uri}{query_string}",
            item_type=BaseItemEntity,
            headers={
                "x-sa-entity-context": base64.b64encode(
                    f"{{{','.join(entity_context)}}}".encode("utf-8")
                ).decode()
            },
        )
        if not response.ok:
            raise AppException(response.error)
        return response.data
