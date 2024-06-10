import threading
import time
from typing import Optional

from ldclient import Config
from ldclient.integrations.test_data import TestData
from ldclient.interfaces import UpdateProcessor, DataSourceUpdateSink, DataSourceState, DataSourceErrorInfo, \
    DataSourceErrorKind
from ldclient.versioned_data_kind import FEATURES


class FailingDataSource(UpdateProcessor):
    def __init__(self, config: Config, store, ready: threading.Event):
        self._data_source_update_sink: Optional[DataSourceUpdateSink] = config.data_source_update_sink
        self._ready = ready

    def start(self):
        if self._data_source_update_sink is None:
            return

        self._ready.set()

        self._data_source_update_sink.update_status(
            DataSourceState.OFF,
            DataSourceErrorInfo(
                DataSourceErrorKind.ERROR_RESPONSE,
                401,
                time.time(),
                str("Bad things")
            )
        )

    def stop(self):
        pass

    def is_alive(self):
        return False

    def initialized(self):
        return False


class DelayedFailingDataSource(UpdateProcessor):
    def __init__(self, config: Config, store, ready: threading.Event):
        self._data_source_update_sink: Optional[DataSourceUpdateSink] = config.data_source_update_sink
        self._ready = ready

    def start(self):
        if self._data_source_update_sink is None:
            return

        self._ready.set()

        def data_source_failure():
            self._data_source_update_sink.update_status(
                DataSourceState.OFF,
                DataSourceErrorInfo(
                    DataSourceErrorKind.ERROR_RESPONSE,
                    401,
                    time.time(),
                    str("Bad things")
                )
            )

        threading.Timer(0.1, data_source_failure).start()

    def stop(self):
        pass

    def is_alive(self):
        return False

    def initialized(self):
        return False


class StaleDataSource(UpdateProcessor):
    def __init__(self, config: Config, store, ready: threading.Event):
        self._data_source_update_sink: Optional[DataSourceUpdateSink] = config.data_source_update_sink
        self._ready = ready

    def start(self):
        self._ready.set()
        self._data_source_update_sink.update_status(DataSourceState.VALID, None)

        def data_source_interrupted():
            self._data_source_update_sink.update_status(
                DataSourceState.INTERRUPTED,
                DataSourceErrorInfo(
                    DataSourceErrorKind.ERROR_RESPONSE,
                    408,
                    time.time(),
                    str("Less bad things")
                )
            )

        threading.Timer(0.1, data_source_interrupted).start()

    def stop(self):
        pass

    def is_alive(self):
        return False

    def initialized(self):
        return True


class UpdatingDataSource(UpdateProcessor):
    def __init__(self, config: Config, store, ready: threading.Event):
        self._data_source_update_sink: Optional[DataSourceUpdateSink] = config.data_source_update_sink
        self._ready = ready

    def start(self):
        self._ready.set()
        self._data_source_update_sink.init({})
        self._data_source_update_sink.update_status(DataSourceState.VALID, None)

        def update_data():
            # The test_data_source is only used to access the flag builder.
            # We call _build here, once TestData supports change handlers we should remove this.
            self._data_source_update_sink.upsert(FEATURES,
                                                 TestData().data_source().flag("potato").on(True)._build(1))

        threading.Timer(0.1, update_data).start()

    def stop(self):
        pass

    def is_alive(self):
        return False

    def initialized(self):
        return True
