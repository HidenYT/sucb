import pytest
import requests
from pytest_mock import MockerFixture

from sucb.base import BaseCircuitBreaker, CBException, CBSettings, State


class MockCBSettings(CBSettings):
    pass


class MockCB(BaseCircuitBreaker[MockCBSettings]):
    def _go_closed_to_open(self) -> bool:
        return True

    def _go_half_open_to_closed(self) -> bool:
        return True

    def _go_half_open_to_open(self) -> bool:
        return True

    def _go_open_to_half_open(self) -> bool:
        return True

    def _on_fail(self) -> None:
        pass

    def _on_success(self) -> None:
        pass

    def _on_state_changed(self) -> None:
        pass


@pytest.fixture()
def mock_cb_settings():
    return MockCBSettings((requests.ReadTimeout,))


@pytest.fixture(params=[State.CLOSED])
def state(request):
    return request.param


@pytest.fixture()
def mock_cb(state, mock_cb_settings):
    return MockCB(mock_cb_settings, state)


def create_func_with_cb_decor(cb, inner_func=lambda: ..., exception=None):
    @cb.with_cb
    def inner():
        if exception is not None:
            raise exception
        exception2 = exception
        inner_func()

    return inner


class TestBaseCircuitBreaker:
    def test_set_state_go_closed_to_open(self, mock_cb: MockCB, mocker: MockerFixture):
        mocker.patch.object(mock_cb, "_go_closed_to_open", return_value=True)

        mock_cb._set_state()

        assert mock_cb._state is State.OPEN

    def test_set_state_stay_closed(self, mock_cb: MockCB, mocker: MockerFixture):
        mocker.patch.object(mock_cb, "_go_closed_to_open", return_value=False)

        mock_cb._set_state()

        assert mock_cb._state is State.CLOSED

    @pytest.mark.parametrize("state", [State.OPEN], indirect=True)
    def test_set_state_stay_open(self, mock_cb: MockCB, mocker: MockerFixture):
        mocker.patch.object(mock_cb, "_go_open_to_half_open", return_value=False)

        mock_cb._set_state()

        assert mock_cb._state is State.OPEN

    @pytest.mark.parametrize("state", [State.OPEN], indirect=True)
    def test_set_state_go_open_to_half_open(
        self, mock_cb: MockCB, mocker: MockerFixture
    ):
        mocker.patch.object(mock_cb, "_go_open_to_half_open", return_value=True)

        mock_cb._set_state()

        assert mock_cb._state is State.HALF_OPEN

    @pytest.mark.parametrize("state", [State.HALF_OPEN], indirect=True)
    def test_set_state_stay_half_open(self, mock_cb: MockCB, mocker: MockerFixture):
        mocker.patch.object(mock_cb, "_go_half_open_to_closed", return_value=False)
        mocker.patch.object(mock_cb, "_go_half_open_to_open", return_value=False)

        mock_cb._set_state()

        assert mock_cb._state is State.HALF_OPEN

    @pytest.mark.parametrize("state", [State.HALF_OPEN], indirect=True)
    def test_set_state_go_half_open_to_open(
        self, mock_cb: MockCB, mocker: MockerFixture
    ):
        mocker.patch.object(mock_cb, "_go_half_open_to_closed", return_value=False)
        mocker.patch.object(mock_cb, "_go_half_open_to_open", return_value=True)

        mock_cb._set_state()

        assert mock_cb._state is State.OPEN

    @pytest.mark.parametrize("state", [State.HALF_OPEN], indirect=True)
    def test_set_state_go_half_open_to_closed(
        self, mock_cb: MockCB, mocker: MockerFixture
    ):
        mocker.patch.object(mock_cb, "_go_half_open_to_closed", return_value=True)
        mocker.patch.object(mock_cb, "_go_half_open_to_open", return_value=False)

        mock_cb._set_state()

        assert mock_cb._state is State.CLOSED

    @pytest.mark.parametrize("state", [State.CLOSED, State.HALF_OPEN], indirect=True)
    def test_make_request_closed_ok(self, mock_cb: MockCB, mocker: MockerFixture):
        mocker.patch.object(mock_cb, "_set_state")
        mocker.patch.object(mock_cb, "_on_success")

        with mock_cb.make_request():
            a = 1 + 5 / 2

        mock_cb._on_success.assert_called_once()
        mock_cb._set_state.assert_called_once()

    @pytest.mark.parametrize("state", [State.CLOSED, State.HALF_OPEN], indirect=True)
    def test_make_request_closed_not_expected_exception(
        self, mock_cb: MockCB, mocker: MockerFixture
    ):
        mocker.patch.object(mock_cb, "_set_state")
        mocker.patch.object(mock_cb, "_on_fail")

        with pytest.raises(requests.ReadTimeout):
            with mock_cb.make_request():
                raise requests.ReadTimeout

        mock_cb._on_fail.assert_called_once()
        mock_cb._set_state.assert_called_once()

    @pytest.mark.parametrize("state", [State.CLOSED, State.HALF_OPEN], indirect=True)
    def test_make_request_closed_exception(
        self, mock_cb: MockCB, mocker: MockerFixture
    ):
        mocker.patch.object(mock_cb, "_set_state")
        mocker.patch.object(mock_cb, "_on_fail")

        with pytest.raises(Exception):
            with mock_cb.make_request():
                raise Exception

        mock_cb._on_fail.assert_not_called()
        mock_cb._set_state.assert_called_once()

    @pytest.mark.parametrize("state", [State.OPEN], indirect=True)
    def test_make_request_open_ok(self, mock_cb: MockCB, mocker: MockerFixture):
        mock_obj = mocker.Mock()
        mocker.patch.object(mock_cb, "_set_state")

        with pytest.raises(CBException):
            with mock_cb.make_request():
                mock_obj()

        mock_obj.assert_not_called()
        mock_cb._set_state.assert_called_once()

    @pytest.mark.parametrize("state", [State.OPEN], indirect=True)
    @pytest.mark.parametrize(
        "exception", [Exception, requests.ReadTimeout, requests.exceptions.HTTPError]
    )
    def test_make_request_open_exception(
        self, mock_cb: MockCB, mocker: MockerFixture, exception
    ):
        mocker.patch.object(mock_cb, "_set_state")

        with pytest.raises(CBException):
            with mock_cb.make_request():
                raise exception

        mock_cb._set_state.assert_called_once()

    @pytest.mark.parametrize("state", [State.CLOSED, State.HALF_OPEN], indirect=True)
    def test_with_cb_closed_ok(self, mock_cb: MockCB, mocker: MockerFixture):
        mocker.patch.object(mock_cb, "_set_state")
        mocker.patch.object(mock_cb, "_on_success")
        func = create_func_with_cb_decor(mock_cb)

        func()

        mock_cb._on_success.assert_called_once()
        mock_cb._set_state.assert_called_once()

    @pytest.mark.parametrize("state", [State.CLOSED, State.HALF_OPEN], indirect=True)
    def test_with_cb_closed_exception(self, mock_cb: MockCB, mocker: MockerFixture):
        mocker.patch.object(mock_cb, "_set_state")
        mocker.patch.object(mock_cb, "_on_fail")
        func = create_func_with_cb_decor(mock_cb, exception=requests.ReadTimeout)

        with pytest.raises(requests.ReadTimeout):
            func()

        mock_cb._on_fail.assert_called_once()
        mock_cb._set_state.assert_called_once()

    @pytest.mark.parametrize("state", [State.CLOSED, State.HALF_OPEN], indirect=True)
    def test_with_cb_closed_not_expected_exception(
        self, mock_cb: MockCB, mocker: MockerFixture
    ):
        mocker.patch.object(mock_cb, "_set_state")
        mocker.patch.object(mock_cb, "_on_fail")
        func = create_func_with_cb_decor(mock_cb, exception=Exception)

        with pytest.raises(Exception):
            func()

        mock_cb._on_fail.assert_not_called()
        mock_cb._set_state.assert_called_once()

    @pytest.mark.parametrize("state", [State.OPEN], indirect=True)
    def test_with_cb_open_ok(self, mock_cb: MockCB, mocker: MockerFixture):
        mock_obj = mocker.Mock()
        mocker.patch.object(mock_cb, "_set_state")
        func = create_func_with_cb_decor(mock_cb, inner_func=mock_obj)

        with pytest.raises(CBException):
            func()

        mock_obj.assert_not_called()
        mock_cb._set_state.assert_called_once()

    @pytest.mark.parametrize("state", [State.OPEN], indirect=True)
    @pytest.mark.parametrize(
        "exception", [Exception, requests.ReadTimeout, requests.exceptions.HTTPError]
    )
    def test_with_cb_open_exception(
        self, mock_cb: MockCB, mocker: MockerFixture, exception
    ):
        mocker.patch.object(mock_cb, "_set_state")
        func = create_func_with_cb_decor(mock_cb, exception=exception)

        with pytest.raises(CBException):
            func()

        mock_cb._set_state.assert_called_once()
