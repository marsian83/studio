import logging
import math
import uuid

from celery import states
from celery.app.task import Task
from celery.result import AsyncResult

from contentcuration.utils.sentry import report_exception


logger = logging.getLogger(__name__)


class ProgressTracker:
    """
    Helper to track task progress
    """
    __slots__ = ("task_id", "send_event", "total", "progress", "last_reported_progress")

    def __init__(self, task_id, send_event):
        """
        :param task_id: The ID of the calling task
        :param send_event: Callback to send the task event
        :type send_event: Callable
        """
        self.task_id = task_id
        self.send_event = send_event
        self.total = 100.0
        self.progress = 0.0
        self.last_reported_progress = 0.0

    def set_total(self, total):
        """
        :param total: The amount for which progress is deemed 100%, defaults to 100
        """
        self.total = total

    def increment(self, increment=1.0):
        """
        Increments and triggers tracking of the progress to the task meta
        """
        self.track(self.progress + increment)

    def track(self, progress):
        """
        :param progress: The current progress amount
        """
        self.progress = progress

        # only update the task progress in >=1% increments
        if math.floor(self.last_reported_progress) < math.floor(self.task_progress):
            self.last_reported_progress = self.task_progress
            self.send_event(progress=self.task_progress)

    @property
    def task_progress(self):
        return int(min((100.0 * self.progress / self.total), 100.0))


def get_task_model(ref, task_id):
    """
    Returns the task model for a task, will create one if not found
    :rtype: contentcuration.models.TaskResult
    """
    return ref.backend.TaskModel.objects.get_task(task_id)


