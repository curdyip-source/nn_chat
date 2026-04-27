from contextvars import ContextVar


_request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)
_client_ip_ctx: ContextVar[str | None] = ContextVar("client_ip", default=None)
_user_agent_ctx: ContextVar[str | None] = ContextVar("user_agent", default=None)
_user_id_ctx: ContextVar[str | None] = ContextVar("user_id", default=None)


def set_request_context(*, request_id: str | None, client_ip: str | None, user_agent: str | None) -> tuple:
    request_id_token = _request_id_ctx.set(request_id)
    client_ip_token = _client_ip_ctx.set(client_ip)
    user_agent_token = _user_agent_ctx.set(user_agent)
    user_id_token = _user_id_ctx.set(None)
    return request_id_token, client_ip_token, user_agent_token, user_id_token


def reset_request_context(tokens: tuple) -> None:
    request_id_token, client_ip_token, user_agent_token, user_id_token = tokens
    _request_id_ctx.reset(request_id_token)
    _client_ip_ctx.reset(client_ip_token)
    _user_agent_ctx.reset(user_agent_token)
    _user_id_ctx.reset(user_id_token)


def set_current_user_id(user_id: int | str | None) -> None:
    _user_id_ctx.set(str(user_id) if user_id is not None else None)


def get_request_context() -> dict[str, str | None]:
    return {
        "request_id": _request_id_ctx.get(),
        "ip_address": _client_ip_ctx.get(),
        "user_agent": _user_agent_ctx.get(),
        "user_id": _user_id_ctx.get(),
    }