from asyncio import StreamWriter

def success(request: str):
    return "\n".join([
        "BEGIN",
        request,
        "SUCCESS",
        "END",
        ""]) #extra newline at end

def error(request: str, error: str):
    return "\n".join([
        "BEGIN",
        request,
        "ERROR",
        "DATA",
        "1",
        error,
        "END",
        ""]) #extra newline at end

def data(request: str, data: list):
    parts = ["BEGIN", request, "SUCCESS", "DATA", str(len(data))] + data + ["END", ""]
    return "\n".join(parts)