class CeleryTask(Task):
    """
    This is set as the Task class on our Celery app, so to track progress on a task, mark it
    when decorating the task:
    ```
        @app.task(bind=True, track_progress=True)
        def my_task(self):
            progress = self.get_progress_tracker()
            progress.increment()
    ```
    """
    # by default, celery does not track task starting itself
    track_started = True
    send_events = True

    # ensure our tasks are restarted if they're interrupted
    acks_late = True
    acks_on_failure_or_timeout = True
    reject_on_worker_lost = True

    @property
    def TaskModel(self):
        """
        :rtype: contentcuration.models.TaskResult
        """
        return self.backend.TaskModel

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """
        Report task failures to sentry as long as the exception is not one of the types for which it should `autoretry`
        """
        if not getattr(self, "autoretry_for", None) or not isinstance(exc, self.autoretry_for):
            report_exception(exc)

    def shadow_name(self, *args, **kwargs):
        """
        DO NOT add functionality here as that will make it impossible to rely on `.name` for finding task by name in the
        result backend
        """
        return super(CeleryTask, self).shadow_name(*args, **kwargs)

    def find_ids(self, channel_id=None, **kwargs):
        """
        :param channel_id:
        :param kwargs: Keyword arguments sent to the task, which will be matched against
        :return: A TaskResult queryset
        :rtype: django.db.models.query.QuerySet
        """
        task_qs = self.TaskModel.objects.filter(task_name=self.name)

        # add channel filter since we have dedicated field
        if channel_id:
            task_qs = task_qs.filter(channel_id=channel_id)
        else:
            task_qs = task_qs.filter(channel_id__isnull=True)

        # search for task args in values
        for value in kwargs.values():
            task_qs = task_qs.filter(task_kwargs__contains=self.backend.encode(value))

        return task_qs.values_list("task_id", flat=True)

    def find_incomplete_ids(self, channel_id=None, **kwargs):
        """
        :param channel_id:
        :param kwargs:
        :return: A TaskResult queryset
        :rtype: django.db.models.query.QuerySet
        """
        return self.find_ids(channel_id=channel_id, **kwargs).exclude(status__in=states.READY_STATES)

    def fetch(self, task_id):
        """
        Gets the result object for a task, assuming it was called async
        :param task_id: The hex task ID
        :return: A CeleryAsyncResult
        :rtype: CeleryAsyncResult
        """
        return self.AsyncResult(task_id)

    def _fetch_match(self, task_id, **kwargs):
        """
        Gets the result object for a task, assuming it was called async, and ensures it was called with kwargs and
        assumes that kwargs is has been decoded from an prepared form
        :param task_id: The hex task ID
        :param kwargs: The kwargs the task was called with, which must match when fetching
        :return: A CeleryAsyncResult
        :rtype: CeleryAsyncResult
        """
        async_result = self.fetch(task_id)
        # the task kwargs are serialized in the DB so just ensure that args actually match
        if async_result.kwargs == kwargs:
            return async_result
        return None

    def _prepare_kwargs(self, kwargs):
        return self.backend.encode({
            key: str(value) if isinstance(value, uuid.UUID) else value
            for key, value in kwargs.items()
        })

    def enqueue(self, user, **kwargs):
        """
        Enqueues the task called with `kwargs`, and requires the user who wants to enqueue it. If `channel_id` is
        passed to the function, that will be set on the TaskResult model as well.

        :param user: User object of the user performing the operation
        :param kwargs: Keyword arguments for task `apply_async`
        :return: The celery async result
        :rtype: CeleryAsyncResult
        """
        from contentcuration.models import User

        if user is None or not isinstance(user, User):
            raise TypeError("All tasks must be assigned to a user.")

        task_id = uuid.uuid4().hex
        prepared_kwargs = self._prepare_kwargs(kwargs)
        transcoded_kwargs = self.backend.decode(prepared_kwargs)
        channel_id = transcoded_kwargs.get("channel_id")

        logging.info(f"Enqueuing task:id {self.name}:{task_id} for user:channel {user.pk}:{channel_id} | {prepared_kwargs}")

        # returns a CeleryAsyncResult
        async_result = self.apply_async(
            task_id=task_id,
            kwargs=transcoded_kwargs,
        )

        # ensure the result is saved to the backend (database)
        self.backend.add_pending_result(async_result)

        # after calling apply, we should have task result model, so get it and set our custom fields
        task_result = get_task_model(self, task_id)
        task_result.task_name = self.name
        task_result.task_kwargs = prepared_kwargs
        task_result.user = user
        task_result.channel_id = channel_id
        task_result.save()
        return async_result

    def fetch_or_enqueue(self, user, **kwargs):
        """
        Fetches an existing incomplete task or enqueues one if not found, called with `kwargs`, and requires the user
        who wants to enqueue it. If `channel_id` is passed to the function, that will be set on the TaskResult model

        :param user: User object of the user performing the operation
        :param kwargs: Keyword arguments for task `apply_async`
        :return: The celery async result
        :rtype: CeleryAsyncResult
        """
        # if we're eagerly executing the task (synchronously), then we shouldn't check for an existing task because
        # implementations probably aren't prepared to rely on an existing asynchronous task
        if not self.app.conf.task_always_eager:
            transcoded_kwargs = self.backend.decode(self._prepare_kwargs(kwargs))
            task_ids = self.find_incomplete_ids(**transcoded_kwargs).order_by("date_created")[:1]
            if task_ids:
                async_result = self._fetch_match(task_ids[0], **transcoded_kwargs)
                if async_result:
                    logging.info(f"Fetched matching task {self.name} for user {user.pk} with id {async_result.id} | {kwargs}")
                    return async_result
        logging.info(f"Didn't fetch matching task {self.name} for user {user.pk} | {kwargs}")
        return self.enqueue(user, **kwargs)

    def requeue(self, **kwargs):
        """
        Re-enqueues the same task, during execution of the task, with the same arguments
        :param kwargs: Keyword arguments to override the original arguments
        :return: The celery async result
        :rtype: CeleryAsyncResult
        """
        request = self.request
        if request is None:
            raise NotImplementedError("This method should only be called within the execution of a task")
        task_result = get_task_model(self, request.id)
        task_kwargs = request.kwargs.copy()
        task_kwargs.update(kwargs)
        logging.info(f"Re-queuing task {self.name} for user {task_result.user.pk} from {request.id} | {task_kwargs}")
        return self.enqueue(task_result.user, **task_kwargs)

    def revoke(self, exclude_task_ids=None, **kwargs):
        """
        Revokes and terminates all unready tasks matching the kwargs
        :param exclude_task_ids: Any task ids to exclude from this behavior
        :param kwargs: Task keyword arguments that will be used to match against tasks
        :return: The number of tasks revoked
        """
        task_ids = self.find_incomplete_ids(**self.backend.decode(self._prepare_kwargs(kwargs)))
        if exclude_task_ids is not None:
            task_ids = task_ids.exclude(task_id__in=task_ids)
        count = 0
        for task_id in task_ids:
            logging.info(f"Revoking task {task_id}")
            self.app.control.revoke(task_id, terminate=True)
            count += 1
        # be sure the database backend has these marked appropriately
        self.TaskModel.objects.filter(task_id__in=task_ids).update(status=states.REVOKED)
        return count


class CeleryAsyncResult(AsyncResult):
    """
    Custom result class which has access to task data stored in the backend

    The properties access additional properties in the same manner as super properties,
    and our custom properties are added to the meta via TaskResultCustom.as_dict()
    """
    def get_model(self):
        """
        :return: The TaskResult model object
        :rtype: contentcuration.models.TaskResult
        """
        return get_task_model(self, self.task_id)

    @property
    def user_id(self):
        return self._get_task_meta().get('user_id')

    @property
    def channel_id(self):
        return self._get_task_meta().get('channel_id')

    @property
    def progress(self):
        return self._get_task_meta().get('progress')
