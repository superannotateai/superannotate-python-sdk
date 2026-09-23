from __future__ import annotations

from functools import partial
from typing import Annotated

from lib.app.interface.base_interface import TrackableMeta
from lib.app.interface.base_interface import Tracker
from lib.app.interface.responses import QueryResult
from lib.app.interface.sdk import BaseNamespace
from lib.app.serializers import BaseSerializer
from lib.core.exceptions import AppException
from pydantic import StringConstraints

NotEmptyStr = Annotated[str, StringConstraints(strict=True, min_length=1)]


class Explore(BaseNamespace, metaclass=TrackableMeta):
    """Namespace for querying and curating project data with the Explore query language.

    Accessed as ``SAClient.explore``. Groups the functions that operate on the Explore
    surface of the platform. Every query in this namespace uses the SuperAnnotate query
    language documented at https://doc.superannotate.com/docs/queries-beta.

    Available methods:

    - ``explore.query()`` - Return items that satisfy a query string. Returns a
      QueryResult, which behaves like a list of dicts and exposes a ``.count()`` method.
    - ``explore.query().count()`` - Returns the total number of items matching the
      query, without fetching item metadata.
    - ``explore.get_subsets()`` - Return the subsets that exist in a project.
    - ``explore.add_items_to_subset()`` - Associate items with a subset, creating the
      subset if it does not exist.
    """

    TRACKING_PREFIX = "explore"

    def query(
        self,
        project: NotEmptyStr | int | tuple[int, int] | tuple[str, str],
        query: NotEmptyStr | None = None,
        subset: NotEmptyStr | None = None,
    ) -> QueryResult:
        """Return items that satisfy the given Explore query.
        Query syntax should be in the SuperAnnotate query language
        (https://doc.superannotate.com/docs/queries-beta).

        The returned QueryResult behaves like a list of dicts, and additionally exposes a .count() method.

        :param project: Accepts a project as a string ("project" or "project/folder") or as a tuple (project_id, folder_id), where the folder is optional.
        :type project: Union[str, int, Tuple[int, int], Tuple[str, str]]

        :param query: Explore query string.
        :type query: str

        :param subset: Subset name. Restricts the query to items in the given subset.
            To return all the items in the specified subset, leave the query as None.
        :type subset: str

        :return: queried items' metadata list
        :rtype: QueryResult (list of dicts with .count() method)

        :raises AppException: If both query and subset are left empty, if the project,
            folder or subset is not found, or with the backend's message if the query is
            rejected (e.g. an invalid query string, or a project that was never resynced).

        Request Example:
        ::

            # To query by status:
            sa_client.explore.query(
                project="Image Project",
                query='_status = "InProgress"'
            )

            # To query within a subset:
            sa_client.explore.query(
                project="Image Project",
                query='_status = "InProgress"',
                subset="golden-set"
            )

        Response Example:
        ::

            [
                {
                    "id": 196560932,
                    "name": "TEST_00001",
                    "folder_id": 867191,
                    "comments": [],
                    "annotation_status": 2,
                    "path": "custom_llm",
                    "approval_status": 0,
                    "createdAt": "2026-08-04T03:50:53.000Z",
                    "updatedAt": "2026-09-02T10:37:18.000Z",
                    "meta": {"integration_id": None},
                    "instances": [],
                    "custom_metadata": {},
                    "subset_ids": [],
                    "category_id": [],
                    "category_name": None,
                    "assignment": [],
                    "last_action": {
                        "date": "2026-09-02T10:37:17.217Z",
                        "email": "test@superannotate.com"
                    },
                    "score": [],
                    "is_pinned": 0,
                    "folder_name": "root",
                    "is_root_folder": 1
                }
            ]

        .. py:method:: query.count() -> int

            Returns the total number of items matching the query, without fetching item metadata.

            :return: total number of matching items
            :rtype: int

            Request Example:
            ::

                total = sa_client.explore.query(
                    project="Image Project", query='_status = "InProgress"'
                ).count()
                print(f"Total matching items: {total}")
        """
        if not any([query, subset]):
            raise AppException("Provide 'query' or 'subset'")
        project_entity, folder = self.controller.get_project_folder(project)
        return QueryResult(
            data_fetcher=lambda: [
                item.model_dump()
                for item in self.controller.explore_query(
                    project_entity, folder, query, subset
                )
            ],
            count_fetcher=partial(
                self._count,
                query=query,
                subset=subset,
                _resolved=(project_entity, folder),
            ),
        )

    def _count(self, query, subset, _resolved) -> int:
        """Backs QueryResult.count() of explore.query().

        query and subset are reported on the "explore.query.count" event; the already
        resolved entities come in _resolved, which telemetry skips.
        """
        project_entity, folder = _resolved
        return self.controller.explore_query_count(
            project_entity, folder, query, subset
        )

    _count = Tracker(_count, event_name="query.count")

    def get_subsets(self, project: NotEmptyStr | int):
        """Returns the subsets that exist in the given project.

        :param project: The name or ID of the project.
        :type project: Union[str, int]

        :return: subsets' metadata
        :rtype: list of dicts

        Request Example:
        ::

            subsets = sa_client.explore.get_subsets(project="Image Project")

        Response Example:
        ::

            [{'name': 'test_subset'}]
        """
        project = self.controller.get_project(project)
        response = self.controller.subsets.list(project)
        if response.errors:
            raise AppException(response.errors)
        return BaseSerializer.serialize_iterable(response.data, ["name"])

    def add_items_to_subset(
        self, project: NotEmptyStr | int, subset: NotEmptyStr, items: list[dict]
    ):
        """Associates selected items with a given subset. Non-existing subset will be automatically created.

        :param project: The name or ID of the project.
        :type project: Union[str, int]

        :param subset: a name of an existing/new subset to associate items with.
            New subsets will be automatically created.
        :type subset: str

        :param items: list of items metadata.
            Required keys are 'name' and 'path' if the 'id' key is not provided in the dict.
        :type items: list of dicts

        :return: dictionary with succeeded, skipped, and failed items lists.
        :rtype: dict

        Request Example:
        ::

            sa_client = SAClient()

            # option 1
            queried_items = sa_client.explore.query(
                project="Image Project",
                query='_status = "InProgress"'
            )

            sa_client.explore.add_items_to_subset(
                project="Medical Annotations",
                subset="Brain Study - Disapproved",
                items=queried_items
            )

            # option 2
            items_list = [
                {
                    'name': 'image_1.jpeg',
                    'path': 'Image Project'
                },
                {
                    'name': 'image_2.jpeg',
                    'path': 'Image Project/Subfolder A'
                }
            ]

            sa_client.explore.add_items_to_subset(
                project="Image Project",
                subset="Subset Name",
                items=items_list
            )

        Response Example:
        ::

            {
                "succeeded": [
                    {
                        'name': 'image_1.jpeg',
                        'path': 'Image Project'
                    },
                    {
                        'name': 'image_2.jpeg',
                        'path': 'Image Project/Subfolder A'
                    }
                ],
                "failed": [],
                "skipped": []
            }
        """
        project = self.controller.get_project(project)
        response = self.controller.subsets.add_items(project, subset, items)
        if response.errors:
            raise AppException(response.errors)
        return response.data
